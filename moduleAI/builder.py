import sc2
import random
import collections
from sc2.units import Unit
from sc2.constants import UnitTypeId, AbilityId, UpgradeId
from sc2.position import Point2

class Builder:
    def __init__(self, bot: sc2.BotAI):
        self.bot = bot
        self.resource_requirements = []
        self.current_mineral_requirments = 0
        self.current_gas_requirements = 0
        self.gas_require_level_section = 50

    def build_gas_station(self):
        for commandcenter in self.bot.structures(UnitTypeId.COMMANDCENTER).ready:
            vespenes = self.bot.vespene_geyser.closer_than(10.0, commandcenter)
            for vespene in vespenes:
                if not self.bot.structures(UnitTypeId.REFINERY).closer_than(1.0, vespene).exists:
                    if not self.bot.can_afford(UnitTypeId.REFINERY):
                        break
                    worker = self.bot.select_build_worker(vespene.position)
                    if worker is None:
                        break
                    if not self.bot.structures(UnitTypeId.REFINERY).closer_than(1.0, vespene).exists:
                        self.bot.do(worker.build_gas(vespene))

    # 暂时没用上，需要精确控制气矿采集时启用
    # def get_gas_spring_station_num(self):
    #     count = 0
    #     avaliable = 0
    #     for commandcenter in self.structures(UnitTypeId.COMMANDCENTER).ready:
    #         vespenes = self.vespene_geyser.closer_than(10.0, commandcenter)
    #         count += vespenes.amount
    #         for vespene in vespenes:
    #             if self.structures(UnitTypeId.REFINERY).closer_than(1.0, vespene):
    #                 avaliable += 1
    #     frame = collections.namedtuple('vespeneNum', ['all', 'avaliable'])
    #     count_collection = frame(all=count, avaliable=avaliable)
    #     return count_collection

    def calculate_resources_requirement(self):
        minerals = 0
        gas = 0
        for unit_id in self.resource_requirements:
            cost = self.bot.calculate_cost(unit_id)
            minerals += cost.minerals
            gas += cost.vespene
        self.current_mineral_requirments = minerals
        self.current_gas_requirements = gas

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