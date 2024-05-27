# Elephant Money Modeler
import numpy as np
import pandas as pd
from numpy import random
import bsc_classes as bsc
from plotting import em_plot_time_subset, em_plot_time
from setup_run import setup_run
from em_data import get_em_data

# Get EM Protocol Data
# Some manual input is necessary in em_data.py due to inability to read some EM contracts
em_data = get_em_data(read_blockchain=False)  # False = pull from pickle vs query blockchain

# Run Model Setup (starting funds, run quarters, current BNB price)
# Edit parameters in setup_run.py to adjust model parameters
model_setup = setup_run('2026-10-01')
# --- initialize variables
# Set up Futures Model
start_date = pd.to_datetime('2023-12-02')  # first date in the csv
# define 3rd order polynomial coefficients
d_coefs = [3.5509, -823.19, 86748, 2E7]
w_coefs = [0.6847, -76.35, 47600, 3E6]
c_coefs = [3.0379, -567.23, 98922, 1E7]
futures_model = bsc.FuturesModel(d_coefs, w_coefs, c_coefs, start_date)
# Set up Elephant Helper
ele_helper = bsc.ElephantHandler(em_data['ele_bnb_lp'], em_data['wbnb'],
                                 em_data['ele_busd_lp'], em_data['busd'],
                                 em_data['elephant'], em_data['bertha'], em_data['graveyard'])
redemptions_paid = 0
cum_futures_payouts = 0
running_inflows = 0
running_outflows = 0
model_output = {}
em_cashflow = bsc.EMCashflow()
futures_done = False
sunset_futures = False
sunset_date = pd.to_datetime('2025-01-01')
new_buffer_pool_apr = 0.0 / 365

# Create and Run Model
for run in range(int(model_setup['run_days'])):
    # Initialize Variables
    del em_cashflow  # probably not necessary
    em_cashflow = bsc.EMCashflow()
    today = model_setup['day']
    tomorrow = model_setup['day'] + pd.Timedelta(1, "d")
    yesterday = model_setup['day'] - pd.Timedelta("1d")
    if em_data['bertha'] < 1E12:
        break  # stop the loop when Bertha is exhausted (< 1T tokens)

    # Get Day Start Prices -----------------------------------------------------------------------
    em_data['wbnb'].usd_value *= model_setup['market_growth'][today]
    em_data['btc'].usd_value *= model_setup['market_growth'][today]
    em_data['trunk'].usd_value *= model_setup['market_growth'][today]
    begin_ele_price = ele_helper.bnb_usd_price
    em_assets_day_start = (ele_helper.bertha_usd_value + em_data['btc_turbine'].usd_value +
                           em_data['trunk_turbine'].usd_value +
                           (em_data['bnb_reserve'] + em_data['rdf']) * em_data['wbnb'].usd_value)
    # Daily Bertha Support ---------------------------------------------------------------------
    daily_bertha_support_usd = ele_helper.bertha_usd_value * (model_setup['support_apr'])
    # Incoming Funds ---------------------------------------------------------------------
    '''  Track futures as aggregate below
    # --- new Futures stakes ---
    wallets = int(model_setup['f_new_wallets'][today])
    deposit = model_setup['f_new_deposit'][today]
    for _ in range(wallets):
        if sunset_futures is True and sunset_date is today or futures_done is True:
            futures_done = True
            pass
        else:
            em_data['btc_turbine'].balance += deposit * 0.1 / em_data['btc'].usd_value
            em_data['rdf'] += deposit * 0.1 / em_data['wbnb'].usd_value
            em_data['bnb_reserve'] += deposit * 0.1 / em_data['wbnb'].usd_value
            bnb_for_trunk = deposit * 0.2 / em_data['wbnb'].usd_value
            trunk_removed = em_data['trunk_bnb_lp'].update_lp(em_data['wbnb'], bnb_for_trunk)
            em_data['trunk_turbine'].balance += trunk_removed
            bnb_for_elephant = deposit * 0.5 / em_data['wbnb'].usd_value
            ele_helper.protocol_buy(bnb_for_elephant)
            futures.append(bsc.YieldEngineV8(deposit, futures_group_rate))  # create new stake
            em_cashflow.in_futures += deposit
    '''
    # --- NFT Mints ---
    mint_funds = model_setup['nft_mint_volume'][today]
    mints_available = int(mint_funds / (em_data['nft'].price * em_data['wbnb'].usd_value))
    em_data['nft'].mint(mints_available)
    em_cashflow.in_nft += mint_funds
    ele_helper.protocol_buy(mint_funds / em_data['wbnb'].usd_value)
    # --- NFT Marketplace Sales ---
    # Market sells are 90% of the current mint price and Bertha gets a 30% cut of that
    sell_funds = model_setup['nft_sales_revenue'][today]
    em_cashflow.in_nft += sell_funds
    ele_helper.protocol_buy(sell_funds / em_data['wbnb'].usd_value)

    # Handle Elephant Buy/Sell ---------------------------------------------------------------------
    # ------ BwB ------
    ele_bought = ele_helper.bwb_buy(model_setup['bwb_volume'][today] / em_data['wbnb'].usd_value)
    em_cashflow.in_buy_volume += model_setup['bwb_volume'][today]
    # ------ SwB ------
    ele_helper.bwb_sell(model_setup['swb_volume'][today])
    em_cashflow.in_taxes += model_setup['swb_volume'][today] * 0.08
    em_cashflow.out_sell_volume += model_setup['swb_volume'][today] * 0.92

    # ------ Market Buys / Sells ------
    ele_helper.pcs_buy(model_setup['pcs_buy_volume'][today])
    em_cashflow.in_buy_volume += model_setup['pcs_buy_volume'][today]
    ele_helper.pcs_sell(model_setup['market_sell_volume'][today])
    em_cashflow.out_sell_volume += model_setup['market_sell_volume'][today]

    # Handle Governance ---------------------------------------------------------------------
    # ------ Graveyard Rebalance ------
    if em_data['graveyard'] >= 510E12:
        em_data['graveyard'] -= 10E12
        bnb_bought = ele_helper.protocol_sell(5E12)
        ele_helper.bnb_lp.add_liquidity(em_data['elephant'], 5E12, em_data['wbnb'], bnb_bought)
    # ------ Protocol Support Outflows ------
    # For now just focus on Elephant and Bertha.  Trunk will be more dominated by the market until Bertha is huge
    # TODO: Specify trunk support mechanisms
    # Don't include the BNB reserve support since moving to aggregated futures handling
    # The APRs and everything will be aggregated into the trendlines of compounds, withdrawls, etc
    support_ele = ele_helper.bertha * 0.04 / 365
    em_cashflow.out_trunk += ele_helper.protocol_sell(support_ele) * em_data['wbnb'].usd_value  # BNB returned
    # ------ Turbine governance ------
    # 1% APR from each turbine is used to buy Elephant
    daily_apr = 0.01 / 365
    btc_sell_usd = em_data['btc_turbine'].balance * daily_apr * em_data['btc'].usd_value
    em_data['btc_turbine'].balance *= (1 - daily_apr)
    trunk_sell_usd = em_data['trunk_turbine'].balance * daily_apr * em_data['trunk'].usd_value
    em_data['trunk_turbine'].balance *= (1 - daily_apr)
    bnb_for_ele = (btc_sell_usd + trunk_sell_usd) / em_data['wbnb'].usd_value
    ele_helper.protocol_buy(bnb_for_ele)

    # Handle Futures ------------------------------------------------------------------------
    # Using aggregated trends vs tracking individual wallets
    # from futures overview at dune: https://dune.com/queries/3317877/5556286
    # currently manually get the trendlines in Excel:
    # TODO: use ML to get trendlines
    # Update Futures Model
    futures_model.today = today
    # process deposits
    deposits = futures_model.deposit_delta
    em_data['btc_turbine'].balance += deposits * 0.1 / em_data['btc'].usd_value
    em_data['rdf'] += deposits * 0.1 / em_data['wbnb'].usd_value
    em_data['bnb_reserve'] += deposits * 0.1 / em_data['wbnb'].usd_value
    bnb_for_trunk = deposits * 0.2 / em_data['wbnb'].usd_value
    trunk_removed = em_data['trunk_bnb_lp'].update_lp(em_data['wbnb'], bnb_for_trunk)
    em_data['trunk_turbine'].balance += trunk_removed
    bnb_for_elephant = deposits * 0.5 / em_data['wbnb'].usd_value
    ele_helper.protocol_buy(bnb_for_elephant)
    em_cashflow.in_futures += deposits
    # process withdrawals
    withdrawals = futures_model.withdrawal_delta
    ele_needed = withdrawals / ele_helper.bnb_usd_price
    bnb_out = ele_helper.protocol_sell(ele_needed)
    em_cashflow.out_futures_sell += bnb_out * em_data['wbnb'].usd_value

    # Handle LP Arbitrage -------------------------------------------------------------------
    # TODO: Write arbitrage function

    # Update assets and debts --------------------------------------------------------------
    em_data['elephant_wallets'] = ele_helper.ele_in_wallets
    em_assets = (ele_helper.bertha_usd_value + em_data['btc_turbine'].usd_value +
                 em_data['trunk_turbine'].usd_value +
                 (em_data['bnb_reserve'] + em_data['rdf']) * em_data['wbnb'].usd_value)
    liquidity = ele_helper.bnb_usd_liquidity + ele_helper.busd_usd_liquidity
    em_market_cap = 1E15 * ele_helper.bnb_usd_price
    em_growth = em_assets - em_assets_day_start  # How much did the asset sheet grow
    usd_daily_debt = futures_model.withdrawal_delta + daily_bertha_support_usd
    usd_total_debt = futures_model.tvl + daily_bertha_support_usd
    running_inflows += em_cashflow.in_total
    running_outflows += em_cashflow.out_total

    # Output Results
    daily_snapshot = {
        "$em_market_cap/m": em_market_cap / 1E6,
        "$em_assets/m": em_assets / 1E6,
        "$em_liquidity/m": liquidity / 1E6,
        "$em_asset_growth/m": em_growth / 1E6,
        "%em_asset_growth": em_growth / em_assets * 100,
        "$funds_in/m": running_inflows / 1E6,
        "$funds_out/m": running_outflows / 1E6,
        "bertha/T": em_data['bertha'] / 1E12,
        "$bertha/m": em_data['bertha'] * ele_helper.bnb_usd_price / 1E6,
        "$elephant/m": ele_helper.bnb_usd_price * 1E6,
        "$trunk": em_data['trunk'].usd_value,
        "trumpet": em_data['trumpet'].price,
        "trumpet_backing": em_data['trumpet'].backing,
        "trumpet_supply": em_data['trumpet'].supply,
        "$BNB": em_data['wbnb'].usd_value,
        "$bertha_payouts/m": usd_daily_debt / 1E6,
        "$total_debt/m": usd_total_debt / 1E6,
        "%total_debt_ratio": ele_helper.bertha_usd_value / usd_total_debt * 100,
    }
    daily_snapshot = {**daily_snapshot, **em_cashflow.get_results()}
    last_week = model_setup['day'] - pd.Timedelta("7d")
    if last_week in model_output:
        daily_snapshot['%em_income_growth'] = \
            (daily_snapshot['$em_income'] / model_output[last_week]['$em_income'] - 1) * 100
        daily_snapshot['%em_outflow_growth'] = \
            (daily_snapshot['$em_outflow'] / model_output[last_week]['$em_outflow'] - 1) * 100
        daily_snapshot['%bertha_growth'] = \
            (daily_snapshot['$bertha/m'] / model_output[last_week]['$bertha/m'] - 1) * 100

    # Log days update and set to tomorrow.
    model_output[today] = daily_snapshot
    model_setup['day'] += pd.Timedelta("1 day")

# for debug, setting break point
# if run >= 800:
#    print(day)
# TODO: Elephant bag tracking

df_model_output = pd.DataFrame(model_output).T
df_model_output.to_csv('outputs/output_time.csv')
em_plot_time_subset(df_model_output)
print("Done")
