"""
This program is created by Andrew Li for producing the daily trading reports(Open Position, ClosePosition and PnL)

There are five inputs including:
    1. pathOda: The path of the order file
    2. currExecution: The path of today's execution details
    3. threshold for checking the percentage of execution

The output are indicator and the percentage of executions

The file is lastly modified on 2019/01/22
"""
import pandas as pd
import numpy as np
from functools import reduce
from ibClass import *
from Utilities import check_nan

class execCalculator:

    def __init__(self,
                 pathOda = '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Input/SampleOrder.csv',
                 currExecution = '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Input/SampleExecution.csv',
                 threshold = 0.8
                ):
        self.currOda = pd.read_csv(pathOda, sep=' ')
        self.currExecutionDf = pd.read_csv(currExecution)
        self.threshold = threshold

    def run(self):
        exectotal = self.processing_execution()
        odaTotal = self.compOdaTotalAmount()
        return True if exectotal/odaTotal > self.threshold else False, exectotal/odaTotal

    def processing_execution(self):
        '''Pre-processing the data
            1. For execution file, accumulating total execution amount
            2. For past open position file, read the data into dictionary
        '''
        self.currExecDict = {}
        self.execDict = {}
        for idx, ticker in enumerate(self.currExecutionDf['ticker']):
            if not ticker in self.currExecDict.keys():
                self.currExecDict[ticker] = [self.currExecutionDf.iloc[idx, 2:].values]
            else:
                self.currExecDict[ticker].append(self.currExecutionDf.iloc[idx, 2:].values)

        for key in self.currExecDict.keys():
            '''Accumulate the buy/sell in the execution file'''
            self.execDict[key] = self.sum_exec_details(self.currExecDict[key])

        totalAmount = reduce(lambda x, y: x + y,
                             [float(self.execDict[key])  for key in self.execDict.keys()])
        return totalAmount

    def sum_exec_details(self, args):
        totalCost = 0
        for item in args:
                totalCost += item[1] * item[2]
        return totalCost

    def compOdaTotalAmount(self):
            odaPriceDict = {self.currOda['ticker'].loc[idx]: self.currOda['price'].loc[idx] for idx in
                            range(self.currOda.shape[0])}
            odaShareDict = {self.currOda['ticker'].loc[idx]: self.currOda['quantity'].loc[idx] for idx in
                            range(self.currOda.shape[0])}
            odaTotal = self.compTotalAmount(odaShareDict, odaPriceDict)
            return odaTotal

    def compTotalAmount(self, shareDict, priceDict):
        try:
            totalAmount = reduce(lambda x, y: x + y,
                                 [float(priceDict[key]) * float(share) for key, share in shareDict.items()
                                  if key in priceDict.keys() and not check_nan(priceDict[key])])
        except:
            print('Forced to stop for unexpected ticker name!')
        return totalAmount

def main():
    record = execCalculator()
    indicator, execPercent = record.run()
    print(indicator,execPercent)

if __name__ == '__main__':
    main()
