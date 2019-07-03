"""
This program is created by Andrew Li for producing the daily trading reports(Open Position, ClosePosition and PnL)

There are five inputs including:
    1. pastRecord: The path of the previous open position
    2. currExecution: The path of today's execution details
    3. pathOpenPosition: The path to store open position report
    4. pathClosePosition: The path to store close position report
    5. pathPNL: The path to store PNL report

The output are the three .csv files containing Open Position, ClosePosition and PnL reports

The file is lastly modified on 2018/11/20
"""
import pandas as pd
import numpy as np
from ibClass import *

class Recorder:

    def __init__(self,
                 pastRecord = '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Input/SamplePrevPosition.csv',
                 currRecord = '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Input/LivePrice.csv',
                 currExecution = '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Input/SampleExecution.csv',
                 pathOpenPosition = '../Output/OpenPosition.csv',
                 pathClosePosition = '../Output/ClosePosition.csv',
                 pathPNL = '../Output/pnl.csv'
                ):

        self.pastPositionDf = pd.read_csv(pastRecord)
        self.currPrice = pd.read_csv(currRecord)
        self.currExecutionDf = pd.read_csv(currExecution)
        self.OpenPosition = pd.DataFrame(columns=['Ticker', 'Side', 'Shares', 'inPrice', 'inDate'])
        self.ClosePosition = pd.DataFrame(columns=['Ticker', 'Side', 'Shares', 'inPrice', 'inDate', 'outPrice', 'outDate'])
        self.pathOpenPosition = pathOpenPosition
        self.pathClosePosition = pathClosePosition
        self.pathPNL = pathPNL

    def run(self):
        self.processing_execution()
        self.generate_open_position()
        self.generate_close_position()
        self.generate_pnl_position()


    def generate_open_position(self):
        '''There is two situation in the open position report
            1. The first situation is to continue the previous action like buying in yesturday and continuing to buy today
            2. The second one is to do the reversed action
                a. Fully cover/sell previous position
                b. Partially cover/sell previous position
        '''
        for ticker in self.execDict.keys():
            if ticker not in self.pastDict.keys():
                array = np.hstack([np.array(ticker), np.array(self.execDict[ticker])])
                df = pd.DataFrame(array.reshape(1, -1))
                df.columns = ['Ticker', 'Side', 'Shares', 'inPrice', 'inDate']
                self.OpenPosition = pd.concat((self.OpenPosition, df), axis=0, ignore_index=True)
            else:
                # Side is the same, which means continuing open
                if self.execDict[ticker][0] == self.pastDict[ticker][0][0]:
                    array = np.hstack([np.array(ticker), np.array(self.execDict[ticker])])
                    df = pd.DataFrame(array.reshape(1, -1))
                    df.columns = ['Ticker', 'Side', 'Shares', 'inPrice', 'inDate']
                    self.OpenPosition = self.OpenPosition.append(df)

                # Partially cover previous position
                elif abs(self.execDict[ticker][1]) <  abs(self.pastDict[ticker][0][1]):
                    position = self.pastDict[ticker][0][1] + self.execDict[ticker][1]

                    if position != 0:
                        ave_price = self.update_cost( past_cost=self.pastDict[ticker][0][2], past_position=self.pastDict[ticker][0][1],
                                                     curr_cost=self.execDict[ticker][2], curr_position=self.execDict[ticker][1], position=position)
                        ave_price = float("%0.4f" % (ave_price))
                        array = np.hstack([np.array(ticker), 'BOT' if position > 0 else 'SLD', position, ave_price, np.array(self.execDict[ticker][3:])])
                        df = pd.DataFrame(array.reshape(1, -1))
                        df.columns = ['Ticker', 'Side', 'Shares', 'inPrice', 'inDate']
                        self.OpenPosition = self.OpenPosition.append(df)
                    else:
                        print('The postion of Stock - {} is fully cleared!'.format(ticker))

        self.OpenPosition.to_csv(self.pathOpenPosition, index=False)


    def generate_pnl_position(self):
        '''Calculate the daily pnl'''
        '''pnl from .csv'''
        currPriceDict = {self.currPrice['ticker'].loc[idx]: self.currPrice['last'].loc[idx] for idx in
                         range(self.currPrice.shape[0])}
        DailyPnl = {}
        for key in self.pastDict.keys():
            DailyPnl[key] = self.daily_pnl_calculator(currPrice=currPriceDict[key], aveCost=self.pastDict[key][0][2], position=self.pastDict[key][0][1])
        pnl = pd.DataFrame.from_dict(DailyPnl, orient='index', columns=['PnL'])
        pnl.to_csv(self.pathPNL)

    def generate_close_position(self):
        for ticker in self.execDict.keys():
            if ticker in self.pastDict.keys():
                if not self.execDict[ticker][0] == self.pastDict[ticker][0][0]:
                    array = np.hstack([np.array(ticker), np.array(self.execDict[ticker][0:2]), np.array(self.pastDict[ticker][0][2:]) , np.array(self.execDict[ticker][2:])])
                    df = pd.DataFrame(array.reshape(1, -1))
                    df.columns = ['Ticker', 'Side', 'Shares', 'inPrice', 'inDate', 'outPrice', 'outDate']
                    self.ClosePosition = self.ClosePosition.append(df)
        self.ClosePosition.to_csv(self.pathClosePosition, index=False)


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

        self.pastDict = {}
        for idx, ticker in enumerate(self.pastPositionDf['Ticker']):
            if not ticker in self.pastDict.keys():
                self.pastDict[ticker] = [self.pastPositionDf.iloc[idx, 1:].values]
            # else:
            #     self.pastDict[ticker].append(self.pastPositionDf.iloc[idx, 1:].values)

    def sum_exec_details(self, args):
        cumPosition = 0
        absPosition = 0
        totalCost = 0
        for item in args:
            if item[0] == 'SLD':
                cumPosition -= item[1]
                absPosition += item[1]
                totalCost += item[1] * item[2]
            else:
                cumPosition += item[1]
                absPosition += item[1]
                totalCost += item[1] * item[2]
        return ['SLD', cumPosition, totalCost / absPosition, item[3].split(' ')[0]] if cumPosition < 0 else [
                    'BOT', cumPosition, totalCost / absPosition, item[3].split(' ')[0]]

    def update_cost(self, past_cost, past_position, curr_cost, curr_position, position):
        '''Non-negative cost'''
        return (abs(past_position) * past_cost - abs(curr_position) * curr_cost) / abs(position)

    def daily_pnl_calculator(self, currPrice, aveCost, position):
        '''return the pnl given prices and position'''
        return (currPrice - aveCost) * position


def main():
    record = Recorder()
    record.run()


if __name__ == '__main__':
    main()
