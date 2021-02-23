import re
import sc2
import random
from typing import Union
from sc2.bot_ai import Unit
from sc2.position import Point2
from custom_logger import output_log
from sc2.constants import UnitTypeId, UpgradeId, AbilityId


class BattleStrategy(sc2.BotAI):
    def get_unit_first_order(self, unit):
        order_queue = unit.orders
        try:
            first_order = re.search('\(name=(.*?)\)', str(order_queue[0].ability)).group(1)
        except Exception as e:
            output_log(e)
            first_order = ''
        first_order = first_order.lower()
        return first_order

    def order_execute_num_in_scv(self, order_name):
        order_name = order_name.lower()
        execute_num = 0
        for scv_unit in self.units(UnitTypeId.SCV).ready:
            first_order = self.get_unit_first_order(scv_unit)
            first_order = first_order.lower()
            if first_order == order_name:
                execute_num += 1
        return execute_num

    def unit_attacking(self, unit: UnitTypeId):
        first_order = self.get_unit_first_order(unit)
        first_order = first_order.lower()
        if first_order == 'attack':
            return True
        else:
            return False

    def get_nearest_enemy_unit(self, unit):
        current_visible_enemy = self.get_visible_enemy_battle_unit_or_building()
        if len(current_visible_enemy) > 0:
            return current_visible_enemy.closest_to(unit.position)
        else:
            return

    def get_highest_dps_enemy_unit(self, unit):
        near_enemys = self.get_visible_enemy_battle_unit_or_building().closer_than(int(unit.radar_range), unit)
        target_enemy = None
        max_dps = 0
        for enemy in near_enemys:
            if unit.is_flying:
                enemy_consider_dps = enemy.air_dps
            else:
                enemy_consider_dps = enemy.ground_dps
            if enemy_consider_dps >= max_dps:
                target_enemy = enemy
        return target_enemy

    def get_army_central_point(self, side='friendly'):
        if side == 'friendly':
            friendly_units = self.get_friendly_battle_unit()
            central_point = friendly_units.center
        else:
            enemy_units = self.get_visible_enemy_battle_unit_or_building()
            if len(enemy_units) > 0:
                central_point = enemy_units.center
            else:
                return
        return central_point

    def get_unit_escape_position(self, unit: Unit):
        current_position = unit.position
        enemy_central_point = self.get_army_central_point('enemy')
        if not enemy_central_point:
            return current_position
        mdv_x = current_position.x
        mdv_y = current_position.y
        ecp_x = enemy_central_point.x
        ecp_y = enemy_central_point.y
        new_position = current_position.offset([-0.7*(ecp_x-mdv_x), -0.7*(ecp_y-mdv_y)])
        return new_position

    def get_visible_enemy_battle_unit_or_building(self):
        return (self.enemy_units+self.enemy_structures).filter(lambda u: (u.is_visible is True and (u.ground_dps > 0 or u.air_dps > 0) and u.type_id not in (UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE, UnitTypeId.LARVA, UnitTypeId.EGG, UnitTypeId.OVERLORD)))

    def get_friendly_battle_unit(self):
        return self.units.filter(lambda u: u.is_mine is True and (u.type_id not in (UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE, UnitTypeId.LARVA, UnitTypeId.EGG, UnitTypeId.OVERLORD)))

    def get_enemy_worker(self):
        return self.enemy_units.filter(lambda u: (u.is_visible is True and u.type_id in (UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE)))

    def get_all_enemy_visible_unit(self):
        return self.enemy_units.filter(lambda u: (u.is_visible is True and u.type_id not in (UnitTypeId.LARVA, UnitTypeId.EGG)))

    def get_all_friendly_battle_unit(self):
        return self.units.filter(lambda u: (u.type_id not in (UnitTypeId.SCV, UnitTypeId.MEDIVAC)))

    def get_all_friendly_unit(self):
        return self.units

    def get_all_friendly_building(self):
        return self.structures

    def get_all_enemy_building(self):
        return self.enemy_structures

    def unit_regroup(self, unit):
        commandcenter_position = random.choice(self.structures(UnitTypeId.COMMANDCENTER)).position
        unit_center_position = self.get_friendly_battle_unit().center
        target_position = Point2(((commandcenter_position.x + unit_center_position.x) / 2,
                                  (commandcenter_position.y + unit_center_position.y) / 2))
        self.do(unit.move(target_position))

    def get_current_battlefield_unit_status(self):
        all_friendly_units = self.get_all_friendly_unit()
        enemy_units = self.get_visible_enemy_battle_unit_or_building()
        known_enemy_units = self.enemy_units
        total_ground_dps = 0
        total_air_dps = 0
        enemy_ground_dps = 0
        enemy_air_dps = 0
        unit_idle = 0
        unit_moving = 0
        unit_attacking = 0
        enemy_unit_attacking = 0
        total_number = 0
        total_enemy_number = 0
        known_enemy_number = 0
        known_enemy_ground_dps = 0
        known_enemy_air_dps = 0
        for friendly_unit in all_friendly_units:
            total_number += 1
            total_ground_dps += friendly_unit.ground_dps
            total_air_dps += friendly_unit.air_dps
            first_order = self.get_unit_first_order(friendly_unit)
            if first_order == 'move':
                unit_moving += 1
            if first_order == '':
                unit_idle += 1
            if self.unit_attacking(friendly_unit):
                unit_attacking += 1
        for enemy_unit in enemy_units:
            total_enemy_number += 1
            enemy_ground_dps += enemy_unit.ground_dps
            enemy_air_dps += enemy_unit.air_dps
            if self.unit_attacking(enemy_unit):
                enemy_unit_attacking += 1
        for enemy_unit in known_enemy_units:
            known_enemy_number += 1
            known_enemy_ground_dps += enemy_unit.ground_dps
            known_enemy_air_dps += enemy_unit.air_dps
        return [total_number, total_ground_dps, total_air_dps, total_enemy_number, enemy_ground_dps, enemy_air_dps,
                unit_idle, unit_moving, unit_attacking, enemy_unit_attacking, known_enemy_number, known_enemy_ground_dps, known_enemy_air_dps]

    def get_unit_around_status(self, current_unit):
        unit_self_health = current_unit.health
        unit_self_movement_speed = current_unit.movement_speed
        all_friendly_units = self.get_all_friendly_unit()
        enemy_units = self.get_visible_enemy_battle_unit_or_building()
        total_ground_dps = 0
        total_air_dps = 0
        enemy_ground_dps = 0
        enemy_air_dps = 0
        unit_idle = 0
        unit_moving = 0
        unit_attacking = 0
        enemy_unit_attacking = 0
        total_number = 0
        total_enemy_number = 0
        for friendly_unit in all_friendly_units:
            if friendly_unit.distance_to(current_unit) > (current_unit.radar_range + 3.0):
                continue
            total_number += 1
            total_ground_dps += friendly_unit.ground_dps
            total_air_dps += friendly_unit.air_dps
            first_order = self.get_unit_first_order(friendly_unit)
            if first_order == 'move':
                unit_moving += 1
            if first_order == '':
                unit_idle += 1
            if self.unit_attacking(friendly_unit):
                unit_attacking += 1
        for enemy_unit in enemy_units:
            if enemy_unit.distance_to(current_unit) > (current_unit.radar_range + 3.0):
                continue
            total_enemy_number += 1
            enemy_ground_dps += enemy_unit.ground_dps
            enemy_air_dps += enemy_unit.air_dps
            if self.unit_attacking(enemy_unit):
                enemy_unit_attacking += 1
        return [unit_self_health, unit_self_movement_speed, total_number, total_ground_dps, total_air_dps, total_enemy_number, enemy_ground_dps, enemy_air_dps, unit_idle, unit_moving, unit_attacking, enemy_unit_attacking]


if __name__ == '__main__':
    for each_dir in dir(sc2.BotAI.game_info):
        print(each_dir)