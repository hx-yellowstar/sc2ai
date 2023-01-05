import sc2
import random
import collections
from sc2.units import Unit
from sc2.constants import UnitTypeId, AbilityId, UpgradeId
from utils import Utils

class Miner:
    def __init__(self, bot: sc2.BotAI):
        self.bot = bot
        self.resource_requirements = []
        self.current_mineral_requirments = 0
        self.current_gas_requirements = 0
        self.gas_require_level_section = 50
        self.util = Utils(bot)

    def set_scv_to_mining(self):
        self.calculate_resources_requirement()
        for commandcenter in self.bot.structures(UnitTypeId.COMMANDCENTER).ready:
            if self.util.get_building_or_unit_num(UnitTypeId.SCV) < self.util.get_building_or_unit_num(UnitTypeId.COMMANDCENTER) * 22:
                if self.bot.can_afford(UnitTypeId.SCV):
                    if commandcenter.is_idle:
                        self.bot.do(commandcenter.train(UnitTypeId.SCV))
        scv_collect_gas_priority = min(self.current_gas_requirements/self.gas_require_level_section, 5)
        if scv_collect_gas_priority > 0:
            self.build_gas_station()
        self.bot.distribute_workers(scv_collect_gas_priority)

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

