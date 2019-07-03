'''
This program is created by Andrew Li for transforming the raw data downloaded from bloomberg to accessible clean data

format:
Date PX_OPEN PX_HIGH PX_LOW PX_CLOSE Volume
: 700
20151101 200 210 190 201 100000
....
20181101 200 210 190 201 100000
: 1
20151101 200 210 190 201 100000
....
20181101 200 210 190 201 100000

There are two inputs including:
    1. dirStock: The path of directory which store the raw data downloaded from BloomBerg
    2. pathMainDf: The path to store the combined .csv file

The output is the .csv files containing the date, ticker, ohlcv

The file is lastly modified on 2018/11/22
'''
import pandas as pd
import os
import numpy as np
import operator
from Utilities import *

def count_valid_line(df, location):
    for idx in range(1,150):
        if check_nan(df.values[location + idx]) or location + idx == df.shape[0] - 1:
            return idx

def stockTrans(dirStock, pathMainDf):
    os.chdir(dirStock)
    files = [file for file in os.listdir(dirStock) if file != '.DS_Store']
    keys = list(map(lambda t: t.split('_')[1], [string for string in files]))
    int_keys = list(map(lambda t: int(t), [key for key in keys if 'Store' != key]))
    SortedList = sorted(zip(int_keys, files), key= operator.itemgetter(0))
    SortedList = [file for key, file in SortedList]
    ticker_dict = {}
    for which_file, file in enumerate(SortedList):
        if file != '.DS_Store':
            print('File is changed to {}'.format(file))
            df = pd.read_csv(file)
            CleanData = pd.DataFrame(columns=['tickers', 'Output', 'Date', 'PX_OPEN', 'PX_HIGH', 'PX_LOW', 'PX_CLOSE', 'Volume'])
            CleanData['tickers'] = df.values[2:len(df.values[:, 4]), 0]
            CleanData['Output'] = df.values[2:len(df.values[:, 4]), 3]
            temp_date = change_date_format(df.values[2:len(df.values[:, 4]), 4])
            CleanData['Date'] = np.array(temp_date)
            CleanData['PX_OPEN'] = df.values[2:len(df.values[:, 4]), 5]
            CleanData['PX_HIGH'] = df.values[2:len(df.values[:, 4]), 6]
            CleanData['PX_LOW'] = df.values[2:len(df.values[:, 4]), 7]
            CleanData['PX_CLOSE'] = df.values[2:len(df.values[:, 4]), 8]
            volume = df.values[2:len(df.values[:, 4]), 9]
            CleanData['Volume'] = np.divide(volume.astype(np.float), 100)

            number_ticker = 0
            for idx, FullTicker in enumerate(CleanData['tickers']):
                if check_nan(FullTicker):
                    break

                if not FullTicker in ticker_dict.keys():
                    try:
                        cleanData_location = CleanData[CleanData['Output'] == FullTicker].index[0]
                        if not check_nan(CleanData['PX_OPEN'].values[cleanData_location]):
                            if check_nan(CleanData['PX_CLOSE'].values[cleanData_location]):
                                cleanData_length = count_valid_line(CleanData['Date'], cleanData_location)
                                ticker_dict[FullTicker] = [CleanData.values[cleanData_location + 1: cleanData_location + cleanData_length, 2:]]
                            else:
                                cleanData_length = count_valid_line(CleanData['Date'], cleanData_location)
                                ticker_dict[FullTicker] = [CleanData.values[cleanData_location: cleanData_location + cleanData_length, 2:]]
                        else:
                            pass
                            # print('There is no data of {} at the file - {}'.format(FullTicker, file))
                    except IndexError:
                        pass
                        # print(''.join([FullTicker, ' is not in the file - {}!'.format(file)]))
                else:
                    try:
                        cleanData_location = CleanData[CleanData['Output'] == FullTicker].index[0]
                        if not check_nan(CleanData['PX_OPEN'].values[cleanData_location]):
                            cleanData_length = count_valid_line(CleanData['Date'], cleanData_location)
                            ticker_dict[FullTicker].append(CleanData.values[cleanData_location: cleanData_location + cleanData_length, 2:])
                        else:
                            # print('There is no data of {} at the file - {}'.format(FullTicker, file))
                            pass
                    except IndexError:
                        pass
                        # print(''.join([FullTicker, ' is not in the file - {}!'.format(file)]))


    main_list = np.array([None, None, None, None, None, None])
    for idx, key in enumerate(ticker_dict.keys()):
        ticker = key.split()[0]
        main_list = np.vstack((main_list,np.array([': {}'.format(ticker), None, None, None, None, None])))
        length = len(ticker_dict[key])
        for num_array in range(length):
            x = np.array(ticker_dict[key].pop(0))
            main_list = np.vstack((main_list, x))
        if idx % 50 == 0:
            print('{} stocks have been saved!'.format(idx))

    main_list = np.array(main_list)
    main_df = pd.DataFrame(main_list ,columns=['Date', 'PX_OPEN', 'PX_HIGH', 'PX_LOW', 'PX_LAST', 'Volume'])
    main_df.to_csv(pathMainDf, index=False)


def main():
    workDir = '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/NAQEx4'
    outDir = '/Users/andrew/Desktop/Combined_file.csv'
    stockTrans(workDir, outDir)

if __name__ == '__main__':
    main()