import copy
import numpy as np
import pandas as pd

#this
def update():
    RL = QLearningTable(['up', 'down', 'left', 'right'])
    # 学习 100 回合
    env = GameEnv()

    for episode in range(100):
        # 初始化 state 的观测值
        observation = env.reset() #env是搭建的游戏环境
        total_reward = 0
        while True:
            
            # 根据当前s 的观测值挑选 a，观测值是环境返回，这里返回的是小红的坐标
            action = RL.choose_action(str(observation))

            # 执行action, 得到s', r，和终止符done
            observation_, reward, done = env.step(action)

            # 从这个序列 (state, action, reward, state_) 中学习
            RL.learn(str(observation), action, reward, str(observation_))

            # 将下一个 state 的值传到下一次循环
            observation = observation_

            total_reward += reward

            if done:
                print('learning series: {0}, result: {1}'.format(episode+1, reward))
                break

    # 结束游戏并关闭窗口
    print('game over')


class QLearningTable: #关于Q表
    def __init__(self, actions, learning_rate=0.01, reward_decay=0.9, e_greedy=0.9):
        self.actions = actions  #选动作，有上下左右
        self.lr = learning_rate #学习率
        self.gamma = reward_decay #奖励衰减
        self.epsilon = e_greedy #贪婪系数
        self.q_table = pd.DataFrame(np.zeros((16, 4), dtype=np.float64), columns=self.actions, index=['00', '01', '02', '03', '10', '11', '12', '13',
                                             '20', '21', '22', '23', '30', '31', '32', '33'], dtype=np.float64) #初始Q表
        '''columns=['00', '01', '02', '03', '10', '11', '12', '13',
                                             '20', '21', '22', '23', '30', '31', '32', '33']'''
        self.states = set()

    def choose_action(self, observation):
        self.check_state_exists(observation)#检测该状态是否存在，不存在就新建
        if np.random.uniform() < self.epsilon: #随机数如果小于epsilon就选择最好的动作，如0.9的概率会选择最大
            state_action = self.q_table.loc[observation, :]
            # 针对同一个 state, 而不同动作的Q值却相同，采取随机选择
            action = np.random.choice(state_action[state_action == np.max(state_action)].index)
        else: #0.1的概率探索没有去过的地方
            action = np.random.choice(self.actions)
        return action

    def learn(self, s, a, r, s_):#更新Q表
        self.check_state_exists(s_)#检测该状态是否存在，不存在就新建
        q_predict = self.q_table.loc[s, a] #得到s和动作a的Q表值，即旧值
        if s_ != 'terminal': #如果游戏没有结束
            #贪婪的得到最大Q值乘学习率，加上reward得到s'和a'，即新值
            q_target = r + self.gamma * self.q_table.loc[s_, :].max()
        else:
            q_target = r  #如果是终点，没有后续动作，就直接是0
        self.q_table.loc[s, a] += self.lr * (q_target - q_predict)  # 时序差分新旧更新Q表

    def check_state_exists(self, observation):
        if observation in self.states:
            return True
        else:
            self.states.add(observation)
            return False


class GameEnv:
    def __init__(self):
        self.game_area = [[1, 0, 0, 0], [0, 0, -1, 0], [0, -1, 2, 0], [0, 0, 0, 0]]
        self.current_location = [0, 0]
        self.new_location = [0, 0]

    def reset(self):
        self.game_area = [[1, 0, 0, 0], [0, 0, -1, 0], [0, -1, 2, 0], [0, 0, 0, 0]]
        self.current_location = [0, 0]
        self.new_location = [0, 0]
        return str(''.join([str(each) for each in self.new_location]))

    def step(self, action):
        if action not in ['up', 'down', 'left', 'right']:
            raise Exception("action must in 'up', 'down', 'left', 'right'")
        self.new_location = copy.copy(self.current_location)
        if action == 'up':
            if self.current_location[0] == 0:
                return str(''.join([str(each) for each in self.new_location])), 0, False
            self.new_location[0] -= 1
        elif action == 'down':
            if self.current_location[0] == 3:
                return str(''.join([str(each) for each in self.new_location])), 0, False
            self.new_location[0] += 1
        elif action == 'left':
            if self.current_location[1] == 0:
                return str(''.join([str(each) for each in self.new_location])), 0, False
            self.new_location[1] -= 1
        else:
            if self.current_location[1] == 3:
                return str(''.join([str(each) for each in self.new_location])), 0, False
            self.new_location[1] += 1
        self.move_to_new_location()
        if (self.new_location[0] == 1 and self.new_location[1] == 2) or (self.new_location[0] == 2 and self.new_location[1] == 1):
            return 'terminal', -1, True
        elif self.new_location[0] == 2 and self.new_location[1] == 2:
            return 'terminal', 1, True
        return str(''.join([str(each) for each in self.new_location])), 0, False

    def move_to_new_location(self):
        self.game_area[self.current_location[0]][self.current_location[1]] = 0
        self.game_area[self.new_location[0]][self.new_location[1]] = 1
        self.current_location = copy.copy(self.new_location)


if __name__ == '__main__':
    update()