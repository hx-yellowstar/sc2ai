import sc2
from sc2.constants import UnitTypeId


class Utils:
    def __init__(self, bot):
        self.bot = bot

    def get_building_or_unit_num(self, building_or_unit):
        if isinstance(building_or_unit, UnitTypeId):
            return max(self.bot.units(building_or_unit).amount, self.bot.structures(building_or_unit).amount)
        else:
            total_unit_num = 0
            if isinstance(building_or_unit, list):
                for unit in building_or_unit:
                    if isinstance(unit, UnitTypeId):
                        total_unit_num += max(self.bot.units(unit).amount, self.bot.structures(unit).amount)
            return total_unit_num