import re
import sc2
import random
from sc2.player import Bot, Computer, Human
from sc2 import run_game, maps, Race, Difficulty, Result
from sc2.constants import UnitTypeId, AbilityId
from sc2.position import Point2
from moduleAI.miner import Miner


class SimpleAI(sc2.BotAI):
    def __init__(self):
        super().__init__()
        self.step_count = 0
        self.miner = Miner(self)

    async def on_step(self, iteration: int):
        self.step_count += 1
        if self.step_count == 1:
            self.set_init_requirement()
        if self.step_count % 1000 == 0:
            print(f'current resource count: mineral: {self.miner.current_mineral_requirments}, gas: {self.miner.current_gas_requirements}')
        await self.miner_move()

    async def miner_move(self):
        self.miner.set_scv_to_mining()

    def set_init_requirement(self):
        self.miner.resource_requirements = [UnitTypeId.SUPPLYDEPOT, UnitTypeId.BARRACKS, UnitTypeId.FACTORY, UnitTypeId.STARPORT]

def start():
    game_result = run_game(maps.get("WorldofSleepersLE"), [Bot(Race.Terran, SimpleAI()), Computer(Race.Random, Difficulty.VeryEasy)], realtime=True)
    print('game_result: {0}'.format(game_result))
    return game_result


if __name__ == '__main__':
    start()
