'''
This program is created by Andrew Li for check the split ratio of HK and NAQ data and retrieve their corresponding price

The file is lastly modified on 2018/1/17
'''


import pandas as pd
import numpy as np
from Utilities import *

def checkSplit(splitFile, ori_dataFile, trans_dataFile):
    '''
    This function is to check whether the split is really happened
    :param splitFile:
    :param ori_dataFile:
    :param trans_dataFile:
    :return:
    '''
    df_split = pd.read_csv(splitFile)
    # for idx in range(df_split.shape[0]):
    #     df_split['date'].loc[idx] = changeDate(df_split['date'].loc[idx])
    df_all_data = pd.read_csv(ori_dataFile, header=None, names=['date', 'open', 'high', 'low', 'close', 'volume'])

    dict_split = {}
    for idx, ticker in enumerate(df_split['ticker']):
        if not ': {}'.format(ticker) in dict_split.keys():
            dict_split[': {}'.format(ticker)] = [df_split['date'].values[idx], df_split['ratio'].values[idx]]
        # else:


    date_flag = False
    current_ticker = None
    ticker_result = []
    flag_result = []
    ratio_result = []
    date_result = []

    for idx, ticker in enumerate(df_all_data['date']):
        try:
            if ticker in dict_split.keys():
                if int(dict_split[ticker][0]) > int(df_all_data['date'].loc[idx+1]):
                    date_flag = True
                    current_ticker = ticker
                    print('{} is detected!'.format(ticker))
                    continue
                else:
                    print('Date error of ticker - {}'.format(ticker))

            if date_flag:
                if int(dict_split[current_ticker][0]) == int(ticker):
                    if df_all_data['close'].values[idx - 1] / df_all_data['open'].values[idx] - int(dict_split[current_ticker][1]) < 1:
                        ticker_result.append(
                            ''.join(current_ticker.split(' ')[1]))
                        flag_result.append('Yes')
                        ratio_result.append(float(dict_split[current_ticker][1]))
                        date_result.append('{}'.format(dict_split[current_ticker][0]))
                        date_flag = False
                    else:
                        ticker_result.append(''.join((current_ticker.split(' ')[1])))
                        flag_result.append('No')
                        ratio_result.append(float(dict_split[current_ticker][1]))
                        date_result.append('{}'.format(dict_split[current_ticker][0]))
                        date_flag = False

        except ValueError:
            print('Error of {}'.format(ticker))
            ticker_result.append(''.join((current_ticker.split(' ')[1], ' - {}'.format(dict_split[current_ticker][0]))))
            flag_result.append('No')
            ratio_result.append(float(dict_split[current_ticker][1]))
            date_result.append('{}'.format(dict_split[current_ticker][0]))
            date_flag = False
            if ticker in dict_split.keys():
                if int(dict_split[ticker][0]) > int(df_all_data['date'].loc[idx+1]):
                    date_flag = True
                    current_ticker = ticker
                    print('{} is detected!'.format(ticker))
                    continue
                else:
                    print('Date error of ticker - {}'.format(ticker))


    # a = np.array([ticker_result, flag_result, ratio_result])
    df = pd.DataFrame({'ticker':ticker_result, 'date':date_result,'flag':flag_result, 'ratio':ratio_result})

    df.to_csv(trans_dataFile, index=False)
    # print(a)


def transferSplitFormat(oriSplitFile, transSplitFile):
    '''
    This function is to transfer the original raw split file from bloomberg to usable format
    :param oriSplitFile:
    :param transSplitFile:
    :return:
    '''
    OriginalSplit = pd.read_csv(oriSplitFile, header=None)

    try:
        AllData = []
        for idx in range(OriginalSplit.shape[0]):
            if OriginalSplit.iloc[idx, 1].split()[1] == 'US':
                AllData.append([OriginalSplit.iloc[idx, 1].split()[0], OriginalSplit.iloc[idx, 3],
                                OriginalSplit.iloc[idx, 7].split()[2]])
        AllDataFrame = pd.DataFrame(np.array(AllData), columns=['ticker', 'date', 'ratio'])
        AllDataFrame.to_csv(transSplitFile, index=False)

    except IndexError:
        print('Error')

def retrievePrice(checkSplitFile, oriPrice, retrievedPriceFile):
    '''
    This function is to retrieve the original price after splitting
    :param checkSplitFile:
    :param oriPrice:
    :param retrievedPriceFile:
    :return:
    '''
    splitData = pd.read_csv(checkSplitFile)
    OriginalPrice = pd.read_csv(oriPrice, header=None, names=['date', 'open', 'high', 'low', 'close', 'volume'])
    splitDict = {key: [splitData['date'].loc[idx], splitData['flag'].loc[idx], splitData['ratio'].loc[idx]] for idx, key in enumerate(splitData['ticker'])}

    indicatorTicker = False
    count = 0
    dateIdx = -1
    prevIdx = -1
    for idx, item in enumerate(OriginalPrice['date']):
        try:
            int(item)
            if indicatorTicker == True:
                if splitDict[currTicker][1] == 'Yes':
                    if str(splitDict[currTicker][0]) == str(item):
                        indicatorDate = True
                        dateIdx = idx
                        count += 1
                        print('current count is:{}'.format(count))

            # Handle the last stock
            if idx == OriginalPrice.shape[0] - 1:
                if indicatorTicker == True:
                    convertedPrice = np.concatenate([convertedPrice, OriginalPrice.values[prevIdx:dateIdx, 1:5],
                                                     OriginalPrice.values[dateIdx:idx, 1:5] * splitDict[currTicker][2]],
                                                    axis=0)
                else:
                    convertedPrice = np.concatenate([convertedPrice, OriginalPrice.values[prevIdx:idx, 1:5]], axis=0)

        except:

            if prevIdx == 0:
                if indicatorTicker == False:
                    convertedPrice = OriginalPrice.values[0:idx, 1:5]
                else:
                    convertedPrice = np.concatenate([OriginalPrice.values[prevIdx:dateIdx, 1:5],
                                            OriginalPrice.values[dateIdx:idx, 1:5] * splitDict[currTicker][2]], axis=0)
            elif dateIdx != -1 and indicatorDate:
                convertedPrice = np.concatenate([convertedPrice, OriginalPrice.values[prevIdx:dateIdx, 1:5],
                                            OriginalPrice.values[dateIdx:idx, 1:5] * splitDict[currTicker][2]], axis=0)
            elif prevIdx != -1:
                convertedPrice = np.concatenate([convertedPrice, OriginalPrice.values[prevIdx:idx, 1:5]], axis=0)

            prevIdx = idx

            #HK data key is type of int but NAQ is type of str
            try:
                currTicker = int(item.split(' ')[1])
            except: # Handle the exception error of nan between the line
                print('Error at {}'.format(idx))
                continue
            indicatorDate = False
            indicatorTicker = False
            if currTicker in splitDict.keys():
                indicatorTicker = True
                continue

    df = pd.DataFrame(convertedPrice, columns=['open', 'high', 'low', 'close'])
    df.to_csv(retrievedPriceFile, index=False, header=False)
    convertedPrice = np.concatenate([OriginalPrice.values[:-1,0].reshape(-1,1), convertedPrice,OriginalPrice.values[:-1,5].reshape(-1,1)], axis=1)
    df2 = pd.DataFrame(convertedPrice)
    df2.to_csv(retrievedPriceFile, index=False, header=False)

# def compCorrelation(dir)

def main():
    # transferSplitFormat('/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/NAQCombine/splitUS.csv',
    #                     '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/NAQCombine/convertedSplitUS.csv')

    # checkSplit(ori_dataFile='/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/HKCombine/HK.csv',
    #            splitFile='/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/HKCombine/convertedSplitHK.csv',
    #            trans_dataFile='/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/HKCombine/checkSplitResult.csv')

    retrievePrice(checkSplitFile='/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/HKCombine/checkSplitResult.csv',
                  oriPrice='/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/HKCombine/HK.csv',
                  retrievedPriceFile='/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/HKCombine/RetrievedHK.csv')


if __name__ == '__main__':
   main()