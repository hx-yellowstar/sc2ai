import re
import cv2
import sys
import time
import random
import traceback
import numpy as np

from sc2 import run_game, maps, Race, Difficulty, Result
from sc2.player import Bot, Computer, Human
from sc2.constants import UnitTypeId, UpgradeId, AbilityId, BuffId
from sc2.position import Point2

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
        self.attack_train_data = []
        self.current_enemy_force_num = 0
        self.current_total_friendly_unit_health = 0
        self.unit_health_status = {}
        self.unit_move_target_position = {}

    async def find_first_building_position(self):
        if self.first_supplydepot_position is not None:
            return
        command_centers = self.structures(UnitTypeId.COMMANDCENTER).ready
        command_center = command_centers.first
        near = command_center.position.to2
        p = await self.find_placement(UnitTypeId.SUPPLYDEPOT, near.rounded, 100, True, 2)
        mineral_fields = self.mineral_field.ready
        if not mineral_fields:
            output_log('this map has no mineral fields')
            return
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
            np.save("attack_train_data/{}.npy".format(str(int(time.time()))), np.array(self.attack_train_data))
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
                                await self.build(UnitTypeId.BARRACKS, near=self.structures(UnitTypeId.BARRACKS).ready.first)
                elif self.get_building_or_unit_num(UnitTypeId.BARRACKS) < 1:
                    if self.check_if_valid_building_exists(UnitTypeId.SUPPLYDEPOT) or self.check_if_valid_building_exists(UnitTypeId.SUPPLYDEPOTLOWERED):
                        print('build first barracks')
                        await self.building_with_position_related_to_supplydepot(UnitTypeId.BARRACKS)
            if self.can_afford(UnitTypeId.FACTORY):
                if self.get_building_or_unit_num(UnitTypeId.COMMANDCENTER) >= 2:
                    if self.check_if_valid_building_exists(UnitTypeId.BARRACKS):
                        if self.get_building_or_unit_num(UnitTypeId.FACTORY) < 1:
                            if self.get_building_or_unit_num(UnitTypeId.BARRACKS) >= 1:
                                await self.build(UnitTypeId.FACTORY, near=self.structures(UnitTypeId.BARRACKS).furthest_to(self.start_location))
            if self.can_afford(UnitTypeId.STARPORT):
                if self.get_building_or_unit_num(UnitTypeId.COMMANDCENTER) >= 2:
                    if self.check_if_valid_building_exists(UnitTypeId.FACTORY):
                        if self.get_building_or_unit_num(UnitTypeId.FACTORY) >= 1:
                            if self.get_building_or_unit_num(UnitTypeId.STARPORT) < 1:
                                if self.order_execute_num_in_scv('Starport') < 1:
                                    await self.build(UnitTypeId.STARPORT, near=self.structures(UnitTypeId.FACTORY).ready.furthest_to(self.structures(UnitTypeId.COMMANDCENTER).ready.first))
            if (self.get_minerals_nearby_command_center() < self.get_building_or_unit_num(UnitTypeId.COMMANDCENTER) * 12) and self.can_afford(UnitTypeId.COMMANDCENTER):
                await self.expand_now()
            if self.can_afford(UnitTypeId.BARRACKSTECHLAB):
                for barracks in self.structures(UnitTypeId.BARRACKS).ready.idle:
                    try:
                        if self.get_building_or_unit_num(UnitTypeId.BARRACKSTECHLAB) < 1 and self.check_army_factory_number() < 5:
                            if barracks.add_on_tag == 0:
                                self.do(barracks.build(UnitTypeId.BARRACKSTECHLAB))
                        elif self.get_building_or_unit_num(UnitTypeId.BARRACKSTECHLAB) < 2:
                            if barracks.add_on_tag == 0:
                                self.do(barracks.build(UnitTypeId.BARRACKSTECHLAB))
                    except Exception as e:
                        output_log(e)
            if self.can_afford(UnitTypeId.STARPORTREACTOR):
                for starport in self.structures(UnitTypeId.STARPORT).ready.idle:
                    try:
                        if self.get_building_or_unit_num(UnitTypeId.STARPORTREACTOR) < 1 and self.check_army_factory_number() < 5:
                            if starport.add_on_tag == 0:
                                self.do(starport.build(UnitTypeId.STARPORTREACTOR))
                        elif self.get_building_or_unit_num(UnitTypeId.STARPORTREACTOR) < 2:
                            if starport.add_on_tag == 0:
                                self.do(starport.build(UnitTypeId.STARPORTREACTOR))
                    except Exception as e:
                        output_log('can\'t build starport reactor: {0}'.format(e))
            if self.can_afford(UnitTypeId.FACTORYTECHLAB):
                for starport in self.structures(UnitTypeId.FACTORY).ready.idle:
                    try:
                        if self.get_building_or_unit_num(UnitTypeId.FACTORYTECHLAB) < 1:
                            self.do(starport.build(UnitTypeId.FACTORYTECHLAB))
                    except Exception as e:
                        output_log('can\'t build factory reactor: {0}'.format(e))
        else:
            if self.get_building_or_unit_num(UnitTypeId.BARRACKS) <= self.get_building_or_unit_num(UnitTypeId.COMMANDCENTER) * 3:
                if self.there_has_valid_supplydepot():
                    output_log('building more barracks')
                    await self.build(UnitTypeId.BARRACKS, near=self.structures(UnitTypeId.BARRACKS).ready.first)

    async def add_new_scv(self):
        for commandcenter in self.structures(UnitTypeId.COMMANDCENTER).ready:
            if self.get_building_or_unit_num(UnitTypeId.SCV) < self.get_building_or_unit_num(UnitTypeId.COMMANDCENTER) * 22:
                if self.can_afford(UnitTypeId.SCV):
                    if commandcenter.is_idle:
                        self.do(commandcenter.train(UnitTypeId.SCV))
                        time.sleep(0.1)

    async def figuring_supply(self):
        for supply_depot in self.structures(UnitTypeId.SUPPLYDEPOT).ready:
            self.do(supply_depot(AbilityId.MORPH_SUPPLYDEPOT_LOWER))
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
                        await self.build(UnitTypeId.SUPPLYDEPOT, self.structures(UnitTypeId.COMMANDCENTER).ready.first, max_distance=20)
                else:
                    return

    async def build_gas_station(self):
        if self.get_building_or_unit_num(UnitTypeId.BARRACKS) < 1:
            return
        for commandcenter in self.structures(UnitTypeId.COMMANDCENTER).ready:
            vespenes = self.vespene_geyser.closer_than(10.0, commandcenter)
            output_log('there is {0} available vespenes'.format(vespenes.amount))
            for vespene in vespenes:
                if not self.structures(UnitTypeId.REFINERY).closer_than(1.0, vespene).exists:
                    output_log('there is valid vespene exists')
                    if not self.can_afford(UnitTypeId.REFINERY):
                        break
                    worker = self.select_build_worker(vespene.position)
                    if worker is None:
                        break
                    if not self.structures(UnitTypeId.REFINERY).closer_than(1.0, vespene).exists:
                        self.do(worker.build(UnitTypeId.REFINERY, vespene))

    async def manufacture_battle_unit(self):
        if self.get_building_or_unit_num(UnitTypeId.FACTORY) <= 1:
            for barracks in self.structures(UnitTypeId.BARRACKS).ready.idle:
                if self.get_building_or_unit_num(UnitTypeId.MARINE) < 3:
                    if self.can_afford(UnitTypeId.MARINE):
                        self.do(barracks.train(UnitTypeId.MARINE))
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
                                        self.do(barracks.train(UnitTypeId.MARAUDER))
                                        # self.do(barracks(AbilityId.BARRACKSTRAIN_MARAUDER))
                                    else:
                                        self.do(barracks(AbilityId.BARRACKSTRAIN_MARAUDER))
                                        # self.do(barracks(UnitTypeId.MARAUDER))
                                    time.sleep(0.1)
                            elif self.can_afford(UnitTypeId.MARINE):
                                self.do(barracks.train(UnitTypeId.MARINE))
                                time.sleep(0.1)
                        else:
                            if self.can_afford(UnitTypeId.MARINE):
                                self.do(barracks.train(UnitTypeId.MARINE))
                                time.sleep(0.1)
        target_medivac_num = round((self.get_building_or_unit_num(UnitTypeId.MARINE)+self.get_building_or_unit_num(UnitTypeId.MARAUDER))/5)
        if self.check_if_valid_building_exists(UnitTypeId.STARPORT):
            if self.get_building_or_unit_num(UnitTypeId.MEDIVAC) < target_medivac_num:
                for starport in self.structures(UnitTypeId.STARPORT).ready.idle:
                    if self.can_afford(UnitTypeId.MEDIVAC):
                        self.do(starport.train(UnitTypeId.MEDIVAC))
        if self.check_if_valid_building_exists(UnitTypeId.FACTORY):
            if self.get_building_or_unit_num(UnitTypeId.SIEGETANK) < round((self.get_building_or_unit_num(UnitTypeId.MARINE)+self.get_building_or_unit_num(UnitTypeId.MARAUDER))/8):
                for factory in self.structures(UnitTypeId.FACTORY).ready.idle:
                    if self.can_afford(UnitTypeId.SIEGETANK):
                        self.do(factory.train(UnitTypeId.SIEGETANK))

    async def scout(self):
        if not self.enemy_structures and not self.enemy_units:
            if self.check_if_valid_building_exists(UnitTypeId.BARRACKS):
                if self.order_execute_num_in_scv('move') < 1:
                    scout_scv = self.units(UnitTypeId.SCV).ready.first
                    for position in self.enemy_start_locations:
                        output_log('scout scv move to {0}'.format(position))
                        self.do(scout_scv.move(position))
                        time.sleep(0.1)

    async def do_upgrade(self):
        for addon in self.structures(UnitTypeId.BARRACKSTECHLAB).idle:
            output_log('start check possible available addon')
            current_upgrades = self.state.upgrades
            output_log('current upgrades: {0}'.format(current_upgrades))
            if self.can_afford(AbilityId.BARRACKSTECHLABRESEARCH_STIMPACK):
                if UpgradeId.STIMPACK not in current_upgrades:
                    self.do(addon(AbilityId.BARRACKSTECHLABRESEARCH_STIMPACK))
                else:
                    output_log('stimpack already upgraded')
            if self.can_afford(AbilityId.RESEARCH_COMBATSHIELD):
                if UpgradeId.SHIELDWALL not in current_upgrades:
                    self.do(addon(AbilityId.RESEARCH_COMBATSHIELD))
                else:
                    output_log('combatshield already upgraded')
        else:
            output_log('there is no available techlab')

    async def move_and_attack(self):
        output_log('type of enemy units property: {0}'.format(type(self.enemy_units)))
        self.running_medivac_strategy()
        self.running_siege_tank_strategy()

        current_friendly_battle_unit_num = self.get_friendly_battle_unit().amount
        if current_friendly_battle_unit_num == 0:
            return

        if current_friendly_battle_unit_num > 0:
            current_battlefield_status = self.get_current_battlefield_unit_status()
            # current_battlefield_status:敌我单位数量、战斗力数据
            if current_battlefield_status[3] == 0:
                choice_seed = random.randint(1, 1000)
                current_total_health = self.get_current_friendly_unit_health()
                current_enemy_num = self.get_visible_enemy_battle_unit_or_building().amount
                random_seed = random.random()
                for unit in self.get_friendly_battle_unit():
                    unit_tag_id = unit.tag
                    if current_enemy_num == self.current_enemy_force_num or current_total_health >= self.current_total_friendly_unit_health:
                        # 没有新的敌人出现，而且没有单位受伤
                        current_first_order = self.get_unit_first_order(unit)
                        if current_first_order == 'move':
                            try:
                                move_target = self.unit_move_target_position[unit_tag_id]
                                distance_to_target = move_target.distance_to(unit)
                                if distance_to_target < 6:
                                    self.do(unit(AbilityId.STOP))
                            except Exception as e:
                                output_log('distance judge error: {0}'.format(e))
                                pass
                        if unit.is_attacking is True:
                            if random_seed > 0.01:
                                continue
                        elif unit.is_idle is False:
                            if random_seed > 0.1:
                                continue
                    if choice_seed > 700:
                        choice_num = 0
                        regroup_point = self.get_army_central_point()
                        self.do(unit.move(regroup_point))
                        self.unit_move_target_position[unit_tag_id] = regroup_point
                    elif choice_seed > 400:
                        choice_num = 2
                        try:
                            move_target_position = self.structures(UnitTypeId.COMMANDCENTER).ready.first
                            self.do(unit.move(move_target_position))
                            self.unit_move_target_position[unit_tag_id] = move_target_position
                        except Exception as e:
                            print(e)
                    elif choice_seed > 100:
                        continue
                    else:
                        choice_num = 1
                        if len(self.enemy_structures) > 0:
                            self.do(unit.attack(random.choice(self.enemy_structures).position))
                    y = np.zeros(3)
                    y[choice_num] = 1
                    self.train_data.append([y, current_battlefield_status])
                self.current_enemy_force_num = current_enemy_num
                self.current_total_friendly_unit_health = current_total_health
            else:
                attack_choice_seed = random.randint(1, 1000)
                for unit in self.get_friendly_battle_unit():
                    random_attack_choice = random.randint(0,4)
                    if unit.health_percentage > 0.2:
                        if unit.is_attacking:
                            continue
                    nearest_enemy = self.get_nearest_enemy_unit(unit)
                    if nearest_enemy:
                        if unit.name in ('Marine', 'Marauder'):
                            if unit.target_in_range(nearest_enemy, 3):
                                if unit.name == 'Marine':
                                    self.do(unit(AbilityId.EFFECT_STIM_MARINE))
                                elif unit.name == 'Marauder':
                                    self.do(unit(AbilityId.EFFECT_STIM_MARAUDER))
                    else:
                        continue
                    current_around_status = self.get_unit_around_status(unit)
                    if attack_choice_seed > 60:
                        if random_attack_choice == 0:
                            if nearest_enemy is not None:
                                self.do(unit.attack(nearest_enemy))
                        elif random_attack_choice == 1:
                            target_enemy = self.get_highest_dps_enemy_unit(unit)
                            if target_enemy is not None:
                                self.do(unit.attack(target_enemy))
                        elif random_attack_choice == 3:
                            evac_postion = self.get_unit_escape_position(unit)
                            self.do(unit.move(evac_postion))
                        else:
                            pass
                    else:
                        random_attack_choice = 4
                        commandcenter_position = random.choice(self.structures(UnitTypeId.COMMANDCENTER)).position
                        unit_center_position = self.get_friendly_battle_unit().center
                        target_position = Point2(((commandcenter_position.x + unit_center_position.x) / 2,
                                                  (commandcenter_position.y + unit_center_position.y) / 2))
                        self.do(unit.move(target_position))
                    y = np.zeros(5)
                    y[random_attack_choice] = 1
                    self.attack_train_data.append([y, current_around_status])

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

    def running_medivac_strategy(self):
        for medivac in self.units(UnitTypeId.MEDIVAC):
            medivac_tag = medivac.tag
            try:
                stored_health = self.unit_health_status[medivac_tag]
            except KeyError:
                stored_health = medivac.health
            current_health = medivac.health
            self.unit_health_status[medivac_tag] = current_health
            if current_health < stored_health:
                new_position = self.get_unit_escape_position(medivac)
                self.do(medivac.move(new_position))
            else:
                all_battle_units = self.get_all_friendly_battle_unit()
                try:
                    if all_battle_units:
                        self.do(medivac.attack(self.get_army_central_point()))
                    else:
                        self.do(medivac.attack(random.choice(self.structures(UnitTypeId.COMMANDCENTER).ready)))
                except Exception as e:
                    print('midivac target selection error: {0}'.format(e))

    def running_siege_tank_strategy(self):
        for tank in self.units(UnitTypeId.SIEGETANK):
            if self.get_visible_enemy_battle_unit_or_building():
                try:
                    if self.enemy_units.closest_distance_to(tank.position) < 12:
                        self.do(tank(AbilityId.SIEGEMODE_SIEGEMODE))
                except Exception as e:
                    output_log('unsiege error, info: {0}'.format(e))
        for tank in self.units(UnitTypeId.SIEGETANKSIEGED):
            if not self.get_visible_enemy_battle_unit_or_building():
                self.do(tank(AbilityId.UNSIEGE_UNSIEGE))
            else:
                try:
                    if self.enemy_units.closest_distance_to(tank.position) >= 13:
                        self.do(tank(AbilityId.UNSIEGE_UNSIEGE))
                except Exception as e:
                    output_log('unsiege error, info: {0}'.format(e))
        all_battle_units = self.get_all_friendly_battle_unit()
        if all_battle_units:
            for tank in self.units(UnitTypeId.SIEGETANK):
                try:
                    self.do(tank.move(self.units.furthest_to(self.structures(UnitTypeId.COMMANDCENTER).ready.first.position)))
                except Exception as e:
                    output_log('attack movement error: {0}'.format(e))


def start():
    game_result = run_game(maps.get("EphemeronLE"), [Bot(Race.Terran, SimpleAI()), Computer(Race.Random, Difficulty.MediumHard)], realtime=False)
    print('game_result: {0}'.format(game_result))
    return game_result


if __name__ == '__main__':
    start()
