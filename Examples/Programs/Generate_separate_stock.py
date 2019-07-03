"""
This program is created by Andrew Li for separating the entire .csv file into different files for regression

There are three inputs including:
    1. CombinedDataLoc: The path of the .csv file which is needed to be separated
    2. SaveDir: The final of address to save all the separated .csv files
    3. startDate: The start date for separating

The output is the .csv files containing the date and the corresponding close price

The file is lastly modified on 2018/11/20
"""

import pandas as pd
import numpy as np
import os
from sklearn.linear_model import LinearRegression
from Utilities import *


def generate_separate_stock(CombinedDataLoc = '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/HKCombine/RetrievedHK.csv',
                            SaveDir = '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/IndividualHKStock/',
                            startDate = 20180103):

    """This program will check the start date of the stock linked with the corresponding index data"""

    HKStocks = pd.read_csv(CombinedDataLoc, names=['Date', 'PX_OPEN','PX_HIGH', 'PX_LOW','PX_LAST', 'VOLUME'])
    tickerIsRecentFlag = False
    NoStockCount = 0
    startDate = int(startDate)
    for idx, ticker in enumerate(HKStocks['Date']):
        if idx < HKStocks.shape[0]:
            try:
                if not check_nan(ticker):
                    if ':' in ticker.split(' '):
                        currTicker = ticker.split(' ')[1]
                        startIdx = idx + 1
                        try:
                            tickerIsRecentFlag = False if int(HKStocks['Date'].loc[startIdx]) < startDate else True
                        except ValueError:
                            print('No date of {}!'.format(ticker))

                        NoStockCount += 1
                        if NoStockCount % 50 == 0:
                            print('Saved {} stocks'.format(NoStockCount))
                        continue

                    date = int(ticker)
                    if not tickerIsRecentFlag:
                        '''Save the data which has the earlier date than startDate'''
                        if date == startDate:
                            startIdx = idx
                        try:
                            int(HKStocks['Date'].loc[idx + 1])
                        except ValueError:
                            currDataframe = pd.DataFrame(np.array([HKStocks['Date'].loc[startIdx:idx],
                                                                   HKStocks['PX_LAST'].loc[startIdx:idx]]).transpose(),
                                                         columns=['date', 'price'])
                            currDataframe.to_csv(
                                '{}{}.csv'.format(SaveDir,
                                    currTicker), index=False)
                    else:
                        '''Save the data which has the later date than startDate'''
                        try:
                            int(HKStocks['Date'].loc[idx + 1])
                        except ValueError:
                            currDataframe = pd.DataFrame(
                                np.array([HKStocks['Date'].loc[startIdx:idx],
                                          HKStocks['PX_LAST'].loc[startIdx:idx]]).transpose(),
                                columns=['date', 'price'])
                            currDataframe.to_csv(
                                '{}{}.csv'.format(SaveDir,
                                    currTicker), index=False)

            except KeyError:
                '''Save the last data'''
                currDataframe = pd.DataFrame(np.array([HKStocks['Date'].loc[startIdx:idx],
                                                       HKStocks['PX_LAST'].loc[startIdx:idx]]).transpose(),
                                             columns=['date', 'price'])
                currDataframe.to_csv(
                    '{}{}.csv'.format(SaveDir,
                        currTicker), index=False)
                break

def main():
    generate_separate_stock()

if __name__ == '__main__':
    main()
