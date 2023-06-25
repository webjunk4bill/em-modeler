"""
This script will read the historical data to show trends in inputs and outputs
"""

import pandas as pd
import os
import glob
import pickle
import numpy as np
import re


def read_data():
    path = '../chain_data'
    files = sorted(glob.glob(os.path.join(path, "*.pkl")))
    historical_data = {}
    for f in files:
        date = re.search(r"emData_(.*)\.pkl", f).group(1)
        d = pd.Timestamp(date)
        f_o = open(f, 'rb')
        pick = pickle.load(f_o)
        f_o.close()
        historical_data[d] = {
            '$elephant/m': pick['start_ele_price'] * 1E6,
            'bnb_lp_elephant': pick['ele_bnb_lp'].token_bal['ELEPHANT'],
            'bnb_lp_bnb': pick['ele_bnb_lp'].token_bal['WBNB'],
            'busd_lp_elephant': pick['ele_busd_lp'].token_bal['ELEPHANT'],
            'busd_lp_busd': pick['ele_busd_lp'].token_bal['BUSD'],
            '$trunk': pick['start_trunk_price'],
            'total_ele_in_lps': pick['ele_bnb_lp'].token_bal['ELEPHANT'] + pick['ele_busd_lp'].token_bal['ELEPHANT'],
            'trunk_lp_trunk': pick['trunk_busd_lp'].token_bal['TRUNK'],
            'trunk_lp_busd': pick['trunk_busd_lp'].token_bal['BUSD'],
            'trunk_lp_busd_to_balance': pick['trunk_busd_lp'].const_prod ** 0.5 -
                                        pick['trunk_busd_lp'].token_bal['BUSD'],
            'bnb_price': pick['bnb'].usd_value,
            'bertha/T': pick['bertha'] / 1E12,
            'busd_treasury': pick['busd_treasury'],
            'trunk_treasury': pick['trunk_treasury'],
            'staking_balance': pick['staking_balance'],
            'farm_tvl': pick['farm_tvl'],
            'trunk_wallets': pick['trunk_held_wallets'],
            'farmers_depot_deposits': pick['farmers_depot'].deposits,
            'farmers_depot_balance': pick['farmers_depot'].balance,
            'futures_deposits': pick['em_futures'].deposits,
            'futures_balance': pick['em_futures'].balance,
            'stampede_bonds': pick['stampede'].bonds,
            'stampede_owed': pick['stampede'].owed,
            'trunk_liquid_debt': pick['trunk_liquid_debt'],
            'redemption_queue': pick['redemption_queue']
        }

    data_frame = pd.DataFrame(historical_data).T

    return data_frame


def calc_delta(start, end):
    """
    Get the delta between any two date pairs
    """
    abs_delta = np.subtract(start, end)
    ratio_pct = np.multiply(np.subtract(np.divide(start, end), 1), 100)

    return abs_delta, ratio_pct


def projections(data, hours):
    projection = {'daily_ele_lp_change': data['total_ele_in_lps']['absolute'] / hours * 24,
                  'daily_trunk_change': data['trunk_lp_trunk']['absolute'] / hours * 24,
                  'daily_bnb_change': data['bnb_price']['absolute'] / hours * 24,
                  'redemption_queue_change': data['redemption_queue']['absolute'] / hours * 24,
                  '$daily_trunk_buys': data['trunk_lp_busd']['absolute'] / hours * 24,
                  '$daily_depot_deposits': data['farmers_depot_deposits']['absolute'] / hours * 24,
                  'daily_stampede_bonds': data['stampede_bonds']['absolute'] / hours * 24,
                  '$daily_futures_deposits': data['futures_deposits']['absolute'] / hours * 24
                  }

    return projection


# ----------------------------------------------------------------------

df = read_data()
df.to_csv('../chain_data/trend.csv', float_format="%.3f")

past_index = -2

recent = pd.DataFrame({'absolute': (calc_delta(df.iloc[-1], df.iloc[past_index]))[0],
                       'percent': (calc_delta(df.iloc[-1], df.iloc[past_index]))[1]})
full = pd.DataFrame({'absolute': (calc_delta(df.iloc[-1], df.iloc[0]))[0],
                     'percent': (calc_delta(df.iloc[-1], df.iloc[0]))[1]})

fname = "../chain_data/delta_{0}_{1}.csv".format(df.index[past_index], df.index[-1])
recent.to_csv(fname, float_format="%.3f")
fname = "../chain_data/delta_{0}_{1}.csv".format(df.index[0], df.index[-1])
full.to_csv(fname, float_format="%.3f")

time_delta = df.index[-1] - df.index[past_index]
num_hours = time_delta.days * 24 + time_delta.components.hours

output = pd.Series(projections(recent.T, num_hours))
output['$elephant/m'] = df.iloc[-1]['$elephant/m']
output['ele_change_usd'] = -1 * output['$elephant/m'] / 1E6 * output['daily_ele_lp_change']
output.to_csv('../chain_data/projections.csv', float_format="%.3f")

print("Done")
