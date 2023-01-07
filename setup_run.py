"""
This file should be used to set the parameters required to run the model
"""
import numpy as np
import pandas as pd
from datetime import date


def setup_run(daily_funds, run_quarters, bnb_price):
    """
    Function returns a dictionary, model_setup, which contains all the parameters needed to execute the simulation run
    """
    # Initialize dictionary with governance contracts
    model_setup = {'trunk_support_apr': 0.1 / 365,
                   'redemption_support_apr': 0.1 / 365,
                   'elephant_buyback_apr': 0.5,
                   'day': pd.Timestamp(date.today())
                   }

    # Incoming Funds - use total and the split by %
    # below should add to 100%
    # These are starting values.  They can be adjusted during the run as needed (FOMO, etc.)
    buy_w_b = 0.2
    buy_trunk_pcs = 0.01  # Trunk buys off PCS.  Assume goes to wallets for arbitrages, swing trading
    buy_depot = 0.05  # Also used for Minting
    buy_peanuts = 0.025
    buy_futures = 0.715
    if 0.99 <= buy_w_b + buy_trunk_pcs + buy_depot + buy_peanuts + buy_futures >= 1.01:
        raise Exception("Incoming fund split needs to equal 100%")

    # Platform Sales
    model_setup['sell_w_b'] = 0.1  # Percentage of BwB volume
    # ele_market_buy = 0
    # ele_market_sell = 0
    model_setup['peg_trunk'] = True  # This will over-ride the amount of sales in order to keep Trunk near $1
    model_setup['yield_sales'] = 0.5  # % of daily available yield to sell (at PEG)
    # Maximum % of trunk held to be sold in a day only *if* the platform can support it.
    model_setup['daily_liquid_trunk_sales'] = 0.02

    # Kept Yield Behavior (needs to add up to 100%) - takes place after the sales % in "yield_sales"
    # Set these values for a fully running system.  Will be modified based on Trunk price during recovery.
    model_setup['yield_to_hold'] = 0.01
    model_setup['yield_to_stake'] = 0.49
    model_setup['yield_to_farm'] = 0.3
    model_setup['yield_to_bond'] = 0.2
    if model_setup['yield_to_hold'] + model_setup['yield_to_stake'] + \
            model_setup['yield_to_farm'] + model_setup['yield_to_bond'] != 1:
        raise Exception("Yield behavior must add to 100%")

    # Setup Run
    schedule = ['roll', 'claim']
    model_setup['run_days'] = run_quarters * 365 / 4
    cycles = round(model_setup['run_days'] / len(schedule)) + 1
    model_setup['roll_claim'] = []
    i = 1
    while i <= cycles:  # Create full schedule for rolls and claims
        for j in schedule:
            model_setup['roll_claim'].append(j)
        i += 1
    # Initialize Variables
    model_setup['day'] = pd.to_datetime(date.today())

    # ------ Set up Growth ------
    start = date(2023, 1, 1)  # Use the previous quarter start
    periods = run_quarters + 2  # we are starting one quarter back from today's date and want to go an extra quarter
    sparse_range = pd.date_range(start, periods=periods, freq="QS")
    full_range = pd.date_range(start, sparse_range.date[-1])
    # --- BNB Growth ---
    # Look for a bull run in 2024.  Start the first two values with the current price
    # bnb_price_movement = [bnb.usd_value, bnb.usd_value, 275, 300, 325, 350, 375, 400, 500, 600,
    #                      650, 700, 725, 750, 650, 625, 700, 750, 800, 800, 750, 800]
    bnb_price_movement = [bnb_price, bnb_price, 275, 300, 325, 375, 450, 550, 650, 600, 650, 700]
    # bnb_price_movement = [250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250]
    if sparse_range.size != bnb_price_movement.__len__():
        raise Exception("BNB Price range does not match date range")
    temp_bnb_s = pd.Series(bnb_price_movement, index=sparse_range)
    model_setup['bnb_price_s'] = pd.Series(temp_bnb_s, index=full_range).interpolate()  # get a daily price increase

    # --- EM Growth ---
    # ---  Quarters: ['23 Jan, Apr, Jul, Oct, '24 Jan, Apr, July, Oct, '25 Jan, Apr, July, Oct]
    # BwB
    ele_buy_multiplier = [1, 8, 16, 32, 32, 32, 32, 32, 32, 32, 32, 32]
    temp_ele_s = pd.Series(ele_buy_multiplier, index=sparse_range)
    temp_ele_full = pd.Series(temp_ele_s, index=full_range).interpolate()
    model_setup['buy_w_b'] = np.multiply(temp_ele_full, buy_w_b * daily_funds)  # This in $USD
    # Other Income
    income_multiplier = [1, 2, 4, 6, 8, 10, 12, 12, 12, 12, 12, 12]
    temp_income_s = pd.Series(income_multiplier, index=sparse_range)
    temp_income_full = pd.Series(temp_income_s, index=full_range).interpolate()
    model_setup['buy_trunk_pcs'] = np.multiply(temp_income_full, buy_trunk_pcs * daily_funds)
    model_setup['buy_depot'] = np.multiply(temp_income_full, buy_depot * daily_funds)
    model_setup['buy_peanuts'] = np.multiply(temp_income_full, buy_peanuts * daily_funds)
    model_setup['buy_futures'] = np.multiply(temp_income_full, buy_futures * daily_funds)

    return model_setup


# setup_run(100000, 10, 254)
