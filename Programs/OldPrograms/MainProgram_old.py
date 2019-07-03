
import sys
import argparse
import datetime
import collections
import inspect
from time import gmtime, strftime
import queue

import logging
import time
import os.path
import keyboard

import ibapi.wrapper as wrapper
from ibapi.client import EClient
from ibapi.utils import iswrapper

# types
from ibapi.common import *
from ibapi.order_condition import *
from ibapi.contract import *
from ibapi.order import *

import numpy as np
import pandas as pd
from ibapi.order_state import *

from ibapi.utils import (current_fn_name, BadMessage)
from ibapi.errors import *
from ibapi.server_versions import *

from ibapi.execution import Execution
from ibapi.execution import ExecutionFilter
from ibapi.commission_report import CommissionReport
from ibapi.scanner import ScannerSubscription
from ibapi.ticktype import *

from ibapi.account_summary_tags import *




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
    def __init__(self):
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
        self.AllStocksDataframe = pd.DataFrame(columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        self.HistoricalDataTickers = pd.read_csv('/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/NAQCombine/Tickers.csv')
        self.account = 'U9853025'


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
            # self.reqGlobalCancel()
            # self.marketDataType_req()
            # self.accountOperations_req()
            # self.tickDataOperations_req()
            # self.marketDepthOperations_req()
            # self.realTimeBars_req()
            # self.historicalDataRequests_req()
            # self.optionsOperations_req()
            # self.marketScanners_req()
            # self.reutersFundamentals_req()
            # self.bulletins_req()
            # self.contractOperations_req()
            # self.contractNewsFeed_req()
            # self.miscelaneous_req()
            # self.linkingOperations()
            # self.financialAdvisorOperations()
            # self.orderOperations_req()
            # self.marketRuleOperations()
            # self.pnlOperations()
            # self.historicalTicksRequests_req()
            # self.tickByTickOperations()
            # self.whatIfOrder_req()


            # self.OrderOperation('../Input/Book1.csv')
            self.PortfolioOperation()
            # self.ContractDetails('AAPL','STK','SMART','USD')
            # self.PnlDetails()
            self.AccountDetails()
            # self.ExecutionDetails()
            # self.OpenOrderDetails()
            self.HistoricalDataOperation()
            # self.SaveDataOperation()
            print("Executing requests ... finished")
            self.running()

    def keyboardInterrupt(self):
        # self.nKeybInt += 1
        # if self.nKeybInt == 1:
            # self.stop()
        while True:
            command = input('If you want to do it again?')
            if command == 'yes':
                self.start()
            if command == 'cancel':
                self.reqGlobalCancel()
            else:
                self.stop()


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

    # ! [error] self.reqId2nErr[reqId] += 1

    @iswrapper
    def winError(self, text: str, lastError: int):
        super().winError(text, lastError)

    #--------------------------------------------------------------------------------
    # A pair of req and response of account details
    # --------------------------------------------------------------------------------
    @printWhenExecuting
    def PortfolioOperation(self):
        self.reqAccountUpdates(True, self.account)

    def updatePortfolio(self, contract:Contract, position:float,
                        marketPrice:float, marketValue:float,
                        averageCost:float, unrealizedPNL:float,
                        realizedPNL:float, accountName:str):
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

    def contractDetails(self, reqId:int, contractDetails:ContractDetails):
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

    def accountSummary(self, reqId:int, account:str, tag:str, value:str,
                       currency:str):
        super().accountSummary(reqId, account, tag, value, currency)

        print('account:', account, 'tag:', tag, 'value:', value, 'currency:', currency)
        if  account == self.account:
            self.cash_balance = value
            self.cash_balance_curr = currency

    def accountSummaryEnd(self, reqId:int):
        '''After obtained all the required account information, Save the data into the csv file'''
        self.SaveDataOperation()

    def SaveDataOperation(self):

        df = pd.DataFrame(np.array(self.portfolio_list), columns=['Ticker', 'Share', 'Exchange', 'PnL', 'Position'])
        df_cashbalance = pd.DataFrame(np.array([self.cash_balance] * df.shape[0]), columns=['Cash Balance in {}'.format(self.cash_balance_curr)])
        df = pd.concat([df, df_cashbalance], axis=1)
        df.to_csv('../Output/PortfolioFile_{}.csv'.format(strftime("%Y-%m-%d %H:%M:%S", time.localtime())))



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

    def execDetails(self, reqId:int, contract:Contract, execution:Execution):
        super().execDetails(reqId, contract, execution)
        # print('Contract:', contract.symbol, 'Execution:', execution.side)
        self.execDetial_list.append([contract.symbol, contract.exchange, execution.side, execution.shares, execution.avgPrice, execution.time])

    # def commissionReport(self, commissionReport:CommissionReport):
    #     super().commissionReport(commissionReport)
    #     self.execDetial_list[-1].append(commissionReport.commission)

    def execDetailsEnd(self, reqId:int):
        super().execDetailsEnd(reqId)
        df = pd.DataFrame(np.array(self.execDetial_list), columns=[ 'Ticker', 'Exchange', 'Side', 'Share', 'AvePrice', 'Time'])
        df.to_csv('../Output/ExectionFile_{}.csv'.format(strftime("%Y-%m-%d %H:%M:%S", time.localtime())))


    # --------------------------------------------------------------------------------
    # A pair of req and response of Execution Details
    # --------------------------------------------------------------------------------
    @printWhenExecuting
    def OpenOrderDetails(self):
        self.reqOpenOrders()


    def openOrder(self, orderId:OrderId, contract:Contract, order:Order,
                  orderState:OrderState):
        super().openOrder(orderId, contract, order, orderState)
        print('order id:', orderId, 'symbol:', contract.symbol)


    def orderStatus(self, orderId:OrderId , status:str, filled:float,
                    remaining:float, avgFillPrice:float, permId:int,
                    parentId:int, lastFillPrice:float, clientId:int,
                    whyHeld:str, mktCapPrice: float):
        super().orderStatus(orderId , status, filled,
                    remaining, avgFillPrice, permId,
                    parentId, lastFillPrice, clientId,
                    whyHeld, mktCapPrice)

        print('order id:', orderId, 'status:', status, 'filled:', filled, 'remaining:', remaining, 'avgFillPrice:', avgFillPrice)

    # --------------------------------------------------------------------------------
    # A pair of req and response of reqHistorical Data
    # --------------------------------------------------------------------------------
    @printWhenExecuting
    def HistoricalDataOperation(self):
        if self.HistoricalDataTickers:
            self.currStock = self.HistoricalDataTickers.pop(0)
            self.currStockData = []
            contract = self.create_contract(self.currStock, 'STK', 'SEHK', 'HKD')
            queryTime = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y%m%d %H:%M:%S")
            self.reqHistoricalData(self.nextReqId(), contract, queryTime, '6 M', '1 day', 'TRADES', 1, 1, False, [])
        else:
            self.cancelHistoricalData(self.nextReqId())
            self.AllStocksDataframe.to_csv('~/Desktop/AllStockData.csv')
            return

    def historicalData(self, reqId:int, bar: BarData):
        super().historicalData(reqId, bar)
        print("HistoricalData. ", reqId, " Date:", bar.date, "Open:", bar.open,
                 "High:", bar.high, "Low:", bar.low, "Close:", bar.close, "Volume:", bar.volume,
                 "Count:", bar.barCount, "WAP:", bar.average)
        self.currStockData.append([bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume])

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        super().historicalDataEnd(reqId, start, end)
        print("HistoricalDataEnd ", reqId, "from", start, "to", end)
        FirstRow = np.array([self.currStock, None, None, None, None, None])
        currDataframe = pd.DataFrame(np.vstack([FirstRow, self.currStockData]), columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        self.AllStocksDataframe = pd.concat([self.AllStocksDataframe, currDataframe], axis=0, ignore_index=True)

        self.HistoricalDataOperation()



    def OrderOperation(self, path):
        transac_info = pd.read_csv(path, sep=' ')
        order_list = []
        contract_list = []
        for idx in range(transac_info.shape[0]):
            contract_list.append(self.create_contract(symbol=transac_info['symbol'].iloc[idx], sec_type=transac_info['sec_type'].iloc[idx],
                                                      exch=transac_info['exch'].iloc[idx], curr=transac_info['currency'].iloc[idx]))
            order_list.append(self.create_order(action=transac_info['action'].iloc[idx], quantity=transac_info['quantity'].iloc[idx],
                                                order_type=transac_info['order_type'].iloc[idx], price=transac_info['price'].iloc[idx]))


        for idx in range(transac_info.shape[0]):
            self.placeOrder(self.nextOrderId(), contract_list[idx], order_list[idx])
            print('Placing the order {} and current order id {}'.format(contract_list[idx].symbol, self.nextValidOrderId))


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



    def running(self):

        self.run()\



            # ! [clientrun]



def main():
    SetupLogger()
    logging.debug("now is %s", datetime.datetime.now())
    logging.getLogger().setLevel(logging.INFO)


    # print(args)

    # enable logging when member vars are assigned
    from ibapi import utils
    from ibapi.order import Order
    Order.__setattr__ = utils.setattr_log
    from ibapi.contract import Contract, DeltaNeutralContract
    Contract.__setattr__ = utils.setattr_log
    DeltaNeutralContract.__setattr__ = utils.setattr_log
    from ibapi.tag_value import TagValue
    TagValue.__setattr__ = utils.setattr_log
    TimeCondition.__setattr__ = utils.setattr_log
    ExecutionCondition.__setattr__ = utils.setattr_log
    MarginCondition.__setattr__ = utils.setattr_log
    PriceCondition.__setattr__ = utils.setattr_log
    PercentChangeCondition.__setattr__ = utils.setattr_log
    VolumeCondition.__setattr__ = utils.setattr_log

    # from inspect import signature as sig
    # import code code.interact(local=dict(globals(), **locals()))
    # sys.exit(1)

    # tc = TestClient(None)
    # tc.reqMktData(1101, ContractSamples.USStockAtSmart(), "", False, None)
    # print(tc.reqId2nReq)
    # sys.exit(1)


    cmdLineParser = argparse.ArgumentParser("api tests")
    # cmdLineParser.add_option("-c", action="store_True", dest="use_cache", default = False, help = "use the cache")
    # cmdLineParser.add_option("-f", action="store", type="string", dest="file", default="", help="the input file")
    cmdLineParser.add_argument("-p", "--port", action="store", type=int,
                               dest="port", default=7496, help="The TCP port to use")
    cmdLineParser.add_argument("-C", "--global-cancel", action="store_true",
                               dest="global_cancel", default=False,
                               help="whether to trigger a globalCancel req")
    args = cmdLineParser.parse_args()
    print("Using args", args)
    logging.debug("Using args %s", args)
    try:
        app = TestApp()
        if args.global_cancel:
            app.globalCancelOnly = True

        app.connect("127.0.0.1", args.port, clientId=999)
        # ! [connect]
        print("serverVersion:%s connectionTime:%s" % (app.serverVersion(),
                                                      app.twsConnectionTime()))
        app.running()

    except:
        raise
    finally:
        app.dumpTestCoverageSituation()
        app.dumpReqAnsErrSituation()



if __name__ == "__main__":
    main()
