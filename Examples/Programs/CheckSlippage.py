'''
This program is created by Andrew Li for checking the slippage between oda and current price file

There are four inputs including:

    1. odaFilePath: The path to oda file
    2. pricePath: The path to current price file
    3. slippage: The threshold of slippage
    4. pricetype: Three types - mid((ask+bid)/2) default, last, worst(buy-ask, sell-bid)

The output is a True/False whether the total slippage is greater than 1.5%

The file is lastly modified on 2019/1/13
'''

import pandas as pd
import numpy as np
from functools import reduce


from Utilities import check_nan

def checkSlippage(odaFilePath, pricePath, slippage=0.015, mode='last'):
    odaDataFrame = pd.read_csv(odaFilePath)
    priceDataFrame = pd.read_csv(pricePath)

    odaPriceDict = {odaDataFrame['ticker'].loc[idx]: odaDataFrame['price'].loc[idx] for idx in
                 range(odaDataFrame.shape[0])}
    odaShareDict = {odaDataFrame['ticker'].loc[idx]: odaDataFrame['quantity'].loc[idx] for idx in
                    range(odaDataFrame.shape[0])}
    odaActionDict = {odaDataFrame['ticker'].loc[idx]: odaDataFrame['action'].loc[idx] for idx in
                    range(odaDataFrame.shape[0])}

    if mode == 'last':
        currPriceDict = {priceDataFrame['ticker'].loc[idx]:priceDataFrame['last'].loc[idx] for idx in
                     range(priceDataFrame.shape[0])}
    elif mode == 'mid':
        currPriceDict = {priceDataFrame['ticker'].loc[idx]:(priceDataFrame['ask'].loc[idx]+priceDataFrame['bid'].loc[idx])/2
                         for idx in range(priceDataFrame.shape[0])}
    elif mode == 'worst':
        currPriceDict = {}
        for idx,ticker in enumerate(odaDataFrame['ticker']):
            if odaActionDict[ticker] == 'BUY':
                currPriceDict[ticker] = priceDataFrame['ask'].loc[idx]
            else:
                currPriceDict[ticker] = priceDataFrame['bid'].loc[idx]


    odaTotal = compTotalAmount(odaShareDict, odaPriceDict)
    currTotal = compTotalAmount(odaShareDict,currPriceDict)
    currSlippage = abs(odaTotal - currTotal)/odaTotal

    # Significant slippage is detected
    if currSlippage > slippage:
        slippage_dict = {key: float(share) * odaPriceDict[key] / odaTotal for key, share in odaShareDict.items()}
        sorted_slippage = sorted(slippage_dict.items(), key=lambda x: x[1], reverse=True)
        remaining = currSlippage
        count = 0
        while remaining > slippage:
            remaining -= currSlippage * sorted_slippage[count][1]
            count += 1
        for idx in range(count):
            print('The stock - {} has been deleted due to slippage'.format(sorted_slippage[idx][0]))

        # To detect whether the slippage is evenly distributed. If yes, adjust the oda file
        if count > int(0.1 * len(sorted_slippage)):
            print('The slippage is quite even and it is needed to re-adjust the oda file!')

    return True if abs(odaTotal - currTotal)/odaTotal > slippage else False, currSlippage

def compTotalAmount(shareDict, priceDict):
    try:
        totalAmount = reduce(lambda x,y: x+y, [float(priceDict[key])*float(share) for key,share in shareDict.items()
                                               if key in priceDict.keys() and not check_nan(priceDict[key]) ])

    except:
        print('Forced to stop for unexpected ticker name!')
    return totalAmount


def main():
    odaFilePath = '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Input/SampleOrder2.csv'
    pricePath = '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Input/LivePrice.csv'
    slippage = 0.015
    flag, currSlippage = checkSlippage(odaFilePath, pricePath, slippage=slippage, )
    print('Slippage is larger than {}'.format(slippage)) if flag else print('Slippage is less than {}'.format(slippage))

if __name__ == '__main__':
    main()