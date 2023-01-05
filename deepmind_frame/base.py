from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import csv
import numpy

from pysc2.agents import base_agent
from pysc2.lib import actions

with open('reward_record.csv', 'w', encoding='utf-8', newline='') as f:
    csv.writer(f).writerow(['last_function_id', 'last_args', 'reward'])

class RandomAgent(base_agent.BaseAgent):
    """A random agent for starcraft."""
    last_function_id = None
    last_args = None

    def step(self, obs):
        super(RandomAgent, self).step(obs)
        reward = obs.reward
        if self.last_function_id is not None and self.last_args is not None:
            with open('reward_record.csv', 'a', encoding='utf-8', newline='') as f:
                csv.writer(f).writerow([self.last_function_id, self.last_args, reward])
        function_id = numpy.random.choice(obs.observation.available_actions)
        self.last_function_id = str(function_id)
        args = [[numpy.random.randint(0, size) for size in arg.sizes]
                for arg in self.action_spec.functions[function_id].args]
        self.last_args = str(args)
        return actions.FunctionCall(function_id, args)
