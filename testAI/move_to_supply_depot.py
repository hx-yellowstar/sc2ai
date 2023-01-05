import re
import sc2
import random
from sc2.player import Bot, Computer, Human
from sc2 import run_game, maps, Race, Difficulty, Result
from sc2.constants import UnitTypeId, AbilityId
from sc2.position import Point2


class SimpleAI(sc2.BotAI):
    last_orders = []
    step_count = 0

    async def on_step(self, iteration: int):
        await self.move_to_supply_depot()

    async def move_to_supply_depot(self):
        self.step_count += 1
        unit = self.units.filter(lambda u: u.is_mine is True)
        if self.step_count == 1:
            for each_unit in unit:
                commandcenter_position = random.choice(self.structures(UnitTypeId.COMMANDCENTER)).position
                target_position = Point2((commandcenter_position.x, commandcenter_position.y))
                self.get_unit_order(each_unit)
                self.do(each_unit.scan_move(target_position))

    def get_unit_order(self, unit):
        order_queue = unit.orders
        order_names = [each.ability for each in order_queue]
        if order_names != self.last_orders:
            print(order_names[0])
            self.last_orders = order_names
        return order_queue


def start():
    game_result = run_game(maps.get("WorldofSleepersLE"), [Bot(Race.Terran, SimpleAI()), Computer(Race.Random, Difficulty.MediumHard)], realtime=True)
    print('game_result: {0}'.format(game_result))
    return game_result


if __name__ == '__main__':
    start()
