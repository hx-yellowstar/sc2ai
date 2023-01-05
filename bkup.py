import random
import traceback
from custom_logger import output_log
from sc2.constants import UnitTypeId, UpgradeId, AbilityId, BuffId


async def move_and_attack(self):
    output_log('type of enemy units property: {0}'.format(type(self.state.enemy_units)))
    for medivac in self.units(UnitTypeId.MEDIVAC):
        if not medivac.is_attacking:
            all_battle_units = self.get_all_friendly_battle_unit()
            if all_battle_units:
                await self.do(
                    medivac.attack(all_battle_units.furthest_to(self.units(UnitTypeId.COMMANDCENTER).ready.first)))
            else:
                await self.do(medivac.attack(random.choice(self.units(UnitTypeId.COMMANDCENTER).ready)))
    if self.get_building_or_unit_num([UnitTypeId.MARINE, UnitTypeId.MARAUDER]) > 20:
        visible_enemy_battle_units = self.get_visible_enemy_battle_unit()
        visible_enemy_worker = self.get_enemy_worker()
        if not visible_enemy_battle_units:
            # 兵力 >= 20，无可见战斗单位
            if visible_enemy_worker:
                output_log('there is no enemy battle unit and has enemy worker')
                for mm in self.get_all_friendly_battle_unit():
                    if not mm.is_attacking:
                        await self.do(mm.attack(random.choice(visible_enemy_worker)))
            else:
                output_log('no enemy units left')
                for mm in self.get_all_friendly_battle_unit():
                    if not mm.is_attacking:
                        if self.known_enemy_structures:
                            await self.do(mm.attack(random.choice(self.known_enemy_structures)))
                for mm in self.get_all_friendly_battle_unit():
                    if not mm.is_attacking:
                        if self.known_enemy_structures:
                            await self.do(mm.attack(random.choice(self.known_enemy_structures)))
        else:
            # 兵力 >= 20，有可见敌人战斗单位
            for mm in self.get_all_friendly_battle_unit():
                if (visible_enemy_battle_units.closest_distance_to(
                        mm.position) < mm.radar_range + 3) and UpgradeId.STIMPACK in self.state.upgrades:
                    output_log('there is enemy unit close and stimpack is upgraded')
                    if not mm.has_buff(BuffId.STIMPACKMARAUDER) and not mm.has_buff(BuffId.STIMPACK):
                        output_log('this unit is not in effect on stimpack')
                        if mm.type_id == UnitTypeId.MARINE:
                            output_log('there is a marine can take stimpack')
                            await self.do(mm(AbilityId.EFFECT_STIM_MARINE))
                        elif mm.type_id == UnitTypeId.MARAUDER:
                            output_log('there is a marauder can take stimpack')
                            await self.do(mm(AbilityId.EFFECT_STIM_MARAUDER))
                        else:
                            output_log('no unit can use stimpack')
                await self.do(mm.attack(visible_enemy_battle_units.closest_to(mm.position)))
    elif self.get_building_or_unit_num([UnitTypeId.MARINE, UnitTypeId.MARAUDER]) >= 1:
        if self.get_all_enemy_visible_unit():
            for mm in self.get_all_friendly_battle_unit():
                if not mm.is_attacking:
                    await self.do(mm.attack(random.choice(self.known_enemy_units)))
        else:
            for mm in self.get_all_friendly_battle_unit():
                if mm.is_attacking:
                    try:
                        await self.do(mm.move(self.units(UnitTypeId.SUPPLYDEPOTLOWERED).ready.first))
                    except:
                        output_log(traceback.format_exc())
                try:
                    if self.units(UnitTypeId.SUPPLYDEPOTLOWERED).closest_distance_to(mm.position) < 10:
                        if mm.is_idle is False:
                            await self.do(mm.stop())
                except:
                    output_log(traceback.format_exc())