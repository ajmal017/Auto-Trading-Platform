'''
This program is created by Andrew Li for checking the executed stocks within the day to readjust the limited price and
jobs are the following:

    1.retrieve the execution details from IB
    2.compute the percentage of how many stocks have been executed
    3.prepare the execution file for strategy

The file is lastly modified on 2018/11/22
'''

from ibClass import *
from CompExecution import execCalculator
#########################################
# Modify the details here
#########################################

# Personal Account
Account = 'DU1196175'

# The directory to store the execution report
pathOda = '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Input/SampleOrder.csv'
currExecution = '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Output/ExecutionFile.csv'
pathExecution =  '/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Output/'
#########################################

def main():
    SetupLogger()
    logging.debug("now is %s", datetime.datetime.now())
    logging.getLogger().setLevel(logging.INFO)

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
        app = TestApp(action='EXEC', account=Account, execFile=pathExecution)
        if args.global_cancel:
            app.globalCancelOnly = True

        app.connect("127.0.0.1", args.port, clientId=999)
        # ! [connect]
        print("serverVersion:%s connectionTime:%s" % (app.serverVersion(),
                                                      app.twsConnectionTime()))
        app.run()
        app.disconnect()

        if app.ExecutionIndicator == True:
            calculator = execCalculator(pathOda=pathOda, currExecution=currExecution, threshold=0.8)
            indicator, execPercent = calculator.run()
            print(indicator, execPercent)
        else:
            print('There is no any execution within the day and no execution file is generated!')
    except:
        raise


if __name__ == "__main__":
    main()
