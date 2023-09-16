"""
This file should be used to set the parameters required to run the model
"""
import numpy as np
import pandas as pd
from datetime import date


def setup_run(end_date, bnb_price):
    """
    Function returns a dictionary, model_setup, which contains all the parameters needed to execute the simulation run
    """
    # Initialize dictionary with governance contracts
    # get data from dune 30 day dashboard (Governance)
    avg_bertha = 167.2E12
    peg_support = 295.5E9
    redeem_support = 495.7E9
    # All APRs are the daily equivalent
    model_setup = {'trunk_support_apr': peg_support / avg_bertha / 30,
                   'redemption_support_apr': redeem_support / avg_bertha / 30,
                   'elephant_buyback_apr': 0.5,
                   'nft_royalty_apr': 0.01 / 365,
                   'performance_support_apr': 0.01 / 365,
                   'day': pd.Timestamp(date.today())
                   }
    model_setup['bertha_outflows'] = model_setup['trunk_support_apr'] + model_setup['redemption_support_apr'] + \
        model_setup['nft_royalty_apr'] + model_setup['performance_support_apr']

    # Incoming Funds
    # These are starting values.  They can be adjusted during the run as needed (FOMO, etc.)
    # Get data from Dune dashboards (Governance, LP Detailed)
    bwb_taxes = 1.7E12 / 30
    buyback_volume = 5.5E12 / 30
    avg_ele_usd = 0.000000386
    sell_volume = 50000
    buy_trunk_pcs = 0  # Trunk buys off PCS.  Assume goes to wallets for arbitrages, swing trading
    bwb_volume = bwb_taxes / 0.08 * avg_ele_usd  # Bertha collects 8% tax
    model_setup['nft_mints'] = 18  # average daily
    model_setup['nft_market_sells'] = 25  # average daily
    # Futures, estimated based off data 01Sept to 15Sept, 2023:
    futures = {'f_new_wallets': 10,
               'f_new_deposit_usd': 4700,
               'f_compounds': 90,
               'f_compound_usd': 200,
               'f_claims': 53,
               'f_claims_usd': 300,
               'f_days_running': 237
               }
    buy_futures = futures['f_new_wallets'] * futures['f_new_deposit_usd'] + \
        futures['f_compound_usd'] * futures['f_compounds']
    model_setup['f_claim_wait'] = 120
    model_setup = {**model_setup, **futures}
    buy_depot = 0

    # Platform Sales
    model_setup['sell_volume'] = sell_volume  # Percentage of BwB volume
    # ele_market_buy = 0
    # ele_market_sell = 0
    model_setup['peg_trunk'] = False  # This will over-ride the amount of sales in order to keep Trunk near $1
    model_setup['yield_sales'] = 0.75  # % of daily available yield to sell (at PEG)
    # Maximum % of trunk held to be sold in a day only *if* the platform can support it.
    model_setup['daily_liquid_trunk_sales'] = 0.005

    # Kept Yield Behavior (needs to add up to 100%) - takes place after the sales % in "yield_sales"
    # Set these values for a fully running system.  Will be modified based on Trunk price during recovery.
    model_setup['yield_to_hold'] = 0.01
    model_setup['yield_to_stake'] = 0.49
    model_setup['yield_to_farm'] = 0.3
    model_setup['yield_to_bond'] = 0.2
    if model_setup['yield_to_hold'] + model_setup['yield_to_stake'] + \
            model_setup['yield_to_farm'] + model_setup['yield_to_bond'] != 1:
        raise Exception("Yield behavior must add to 100%")

    # Get Time info
    end_date = pd.Timestamp(end_date)
    days_temp = end_date - model_setup['day']
    model_setup['run_days'] = days_temp.days
    full_range = pd.date_range(model_setup['day'], end_date, freq="D")
    '''
    # Setup Stampede
    schedule = ['roll', 'claim', 'hold']
    cycles = round(model_setup['run_days'] / len(schedule)) + 1
    model_setup['roll_claim'] = []
    i = 1
    while i <= cycles:  # Create full schedule for rolls and claims
        for j in schedule:
            model_setup['roll_claim'].append(j)
        i += 1

    # ------ Set up Futures Behavior ------
    schedule = ['dep', 'dep', 'claim']
    
    first_claim = 90  # Days before first claim, then follow schedule
    cycles = round((model_setup['run_days'] - first_claim) / model_setup['futures_interval']) + 1
    model_setup['futures_action'] = []
    i = 1
    while i <= round(first_claim / model_setup['futures_interval']) + 1:  # Fill the intervals before first claim
        model_setup['futures_action'].append('dep')
        i += 1
    i = 1
    while i <= cycles:  # Fill the remainder cycles
        for j in schedule:
            model_setup['futures_action'].append(j)
        i += 1
    '''

    # ------ Set up BNB Growth ------
    bnb_price_movement = [bnb_price, 350, 400, 500, 600]  # This will be split over the run period.
    bnb_sparse_range = pd.interval_range(model_setup['day'], end_date, len(bnb_price_movement)).left
    temp_bnb_s = pd.Series(bnb_price_movement, index=bnb_sparse_range)
    temp_bnb_s[end_date] = 650  # final BNB price
    model_setup['bnb_price_s'] = pd.Series(temp_bnb_s, index=full_range).interpolate()  # get a daily price increase

    # --- EM Growth ---
    # BwB
    ele_buy_multiplier = [1, 1]
    ele_sparse_range = pd.interval_range(model_setup['day'], end_date, len(ele_buy_multiplier)).left
    temp_ele_s = pd.Series(ele_buy_multiplier, index=ele_sparse_range)
    temp_ele_s[end_date] = 1
    temp_ele_full = pd.Series(temp_ele_s, index=full_range).interpolate()
    model_setup['buy_volume'] = np.multiply(temp_ele_full, bwb_volume)  # This in $USD

    # Other Income
    income_multiplier = [1, 1]
    inc_sparse_range = pd.interval_range(model_setup['day'], end_date, len(income_multiplier)).left
    temp_income_s = pd.Series(income_multiplier, index=inc_sparse_range)
    temp_income_s[end_date] = 1
    temp_income_full = pd.Series(temp_income_s, index=full_range).interpolate()
    model_setup['buy_trunk_pcs'] = np.multiply(temp_income_full, buy_trunk_pcs)
    model_setup['buy_depot'] = np.multiply(temp_income_full, buy_depot)
    model_setup['buy_futures'] = np.multiply(temp_income_full, buy_futures)

    return model_setup


# setup_run("2024-12-31", 310)
