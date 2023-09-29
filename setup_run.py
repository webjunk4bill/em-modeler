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
    # Get data from Dune dashboards (Governance sheet) and LP
    ele_treasury_in_usd = 3.1E6 / 30  # Total 30d in from governance page
    # Use %-ages from the governance page
    nft_mint_volume = 63.1 / 100 * ele_treasury_in_usd
    nft_sell_taxes = 1.23 / 100 * ele_treasury_in_usd
    buyback = 25.0 / 100 * ele_treasury_in_usd
    bwb_taxes = 11.4 / 100 * ele_treasury_in_usd
    # Get Buy / Sell Volume from LP page.  Need to export to CSV and average to get 30d average
    avg_nb_buy_volume = 476000 - buyback - nft_mint_volume  # "non-Bertha" buy volume since traced separately
    avg_sell_volume = 98000
    buy_sell_ratio = avg_nb_buy_volume / (avg_sell_volume + avg_nb_buy_volume)
    bwb_volume = bwb_taxes / 0.08 * buy_sell_ratio  # Bertha collects 8% tax
    swb_volume = bwb_taxes / 0.08 * (1 - buy_sell_ratio)
    market_buy_volume = avg_nb_buy_volume - bwb_volume
    market_sell_volume = avg_sell_volume - swb_volume
    buy_trunk_pcs = 15000  # Trunk buys off PCS.  Assume goes to wallets for arbitrages, swing trading
    # Futures, estimated based off new wallets and busd_treasury inflows
    # This doesn't always match buyback due to the trailing nature of only using 50% of the busd treasury for buybacks
    busd_treasury_in = 1.9E6 / 30
    # Get new wallets from the dune holders page
    new_wallets = int(76 / 7)
    new_deposit = busd_treasury_in / new_wallets
    futures = {'f_compounds': 90,
               'f_compound_usd': 200,
               'f_claims_usd': 300,
               'f_days_running': 237
               }
    model_setup['f_claim_wait'] = 120
    model_setup = {**model_setup, **futures}
    buy_depot = 0

    # Platform Sales
    model_setup['peg_trunk'] = False  # This will over-ride the amount of sales in order to keep Trunk near $1
    model_setup['yield_sales'] = 0.75  # % of daily available yield to sell (at PEG)
    # Maximum % of trunk held to be sold in a day only *if* the platform can support it.
    model_setup['daily_liquid_trunk_sales'] = 0.005

    # Kept Yield Behavior (needs to add up to 100%) - takes place after the sales % in "yield_sales"
    # Set these values for a fully running system.  Will be modified based on Trunk price during recovery.
    model_setup['yield_to_trumpet'] = 0.8
    model_setup['yield_to_hold'] = 0.2
    model_setup['yield_to_farm'] = 0
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
    bnb_price_movement = [bnb_price, 250, 200, 225]  # This will be split over the run period.
    bnb_sparse_range = pd.interval_range(model_setup['day'], end_date, len(bnb_price_movement)).left
    temp_bnb_s = pd.Series(bnb_price_movement, index=bnb_sparse_range)
    temp_bnb_s[end_date] = 250  # final BNB price
    model_setup['bnb_price_s'] = pd.Series(temp_bnb_s, index=full_range).interpolate()  # get a daily price increase

    # --- EM Growth ---
    # Non-Debt producing Growth
    ele_buy_multiplier = [1]
    ele_sparse_range = pd.interval_range(model_setup['day'], end_date, len(ele_buy_multiplier)).left
    temp_ele_s = pd.Series(ele_buy_multiplier, index=ele_sparse_range)
    temp_ele_s[end_date] = 1
    temp_ele_full = pd.Series(temp_ele_s, index=full_range).interpolate()
    model_setup['bwb_volume'] = np.multiply(temp_ele_full, bwb_volume)  # This in $USD
    model_setup['swb_volume'] = np.multiply(temp_ele_full, swb_volume)
    model_setup['market_buy_volume'] = np.multiply(temp_ele_full, market_buy_volume)
    model_setup['market_sell_volume'] = np.multiply(temp_ele_full, market_sell_volume)
    model_setup['nft_mint_volume'] = np.multiply(temp_ele_full, nft_mint_volume)
    model_setup['nft_sales_revenue'] = np.multiply(temp_ele_full, nft_sell_taxes)

    # Debt producing growth
    income_multiplier = [1]
    inc_sparse_range = pd.interval_range(model_setup['day'], end_date, len(income_multiplier)).left
    temp_income_s = pd.Series(income_multiplier, index=inc_sparse_range)
    temp_income_s[end_date] = 1
    temp_income_full = pd.Series(temp_income_s, index=full_range).interpolate()
    model_setup['buy_trunk_pcs'] = np.multiply(temp_income_full, buy_trunk_pcs)
    model_setup['buy_depot'] = np.multiply(temp_income_full, buy_depot)
    model_setup['f_new_wallets'] = np.multiply(temp_income_full, new_wallets)
    model_setup['f_new_deposit'] = np.multiply(temp_income_full, new_deposit)

    return model_setup

# setup_run("2024-12-31", 310)
