import re
import cv2
import sys
import time
import random
import traceback
import numpy as np

from sc2 import run_game, maps, Race, Difficulty, Result
from sc2.player import Bot, Computer
from sc2.constants import UnitTypeId, UpgradeId, AbilityId, BuffId

from sc2ai_lib import *
from status_check import StatusCheck
from battle_strategy import BattleStrategy
from development import DevelopMent

from custom_logger import output_log


class SimpleAI(StatusCheck, BattleStrategy, DevelopMent):
    def __init__(self):
        super().__init__()
        self.first_supplydepot_position = None
        self.step_count = 0
        self.train_data = []
        self.current_enemy_force_num = 0
        self.current_total_friendly_unit_health = 0

    async def find_first_building_position(self):
        if self.first_supplydepot_position is not None:
            return
        command_center = self.units(UnitTypeId.COMMANDCENTER).ready.first
        near = command_center.position.to2
        p = await self.find_placement(UnitTypeId.SUPPLYDEPOT, near.rounded, 100, True, 2)
        mineral_fields = self.state.mineral_field.ready
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
        await self.add_new_scv()
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
        for unit in self.get_all_friendly_unit():
            unit_position = unit.position
            cv2.circle(game_data, (int(unit_position[0]), int(unit_position[1])), 1, (255, 0, 0), -1)
        for unit in self.get_all_enemy_visible_unit():
            unit_position = unit.position
            cv2.circle(game_data, (int(unit_position[0]), int(unit_position[1])), 1, (0, 0, 255), -1)
        for unit in self.get_all_friendly_building():
            unit_position = unit.position
            cv2.circle(game_data, (int(unit_position[0]), int(unit_position[1])), 2, (255, 0, 0), -1)
        for unit in self.get_all_enemy_building():
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
        if self.check_army_factory_number() <= 3:
            if self.can_afford(UnitTypeId.BARRACKS):
                output_log('can afford barracks now')
                if self.get_building_or_unit_num(UnitTypeId.COMMANDCENTER) >= 2:
                    if (self.get_building_or_unit_num(UnitTypeId.FACTORY) >= 1 and self.get_building_or_unit_num(UnitTypeId.STARPORT) >= 1) or self.get_building_or_unit_num(UnitTypeId.BARRACKS) < 1:
                        if self.get_building_or_unit_num(UnitTypeId.BARRACKS) < 1:
                            if self.there_has_valid_supplydepot():
                                await self.building_with_position_related_to_supplydepot(UnitTypeId.BARRACKS)
                        else:
                            if self.there_has_valid_supplydepot():
                                print('build barracks no.{0}'.format(self.get_building_or_unit_num(UnitTypeId.BARRACKS)))
                                await self.build(UnitTypeId.BARRACKS, near=self.units(UnitTypeId.BARRACKS).ready.first)
                elif self.get_building_or_unit_num(UnitTypeId.BARRACKS) < 1:
                    if self.check_if_valid_building_exists(UnitTypeId.SUPPLYDEPOT) or self.check_if_valid_building_exists(UnitTypeId.SUPPLYDEPOTLOWERED):
                        print('build first barracks')
                        await self.building_with_position_related_to_supplydepot(UnitTypeId.BARRACKS)
            if self.can_afford(UnitTypeId.FACTORY):
                if self.get_building_or_unit_num(UnitTypeId.COMMANDCENTER) >= 2:
                    if self.check_if_valid_building_exists(UnitTypeId.BARRACKS):
                        if self.get_building_or_unit_num(UnitTypeId.FACTORY) < 1:
                            if self.get_building_or_unit_num(UnitTypeId.BARRACKS) >= 1:
                                await self.build(UnitTypeId.FACTORY, near=self.units(UnitTypeId.BARRACKS).ready.furthest_to(self.units(UnitTypeId.COMMANDCENTER).ready.first))
            if self.can_afford(UnitTypeId.STARPORT):
                if self.get_building_or_unit_num(UnitTypeId.COMMANDCENTER) >= 2:
                    if self.check_if_valid_building_exists(UnitTypeId.FACTORY):
                        if self.get_building_or_unit_num(UnitTypeId.FACTORY) >= 1:
                            if self.get_building_or_unit_num(UnitTypeId.STARPORT) < 1:
                                if self.order_execute_num_in_scv('Starport') < 1:
                                    await self.build(UnitTypeId.STARPORT, near=self.units(UnitTypeId.FACTORY).ready.furthest_to(self.units(UnitTypeId.COMMANDCENTER).ready.first))
            if self.get_building_or_unit_num(UnitTypeId.COMMANDCENTER) < 2 and self.can_afford(UnitTypeId.COMMANDCENTER):
                await self.expand_now()
            if self.can_afford(UnitTypeId.BARRACKSTECHLAB):
                for barracks in self.units(UnitTypeId.BARRACKS).ready.noqueue:
                    try:
                        if self.get_building_or_unit_num(UnitTypeId.BARRACKSTECHLAB) < 1 and self.check_army_factory_number() < 5:
                            if barracks.add_on_tag == 0:
                                await self.do(barracks.build(UnitTypeId.BARRACKSTECHLAB))
                        elif self.get_building_or_unit_num(UnitTypeId.BARRACKSTECHLAB) < 2:
                            if barracks.add_on_tag == 0:
                                await self.do(barracks.build(UnitTypeId.BARRACKSTECHLAB))
                    except Exception as e:
                        output_log(e)
            if self.can_afford(UnitTypeId.STARPORTREACTOR):
                for starport in self.units(UnitTypeId.STARPORT).ready.noqueue:
                    try:
                        if self.get_building_or_unit_num(UnitTypeId.STARPORTREACTOR) < 1 and self.check_army_factory_number() < 5:
                            if starport.add_on_tag == 0:
                                await self.do(starport.build(UnitTypeId.STARPORTREACTOR))
                        elif self.get_building_or_unit_num(UnitTypeId.STARPORTREACTOR) < 2:
                            if starport.add_on_tag == 0:
                                await self.do(starport.build(UnitTypeId.STARPORTREACTOR))
                    except Exception as e:
                        output_log('can\'t build starport reactor: {0}'.format(e))
            if self.can_afford(UnitTypeId.FACTORYTECHLAB):
                for starport in self.units(UnitTypeId.FACTORY).ready.noqueue:
                    try:
                        if self.get_building_or_unit_num(UnitTypeId.FACTORYTECHLAB) < 1:
                            await self.do(starport.build(UnitTypeId.FACTORYTECHLAB))
                    except Exception as e:
                        output_log('can\'t build factory reactor: {0}'.format(e))
        else:
            if self.get_building_or_unit_num(UnitTypeId.BARRACKS) <= self.get_building_or_unit_num(UnitTypeId.COMMANDCENTER) * 3:
                if self.there_has_valid_supplydepot():
                    output_log('building more barracks')
                    await self.build(UnitTypeId.BARRACKS, near=self.units(UnitTypeId.BARRACKS).ready.first)

    async def add_new_scv(self):
        for commandcenter in self.units(UnitTypeId.COMMANDCENTER).ready:
            if self.get_building_or_unit_num(UnitTypeId.SCV) < self.get_building_or_unit_num(UnitTypeId.COMMANDCENTER) * 22:
                if self.can_afford(UnitTypeId.SCV):
                    if commandcenter.noqueue:
                        await self.do(commandcenter.train(UnitTypeId.SCV))
                        time.sleep(0.1)

    async def figuring_supply(self):
        for supply_depot in self.units(UnitTypeId.SUPPLYDEPOT).ready:
            await self.do(supply_depot(AbilityId.MORPH_SUPPLYDEPOT_LOWER))
        if self.supply_remaining_intense():
            if self.can_afford(UnitTypeId.SUPPLYDEPOT):
                if self.there_has_valid_supplydepot():
                    if self.order_execute_num_in_scv('SupplyDepot') < 1:
                        print('build a supplydepot near the supplydepot which furthest to the commandcenter')
                        await self.building_with_position_related_to_supplydepot(UnitTypeId.SUPPLYDEPOT)
                elif self.check_if_valid_building_exists(UnitTypeId.COMMANDCENTER):
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
        if self.get_building_or_unit_num(UnitTypeId.BARRACKS) < 1:
            return
        for commandcenter in self.units(UnitTypeId.COMMANDCENTER).ready:
            vespenes = self.state.vespene_geyser.closer_than(10.0, commandcenter)
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
                        await self.do(worker.build(UnitTypeId.REFINERY, vespene))

    async def manufacture_battle_unit(self):
        if self.get_building_or_unit_num(UnitTypeId.FACTORY) <= 1:
            for barracks in self.units(UnitTypeId.BARRACKS).ready.noqueue:
                if self.get_building_or_unit_num(UnitTypeId.MARINE) < 3:
                    if self.can_afford(UnitTypeId.MARINE):
                        await self.do(barracks.train(UnitTypeId.MARINE))
                        time.sleep(0.1)
                elif self.check_if_valid_building_exists(UnitTypeId.FACTORY):
                    output_log('current has valid factory')
                    if self.get_building_or_unit_num(UnitTypeId.STARPORT) >= 1:
                        output_log('starport built')
                        if barracks.has_add_on == 1:
                            output_log('there is a barracks had add-on')
                            if self.get_building_or_unit_num(UnitTypeId.MARAUDER) < 3:
                                output_log('now marauder num is less than 3')
                                if self.can_afford(UnitTypeId.MARAUDER):
                                    if sys.platform == 'win32':
                                        await self.do(barracks.train(UnitTypeId.MARAUDER))
                                        # await self.do(barracks(AbilityId.BARRACKSTRAIN_MARAUDER))
                                    else:
                                        await self.do(barracks(AbilityId.BARRACKSTRAIN_MARAUDER))
                                        # await self.do(barracks(UnitTypeId.MARAUDER))
                                    time.sleep(0.1)
                            elif self.can_afford(UnitTypeId.MARINE):
                                await self.do(barracks.train(UnitTypeId.MARINE))
                                time.sleep(0.1)
                        else:
                            if self.can_afford(UnitTypeId.MARINE):
                                await self.do(barracks.train(UnitTypeId.MARINE))
                                time.sleep(0.1)
        target_medivac_num = round((self.get_building_or_unit_num(UnitTypeId.MARINE)+self.get_building_or_unit_num(UnitTypeId.MARAUDER))/5)
        if self.check_if_valid_building_exists(UnitTypeId.STARPORT):
            if self.get_building_or_unit_num(UnitTypeId.MEDIVAC) < target_medivac_num:
                for starport in self.units(UnitTypeId.STARPORT).ready.noqueue:
                    if self.can_afford(UnitTypeId.MEDIVAC):
                        await self.do(starport.train(UnitTypeId.MEDIVAC))

    async def scout(self):
        if not self.known_enemy_structures and not self.known_enemy_units:
            if self.check_if_valid_building_exists(UnitTypeId.BARRACKS):
                if self.order_execute_num_in_scv('move') < 1:
                    scout_scv = self.units(UnitTypeId.SCV).ready.first
                    for position in self.enemy_start_locations:
                        output_log('scout scv move to {0}'.format(position))
                        await self.do(scout_scv.move(position))
                        time.sleep(0.1)

    async def do_upgrade(self):
        for addon in self.units(UnitTypeId.BARRACKSTECHLAB).noqueue:
            output_log('start check possible available addon')
            current_upgrades = self.state.upgrades
            output_log('current upgrades: {0}'.format(current_upgrades))
            if self.can_afford(AbilityId.BARRACKSTECHLABRESEARCH_STIMPACK):
                if UpgradeId.STIMPACK not in current_upgrades:
                    await self.do(addon(AbilityId.BARRACKSTECHLABRESEARCH_STIMPACK))
                else:
                    output_log('stimpack already upgraded')
            if self.can_afford(AbilityId.RESEARCH_COMBATSHIELD):
                if UpgradeId.SHIELDWALL not in current_upgrades:
                    await self.do(addon(AbilityId.RESEARCH_COMBATSHIELD))
                else:
                    output_log('combatshield already upgraded')
        else:
            output_log('there is no available techlab')

    async def move_and_attack(self):
        output_log('type of enemy units property: {0}'.format(type(self.state.enemy_units)))
        for medivac in self.units(UnitTypeId.MEDIVAC):
            if not medivac.is_attacking:
                all_battle_units = self.get_all_friendly_battle_unit()
                if all_battle_units:
                    await self.do(medivac.attack(all_battle_units.furthest_to(self.units(UnitTypeId.COMMANDCENTER).ready.first)))
                else:
                    await self.do(medivac.attack(random.choice(self.units(UnitTypeId.COMMANDCENTER).ready)))
        if self.get_friendly_battle_unit().amount == 0:
            return
        for unit in self.get_friendly_battle_unit():
            current_around_status = self.get_unit_around_status(unit)
            choice_num = random.randint(1, 6)
            current_total_health = self.get_current_friendly_unit_health()
            current_enemy_num = self.get_visible_enemy_battle_unit_or_building().amount
            if current_enemy_num == self.current_enemy_force_num and current_total_health >= self.current_total_friendly_unit_health:
                self.current_total_friendly_unit_health = current_total_health
                if unit.is_idle is False:
                    continue
            self.current_enemy_force_num = current_enemy_num
            self.current_total_friendly_unit_health = current_total_health
            if choice_num == 1:
                nearest_unit = self.get_nearest_enemy_unit(unit)
                if nearest_unit is not None:
                    await self.do(unit.attack(nearest_unit))
            elif choice_num == 2:
                target_enemy = self.get_highest_dps_enemy_unit(unit)
                if target_enemy is not None:
                    await self.do(unit.attack(target_enemy))
            elif choice_num == 3:
                regroup_point = self.get_regroup_point()
                await self.do(unit.move(regroup_point))
            elif choice_num == 4:
                if len(self.known_enemy_structures) > 0:
                    await self.do(unit.attack(random.choice(self.known_enemy_structures)))
            elif choice_num == 5:
                try:
                    await self.do(unit.move(self.units(UnitTypeId.COMMANDCENTER).ready.first))
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
            print('MARAUDER NUM: {0}'.format(self.get_building_or_unit_num(UnitTypeId.MARAUDER)))


def start():
    game_result = run_game(maps.get("EphemeronLE"), [Bot(Race.Terran, SimpleAI()), Computer(Race.Random, Difficulty.Medium)], realtime=False)
    print('game_result: {0}'.format(game_result))
    return game_result


if __name__ == '__main__':
    start()
