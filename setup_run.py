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

    # Get EM Data
    f_o = open('chain_data/emData.pkl', 'rb')
    em_data = pickle.load(f_o)
    f_o.close()

    # All APRs are the daily equivalent
    model_setup = {'support_apr': 0.05,  # 1% ea for BNB reserve, perf fund, NFTs.  2% Trunk/Trumpet
                   'day': pd.Timestamp(date.today()),
                   'f_compound_usd': 200,
                   'f_claim_wait': 120
                   }
    # Futures, estimated based off new wallets and busd_treasury inflows
    # This doesn't always match buyback due to the trailing nature of only using 50% of the busd treasury for buybacks
    busd_treasury_in = dune['Buyback'] * 2  # Buyback only accounts for 50% of inflows now.
    # Get new wallets from the dune holders page
    new_wallets = 8
    new_deposit = busd_treasury_in / new_wallets

    # Get Time info
    end_date = pd.Timestamp(end_date)
    days_temp = end_date - model_setup['day']
    model_setup['run_days'] = days_temp.days
    full_range = pd.date_range(model_setup['day'], end_date, freq="D")

    # ------ Set up Market Growth ------
    # This will be a general multiplier for BNB, BTC, and Trunk from market participation
    market_growth = [1, 1.5]
    mkt_sparse_range = pd.interval_range(model_setup['day'], end_date, len(market_growth)).left
    temp_mkt_s = pd.Series(market_growth, index=mkt_sparse_range)
    temp_mkt_s[end_date] = 2
    temp_mkt_full = pd.Series(temp_mkt_s, index=full_range).interpolate()
    model_setup['bnb_price_s'] = np.multiply(temp_mkt_full, em_data['wbnb'].usd_value)
    model_setup['btc_price_s'] = np.multiply(temp_mkt_full, em_data['btc'].usd_value)
    model_setup['trunk_price_s'] = np.multiply(temp_mkt_full, em_data['trunk'].usd_value)

    # --- EM Growth ---
    # Buy Side
    ele_buy_multiplier = [1, 1.1]
    ele_sparse_range = pd.interval_range(model_setup['day'], end_date, len(ele_buy_multiplier)).left
    temp_ele_s = pd.Series(ele_buy_multiplier, index=ele_sparse_range)
    temp_ele_s[end_date] = 1.2
    temp_ele_full = pd.Series(temp_ele_s, index=full_range).interpolate()
    model_setup['bwb_volume'] = np.multiply(temp_ele_full, dune['bwb_volume'])  # This in $USD
    model_setup['market_buy_volume'] = np.multiply(temp_ele_full, dune['pcs_buy_volume'])
    model_setup['nft_mint_volume'] = np.multiply(temp_ele_full, dune['nft_mint_volume'])
    model_setup['nft_sales_revenue'] = np.multiply(temp_ele_full, dune['nft_sell_taxes'])

    # Sell Side
    ele_sell_multiplier = [1, 0.8]
    ele_sparse_range = pd.interval_range(model_setup['day'], end_date, len(ele_sell_multiplier)).left
    temp_ele_s = pd.Series(ele_sell_multiplier, index=ele_sparse_range)
    temp_ele_s[end_date] = 0.7
    temp_ele_full = pd.Series(temp_ele_s, index=full_range).interpolate()
    model_setup['swb_volume'] = np.multiply(temp_ele_full, dune['swb_volume'])
    model_setup['market_sell_volume'] = np.multiply(temp_ele_full, dune['pcs_sell_volume'])

    # Debt producing growth
    income_multiplier = [1, 1.5]
    inc_sparse_range = pd.interval_range(model_setup['day'], end_date, len(income_multiplier)).left
    temp_income_s = pd.Series(income_multiplier, index=inc_sparse_range)
    temp_income_s[end_date] = 2
    temp_income_full = pd.Series(temp_income_s, index=full_range).interpolate()
    model_setup['f_new_wallets'] = np.multiply(temp_income_full, new_wallets)
    model_setup['f_new_deposit'] = np.multiply(temp_income_full, new_deposit)

    return model_setup

# setup_run("2024-12-31", 310)
