import re
import sc2
from sc2ai_lib import *
from custom_logger import output_log
from sc2.constants import UnitTypeId, UpgradeId, AbilityId


class StatusCheck(sc2.BotAI):
    def supply_remaining_intense(self):
        if self.check_army_factory_number() <= 3:
            if self.supply_left < 3:
                if self.check_if_valid_building_exists(UnitTypeId.COMMANDCENTER) and not self.already_pending(UnitTypeId.SUPPLYDEPOT):
                    return True
        elif self.check_army_factory_number() < 6:
            if self.supply_left < 6:
                if self.check_if_valid_building_exists(UnitTypeId.COMMANDCENTER) and not self.already_pending(UnitTypeId.SUPPLYDEPOT):
                    return True
        else:
            if self.supply_left < 8:
                if self.check_if_valid_building_exists(UnitTypeId.COMMANDCENTER):
                    return True
        return False

    def check_army_factory_number(self):
        return self.units(UnitTypeId.BARRACKS).amount + self.units(UnitTypeId.FACTORY).amount + self.units(UnitTypeId.STARPORT).amount

    def check_if_valid_building_exists(self, building_unit: UnitTypeId):
        if self.units(building_unit).ready.exists:
            return True
        else:
            return False

    def get_building_or_unit_num(self, building_or_unit):
        if isinstance(building_or_unit, UnitTypeId):
            return self.units(building_or_unit).amount
        else:
            total_unit_num = 0
            if isinstance(building_or_unit, list):
                for unit in building_or_unit:
                    if isinstance(unit, UnitTypeId):
                        total_unit_num += self.units(unit).amount
            return total_unit_num

    def there_has_valid_supplydepot(self):
        return self.check_if_valid_building_exists(UnitTypeId.SUPPLYDEPOT) or self.check_if_valid_building_exists(UnitTypeId.SUPPLYDEPOTLOWERED)

    def get_current_friendly_unit_health(self):
        all_unit_or_building = self.state.units.filter(lambda u: (u.is_mine is True))
        total_health = 0
        for unit in all_unit_or_building:
            total_health += unit.health
        return total_health
