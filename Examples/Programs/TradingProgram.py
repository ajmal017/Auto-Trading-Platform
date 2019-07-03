'''
The program is created by Andrew Li and it is the main trading program which should do the following jobs sequentially:

1. Download the live prices from IB and save to the indicated address
2. Compute the slippage by using the ODA and live  price files
3. If passed the slippage check, execute the orders through IB

The file is lastly modified on 2019/01/24
'''

from ibClass import *
from CheckSlippage import *
#########################################
# Modify the details here
#########################################

#########################################

# Account = 'U9853025'
Account = 'DU1196175'

# The directory to store the execution report
pathOda = '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Input/SampleOrder2.csv'
pathLivePrice = '~/Desktop/LivePrice.csv'
priceType = 'Live'
#########################################

def main():
    SetupLogger()
    logging.debug("now is %s", datetime.datetime.now())
    logging.getLogger().setLevel(logging.ERROR)

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
        # Step 1: Ask for live prices
        print('Downloading the live price...')
        app1 = TestApp(action='LIVEPRICE', account=Account, openPricePath=pathLivePrice, tickerFile=pathOda, priceType=priceType)
        app1.connect("127.0.0.1", args.port, clientId=999)
        app1.run()
        app1.disconnect()

        # Step 2: Compute the slippage
        print('Checking the slippage...')
        indicator, slippage = checkSlippage(odaFilePath=pathOda, pricePath=pathLivePrice, slippage=0.015, mode='last')
        print('Current slippage is {}'.format(slippage))

        # Step 3: Place the orders
        if indicator == False:
            print('Placing the order...')
            app2 = TestApp(action='TRADE', account=Account, tradingFile=pathOda)
            app2.connect("127.0.0.1", args.port, clientId=999)
            app2.run()
            app2.disconnect()
        else:
            print('Slippage check failed and resend the live price')

    except:
        raise
    # finally:
    #     app2.dumpTestCoverageSituation()
    #     app2.dumpReqAnsErrSituation()

if __name__ == "__main__":
    main()
