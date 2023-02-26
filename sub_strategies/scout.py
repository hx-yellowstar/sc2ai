from sc2.main import BotAI
from custom_logger import output_log
from sc2.constants import UnitTypeId, UpgradeId, AbilityId
from sub_strategies.status_check import StatusCheck
from sub_strategies.battle_strategy import BattleStrategy


class ScoutStrategies:
    def __init__(self, ai_instance: BotAI):
        self.ai: BotAI = ai_instance
        # 格式：[(Unit, UnitTypeId)...]
        self.scout_units = []
        self.status_check = StatusCheck(ai_instance)
        self.battle_st = BattleStrategy(ai_instance)

    def choose_scout_unit(self):
        if UnitTypeId.SCV not in [each[1] for each in self.scout_units] and len(self.scout_units) == 0:
            if len(self.ai.workers) >= 15:
                scout_scv = self.ai.workers.first
                self.scout_units.append((scout_scv, UnitTypeId.SCV))
        if UnitTypeId.REAPER not in [each[1] for each in self.scout_units] and self.status_check.get_building_or_unit_num(UnitTypeId.REAPER) > 0:
            scout_reaper = self.ai.units(UnitTypeId.REAPER).first
        if self.status_check.get_building_or_unit_num(UnitTypeId.HELLION) > 0:
            self.scout_units.append((self.ai.units.of_type(UnitTypeId.HELLION), UnitTypeId.HELLION))
        if len(self.scout_units) > 1:
            self.scout_units = [each for each in self.scout_units if each[1] != UnitTypeId.SCV]

    def do_scout(self):
        for scout_info in self.scout_units:
            scout_units = scout_info[0]
            unit_type = scout_info[1]
            all_friendly_building = self.battle_st.get_all_friendly_building()
            enemy_start_location = self.ai.enemy_start_locations[0]
            if len(all_friendly_building) > 0:
                friendly_building_to_retreat = all_friendly_building[0]
            else:
                friendly_building_to_retreat = None
            if unit_type == UnitTypeId.SCV:
                nearest_enemy = self.battle_st.get_nearest_enemy_unit(scout_units)
                if nearest_enemy:
                    if nearest_enemy.movement_speed > scout_units.movement_speed * 0.75:
                        for commandcenter in self.ai.structures.of_type(UnitTypeId.COMMANDCENTER):
                            cc_local_minerals = [mineral for mineral in self.ai.mineral_field if mineral.distance_to(commandcenter) <= 8]
                            if len(cc_local_minerals) > 0:
                                target_mineral = cc_local_minerals[0]
                                scout_units.gather(target_mineral)
                                break
                        continue
                if len(self.ai.enemy_start_locations) == 0:
                    continue
                scout_units.move(enemy_start_location)
            elif unit_type in (UnitTypeId.REAPER, UnitTypeId.HELLION):
                nearest_enemy = self.battle_st.get_nearest_enemy_unit(scout_units)
                if nearest_enemy:
                    if nearest_enemy.movement_speed > scout_units.movement_speed * 0.9:
                        if friendly_building_to_retreat is not None:
                            scout_units.move(friendly_building_to_retreat.position)
                    elif (nearest_enemy.distance_to(scout_units) - nearest_enemy.ground_range) <= scout_units.ground_range / 2:
                        if friendly_building_to_retreat is not None:
                            scout_units.move(friendly_building_to_retreat)
                    else:
                        scout_units.attack(nearest_enemy)
                else:
                    scout_units.move(enemy_start_location)
