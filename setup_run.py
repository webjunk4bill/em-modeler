"""
This file should be used to set the parameters required to run the model
"""
import numpy as np
import pandas as pd
from datetime import date
import pickle


def setup_run(end_date):
    """
    Function returns a dictionary, model_setup, which contains all the parameters needed to execute the simulation run
    """

    # Get Dune Data
    f_o = open('chain_data/DuneData.pkl', 'rb')
    dune = pickle.load(f_o)
    f_o.close()

    # All APRs are the daily equivalent
    model_setup = {'support_apr': 0.05 / 365,  # 1% ea for BNB reserve, perf fund, NFTs.  2% Trunk/Trumpet
                   'day': pd.Timestamp(date.today()),
                   'futures_model': dune['futures_model']
                   }

    # Get Time info
    end_date = pd.Timestamp(end_date)
    days_temp = end_date - model_setup['day']
    model_setup['run_days'] = days_temp.days
    full_range = pd.date_range(model_setup['day'], end_date, freq="D")

    # ------ Set up Market Growth ------
    # This will be a general multiplier for BNB, BTC, and Trunk from market participation
    # It's set up as an APR, which can be multiplied to the price each day
    end_growth = 2
    model_setup['market_growth'] = end_growth ** (1 / days_temp.days)

    # --- EM Growth ---
    # Buy Side
    ele_buy_multiplier = [1]
    ele_sparse_range = pd.interval_range(model_setup['day'], end_date, len(ele_buy_multiplier)).left
    temp_ele_s = pd.Series(ele_buy_multiplier, index=ele_sparse_range)
    temp_ele_s[end_date] = 1
    temp_ele_full = pd.Series(temp_ele_s, index=full_range).interpolate()
    model_setup['bwb_volume'] = np.multiply(temp_ele_full, dune['bwb_volume'])  # This in $USD
    model_setup['pcs_buy_volume'] = np.multiply(temp_ele_full, dune['pcs_buy_volume'])
    model_setup['nft_mint_volume'] = np.multiply(temp_ele_full, dune['nft_mint_volume'])
    model_setup['nft_sales_revenue'] = np.multiply(temp_ele_full, dune['nft_sell_taxes'])

    # Sell Side
    ele_sell_multiplier = [1]
    ele_sparse_range = pd.interval_range(model_setup['day'], end_date, len(ele_sell_multiplier)).left
    temp_ele_s = pd.Series(ele_sell_multiplier, index=ele_sparse_range)
    temp_ele_s[end_date] = 1
    temp_ele_full = pd.Series(temp_ele_s, index=full_range).interpolate()
    model_setup['swb_volume'] = np.multiply(temp_ele_full, dune['swb_volume'])
    model_setup['pcs_sell_volume'] = np.multiply(temp_ele_full, dune['pcs_sell_volume'])

    return model_setup

# setup_run("2024-12-31", 310)
