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
import os
from sklearn.linear_model import LinearRegression
from Utilities import *

def model_construction(indexPrice, stockPirce, mode):
    '''Doing regression of the input index and stock'''
    if mode == 'logReturn':
        ReturnIndex = np.nan_to_num(np.diff(np.log(indexPrice)))
        ReturnStock = np.nan_to_num(np.diff(np.log(stockPirce)))
        reg = LinearRegression().fit(ReturnIndex.reshape(-1, 1), ReturnStock.reshape(-1, 1))
    elif mode == 'Return':
        ReturnIndex = np.diff(indexPrice)
        ReturnStock = np.diff(stockPirce)
        reg = LinearRegression().fit(ReturnIndex.reshape(-1, 1), ReturnStock.reshape(-1, 1))
    elif mode == 'Price':
        ReturnIndex = indexPrice
        ReturnStock = stockPirce
        reg = LinearRegression().fit(ReturnIndex.reshape(-1, 1), ReturnStock.reshape(-1, 1))
    else:
        raise ValueError

    return [float("%0.4f" % (reg.intercept_[0])), float("%0.4f" % (reg.coef_[0][0])),
            float("%0.4f" % (np.corrcoef((ReturnStock,ReturnIndex))[0][1]))]

def regression(dirStock = '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/IndividualHKStock/',
               indexPath = '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/Index/HSI.csv',
               regPath = '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Data/Regression Result/regHK.csv',
               mode='logReturn'):
    '''Read the numbers of file inside the stockDir and doing regression one by one'''
    os.chdir(dirStock)
    dfIndex = pd.read_csv(indexPath)
    files = [file for file in os.listdir(dirStock) if file != '.DS_Store']
    main_df = pd.DataFrame(columns=['ticker', 'alpha', 'beta', 'corr'])
    count = 0
    for file in files:
        dfStock = pd.read_csv(file)
        length = dfStock.shape[0]
        for idx, date in enumerate(dfIndex['Date']):
            # HK uncomment fllowing line and NAQ disable the following line
            date = changeDate(date)
            if date == str(dfStock['date'].loc[0]):
                pairedIndex = dfIndex['PX_LAST'].loc[idx : idx + length].values
                try:
                    alpha, beta, corr = model_construction(pairedIndex, dfStock['price'].values, mode)
                except ValueError:
                    # print('Successful - {}!'.format(file))
                    pairedIndex = dfIndex['PX_LAST'].loc[idx: idx + length - 1].values
                    alpha, beta, corr = model_construction(pairedIndex, dfStock['price'].values, mode)
                curr_df = pd.DataFrame(np.array([file.split('.')[0], alpha, beta, corr,]).reshape(1, -1),columns=['ticker', 'alpha', 'beta', 'corr'])
                main_df = pd.concat([main_df, curr_df], axis=0, ignore_index=True)
                break
        count += 1
        if count % 50 == 0:
            print('Compute {} stocks'.format(count))
    main_df.sort_values('beta', ascending=False, inplace=True)
    main_df.to_csv(regPath, index=False)


def main():
    regression()

if __name__ == '__main__':
    main()

