import pandas as pd
import os
import numpy as np
os.chdir('/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Test_Data')
files = [file for file in os.listdir('/Users/andrew/Desktop/HKUST/Projects/IB/Test_1101/Test_Data')]


def check_nan(args):
    return str(args) == str(1e400*0)

def count_valid_line(df):
    length = [idx - 1 for idx in range(1,65) if not check_nan(df.values[idx])]
    return length.pop(0)

def count_invalid_line(df):
    length = [idx - 2 for idx in range(2,200) if check_nan(df.values[idx])]
    return length.pop(1)
main_df = pd.DataFrame(columns=['Date', 'PX_OPEN', 'PX_HIGH', 'PX_LOW', 'PX_LAST', 'Volume'])
# main_df = pd.read_csv('/Users/andrew/Desktop/Combined_file1.csv')

for which_file, file in enumerate(files):
    if file != '.DS_Store':
        df = pd.read_csv(file)
        CleanData = pd.DataFrame(columns=['Output', 'Date', 'PX_OPEN', 'PX_HIGH', 'PX_LOW', 'PX_CLOSE', 'Volume'])
        CleanData['Output'] = df.values[2:len(df.values[:, 4]), 3]
        CleanData['Date'] = df.values[2:len(df.values[:, 4]), 4]
        CleanData['PX_OPEN'] = df.values[2:len(df.values[:, 4]), 5]
        CleanData['PX_HIGH'] = df.values[2:len(df.values[:, 4]), 6]
        CleanData['PX_LOW'] = df.values[2:len(df.values[:, 4]), 7]
        CleanData['PX_CLOSE'] = df.values[2:len(df.values[:, 4]), 8]
        volume = df.values[2:len(df.values[:, 4]), 9]
        CleanData['Volume'] = np.divide(volume.astype(np.float), 100)

        ticker_list = []
        number_ticker = 0



        for idx, NextTicker in enumerate(CleanData['Output']):
            ohlcv_list = CleanData.values[idx, 1:]
            if check_nan(NextTicker) != True:
                cum_list = []
                cum_nan = 0
                ticker = NextTicker.split()[0]
                number_ticker += 1
                if number_ticker % 10 == 0:
                    print('{}'.format(number_ticker))
                if not main_df['Date'].str.contains(': {}'.format(NextTicker)).any() and which_file == 1:
                    main_df.loc[main_df['Date'].shape[0]] = [': {}'.format(ticker), None, None, None, None, None]
                    cleanData_location = CleanData[CleanData['Output'] == NextTicker].index[0]
                    length = count_valid_line(CleanData['Output'].loc[cleanData_location: cleanData_location + 65])


            if check_nan(ohlcv_list[4]) != True:
                cum_list.append(ohlcv_list)
            else:
                cum_nan += 1

            if main_df['Date'].str.contains(': {}'.format(ticker)).any() and len(cum_list) == length and check_nan(ohlcv_list[2]) != True:
                location = main_df[main_df['Date'] == ': {}'.format(ticker)].index[0]
                if location + 1 >= main_df['Date'].shape[0]:
                    main_df = pd.concat([main_df, pd.DataFrame(np.array(cum_list), columns=['Date', 'PX_OPEN', 'PX_HIGH', 'PX_LOW', 'PX_LAST', 'Volume'])],ignore_index=True, axis=0)
                else:
                    main_df = pd.concat([main_df.loc[:location + length_data_saved], pd.DataFrame(np.array(cum_list),
                                                                                  columns=['Date', 'PX_OPEN', 'PX_HIGH',
                                                                                           'PX_LOW', 'PX_LAST',
                                                                                           'Volume']), main_df.loc[location + 1 + length_data_saved:]],
                                        ignore_index=True, axis=0, sort= False)

            if cum_nan >= 20:
                main_df.to_csv('/Users/andrew/Desktop/Combined_file{}.csv'.format(which_file))
                break

        print('File Changed')
        length_data_saved = count_invalid_line(main_df['Date'])
main_df.reset_index(inplace=True, drop=True)
main_df.to_csv('/Users/andrew/Desktop/Combined_file.csv')
