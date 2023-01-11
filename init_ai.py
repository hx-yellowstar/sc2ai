import re
import cv2
import sys
import time
import random
import traceback
import numpy as np

from sc2 import maps
from sc2.main import run_game, BotAI
from sc2.data import Race, Difficulty, Result
from sc2.player import Bot, Computer, Human
from sc2.constants import UnitTypeId, UpgradeId, AbilityId, BuffId

from sc2ai_lib import *
from status_check import StatusCheck
from battle_strategy import BattleStrategy
from development import DevelopMent

from custom_logger import output_log


class SimpleAI(BotAI):
    def __init__(self):
        super().__init__()
        self.battle_strategy = BattleStrategy(self)
        self.develop_strategy = DevelopMent(self)
        self.status_check = StatusCheck(self)
        self.first_supplydepot_position = None
        self.current_second = 0         # 目前游戏进行的秒数
        self.step_count = 0
        self.train_data = []
        self.current_enemy_force_num = 0
        self.current_total_friendly_unit_health = 0

    async def find_first_building_position(self):
        if self.first_supplydepot_position is not None:
            return
        command_center = self.structures(UnitTypeId.COMMANDCENTER).first
        near = command_center.position.to2
        p = await self.find_placement(UnitTypeId.SUPPLYDEPOT, near.rounded, 100, True, 2)
        mineral_fields = self.mineral_field.ready
        closest_dist = mineral_fields.closest_distance_to(p)
        output_log('closest distance: {0}'.format(closest_dist))
        output_log(type(closest_dist))
        if closest_dist < 10:
            output_log('too close to mineral')
            return
        if self.first_supplydepot_position is None:
            output_log('log depot_position')
            self.first_supplydepot_position = p

    def on_end(self, game_result: Result):
        print('------game_result------')
        print(game_result)
        if game_result == Result.Victory:
            print('Result is victory')
            np.save("train_data/{}.npy".format(str(int(time.time()))), np.array(self.train_data))
        print('-----------------------')

    async def on_step(self, iteration: int):
        await self.distribute_workers()
        await self.find_first_building_position()
        await self.eco_development()
        await self.figuring_supply()
        await self.build_gas_station()
        await self.development()
        await self.record_speicfic_unit_orders()
        await self.manufacture_battle_unit()
        await self.do_upgrade()
        await self.move_and_attack()
        await self.scout()
        await self.drawing()
        await self.show_unit_status()

    async def drawing(self):
        game_data = np.zeros((self.game_info.map_size[1], self.game_info.map_size[0], 3), np.uint8)
        for unit in self.battle_strategy.get_all_friendly_unit():
            unit_position = unit.position
            cv2.circle(game_data, (int(unit_position[0]), int(unit_position[1])), 1, (255, 0, 0), -1)
        for unit in self.battle_strategy.get_all_enemy_visible_unit():
            unit_position = unit.position
            cv2.circle(game_data, (int(unit_position[0]), int(unit_position[1])), 1, (0, 0, 255), -1)
        for unit in self.battle_strategy.get_all_friendly_building():
            unit_position = unit.position
            cv2.circle(game_data, (int(unit_position[0]), int(unit_position[1])), 2, (255, 0, 0), -1)
        for unit in self.battle_strategy.get_all_enemy_building():
            unit_position = unit.position
            cv2.circle(game_data, (int(unit_position[0]), int(unit_position[1])), 2, (0, 0, 255), -1)
        flipped = cv2.flip(game_data, 0)
        show_data = cv2.resize(flipped, dsize=None, fx=2, fy=2)
        if sys.platform == 'win32':
            cv2.imshow('mapping', show_data)
        else:
            cv2.imwrite('battleminimap/mapping.jpg', show_data)
        cv2.waitKey(1)

    async def development(self):
        await self.develop_strategy.decide_which_building_to_build()

    async def eco_development(self):
        # 发展经济，制造scv，变形星轨或行星要塞，砸矿骡
        for commandcenter in self.structures.of_type([UnitTypeId.COMMANDCENTER, UnitTypeId.ORBITALCOMMAND, UnitTypeId.PLANETARYFORTRESS]):
            target_workers_num = len({mineral.tag for mineral in self.mineral_field if mineral.distance_to(commandcenter) <= 8}) * 2 + 6
            if self.status_check.get_building_or_unit_num(UnitTypeId.SCV) < target_workers_num:
                if self.can_afford(UnitTypeId.SCV):
                    if commandcenter.is_idle:
                        commandcenter.train(UnitTypeId.SCV)
                        time.sleep(0.1)

    async def figuring_supply(self):
        for supply_depot in self.units(UnitTypeId.SUPPLYDEPOT).ready:
            supply_depot(AbilityId.MORPH_SUPPLYDEPOT_LOWER)
        if self.status_check.supply_remaining_intense():
            if self.can_afford(UnitTypeId.SUPPLYDEPOT):
                if self.status_check.there_has_valid_supplydepot():
                    if self.battle_strategy.order_execute_num_in_scv('SupplyDepot') < 1:
                        print('build a supplydepot near the supplydepot which furthest to the commandcenter')
                        await self.develop_strategy.building_with_position_related_to_supplydepot(UnitTypeId.SUPPLYDEPOT)
                elif self.status_check.check_if_valid_building_exists(UnitTypeId.COMMANDCENTER):
                    print('build first supplydepot near command center')
                    if self.first_supplydepot_position is not None:
                        output_log('find_position:{0}'.format(self.first_supplydepot_position))
                        await self.build(UnitTypeId.SUPPLYDEPOT, near=self.first_supplydepot_position, max_distance=1)
                    else:
                        output_log('still not found depot position, using a default')
                        await self.build(UnitTypeId.SUPPLYDEPOT, self.units(UnitTypeId.COMMANDCENTER).ready.first, max_distance=20)
                else:
                    return

    async def build_gas_station(self):
        if self.status_check.get_building_or_unit_num(UnitTypeId.BARRACKS) < 1:
            return
        for commandcenter in self.units(UnitTypeId.COMMANDCENTER).ready:
            vespenes = self.vespene_geyser.closer_than(10.0, commandcenter)
            output_log('there is {0} available vespenes'.format(vespenes.amount))
            for vespene in vespenes:
                if not self.units(UnitTypeId.REFINERY).closer_than(1.0, vespene).exists:
                    output_log('there is valid vespene exists')
                    if not self.can_afford(UnitTypeId.REFINERY):
                        break
                    worker = self.select_build_worker(vespene.position)
                    if worker is None:
                        break
                    if not self.units(UnitTypeId.REFINERY).closer_than(1.0, vespene).exists:
                        worker.build(UnitTypeId.REFINERY, vespene.position)

    async def manufacture_battle_unit(self):
        if self.status_check.get_building_or_unit_num(UnitTypeId.FACTORY) <= 1:
            for barracks in self.units(UnitTypeId.BARRACKS).ready:
                if self.status_check.get_building_or_unit_num(UnitTypeId.MARINE) < 20:
                    if self.can_afford(UnitTypeId.MARINE) and barracks.is_idle:
                        barracks.train(UnitTypeId.MARINE)
                        time.sleep(0.1)
                elif self.status_check.check_if_valid_building_exists(UnitTypeId.FACTORY):
                    output_log('current has valid factory')
                    if self.status_check.get_building_or_unit_num(UnitTypeId.STARPORT) >= 1:
                        output_log('starport built')
                        if barracks.has_add_on == 1:
                            output_log('there is a barracks had add-on')
                            if self.status_check.get_building_or_unit_num(UnitTypeId.MARAUDER) < 3:
                                output_log('now marauder num is less than 3')
                                if self.can_afford(UnitTypeId.MARAUDER):
                                    if sys.platform == 'win32':
                                        barracks.train(UnitTypeId.MARAUDER)
                                        # barracks(AbilityId.BARRACKSTRAIN_MARAUDER)
                                    else:
                                        barracks(AbilityId.BARRACKSTRAIN_MARAUDER)
                                        # barracks(UnitTypeId.MARAUDER)
                                    time.sleep(0.1)
                            elif self.can_afford(UnitTypeId.MARINE):
                                barracks.train(UnitTypeId.MARINE)
                                time.sleep(0.1)
                        else:
                            if self.can_afford(UnitTypeId.MARINE):
                                barracks.train(UnitTypeId.MARINE)
                                time.sleep(0.1)
        target_medivac_num = round((self.status_check.get_building_or_unit_num(UnitTypeId.MARINE)+self.status_check.get_building_or_unit_num(UnitTypeId.MARAUDER))/5)
        if self.status_check.check_if_valid_building_exists(UnitTypeId.STARPORT):
            if self.status_check.get_building_or_unit_num(UnitTypeId.MEDIVAC) < target_medivac_num:
                for starport in self.units(UnitTypeId.STARPORT).ready:
                    if self.can_afford(UnitTypeId.MEDIVAC) and starport.is_idle:
                        starport.train(UnitTypeId.MEDIVAC)

    async def scout(self):
        if not self.enemy_structures and not self.enemy_units:
            if self.status_check.check_if_valid_building_exists(UnitTypeId.BARRACKS):
                if self.battle_strategy.order_execute_num_in_scv('move') < 1:
                    scout_scv = self.units(UnitTypeId.SCV).ready.first
                    for position in self.enemy_start_locations:
                        output_log('scout scv move to {0}'.format(position))
                        scout_scv.move(position)
                        time.sleep(0.1)

    async def do_upgrade(self):
        for addon in self.units(UnitTypeId.BARRACKSTECHLAB).ready:
            if not addon.is_idle:
                continue
            output_log('start check possible available addon')
            current_upgrades = self.state.upgrades
            output_log('current upgrades: {0}'.format(current_upgrades))
            if self.can_afford(AbilityId.BARRACKSTECHLABRESEARCH_STIMPACK):
                if UpgradeId.STIMPACK not in current_upgrades:
                    addon(AbilityId.BARRACKSTECHLABRESEARCH_STIMPACK)
                else:
                    output_log('stimpack already upgraded')
            if self.can_afford(AbilityId.RESEARCH_COMBATSHIELD):
                if UpgradeId.SHIELDWALL not in current_upgrades:
                    addon(AbilityId.RESEARCH_COMBATSHIELD)
                else:
                    output_log('combatshield already upgraded')
        else:
            output_log('there is no available techlab')

    async def move_and_attack(self):
        output_log('type of enemy units property: {0}'.format(type(self.enemy_units)))
        for medivac in self.units(UnitTypeId.MEDIVAC):
            if not medivac.is_attacking:
                all_battle_units = self.battle_strategy.get_all_friendly_battle_unit()
                if all_battle_units:
                    medivac.attack(all_battle_units.furthest_to(self.units(UnitTypeId.COMMANDCENTER).ready.first))
                else:
                    medivac.attack(random.choice(self.units(UnitTypeId.COMMANDCENTER).ready))
        if self.battle_strategy.get_friendly_battle_unit().amount == 0:
            return
        for unit in self.battle_strategy.get_friendly_battle_unit():
            current_around_status = self.battle_strategy.get_unit_around_status(unit)
            choice_num = random.randint(1, 6)
            current_total_health = self.status_check.get_current_friendly_unit_health()
            current_enemy_num = self.battle_strategy.get_visible_enemy_battle_unit_or_building().amount
            if current_enemy_num == self.current_enemy_force_num and current_total_health >= self.current_total_friendly_unit_health:
                self.current_total_friendly_unit_health = current_total_health
                if unit.is_idle is False:
                    continue
            self.current_enemy_force_num = current_enemy_num
            self.current_total_friendly_unit_health = current_total_health
            if choice_num == 1:
                nearest_unit = self.battle_strategy.get_nearest_enemy_unit(unit)
                if nearest_unit is not None:
                    unit.attack(nearest_unit)
            elif choice_num == 2:
                target_enemy = self.battle_strategy.get_highest_dps_enemy_unit(unit)
                if target_enemy is not None:
                    unit.attack(target_enemy)
            elif choice_num == 3:
                regroup_point = self.battle_strategy.get_regroup_point()
                unit.move(regroup_point)
            elif choice_num == 4:
                if len(self.enemy_structures) > 0:
                    unit.attack(random.choice(self.enemy_structures))
            elif choice_num == 5:
                try:
                    unit.move(self.units(UnitTypeId.COMMANDCENTER).ready.first)
                except Exception as e:
                    print(e)
            else:
                continue
            self.train_data.append([choice_num, current_around_status])

    async def record_speicfic_unit_orders(self):
        for scv_unit in self.units(UnitTypeId.SCV).ready:
            first_order = get_unit_first_order(scv_unit)
            if first_order not in ['Gather', 'ReturnCargo']:
                output_log('new scv order: {0}'.format(first_order))
        for marine in self.units(UnitTypeId.MARINE).ready:
            first_order = get_unit_first_order(marine)
            output_log('new marine order: {0}'.format(first_order))

    async def show_unit_status(self):
        self.step_count += 1
        if self.step_count % 1000 == 0:
            print('MARAUDER NUM: {0}'.format(self.status_check.get_building_or_unit_num(UnitTypeId.MARAUDER)))


def start():
    game_result = run_game(maps.get("EphemeronLE"), [Bot(Race.Terran, SimpleAI()), Computer(Race.Random, Difficulty.Easy)], realtime=True)
    print('game_result: {0}'.format(game_result))
    return game_result


if __name__ == '__main__':
    start()
