import re
import sc2
from sc2ai_lib import *
from custom_logger import output_log
from sc2.constants import UnitTypeId, UpgradeId, AbilityId
from sc2.main import BotAI
from sc2.units import Units


class StatusCheck:
    def __init__(self, bot_inst: BotAI):
        self.ai: BotAI = bot_inst

    def supply_remaining_intense(self):
        if self.check_army_factory_number() <= 3:
            if self.ai.supply_left < 3:
                if self.check_if_valid_building_exists(UnitTypeId.COMMANDCENTER) and not self.ai.already_pending(UnitTypeId.SUPPLYDEPOT):
                    return True
        elif self.check_army_factory_number() < 6:
            if self.ai.supply_left < 6:
                if self.check_if_valid_building_exists(UnitTypeId.COMMANDCENTER) and not self.ai.already_pending(UnitTypeId.SUPPLYDEPOT):
                    return True
        else:
            if self.ai.supply_left < 8:
                if self.check_if_valid_building_exists(UnitTypeId.COMMANDCENTER):
                    return True
        return False

    def check_army_factory_number(self):
        return self.ai.structures(UnitTypeId.BARRACKS).amount + \
            self.ai.structures(UnitTypeId.FACTORY).amount + \
            self.ai.structures(UnitTypeId.STARPORT).amount

    def check_if_valid_building_exists(self, building_unit: UnitTypeId):
        if self.ai.structures(building_unit).ready.exists:
            return True
        else:
            return False

    def get_building_or_unit_num(self, building_or_unit: UnitTypeId):
        return max([self.ai.units(building_or_unit).amount, self.ai.structures(building_or_unit).amount])

    def there_has_valid_supplydepot(self):
        return self.check_if_valid_building_exists(UnitTypeId.SUPPLYDEPOT) or self.check_if_valid_building_exists(UnitTypeId.SUPPLYDEPOTLOWERED)

    def get_current_friendly_unit_health(self):
        all_unit_or_building = self.ai.units.filter(lambda u: (u.is_mine is True))
        total_health = 0
        for unit in all_unit_or_building:
            total_health += unit.health
        return total_health
