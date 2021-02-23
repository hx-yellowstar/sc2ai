import re
import sc2
from custom_logger import output_log
from sc2.constants import UnitTypeId, UpgradeId, AbilityId


class DevelopMent(sc2.BotAI):
    async def building_with_position_related_to_supplydepot(self, building_name: UnitTypeId):
        try:
            return await self.build(building_name, near=self.structures(UnitTypeId.SUPPLYDEPOT).ready.furthest_to(self.structures(UnitTypeId.COMMANDCENTER).ready.first))
        except:
            try:
                return await self.build(building_name, near=self.structures(UnitTypeId.SUPPLYDEPOTLOWERED).ready.furthest_to(self.structures(UnitTypeId.COMMANDCENTER).ready.first))
            except:
                output_log('no valid supplydepot')