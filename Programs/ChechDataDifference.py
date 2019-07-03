'''
This program is created by Andrew Li for checking the difference between the BloomBerg's and IB's data

There are three main functions including:

    1. pathTicker: The path of tickers.csv
    2. pathBb: The path of BloomBerg's data
    3. pathIb: The path of IB's data

The file is lastly modified on 2018/11/23
'''
import pandas as pd
import numpy as np

def compData(pathTicker, pathBb, pathIb):
    tickers = pd.read_csv(pathTicker, names=['tickers'])
    dataBB = pd.read_csv(pathBb, names=['date', 'open', 'high', 'low', 'close', 'volume'])
    dataIB = pd.read_csv(pathIb, names=['date', 'open', 'high', 'low', 'close', 'volume'])
    remainList = checkTicker(tickers, dataBB, dataIB)
    df = pd.DataFrame(np.array(remainList).reshape(-1, 1))
    df.to_csv('~/Desktop/tickers_adj.csv', index=False, header=False)


def checkTicker(tickers, dataBB, dataIB):
    '''
    This function is to check the existence of tickers in the IB and BB's dataset
    :param tickers: All the tickers
    :param dataBB: Data from BB
    :param dataIB: Data from IB
    :return: A list of tickers that exist in both datase
    '''
    tickerList = [ticker.split()[0] for ticker in tickers.tickers]
    for item in dataBB.date[1:]:
        try:
            if item.split()[1] in tickerList:
                attribute = item.split()[1]
                tickerList.remove(attribute)
        except:
            continue
    missingBB = tickerList

    tickerList = [int(ticker.split()[0]) for ticker in tickers.tickers]
    for item in dataIB.date:
        try:
            if item in tickerList:
                attribute = item
                tickerList.remove(attribute)
        except:
            continue
    missingIB = tickerList
    missingTotal = missingBB + missingIB
    missingTotal = [str(item) for item in missingTotal]

    tickerList = [(ticker.split()[0]) for ticker in tickers.tickers]
    remainTotal = [ticker for ticker in tickerList if ticker not in missingTotal]
    return remainTotal

def main():
    compData('/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/HKCombine/Tickers.csv',
             '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/HKCombine/HKDATA.csv',
             '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/HKCombine/IBData.csv')

if __name__ == '__main__':
    main()




