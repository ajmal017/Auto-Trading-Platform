'''
This program is created by Andrew Li for saving some auxiliary function which can be used repeatedly in the project

The file is lastly modified on 2018/11/22
'''

def check_nan(args):
    '''
    Check whether the input is nan or not
    :param args: number like int, str, float
    :return: True if input is nan otherwise False
    '''
    return str(args) == str(1e400*0)

def changeDate(date):
    '''
    Just change one date
    Input: A single date in string format
    Output: Date string
    '''
    separate_str = date.split('/')
    if len(separate_str[0]) < 2:
        separate_str[0] = ''.join(('0', separate_str[0]))
    if len(separate_str[1]) < 2:
        separate_str[1] = ''.join(('0', separate_str[1]))
    return ''.join((separate_str[2], separate_str[0], separate_str[1]))

def change_date_format(df):
    '''
    Change a list of date format from month/day/year to year + month + day
    :param df: pd.Dataframe including the date
    :return: a list of changed date
    '''
    new_list = []
    for str in df:
        if not check_nan(str):
            separate_str = str.split('/')
            if len(separate_str[0]) < 2:
                separate_str[0] = ''.join(('0', separate_str[0]))
            if len(separate_str[1]) < 2:
                separate_str[1] = ''.join(('0', separate_str[1]))
            new_list.append(''.join((separate_str[2], separate_str[0], separate_str[1])))
        else:
            new_list.append(str)
    return new_list