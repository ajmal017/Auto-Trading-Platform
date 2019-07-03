import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

AllStockDF = pd.read_csv('/Users/andrew/Desktop/Combined_Data.csv', header=None, names=['date', 'open', 'high', 'low', 'close', 'volume'])
plotFlag = False
while True:
    ticker = input('Please enter stcok name:')
    # ticker = int(ticker)

    for idx, item in enumerate(AllStockDF['date']):
        try:
            int(item)

        except ValueError:
            if type(item) == float:
                break

            if plotFlag:
                plt.clf()
                plt.plot(AllStockDF['open'].values[prevPosition : idx - 1], color='r', linewidth = 1)
                plt.plot(AllStockDF['close'].values[prevPosition : idx - 1], color='b', linewidth = 1)
                plt.show()
                plotFlag = False
                break

            if item.split(' ')[1] == ticker:
                plotFlag = True
                prevPosition = idx + 1

    print('There is no such stock!')