import csv
import time
import random
from init_ai import start
from multiprocessing import Pool

def multi_start():
    pool = Pool(4)
    n = 0
    while n < 100000:
        n += 1
        pool.apply_async(start_sim)
    pool.close()
    pool.join()

def start_sim():
    try:
        result = start()
    except Exception as e:
        print(e)
        result = 'Defeat due to error'
    with open('game_result.csv', 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([time.asctime(), str(result)])

if __name__ == '__main__':
    multi_start()
