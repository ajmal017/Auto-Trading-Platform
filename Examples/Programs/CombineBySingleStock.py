'''
This program is created by Andrew Li for combining the transformed data created from StockTransformo.py

There are three inputs including:
    1. dirStock: The path of directory which store the separated stock files
    2. pathTicker: The path of the .csv file which contains the ticker information
    3. pathMainDf: The path to store the combined .csv file

The output is the .csv files containing the date, ticker, ohlcv

The file is lastly modified on 2018/11/22
'''

import pandas as pd
import numpy as np
import os
from Utilities import check_nan
def combSingleStock(dirStock, pathTicker, pathMainDf):
    '''This program will select ticker individually from ticker list and search whether the ticker exists in the files
    under the dirStock directory. Thus, the logic of this combination program is to select data given ticker one by one.
    '''
    os.chdir(dirStock)
    files = sorted(os.listdir(dirStock))
    tickers = pd.read_csv(pathTicker, header=None)
    mainDataFrame = pd.DataFrame(columns=['Date', 'PX_OPEN', 'PX_HIGH', 'PX_LOW', 'PX_LAST', 'Volume'])
    count = 0
    for ticker in tickers[0]:
        currTicker = pd.DataFrame(np.array([': {}'.format(ticker.split()[0]), None, None, None, None, None]).reshape(1, -1),
                                  columns=['Date', 'PX_OPEN', 'PX_HIGH', 'PX_LOW', 'PX_LAST', 'Volume'])
        for file in files:
            '''Do combination of different files under the dirStock in order'''
            currFile = pd.read_csv(file, names=['Date', 'PX_OPEN', 'PX_HIGH', 'PX_LOW', 'PX_LAST', 'Volume'])
            startFlag = False
            for idx, item in enumerate(currFile.Date):
                if check_nan(item):
                    '''Check end point'''
                    break

                if ': {}'.format(ticker.split(' ')[0]) == item:
                    '''Current item match the ticker name and store the first date'''
                    startIdx = idx + 1
                    startFlag = True
                    continue

                if startFlag and ':' == item.split()[0]:
                    '''End date is detected and combine the currFile with the previous ones'''
                    currTicker = pd.concat([currTicker, currFile.loc[startIdx:idx-1]], ignore_index=True)
                    break

        mainDataFrame = pd.concat([mainDataFrame, currTicker], ignore_index=True)
        count += 1
        if count % 20 == 0:
            print('{} have been saved'.format(count))
    mainDataFrame.to_csv(pathMainDf, index=False, header=False)

def main():
    dirStock = '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/AllNAQEx1'
    pathTicker = '/Users/andrew/Desktop/Tickers.csv'
    pathMainDf = '/Users/andrew/Desktop/Main.csv'
    combSingleStock(dirStock, pathTicker, pathMainDf)

if __name__ == '__main__':
    main()