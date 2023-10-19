"""
This file should be used to set the parameters required to run the model
"""
import numpy as np
import pandas as pd
from datetime import date
import pickle


def setup_run(end_date, bnb_price):
    """
    Function returns a dictionary, model_setup, which contains all the parameters needed to execute the simulation run
    """

    # Get Dune Data
    f_o = open('chain_data/DuneData_2023-10-19 09:12.pkl', 'rb')
    dune = pickle.load(f_o)
    f_o.close()

    # All APRs are the daily equivalent
    model_setup = {'trunk_support_apr': dune['trunk_support_apr'],
                   'redemption_support_apr': dune['redemption_support_apr'],
                   'elephant_buyback_apr': 0.5,
                   'nft_royalty_apr': 0.01 / 365,
                   'performance_support_apr': 0.01 / 365,
                   'day': pd.Timestamp(date.today())
                   }
    model_setup['bertha_outflows'] = model_setup['trunk_support_apr'] + model_setup['redemption_support_apr'] + \
                                     model_setup['nft_royalty_apr'] + model_setup['performance_support_apr']

    buy_trunk_pcs = 15000  # Trunk buys off PCS.  Assume goes to wallets for arbitrages, swing trading
    # Futures, estimated based off new wallets and busd_treasury inflows
    # This doesn't always match buyback due to the trailing nature of only using 50% of the busd treasury for buybacks
    busd_treasury_in = 2.4E6 * 0.97 / 30  # From governance page on dune
    # Get new wallets from the dune holders page
    new_wallets = int(54 / 7)
    new_deposit = busd_treasury_in / new_wallets
    model_setup['f_compound_usd'] = 200
    model_setup['f_claim_wait'] = 120
    buy_depot = 0

    # Platform Sales
    model_setup['peg_trunk'] = False  # This will over-ride the amount of sales in order to keep Trunk near $1
    model_setup['yield_sales'] = 1  # % of daily available yield to sell (at PEG)
    # Maximum % of trunk held to be sold in a day only *if* the platform can support it.
    model_setup['daily_liquid_trunk_sales'] = 0.005

    # Kept Yield Behavior (needs to add up to 100%) - takes place after the sales % in "yield_sales"
    # Set these values for a fully running system.  Will be modified based on Trunk price during recovery.
    model_setup['yield_to_trumpet'] = 0.75
    model_setup['yield_to_hold'] = 0.2
    model_setup['yield_to_farm'] = 0.05
    model_setup['yield_to_bond'] = 0
    if model_setup['yield_to_trumpet'] + model_setup['yield_to_farm'] + \
            model_setup['yield_to_bond'] + model_setup['yield_to_hold'] != 1:
        raise Exception("Yield behavior must add to 100%")

    # Get Time info
    end_date = pd.Timestamp(end_date)
    days_temp = end_date - model_setup['day']
    model_setup['run_days'] = days_temp.days
    full_range = pd.date_range(model_setup['day'], end_date, freq="D")

    # ------ Set up BNB Growth ------
    bnb_price_movement = [bnb_price]  # This will be split over the run period.
    bnb_sparse_range = pd.interval_range(model_setup['day'], end_date, len(bnb_price_movement)).left
    temp_bnb_s = pd.Series(bnb_price_movement, index=bnb_sparse_range)
    temp_bnb_s[end_date] = 225  # final BNB price
    model_setup['bnb_price_s'] = pd.Series(temp_bnb_s, index=full_range).interpolate()  # get a daily price increase

    # --- EM Growth ---
    # Non-Debt producing Growth
    ele_buy_multiplier = [1, 1.25, 1.57]
    ele_sparse_range = pd.interval_range(model_setup['day'], end_date, len(ele_buy_multiplier)).left
    temp_ele_s = pd.Series(ele_buy_multiplier, index=ele_sparse_range)
    temp_ele_s[end_date] = 1.95
    temp_ele_full = pd.Series(temp_ele_s, index=full_range).interpolate()
    model_setup['bwb_volume'] = np.multiply(temp_ele_full, dune['bwb_volume'])  # This in $USD
    model_setup['swb_volume'] = np.multiply(temp_ele_full, dune['swb_volume'])
    model_setup['market_buy_volume'] = np.multiply(temp_ele_full, dune['pcs_buy_volume'])
    model_setup['market_sell_volume'] = np.multiply(temp_ele_full, dune['pcs_sell_volume'])
    model_setup['nft_mint_volume'] = np.multiply(temp_ele_full, dune['nft_mint_volume'])
    model_setup['nft_sales_revenue'] = np.multiply(temp_ele_full, dune['nft_sell_taxes'])

    # Debt producing growth
    income_multiplier = [1, 1.25, 1.57]
    inc_sparse_range = pd.interval_range(model_setup['day'], end_date, len(income_multiplier)).left
    temp_income_s = pd.Series(income_multiplier, index=inc_sparse_range)
    temp_income_s[end_date] = 1.95
    temp_income_full = pd.Series(temp_income_s, index=full_range).interpolate()
    model_setup['buy_trunk_pcs'] = np.multiply(temp_income_full, buy_trunk_pcs)
    model_setup['buy_depot'] = np.multiply(temp_income_full, buy_depot)
    model_setup['f_new_wallets'] = np.multiply(temp_income_full, new_wallets)
    model_setup['f_new_deposit'] = np.multiply(temp_income_full, new_deposit)

    return model_setup

# setup_run("2024-12-31", 310)
