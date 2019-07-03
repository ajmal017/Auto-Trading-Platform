'''
This program is created by Andrew Li for regression by using the separate data created from Generate_separate_stock.py

There are three inputs including:
    1. dirStock: The path of directory which store the separated stock files
    2. indexPath: The path of the .csv file which contains the index information
    3. regPath: The path to store the regression file

The output is the .csv files containing the ticker, alpha and beta

The file is lastly modified on 2018/11/20
'''

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

StockDf1 = pd.read_csv('/Users/andrew/Desktop/Combined_file3.csv', header=None, names=['date', 'open', 'high', 'low', 'close', 'volume'])
StockDf2 = pd.read_csv('/Users/andrew/Desktop/Combined_file4.csv', header=None, names=['date', 'open', 'high', 'low', 'close', 'volume'])
TickerDf = pd.read_csv('/Users/andrew/Desktop/Tickers.csv', names=['Securities'])
TickerList = list(map(lambda t: t.split(' ')[0], [ticker for ticker in TickerDf['Securities'].loc[:600]]))
# TickerList = list(map(lambda t: t.split(' ')[0], [ticker for ticker in TickerDf['Securities'].loc[601:]]))
AllDataDict = {}
prevTicker = None
PrintCount = 0
prevIdx = 0
prevFlag = False
for idx, item in enumerate(StockDf1['date']):
    if ':' in item.split(' '):
        if prevTicker != None:
            if prevFlag == True:
                AllDataDict[prevTicker] = [StockDf1.values[prevPosition: idx, :]]
                prevFlag = False
                # TickerList.pop(0)
                PrintCount += 1
                if PrintCount % 20 == 0:
                    print('{} stocks are stored!'.format(PrintCount))

            if item.split(' ')[1] in TickerList:
                prevFlag = True
                prevPosition = idx + 1
                prevTicker = item


        else:
            if item.split(' ')[1] in TickerList:
                prevTicker = item
                prevPosition = idx + 1
                prevFlag = True

print('Change to dict successfully')
prevTicker = None
PrintCount = 0
prevFlag = False
for idx, item in enumerate(StockDf2['date']):
    if ':' in item.split(' '):
        if prevTicker != None:
            if prevFlag == True:
                if prevFlag:
                    PrintCount += 1
                    if PrintCount % 20 == 0:
                        print('{} stocks are stored!'.format(PrintCount))
                    if prevTicker in AllDataDict.keys():
                        AllDataDict[prevTicker].append(StockDf2.values[prevPosition: idx, :])
                        prevFlag = False
                    else:
                        AllDataDict[prevTicker] = [StockDf2.values[prevPosition: idx, :]]
                        prevFlag = False

            if item.split(' ')[1] in TickerList:
                prevFlag = True
                prevPosition = idx + 1
                prevTicker = item
                prevFlag = True

        else:
            if item.split(' ')[1] in TickerList:
                prevTicker = item
                prevPosition = idx + 1
                prevFlag = True

del StockDf1
del StockDf2
del TickerList
print('Save to dict successfully')


main_list1 = np.array([None, None, None, None, None, None])
main_list2 = np.array([None, None, None, None, None, None])
for idx, key in enumerate(AllDataDict.keys()):
    if idx < 300:
        ticker = key.split()[1]
        main_list1 = np.vstack((main_list1,np.array([': {}'.format(ticker), None, None, None, None, None])))
        length = len(AllDataDict[key])
        for num_array in range(length):
            x1 = np.array(AllDataDict[key].pop(0))
            main_list1 = np.vstack((main_list1, x1))
        if idx % 50 == 0:
            print('{} stocks have been saved!'.format(idx))
    else:
        ticker = key.split()[1]
        main_list2 = np.vstack((main_list2,np.array([': {}'.format(ticker), None, None, None, None, None])))
        length = len(AllDataDict[key])
        for num_array in range(length):
            x2 = np.array(AllDataDict[key].pop(0))
            main_list2 = np.vstack((main_list2, x2))
        if idx % 50 == 0:
            print('{} stocks have been saved!'.format(idx))

main_list1 = np.array(main_list1)
main_df1 = pd.DataFrame(main_list1 ,columns=['Date', 'PX_OPEN', 'PX_HIGH', 'PX_LOW', 'PX_LAST', 'Volume'])
main_list2 = np.array(main_list2)
main_df2 = pd.DataFrame(main_list2 ,columns=['Date', 'PX_OPEN', 'PX_HIGH', 'PX_LOW', 'PX_LAST', 'Volume'])
del main_list1
del main_list2

main_df = pd.concat([main_df1, main_df2], ignore_index=True, axis=0)
main_df.to_csv('/Users/andrew/Desktop/Date_Combined_file3.csv')