# Elephant Money Modeler

import pandas as pd
import bsc_classes as bsc
from plotting import em_plot_time
from setup_run import setup_run
from em_data import get_em_data

# Get EM Protocol Data
# Some manual input is necessary in em_data.py due to inability to read some EM contracts
em_data = get_em_data(read_blockchain=False)  # False = pull from pickle vs query blockchain

# Run Model Setup (starting funds, run quarters, current BNB price)
# Edit parameters in setup_run.py to adjust model parameters
model_setup = setup_run(50000, 12, em_data['bnb'].usd_value)
# initialize variables
yesterday = model_setup['day'] - pd.Timedelta("1d")
futures = {yesterday: em_data['busd_futures']}  # Start with current futures TVL
redemptions_paid = 0
running_income_funds = 0
model_output = {}

# Create and Run Model
for run in range(int(model_setup['run_days'])):
    # Daily Bertha Support ---------------------------------------------------------------------
    average_ele_price = bsc.get_ave_ele(em_data['ele_busd_lp'], em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
    daily_bertha_support_usd = em_data['bertha'] * average_ele_price * \
                               (model_setup['redemption_support_apr'] + model_setup['trunk_support_apr'])
    em_assets_day_start = em_data['bertha'] * average_ele_price + em_data['trunk_busd_lp'].token_bal['BUSD'] + \
                          em_data['ele_busd_lp'].token_bal['BUSD'] + em_data['ele_bnb_lp'].token_bal['WBNB'] * \
                          em_data['bnb'].usd_value + em_data['busd_treasury'] + em_data['trunk_treasury'] * \
                          em_data['trunk_busd_lp'].price

    # Get Day Start Prices -----------------------------------------------------------------------
    begin_ele_price = average_ele_price
    begin_bnb_price = em_data['bnb'].usd_value
    begin_trunk_price = em_data['trunk_busd_lp'].price

    # Incoming Funds ---------------------------------------------------------------------
    # --- Peanuts ---
    em_data['stampede'].bond(model_setup['buy_peanuts'][model_setup['day']] / max(em_data['trunk_busd_lp'].price, 0.25))
    em_data['busd_treasury'] += model_setup['buy_peanuts'][model_setup['day']]
    # --- Farmer's Depot ---
    depot_buy_usd = model_setup['buy_depot'][model_setup['day']]  # Don't want to directly modify the starting value
    if em_data['trunk_busd_lp'].price < 0.98:  # 10% of funds auto purchase market Trunk if below $0.98
        em_data['trunk_treasury'] += em_data['trunk_busd_lp'].update_lp('BUSD', depot_buy_usd * 0.1)
        depot_buy_usd *= 0.9
    depot_buy = depot_buy_usd / max(em_data['trunk_busd_lp'].price, 0.25)  # Convert to Trunk
    em_data['farmers_depot'].deposit(depot_buy)
    em_data['busd_treasury'] += depot_buy_usd  # funds go to busd treasury
    # --- Futures ---
    # Create a new futures stake with the daily deposit money
    futures[model_setup['day']] = bsc.BUSDFuturesEngine(model_setup['buy_futures'][model_setup['day']])
    em_data['futures_busd_pool'] += model_setup['buy_futures'][model_setup['day']] * 0.1  # 10% hold for payouts
    em_data['busd_treasury'] += model_setup['buy_futures'][model_setup['day']] * 0.9  # remainder to busd treasury

    # Handle Elephant Buy/Sell ---------------------------------------------------------------------
    # ------ BwB ------
    ele_bought = bsc.elephant_buy(model_setup['buy_w_b'][model_setup['day']], em_data['ele_busd_lp'],
                                  em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
    em_data['bertha'] += ele_bought * 0.08  # 8% tax to Bertha
    # ------ SwB ------
    ele_sold = model_setup['sell_w_b'] * model_setup['buy_w_b'][model_setup['day']] / average_ele_price
    # 92% of Elephant sold goes to LP, 8% to Bertha
    busd_removed = bsc.elephant_sell(ele_sold * 0.92, em_data['ele_busd_lp'], em_data['ele_bnb_lp'],
                                     em_data['bnb'].usd_value)
    em_data['bertha'] += ele_sold * 0.08
    # TODO: Elephant Market Buy
    # TODO: Elephant Market Sell

    # Handle Governance ---------------------------------------------------------------------
    # ------ Elephant Buyback (for Bertha) ------
    buyback_funds = em_data['busd_treasury'] * model_setup['elephant_buyback_apr']  # In USD
    em_data['busd_treasury'] -= buyback_funds  # Remove funds
    ele_bought = bsc.elephant_buy(buyback_funds, em_data['ele_busd_lp'], em_data['ele_bnb_lp'],
                                  em_data['bnb'].usd_value)
    em_data['bertha'] += ele_bought  # All of these funds go to bertha

    # ------ Redemptions ------
    redemption_funds = em_data['bertha'] * model_setup['redemption_support_apr']  # Daily funds in ELEPHANT
    em_data['bertha'] -= redemption_funds  # Update bertha balance
    busd_received = bsc.elephant_sell(redemption_funds, em_data['ele_busd_lp'], em_data['ele_bnb_lp'],
                                      em_data['bnb'].usd_value)  # Sell Elephant
    redeem_wait_days = int(em_data['redemption_queue'] / busd_received) + 1
    em_data['redemption_pool'] += busd_received  # Add BUSD funds to the redemption pool
    if em_data['redemption_queue'] >= em_data['redemption_pool']:
        em_data['redemption_queue'] -= em_data['redemption_pool']  # Payout as much of queue as possible
        redemptions_paid += em_data['redemption_pool']
        em_data['redemption_pool'] = 0  # Pool is now drained
    else:
        em_data['redemption_pool'] -= em_data['redemption_queue']  # Payout remainder of redemption queue
        redemptions_paid += em_data['redemption_queue']
        em_data['redemption_queue'] = 0  # Queue is now at 0

    # ------ Trunk Support ------
    support_funds = em_data['bertha'] * model_setup['trunk_support_apr']  # Daily funds in ELEPHANT
    em_data['bertha'] -= support_funds  # Update Bertha balance
    busd_received = bsc.elephant_sell(support_funds, em_data['ele_busd_lp'], em_data['ele_bnb_lp'],
                                      em_data['bnb'].usd_value)
    em_data['trunk_support_pool'] += busd_received  # Add BUSD funds to the trunk support pool
    if em_data['trunk_busd_lp'].price < 1:
        delta = (em_data['trunk_busd_lp'].const_prod ** 0.5 - em_data['trunk_busd_lp'].token_bal['BUSD'])
        if em_data['trunk_support_pool'] >= delta:
            em_data['trunk_busd_lp'].update_lp('BUSD', delta)  # Buy Trunk off PCS
            em_data['trunk_support_pool'] -= delta
        else:
            em_data['trunk_busd_lp'].update_lp('BUSD', em_data['trunk_support_pool'])  # Buy Trunk off PCS
            em_data['trunk_support_pool'] = 0  # All funds spent
        em_data['trunk_treasury'] += em_data[
            'trunk_busd_lp'].tokens_removed  # Trunk is deposited in the trunk treasury for further use
    else:
        pass  # support pool just grows if Trunk is already at Peg

    # ------ Futures Payouts ------
    futures_claimed = 0
    action = ''
    for stake in futures.values():  # Need to process each separate futures stake
        stake.pass_days(1)
        if stake.days_since_action == model_setup['futures_interval']:
            index = int(stake.total_days / model_setup['futures_interval'])
            action = model_setup['futures_action'][index]
            if action == 'dep':
                stake.deposit(model_setup['futures_compound_dep'])  # deposit the money to compound stake
            elif action == 'claim':
                futures_claimed += stake.claim()
    if em_data['futures_busd_pool'] >= futures_claimed:
        em_data['futures_busd_pool'] -= futures_claimed  # payout claims
    else:  # Sell Elephant to replenish pool.  Sell a 10% Buffer
        to_sell = futures_claimed * 1.1 / average_ele_price  # get num Elephant to sell
        em_data['bertha'] -= to_sell  # remove elephant from Bertha
        em_data['futures_busd_pool'] += bsc.elephant_sell(to_sell, em_data['ele_busd_lp'], em_data['ele_bnb_lp'],
                                                          em_data['bnb'].usd_value)  # sell ELEPHANT
        em_data['futures_busd_pool'] -= futures_claimed  # payout claims

    # Handle Yield and Sales/Redemptions (all in Trunk) ----------------------------------------------------------------
    # ------ Calculate Daily Trunk Yield ------ #
    action = model_setup['roll_claim'].pop(0)
    stp_yield = em_data['stampede'].update(action, em_data['trunk_busd_lp'].price)
    stk_yield = em_data['staking_balance'] * em_data['staking_apr']  # In Trunk
    fm_yield = em_data['farm_tvl'] * em_data['farms_max_apr'] * em_data['trunk_busd_lp'].price
    daily_yield = stk_yield + fm_yield + stp_yield
    presale_daily_yield = daily_yield
    if em_data['trunk_treasury'] > daily_yield:  # Yield will be paid from Trunk treasury, or else minted
        em_data['trunk_treasury'] -= daily_yield

    # ------ Determine community Peg support and sales amount ------
    if model_setup['peg_trunk'] and em_data['trunk_busd_lp'].price < 1:
        trunk_sales = daily_bertha_support_usd  # By looking at only USD, will keep selling low while $trunk is low
    elif model_setup['peg_trunk']:  # Allow up to 10% drop in Trunk Price
        trunk_sales = (1 - 0.9 ** 0.5) * em_data['trunk_busd_lp'].token_bal['TRUNK']
    else:
        trunk_sales = daily_yield * model_setup['yield_sales'] * em_data['trunk_busd_lp'].price
    if trunk_sales > daily_yield:
        trunk_sales = daily_yield  # Never try to sell more than the actual yield

    # ------ Yield Redemption/Sales ------
    if redeem_wait_days <= 30 and em_data['trunk_busd_lp'].price < 0.90:  # This can be adjusted, just guessing
        em_data['redemption_queue'] += trunk_sales
    else:
        em_data['trunk_busd_lp'].update_lp('TRUNK', trunk_sales)
    daily_yield -= trunk_sales  # depending on whether this is positive or negative will determine sales vs hold

    # ------ Update balances based on unsold yield ------
    # --- Buys off PCS - included here so that it can use the same deposit ratios defined
    # Once Peg is hit, this is the same as minting
    em_data['trunk_busd_lp'].update_lp('BUSD', model_setup['buy_trunk_pcs'][model_setup['day']])  # purchase trunk
    daily_yield += em_data['trunk_busd_lp'].tokens_removed
    # --- Farmer's Depot ---
    em_data['farmers_depot'].pass_days(1)  # Update depot by 1 day
    depot_claim = em_data['farmers_depot'].claim()
    daily_yield += depot_claim  # Claim available funds and deposit based on ratios
    if em_data['trunk_treasury'] > depot_claim:
        em_data['trunk_treasury'] -= depot_claim  # Trunk will be paid from treasury vs minted
    # --- Update Balances ---
    if daily_yield > 0:
        em_data['staking_balance'] += daily_yield * model_setup['yield_to_stake']
        em_data['trunk_held_wallets'] += daily_yield * model_setup['yield_to_hold']
        # Farm TVL still goes up by total amount, assume bringing pair token
        em_data['farm_tvl'] += daily_yield * model_setup['yield_to_farm']
        em_data['trunk_liquid_debt'] = em_data['staking_balance'] + em_data['farm_tvl'] / 2 + \
                                       em_data['trunk_held_wallets']  # Update liquid debt
        em_data['stampede'].bond(daily_yield * model_setup['yield_to_bond'])

    # ------ Arbitrage Trunk LP with Redemption Pool or Minting ------
    # SQRT(CP) will give perfect split.
    delta = (em_data['trunk_busd_lp'].const_prod ** 0.5 - em_data['trunk_busd_lp'].token_bal['BUSD'])
    if em_data['trunk_busd_lp'].price <= 1.00 and redeem_wait_days < 25:  # No arbitrage until queue is reasonable.
        em_data['trunk_busd_lp'].update_lp('BUSD', delta)
        em_data['redemption_queue'] += delta * 0.1
    elif em_data['trunk_busd_lp'].price > 1.00:  # Trunk is over $1.  "Delta" will be negative
        em_data['trunk_busd_lp'].update_lp('TRUNK', abs(delta))  # Sell trunk on PCS
        em_data['busd_treasury'] += abs(delta)  # Arber would need to mint trunk from the protocol
        if em_data['trunk_treasury'] > abs(delta):
            em_data['trunk_treasury'] -= abs(delta)  # Comes from Trunk Treasury if there are funds
    else:
        pass

    # Handle Liquid Trunk Selling/Redeeming ---------------------------------------------------------------------
    if model_setup['peg_trunk'] and em_data['trunk_busd_lp'].price > 0.99:  # Allow some selling
        trunk_to_sell = em_data['trunk_busd_lp'].token_bal['BUSD'] - (em_data['trunk_busd_lp'].const_prod * 0.9) ** 0.5
    elif model_setup['peg_trunk']:
        trunk_to_sell = 0
    elif em_data['trunk_busd_lp'].price > 0.5:
        trunk_to_sell = em_data['trunk_liquid_debt'] * model_setup['daily_liquid_trunk_sales']
    else:
        trunk_to_sell = 0
    # Split between Redeem and Sell
    # Need to ensure there is actually trunk left to sell
    if em_data['trunk_held_wallets'] > trunk_to_sell / 2 and \
            em_data['staking_balance'] > trunk_to_sell / 2 and \
            em_data['farm_tvl'] > trunk_to_sell:
        if redeem_wait_days <= 30:  # Redemption Queue at one week time to payout
            em_data['redemption_queue'] += trunk_to_sell  # Redeem Trunk
        else:
            em_data['trunk_busd_lp'].update_lp('TRUNK', trunk_to_sell)  # Sell Trunk
        # Decide where sold trunk should come from.  Use a weighted % of holdings
        wallet_ratio = em_data['trunk_held_wallets'] / em_data['trunk_liquid_debt']
        em_data['trunk_held_wallets'] -= wallet_ratio * trunk_to_sell
        stake_ratio = em_data['staking_balance'] / em_data['trunk_liquid_debt']
        em_data['staking_balance'] -= stake_ratio * trunk_to_sell
        farm_ratio = em_data['farm_tvl'] / 2 / em_data['trunk_liquid_debt']
        em_data['farm_tvl'] -= farm_ratio * trunk_to_sell * 2
    else:
        trunk_to_sell = 0

    # ------ Handle Daily Raffle ------
    # 10% of the trunk treasury is paid out to raffle winners
    if em_data['trunk_treasury'] > 0:
        em_data['stampede'].bond(em_data['trunk_treasury'] * 0.1)
        em_data['trunk_treasury'] *= 0.9  # remove trunk from treasury paid to raffle winners

    # ------- Update assets and debts ----------
    average_ele_price = bsc.get_ave_ele(em_data['ele_busd_lp'], em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
    em_assets = em_data['bertha'] * average_ele_price + em_data['trunk_busd_lp'].token_bal['BUSD'] \
                + em_data['ele_busd_lp'].token_bal['BUSD'] + em_data['ele_bnb_lp'].token_bal['WBNB'] * em_data[
                    'bnb'].usd_value \
                + em_data['busd_treasury'] + em_data['trunk_treasury'] * em_data['trunk_busd_lp'].price
    em_income = em_assets - em_assets_day_start  # How much did the asset sheet grow
    daily_yield_usd = presale_daily_yield * em_data['trunk_busd_lp'].price + futures_claimed
    em_liquidity = em_income - daily_yield_usd
    em_data['trunk_liquid_debt'] = em_data['trunk_held_wallets'] + em_data['farm_tvl'] / 2 + \
                                   em_data['staking_balance'] + em_data['stampede'].accumulated
    trunk_total_debt = em_data['trunk_liquid_debt'] + em_data['stampede'].owed
    usd_liquid_debt = em_data['trunk_liquid_debt'] * em_data['trunk_busd_lp'].price
    usd_total_debt = trunk_total_debt * em_data['trunk_busd_lp'].price
    today = model_setup['day']
    tomorrow = model_setup['day'] + pd.Timedelta(1, "d")
    running_income_funds += model_setup['buy_w_b'][today] + \
                            model_setup['buy_trunk_pcs'][today] + \
                            model_setup['buy_depot'][today] + \
                            model_setup['buy_peanuts'][today] + \
                            model_setup['buy_futures'][today]
    today_funds = model_setup['buy_w_b'][today] + \
                  model_setup['buy_trunk_pcs'][today] + \
                  model_setup['buy_depot'][today] + \
                  model_setup['buy_peanuts'][today] + \
                  model_setup['buy_futures'][today]
    tomorrow_funds = model_setup['buy_w_b'][tomorrow] + \
                     model_setup['buy_trunk_pcs'][tomorrow] + \
                     model_setup['buy_depot'][tomorrow] + \
                     model_setup['buy_peanuts'][tomorrow] + \
                     model_setup['buy_futures'][tomorrow]
    total_growth_pct = (tomorrow_funds / today_funds - 1) * 100
    ele_purchase_growth_pct = (model_setup['buy_w_b'][tomorrow] / model_setup['buy_w_b'][today] - 1) * 100
    futures_growth_pct = (model_setup['buy_futures'][tomorrow] / model_setup['buy_futures'][today] - 1) * 100

    # Output Results
    daily_snapshot = {
        "$em_assets/m": em_assets / 1E6,
        "$em_income": em_income,
        "$em_liquidity": em_liquidity,
        "$funds_in/m": running_income_funds / 1E6,
        "bertha/T": em_data['bertha'] / 1E12,
        "$bertha/m": em_data['bertha'] * average_ele_price / 1E6,
        "$elephant/m": average_ele_price * 1E6,
        "$trunk": em_data['trunk_busd_lp'].price,
        "$BNB": em_data['bnb'].usd_value,
        "$bertha_payouts/m": (daily_bertha_support_usd + futures_claimed) / 1E6,
        "daily_trunk_yield": daily_yield,
        "daily_futures_yield": futures_claimed,
        "$daily_yield/m": daily_yield_usd / 1E6,
        "$liquid_debt/m": usd_liquid_debt / 1E6,
        "liquid_debt/m": em_data['trunk_liquid_debt'] / 1E6,
        "$total_debt/m": usd_total_debt / 1E6,
        "total_debt/m": trunk_total_debt / 1E6,
        "total_debt_ratio": em_data['bertha'] * average_ele_price / usd_total_debt,
        "liquid_debt_ratio": em_data['bertha'] * average_ele_price / usd_liquid_debt,
        "daily_debt_ratio": daily_bertha_support_usd / daily_yield_usd,  # Bertha payouts vs yield
        "redemption_queue": em_data['redemption_queue'],
        "busd_treasury": em_data['busd_treasury'],
        "trunk_treasury": em_data['trunk_treasury'],
        "trunk_support_pool": em_data['trunk_support_pool'],
        "redemption_pool": em_data['redemption_pool'],
        "$redemptions_paid/m": (redemptions_paid + em_data['em_futures'].claimed) / 1E6,
        "staking_balance/m": em_data['staking_balance'] / 1E6,
        "trunk_wallets/m": em_data['trunk_held_wallets'] / 1E6,
        'farm_tvl/m': em_data['farm_tvl'] / 1E6,
        "queue_wait": redeem_wait_days,
        "farmers_depot": em_data['farmers_depot'].balance,
        "futures_busd_pool": em_data['futures_busd_pool'],
        "bonds/m": em_data['stampede'].bonds / 1E6,
        "stampede_owed/m": em_data['stampede'].owed / 1E6,
        "stampede_accumulating_yield/m": em_data['stampede'].accumulated / 1E6,
        "daily_ele_growth": ele_purchase_growth_pct,
        "daily_futures_growth": futures_growth_pct,
        "daily_total_growth": total_growth_pct
    }

    # Make daily updates and model increases in interest as protocol grows
    model_setup['day'] += pd.Timedelta("1 day")
    em_data['bnb'].usd_value = model_setup['bnb_price_s'][model_setup['day']]  # Update BNB value
    model_output[model_setup['day']] = daily_snapshot

# for debug, setting break point
# if run >= 800:
#    print(day)
# TODO: Add individual stampede and Elephant bag tracking

df_model_output = pd.DataFrame(model_output).T
df_model_output.to_csv('outputs/output_time.csv')
em_plot_time(df_model_output)
print("Done")
