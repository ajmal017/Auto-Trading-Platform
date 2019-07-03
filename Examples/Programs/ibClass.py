'''
This program is created by Andrew Li for connecting with Interactive Brokers

There are three main functions including:

    1. TRADE: This function is to send ODA file to IB
    2. EXEC: This function is to check how many orders have been executed and save the executions to a .csv file
    3. ACCOUNT: This function is to retrieve the portfolio status of the account and save the open position to a .csv file

The file is lastly modified on 2018/11/22
'''

import sys
import argparse
import datetime
import collections
import inspect
from time import gmtime, strftime, sleep
import queue

import logging
import time
import os.path
import threading
import keyboard

import ibapi.wrapper as wrapper
from ibapi.client import EClient
from ibapi.utils import iswrapper

# types
from ibapi.common import *
from ibapi.order_condition import *
from ibapi.contract import *
from ibapi.order import *
from ibapi.ticktype import *

import numpy as np
import pandas as pd
from ibapi.order_state import *

from ibapi.execution import Execution
from ibapi.execution import ExecutionFilter

from source_sample.ContractSamples import ContractSamples

def SetupLogger():
    if not os.path.exists("log"):
        os.makedirs("log")

    time.strftime("pyibapi.%Y%m%d_%H%M%S.log")

    recfmt = '(%(threadName)s) %(asctime)s.%(msecs)03d %(levelname)s %(filename)s:%(lineno)d %(message)s'

    timefmt = '%y%m%d_%H:%M:%S'

    # logging.basicConfig( level=logging.DEBUG,
    #                    format=recfmt, datefmt=timefmt)
    logging.basicConfig(filename=time.strftime("log/pyibapi.%y%m%d_%H%M%S.log"),
                        filemode="w",
                        level=logging.INFO,
                        format=recfmt, datefmt=timefmt)
    logger = logging.getLogger()
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logger.addHandler(console)


def printWhenExecuting(fn):
    def fn2(self):
        print("   doing", fn.__name__)
        fn(self)
        print("   done w/", fn.__name__)

    return fn2


def printinstance(inst: Object):
    attrs = vars(inst)
    print(', '.join("%s: %s" % item for item in attrs.items()))


class Activity(Object):
    def __init__(self, reqMsgId, ansMsgId, ansEndMsgId, reqId):
        self.reqMsdId = reqMsgId
        self.ansMsgId = ansMsgId
        self.ansEndMsgId = ansEndMsgId
        self.reqId = reqId


class RequestMgr(Object):
    def __init__(self):
        # I will keep this simple even if slower for now: only one list of
        # requests finding will be done by linear search
        self.requests = []

    def addReq(self, req):
        self.requests.append(req)

    def receivedMsg(self, msg):
        pass


# ! [socket_declare]
class TestClient(EClient):
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)
        # ! [socket_declare]

        # how many times a method is called to see test coverage
        self.clntMeth2callCount = collections.defaultdict(int)
        self.clntMeth2reqIdIdx = collections.defaultdict(lambda: -1)
        self.reqId2nReq = collections.defaultdict(int)
        self.setupDetectReqId()

    def countReqId(self, methName, fn):
        def countReqId_(*args, **kwargs):
            self.clntMeth2callCount[methName] += 1
            idx = self.clntMeth2reqIdIdx[methName]
            if idx >= 0:
                sign = -1 if 'cancel' in methName else 1
                self.reqId2nReq[sign * args[idx]] += 1
            return fn(*args, **kwargs)

        return countReqId_

    def setupDetectReqId(self):

        methods = inspect.getmembers(EClient, inspect.isfunction)
        for (methName, meth) in methods:
            if methName != "send_msg":
                # don't screw up the nice automated logging in the send_msg()
                self.clntMeth2callCount[methName] = 0
                # logging.debug("meth %s", name)
                sig = inspect.signature(meth)
                for (idx, pnameNparam) in enumerate(sig.parameters.items()):
                    (paramName, param) = pnameNparam
                    if paramName == "reqId":
                        self.clntMeth2reqIdIdx[methName] = idx

                setattr(TestClient, methName, self.countReqId(methName, meth))

                # print("TestClient.clntMeth2reqIdIdx", self.clntMeth2reqIdIdx)


# ! [ewrapperimpl]
class TestWrapper(wrapper.EWrapper):
    # ! [ewrapperimpl]
    def __init__(self):
        wrapper.EWrapper.__init__(self)

        self.wrapMeth2callCount = collections.defaultdict(int)
        self.wrapMeth2reqIdIdx = collections.defaultdict(lambda: -1)
        self.reqId2nAns = collections.defaultdict(int)
        self.setupDetectWrapperReqId()

    # TODO: see how to factor this out !!

    def countWrapReqId(self, methName, fn):
        def countWrapReqId_(*args, **kwargs):
            self.wrapMeth2callCount[methName] += 1
            idx = self.wrapMeth2reqIdIdx[methName]
            if idx >= 0:
                self.reqId2nAns[args[idx]] += 1
            return fn(*args, **kwargs)

        return countWrapReqId_

    def setupDetectWrapperReqId(self):

        methods = inspect.getmembers(wrapper.EWrapper, inspect.isfunction)
        for (methName, meth) in methods:
            self.wrapMeth2callCount[methName] = 0
            # logging.debug("meth %s", name)
            sig = inspect.signature(meth)
            for (idx, pnameNparam) in enumerate(sig.parameters.items()):
                (paramName, param) = pnameNparam
                # we want to count the errors as 'error' not 'answer'
                if 'error' not in methName and paramName == "reqId":
                    self.wrapMeth2reqIdIdx[methName] = idx

            setattr(TestWrapper, methName, self.countWrapReqId(methName, meth))

            # print("TestClient.wrapMeth2reqIdIdx", self.wrapMeth2reqIdIdx)


# this is here for documentation generation
"""
#! [ereader]
        # You don't need to run this in your code!
        self.reader = reader.EReader(self.conn, self.msg_queue)
        self.reader.start()   # start thread
#! [ereader]
"""


# ! [socket_init]
class TestApp(TestWrapper, TestClient):
    def __init__(self, action, account, tradingFile = None, execFile = None, acctFile = None, tickerFile = None, allDataPath = None,
                 openPricePath = None, priceType = None, singleTicker = None):
        TestWrapper.__init__(self)
        TestClient.__init__(self, wrapper=self)
        # ! [socket_init]
        self.nKeybInt = 0
        self.started = False
        self.nextValidOrderId = None
        self.nextValidReqId = 1000
        self.permId2ord = {}
        self.reqId2nErr = collections.defaultdict(int)
        self.globalCancelOnly = False
        self.simplePlaceOid = None
        self.portfolio_list = []
        self.execDetial_list = []
        self.currStockData = []
        self.action_type = action
        self.account = account
        self.tradingFile = tradingFile
        self.execFile = execFile
        self.acctFile = acctFile
        self.count = 0
        if action == 'HISTDATA':
            self.AllStocksDataframe = pd.DataFrame(columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
            self.HistoricalDataTickers = pd.read_csv(
                tickerFile, names=['Tickers']).values.tolist()
            self.pathSaveAllStock = allDataPath
            self.HistoricalDataTickers = [ticker for sublist in self.HistoricalDataTickers for ticker in sublist]
            self.listReqTicker = []

        if action == 'LIVEPRICE':
            self.TickerArray = []
            self.TickerList = pd.read_csv(
                tickerFile)['ticker'].values.tolist()
            # self.TickerList = pd.read_csv(
            #     tickerFile, names=['Tickers']).values.tolist()
            self.OpenPriceList = []
            self.OpenPricePath = openPricePath
            self.prevReqList = []
            self.priceType = priceType
            self.mktSnapShot_dict = {}
            self.undoTasks = 0

    def dumpTestCoverageSituation(self):
        for clntMeth in sorted(self.clntMeth2callCount.keys()):
            logging.debug("ClntMeth: %-30s %6d" % (clntMeth,
                                                   self.clntMeth2callCount[clntMeth]))

        for wrapMeth in sorted(self.wrapMeth2callCount.keys()):
            logging.debug("WrapMeth: %-30s %6d" % (wrapMeth,
                                                   self.wrapMeth2callCount[wrapMeth]))

    def dumpReqAnsErrSituation(self):
        logging.debug("%s\t%s\t%s\t%s" % ("ReqId", "#Req", "#Ans", "#Err"))
        for reqId in sorted(self.reqId2nReq.keys()):
            nReq = self.reqId2nReq.get(reqId, 0)
            nAns = self.reqId2nAns.get(reqId, 0)
            nErr = self.reqId2nErr.get(reqId, 0)
            logging.debug("%d\t%d\t%s\t%d" % (reqId, nReq, nAns, nErr))



    @iswrapper
    # ! [connectack]
    def connectAck(self):
        if self.async:
            self.startApi()

    # ! [connectack]

    @iswrapper
    # ! [nextvalidid]
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)

        logging.debug("setting nextValidOrderId: %d", orderId)
        self.nextValidOrderId = orderId
        # ! [nextvalidid]

        # we can start now
        self.start()


    def start(self):
        # if self.started:
        #     return

        # self.started = True

        if self.globalCancelOnly:
            print("Executing GlobalCancel only")
            self.reqGlobalCancel()
        else:
            print("Executing requests")

            if self.action_type == 'TRADE':
                self.OrderOperation(self.tradingFile)
            elif self.action_type == 'ACCOUNT':
                self.PnlDetails()
                self.PortfolioOperation()
                self.AccountDetails()
            elif self.action_type == 'EXEC':
                self.ExecutionDetails()
            elif self.action_type == 'HISTDATA':
                self.HistoricalDataOperation()
            elif self.action_type == 'LIVEPRICE':
                self.LiveMarketOperation()
            elif self.action_type == 'SINGLEPRICE':
                self.SinglePrice()
            # self.PortfolioOperation()
            # self.PnlDetails()
            # self.AccountDetails()
            # self.ExecutionDetails()
            # self.OpenOrderDetails()
            # self.SaveDataOperation()
            print("Executing requests ... finished")
            # self.running()


    # def keyboardInterrupt(self):
    #     # self.nKeybInt += 1
    #     # if self.nKeybInt == 1:
    #     # self.stop()
    #     while True:
    #         command = input('If you want to do it again?')
    #         if command == 'yes':
    #             self.start()
    #         if command == 'cancel':
    #             self.reqGlobalCancel()
    #         else:
    #             self.stop()


    def stop(self):
        print("Executing cancels")
        # self.orderOperations_cancel()
        # self.accountOperations_cancel()
        # self.tickDataOperations_cancel()
        # self.marketDepthOperations_cancel()
        # self.realTimeBars_cancel()
        # self.historicalDataRequests_cancel()
        # self.optionsOperations_cancel()
        # self.marketScanners_cancel()
        # self.reutersFundamentals_cancel()
        # self.bulletins_cancel()
        print("Executing cancels ... finished")


    def nextOrderId(self):
        oid = self.nextValidOrderId
        self.nextValidOrderId += 1
        return oid


    def nextReqId(self):
        reqid = self.nextValidReqId
        self.nextValidReqId += 1
        return reqid


    @iswrapper
    # ! [error]
    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        super().error(reqId, errorCode, errorString)
        print("Error. Id: ", reqId, " Code: ", errorCode, " Msg: ", errorString)
        if errorCode == 200 or errorCode ==  162:
            try:
                self.listReqTicker.pop(0)
                self.HistoricalDataOperation()
            except:
                # BadTicker = self.TickerList.pop(0)
                # print('Bad ticker is: ', BadTicker)
                self.undoTasks -= 1
                self.count += 1
                # self.LiveMarketOperation()


    # ! [error] self.reqId2nErr[reqId] += 1

    @iswrapper
    def winError(self, text: str, lastError: int):
        super().winError(text, lastError)

    def currentTime(self, time: int):
        print('time is: ',time)
    # --------------------------------------------------------------------------------
    # A pair of req and response of live open price
    # --------------------------------------------------------------------------------
    def LiveMarketOperation(self):
        length_of_tickers = len(self.TickerList)
        if length_of_tickers > 100:
            self.undoTasks = 100
            idx = 0
            while idx < 100:
                currStock = str(self.TickerList[0][0]).split()[0]
                contract = self.create_contract(currStock, 'STK', 'SEHK', 'HKD')
                # data sequence ticker, bid, ask, last, open, high, low, volume
                self.mktSnapShot_dict[self.nextValidReqId] = [currStock, None, None, None, None, None, None, None]
                self.reqMktData(self.nextReqId(), contract, '', True, False, [])
                try:
                    self.TickerList.pop(0)
                except IndexError or KeyError:
                    print('Error!')
                idx += 1
        elif length_of_tickers > 0:
            self.undoTasks = length_of_tickers
            idx = 0
            while idx < length_of_tickers:
                currStock = str(self.TickerList[0]).split()[0]
                contract = self.create_contract(currStock, 'STK', 'SEHK', 'HKD')
                # data sequence ticker, bid, ask, last, open, high, low, volume
                self.mktSnapShot_dict[self.nextValidReqId] = [currStock, None, None, None, None, None, None, None]
                self.reqMktData(self.nextReqId(), contract, '', True, False, [])
                try:
                    self.TickerList.pop(0)
                except IndexError or KeyError:
                    print('Error!')
                idx += 1

        else:
            df = pd.DataFrame.from_dict(self.mktSnapShot_dict, orient='index', columns=['ticker', 'bid', 'ask', 'last', 'open', 'high', 'low', 'volume'])
            df.to_csv(self.OpenPricePath, index=False)
            self.done = True


    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float, attrib: TickAttrib):
        super().tickPrice(reqId, tickType, price, attrib)
        if tickType == TickTypeEnum.BID:
            self.mktSnapShot_dict[reqId][1] = price
        elif tickType == TickTypeEnum.ASK:
            self.mktSnapShot_dict[reqId][2] = price
        elif tickType == TickTypeEnum.LAST:
            self.mktSnapShot_dict[reqId][3] = price
        elif tickType == TickTypeEnum.OPEN:
            self.mktSnapShot_dict[reqId][4] = price
        elif tickType == TickTypeEnum.HIGH:
            self.mktSnapShot_dict[reqId][5] = price
        elif tickType == TickTypeEnum.LOW:
            self.mktSnapShot_dict[reqId][6] = price


    def tickGeneric(self, reqId:TickerId, tickType:TickType, value:float):
        '''Handle the situation that Stock is halted and no open price'''
        super().tickGeneric(reqId, tickType, value)
        # print(reqId)
        if tickType == TickTypeEnum.HALTED and reqId not in self.prevReqList:
            # self.cancelMktData(self.nextValidReqId - 1)
            # self.TickerList.pop(0)
            self.prevReqList.append(reqId)
            # self.undoTasks -= 1


    def tickSize(self, reqId: TickerId, tickType: TickType, size: int):
        super().tickSize(reqId, tickType, size)
        if tickType == TickTypeEnum.VOLUME:
            self.mktSnapShot_dict[reqId][7] = size

    def tickSnapshotEnd(self, reqId:int):
        super().tickSnapshotEnd(reqId)
        self.undoTasks -= 1
        self.count += 1
        print('current count is {}'.format(self.count))
        # if self.count % 50 == 0:
        #     print('{} is done'.format(self.count))
        if self.undoTasks == 0:
            sleep(0.5)
            self.LiveMarketOperation()

    # def tickReqParams(self, tickerId: int, minTick: float,bboExchange:str, snapshotPermissions: int):
    #     super().tickReqParams(tickerId, minTick, bboExchange, snapshotPermissions)
    #
    #     print("TickReqParams. TickerId:", tickerId, "MinTick:", minTick,"BboExchange:", bboExchange,
    #           "SnapshotPermissions:", snapshotPermissions)
    # --------------------------------------------------------------------------------
    # A pair of req and response of account details
    # --------------------------------------------------------------------------------
    @printWhenExecuting
    def PortfolioOperation(self):
        self.reqAccountUpdates(True, self.account)


    def updatePortfolio(self, contract: Contract, position: float,
                        marketPrice: float, marketValue: float,
                        averageCost: float, unrealizedPNL: float,
                        realizedPNL: float, accountName: str):
        super().updatePortfolio(contract, position,
                                marketPrice, marketValue,
                                averageCost, unrealizedPNL,
                                realizedPNL, accountName)
        if position > 0:
            self.portfolio_list.append([contract.symbol, position, contract.primaryExchange, unrealizedPNL, 'Long'])
        else:
            self.portfolio_list.append([contract.symbol, position, contract.primaryExchange, unrealizedPNL, 'Short'])


    # --------------------------------------------------------------------------------
    # A pair of req and response of contract details
    # --------------------------------------------------------------------------------
    def ContractDetails(self, *args):
        self.reqContractDetails(self.nextReqId(), self.create_contract(*args))


    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        super().contractDetails(reqId, contractDetails)
        print(contractDetails.contract)


    # --------------------------------------------------------------------------------
    # A pair of req and response of PNL
    # --------------------------------------------------------------------------------
    @printWhenExecuting
    def PnlDetails(self):
        self.reqPnL(self.nextReqId(), self.account, '')


    def pnl(self, reqId: int, dailyPnL: float, unrealizedPnL: float, realizedPnL: float):
        super().pnl(reqId, dailyPnL, unrealizedPnL, realizedPnL)
        print('daily pnl:', dailyPnL, 'unrealizedPnL:', unrealizedPnL, 'realizedPnL:', realizedPnL)
        self.cancelPnL(reqId)


    # --------------------------------------------------------------------------------
    # A pair of req and response of AccountSummary
    # --------------------------------------------------------------------------------
    @printWhenExecuting
    def AccountDetails(self):
        self.reqAccountSummary(self.nextReqId(), 'All', 'TotalCashValue')


    def accountSummary(self, reqId: int, account: str, tag: str, value: str,
                       currency: str):
        super().accountSummary(reqId, account, tag, value, currency)

        print('account:', account, 'tag:', tag, 'value:', value, 'currency:', currency)
        if account == self.account:
            self.cash_balance = value
            self.cash_balance_curr = currency


    # # --------------------------------------------------------------------------------
    # # A pair of req and response of Execution Details
    # # --------------------------------------------------------------------------------
    @printWhenExecuting
    def ExecutionDetails(self):
        self.reqExecutions(self.nextReqId(), self.create_ExecutionFilter())


    def create_ExecutionFilter(self):
        filter = ExecutionFilter()
        filter.clientId = 999
        filter.acctCode = self.account
        yesterday = datetime.datetime.now() - datetime.timedelta(1)
        filter.time = yesterday.strftime('%Y%m%d-18:00:00')
        return filter


    def execDetails(self, reqId: int, contract: Contract, execution: Execution):
        super().execDetails(reqId, contract, execution)
        # print('Contract:', contract.symbol, 'Execution:', execution.side)
        self.execDetial_list.append(
            [contract.symbol, contract.exchange, execution.side, execution.shares, execution.avgPrice, execution.time])


    # def commissionReport(self, commissionReport:CommissionReport):
    #     super().commissionReport(commissionReport)
    #     self.execDetial_list[-1].append(commissionReport.commission)

    def execDetailsEnd(self, reqId: int):
        super().execDetailsEnd(reqId)
        if self.execDetial_list:
            df = pd.DataFrame(np.array(self.execDetial_list),
                              columns=['ticker', 'exchange', 'side', 'share', 'avePrice', 'time'])
            df.to_csv('{}/ExecutionFile.csv'.format(self.execFile),index=False)
            # df.to_csv('{}/ExectionFile_{}.csv'.format(self.execFile, strftime("%Y-%m-%d %H:%M:%S", time.localtime())), index=False)
            self.done = True
            self.ExecutionIndicator = True
        else:
            print('There is no execution within the day!')
            self.done = True
            self.ExecutionIndicator = False


    # --------------------------------------------------------------------------------
    # A pair of req and response of Execution Details
    # --------------------------------------------------------------------------------
    @printWhenExecuting
    def OpenOrderDetails(self):
        self.reqOpenOrders()


    def openOrder(self, orderId: OrderId, contract: Contract, order: Order,
                  orderState: OrderState):
        super().openOrder(orderId, contract, order, orderState)
        print('order id:', orderId, 'symbol:', contract.symbol)


    def orderStatus(self, orderId: OrderId, status: str, filled: float,
                    remaining: float, avgFillPrice: float, permId: int,
                    parentId: int, lastFillPrice: float, clientId: int,
                    whyHeld: str, mktCapPrice: float):
        super().orderStatus(orderId, status, filled,
                            remaining, avgFillPrice, permId,
                            parentId, lastFillPrice, clientId,
                            whyHeld, mktCapPrice)

        print('order id:', orderId, 'status:', status, 'filled:', filled, 'remaining:', remaining, 'avgFillPrice:',
              avgFillPrice)

    # --------------------------------------------------------------------------------
    # Req Single Price
    # --------------------------------------------------------------------------------
    # def SinglePrice(self):
    #     self.disconnect()
    #     return True
    # --------------------------------------------------------------------------------
    # A pair of req and response of reqHistorical Data
    # --------------------------------------------------------------------------------
    def HistoricalDataOperation(self):
        if self.HistoricalDataTickers:
            self.count += 1
            if self.count % 20 == 0:
                print('{} stocks have been stored!'.format(self.count))
            self.currStock = self.HistoricalDataTickers.pop(0).split()[0]
            contract = self.create_contract(self.currStock, 'STK', 'SEHK', 'HKD')
            queryTime = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y%m%d %H:%M:%S")
            self.reqHistoricalData(self.nextReqId(), contract, queryTime, '6 M', '1 day', 'TRADES', 1, 1, False, [])
            self.listReqTicker.append(self.currStock)
        elif not self.listReqTicker:
            self.AllStocksDataframe.to_csv(self.pathSaveAllStock, index=False, header=False)
            self.historicalDataRequests_cancel()

    def historicalData(self, reqId:int, bar: BarData):
        super().historicalData(reqId, bar)
        # print("HistoricalData. ", reqId, " Date:", bar.date, "Open:", bar.open,
        #          "High:", bar.high, "Low:", bar.low, "Close:", bar.close, "Volume:", bar.volume,
        #          "Count:", bar.barCount, "WAP:", bar.average)
        self.currStockData.append([bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume])

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        super().historicalDataEnd(reqId, start, end)
        # print("HistoricalDataEnd ", reqId, "from", start, "to", end)
        try:
            currTicker = self.listReqTicker.pop(0)
        except:
            return self.HistoricalDataOperation()
        FirstRow = np.array([currTicker, None, None, None, None, None])
        currDataframe = pd.DataFrame(np.vstack([FirstRow, self.currStockData]), columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        self.AllStocksDataframe = pd.concat([self.AllStocksDataframe, currDataframe], axis=0, ignore_index=True)
        self.currStockData = []
        time.sleep(0.1)
        self.HistoricalDataOperation()

    @printWhenExecuting
    def historicalDataRequests_cancel(self):
        # Canceling historical data requests
        self.cancelHistoricalData(self.nextReqId())
        self.action_type = None

    # def openOrder(self, orderId:OrderId, contract:Contract, order:Order,
    #               orderState:OrderState):
    #     super().openOrder(orderId, contract, order, orderState)
    #     self.orderStatusList = []
    #     # self.orderStatusList.append(orderId, contract.symbol, contract.exchange, order.action)
    #
    #
    # def orderStatus(self, orderId:OrderId , status:str, filled:float,
    #                 remaining:float, avgFillPrice:float, permId:int,
    #                 parentId:int, lastFillPrice:float, clientId:int,
    #                 whyHeld:str, mktCapPrice: float):
    #     super().orderStatus(orderId , status, filled,
    #                 remaining, avgFillPrice, permId,
    #                 parentId, lastFillPrice, clientId,
    #                 whyHeld, mktCapPrice)
    #
    #     if filled != 0:
    #         # self.orderStatusList.append(filled, avgFillPrice)
    #         pass

    def accountSummaryEnd(self, reqId: int):
        '''After obtained all the required account information, Save the data into the csv file'''
        self.SaveDataOperation()


    def SaveDataOperation(self):
        df = pd.DataFrame(np.array(self.portfolio_list), columns=['Ticker', 'Share', 'Exchange', 'PnL', 'Position'])
        df_cashbalance = pd.DataFrame(np.array([self.cash_balance] * df.shape[0]),
                                      columns=['Cash Balance in {}'.format(self.cash_balance_curr)])
        df = pd.concat([df, df_cashbalance], axis=1)
        df.to_csv('{}/PortfolioFile_{}.csv'.format(self.acctFile, strftime("%Y-%m-%d %H:%M:%S", time.localtime())), index=False)
        self.done

    def OrderOperation(self, path):
        transac_info = pd.read_csv(path)
        order_list = []
        contract_list = []
        for idx in range(transac_info.shape[0]):
            contract_list.append(
                self.create_contract(symbol=transac_info['ticker'].iloc[idx], sec_type=transac_info['sec_type'].iloc[idx],
                                     exch=transac_info['exch'].iloc[idx], curr=transac_info['currency'].iloc[idx]))
            order_list.append(
                self.create_order(action=transac_info['action'].iloc[idx], quantity=transac_info['quantity'].iloc[idx],
                                  order_type=transac_info['order_type'].iloc[idx], price=transac_info['price'].iloc[idx]))

        for idx in range(transac_info.shape[0]):
            self.placeOrder(self.nextOrderId(), contract_list[idx], order_list[idx])
            print('Placing the order {} and current order id {}'.format(contract_list[idx].symbol, self.nextValidOrderId))
            sleep(0.2)
        # self.done = True

    def nextOrderId(self):
        oid = self.nextValidOrderId
        self.nextValidOrderId += 1
        return oid


    def create_contract(self, symbol, sec_type, exch, curr):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = sec_type
        contract.exchange = exch
        contract.currency = curr

        return contract


    def create_order(self, action, quantity, order_type, price=None):
        order = Order()
        if order_type == 'LMT':
            order.action = action
            order.orderType = 'LMT'
            order.totalQuantity = quantity
            order.lmtPrice = price
        elif order_type == 'MKT':
            order.action = action
            order.orderType = 'MKT'
            order.totalQuantity = quantity
        return order


    # def running(self):
    #     # print('')
    #     self.run()

