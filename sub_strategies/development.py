import re
import sc2
from sc2.main import BotAI
from custom_logger import output_log
from sc2.constants import UnitTypeId, UpgradeId, AbilityId
from sub_strategies.status_check import StatusCheck
from sub_strategies.battle_strategy import BattleStrategy
from sc2.units import Units


class DevelopMent:
    def __init__(self, bot_inst: BotAI):
        self.ai = bot_inst
        self.status_check = StatusCheck(bot_inst)
        self.battle_strategy = BattleStrategy(bot_inst)

    async def building_with_position_related_to_supplydepot(self, building_name: UnitTypeId):
        try:
            return await self.ai.build(building_name, near=self.ai.structures(UnitTypeId.SUPPLYDEPOT).ready.furthest_to(self.ai.structures(UnitTypeId.COMMANDCENTER).ready.first))
        except:
            try:
                return await self.ai.build(building_name, near=self.ai.structures(UnitTypeId.SUPPLYDEPOTLOWERED).ready.furthest_to(self.ai.structures(UnitTypeId.COMMANDCENTER).ready.first))
            except:
                output_log('no valid supplydepot')

    async def build_for_normal_tactics(self):
        if self.status_check.check_army_factory_number() <= 3:
            if self.ai.can_afford(UnitTypeId.BARRACKS):
                output_log('can afford barracks now')
                if self.status_check.get_building_or_unit_num(UnitTypeId.COMMANDCENTER) >= 2:
                    if (self.status_check.get_building_or_unit_num(UnitTypeId.FACTORY) >= 1 and self.status_check.get_building_or_unit_num(UnitTypeId.STARPORT) >= 1) or self.status_check.get_building_or_unit_num(UnitTypeId.BARRACKS) < 1:
                        if self.status_check.get_building_or_unit_num(UnitTypeId.BARRACKS) < 1:
                            if self.status_check.there_has_valid_supplydepot():
                                await self.building_with_position_related_to_supplydepot(UnitTypeId.BARRACKS)
                        else:
                            if self.status_check.there_has_valid_supplydepot():
                                print('build barracks no.{0}'.format(self.status_check.get_building_or_unit_num(UnitTypeId.BARRACKS)))
                                await self.ai.build(UnitTypeId.BARRACKS, near=self.ai.units(UnitTypeId.BARRACKS).ready.first)
                elif self.status_check.get_building_or_unit_num(UnitTypeId.BARRACKS) < 1:
                    if self.status_check.check_if_valid_building_exists(UnitTypeId.SUPPLYDEPOT) or self.status_check.check_if_valid_building_exists(UnitTypeId.SUPPLYDEPOTLOWERED):
                        print('build first barracks')
                        await self.building_with_position_related_to_supplydepot(UnitTypeId.BARRACKS)
            if self.ai.can_afford(UnitTypeId.FACTORY):
                if self.status_check.get_building_or_unit_num(UnitTypeId.COMMANDCENTER) >= 2:
                    if self.status_check.check_if_valid_building_exists(UnitTypeId.BARRACKS):
                        if self.status_check.get_building_or_unit_num(UnitTypeId.FACTORY) < 1:
                            if self.status_check.get_building_or_unit_num(UnitTypeId.BARRACKS) >= 1:
                                await self.ai.build(UnitTypeId.FACTORY, near=self.ai.units(UnitTypeId.BARRACKS).ready.furthest_to(self.ai.units(UnitTypeId.COMMANDCENTER).ready.first))
            if self.ai.can_afford(UnitTypeId.STARPORT):
                if self.status_check.get_building_or_unit_num(UnitTypeId.COMMANDCENTER) >= 2:
                    if self.status_check.check_if_valid_building_exists(UnitTypeId.FACTORY):
                        if self.status_check.get_building_or_unit_num(UnitTypeId.FACTORY) >= 1:
                            if self.status_check.get_building_or_unit_num(UnitTypeId.STARPORT) < 1:
                                if self.battle_strategy.order_execute_num_in_scv('Starport') < 1:
                                    await self.ai.build(UnitTypeId.STARPORT, near=self.ai.units(UnitTypeId.FACTORY).ready.furthest_to(self.ai.units(UnitTypeId.COMMANDCENTER).ready.first))
            if self.status_check.get_building_or_unit_num(UnitTypeId.COMMANDCENTER) < 2 and self.ai.can_afford(UnitTypeId.COMMANDCENTER):
                await self.ai.expand_now()
            if self.ai.can_afford(UnitTypeId.BARRACKSTECHLAB):
                for barracks in self.ai.units(UnitTypeId.BARRACKS).ready:
                    try:
                        if self.status_check.get_building_or_unit_num(UnitTypeId.BARRACKSTECHLAB) < 1 and self.status_check.check_army_factory_number() < 5:
                            if barracks.add_on_tag == 0:
                                barracks.build(UnitTypeId.BARRACKSTECHLAB)
                        elif self.status_check.get_building_or_unit_num(UnitTypeId.BARRACKSTECHLAB) < 2:
                            if barracks.add_on_tag == 0:
                                barracks.build(UnitTypeId.BARRACKSTECHLAB)
                    except Exception as e:
                        output_log(e)
            if self.ai.can_afford(UnitTypeId.STARPORTREACTOR):
                for starport in self.ai.units(UnitTypeId.STARPORT).ready:
                    try:
                        if self.status_check.get_building_or_unit_num(UnitTypeId.STARPORTREACTOR) < 1 and self.status_check.check_army_factory_number() < 5:
                            if starport.add_on_tag == 0:
                                starport.build(UnitTypeId.STARPORTREACTOR)
                        elif self.status_check.get_building_or_unit_num(UnitTypeId.STARPORTREACTOR) < 2:
                            if starport.add_on_tag == 0:
                                starport.build(UnitTypeId.STARPORTREACTOR)
                    except Exception as e:
                        output_log('can\'t build starport reactor: {0}'.format(e))
            if self.ai.can_afford(UnitTypeId.FACTORYTECHLAB):
                for starport in self.ai.units(UnitTypeId.FACTORY).ready:
                    try:
                        if self.status_check.get_building_or_unit_num(UnitTypeId.FACTORYTECHLAB) < 1:
                            starport.build(UnitTypeId.FACTORYTECHLAB)
                    except Exception as e:
                        output_log('can\'t build factory reactor: {0}'.format(e))
        else:
            if self.status_check.get_building_or_unit_num(UnitTypeId.BARRACKS) <= self.status_check.get_building_or_unit_num(UnitTypeId.COMMANDCENTER) * 3:
                if self.status_check.there_has_valid_supplydepot():
                    output_log('building more barracks')
                    await self.ai.build(UnitTypeId.BARRACKS, near=self.ai.units(UnitTypeId.BARRACKS).ready.first)

    async def build_for_reaper_rush(self):
        if self.status_check.get_building_or_unit_num(UnitTypeId.BARRACKS) < 1:
            if self.ai.can_afford(UnitTypeId.BARRACKS):
                if self.status_check.check_if_valid_building_exists(
                        UnitTypeId.SUPPLYDEPOT) or self.status_check.check_if_valid_building_exists(
                        UnitTypeId.SUPPLYDEPOTLOWERED):
                    print('build first barracks')
                    await self.building_with_position_related_to_supplydepot(UnitTypeId.BARRACKS)

