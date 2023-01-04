# Elephant Money Modeler

import pandas as pd
import addr_contracts
import bsc_classes as bsc
import addr_tokens
from datetime import date
from plotting import em_plot_time
from plotting import em_plot_funds
import pickle

read_blockchain = False  # Flag True to update balances from blockchain.  Takes a LONG time.  Requires Moralis API
if read_blockchain:
    # get EM info (this can be done automatically)
    # get LPs
    ele_bnb_lp = bsc.CakeLP(addr_tokens.Elephant, addr_tokens.BNB)
    ele_busd_lp = bsc.CakeLP(addr_tokens.Elephant, addr_tokens.BUSD)
    trunk_busd_lp = bsc.CakeLP(addr_tokens.Trunk, addr_tokens.BUSD)
    # get Tokens used
    bnb = bsc.Token('BNB', addr_tokens.BNB)
    # get Treasury balances
    bertha = bsc.GetWalletBalance(addr_contracts.ele_bertha, addr_tokens.Elephant).balance
    busd_treasury = bsc.GetWalletBalance(addr_contracts.ele_busd_treasury, addr_tokens.BUSD).balance
    trunk_treasury = bsc.GetWalletBalance(addr_contracts.trunk_treasury, addr_tokens.Trunk).balance

    to_pickle = [ele_bnb_lp, ele_busd_lp, trunk_busd_lp, bnb, bertha, busd_treasury, trunk_treasury]
    f = open('chainData_{0}.pkl'.format(date.today()), 'wb')
    pickle.dump(to_pickle, f)
    f.close()
else:
    f_o = open('chainData_2023-01-03.pkl', 'rb')  # TODO: figure out how to update this automatically
    from_pickle = pickle.load(f_o)
    f_o.close()
    [ele_bnb_lp, ele_busd_lp, trunk_busd_lp, bnb, bertha, busd_treasury, trunk_treasury] = from_pickle

# get EM info (this has to be done manually - Updated Dec 28, 2022)
stampede_max_apr = 2.05 / 365  # Use Daily APR
em_farms_max_apr = 1.25 / 365  # Use Daily APR
staking_apr = 0.3 / 365  # This is variable.  Check the site.  No good way to calculate the change
redemption_queue = 1.44E6
staking_balance = 9.078E6
em_farm_tvl = 7.265E6  # Yield is paid out on TVL
em_farm_balance = em_farm_tvl / 2  # This is the total trunk balance in the farms
stampede_bonds = 55.42E6
stampede_payouts = 57.94E6
stampede_owed = 2.05 * stampede_bonds - stampede_payouts  # Total platform debt as of "today"
trunk_supply = 29.892E6
trunk_held_wallets = trunk_supply * 0.0355  # Estimate based off bscscan token holders:
# https://bscscan.com/token/tokenholderchart/0xdd325C38b12903B727D16961e61333f4871A70E0
trunk_liquid_debt = staking_balance + trunk_held_wallets + em_farm_balance
trunk_total_debt = trunk_liquid_debt + stampede_owed

# governance contracts
trunk_support_apr = 0.1 / 365  # Get Daily APR - 10% yearly per last BT comment
trunk_support_pool = 0
redemption_support_apr = 0.1 / 365  # Get Daily APR - 10% yearly per last BT comment
redemption_pool = 0
elephant_buyback_apr = 0.5  # This is per day of the BUSD treasury
depot_deposits = 0
depot_balance = 0

# Incoming Funds - use total and the split by %
incoming_funds = 100000
# below should add to 100%
buy_w_b = 0.3
buy_trunk_pcs = 0.1  # Trunk buys off PCS.  Assume goes to wallets for arbitrages, swing trading
farm_depot = 0.3  # Also used for Minting
peanuts = 0.3
if 0.99 <= buy_w_b + buy_trunk_pcs + farm_depot + peanuts >= 1.01:
    raise Exception("Incoming fund split needs to equal 100%")

# Platform Sales
sell_w_b = 0  # In USD
# ele_market_buy = 0
# ele_market_sell = 0
peg_trunk = True  # This will over-ride the amount of sales in order to keep Trunk near $1
yield_sales = 0.5  # % of daily available yield to sell (at PEG)
daily_liquid_trunk_sales = 0.02  # Maximum % of trunk held to be sold in a day only *if* the platform can support it.

# Yield Behavior (needs to add up to 100%) - only for "claim" days
# Set these values for a fully running system.  Will be modified based on Trunk price during recovery.
yield_to_hold = 0.01
yield_to_stake = 0.49
yield_to_farm = 0.3
yield_to_bond = 0.2
if yield_to_hold + yield_to_stake + yield_to_farm + yield_to_bond != 1:
    raise Exception("Yield behavior must add to 100%")

# Setup Run
schedule = ['roll', 'claim']
run_quarters = 10
run_days = run_quarters * 365 / 4
cycles = round(run_days / len(schedule)) + 1
roll_claim = []
i = 1
while i <= cycles:  # Create full schedule for rolls and claims
    for j in schedule:
        roll_claim.append(j)
    i += 1
day = pd.to_datetime(date.today())
em_data_time = {}
em_data_funds = {}
running_income_funds = 0
redemptions_paid = 0
starting_ele_price = ele_busd_lp.price
starting_trunk_price = trunk_busd_lp.price
starting_bnb_price = bnb.usd_value
starting_bwb = buy_w_b
starting_incoming = incoming_funds

# ------ Set up BNB changes ------
# TODO: Turn this into a function.  it can definitely be cleaned up.
start = date(2023, 1, 1)  # Use the previous quarter start
periods = run_quarters + 2  # we are starting one quarter back from today's date and want to go an extra quarter
sparse_range = pd.date_range(start, periods=periods, freq="QS")
full_range = pd.date_range(start, sparse_range.date[-1])
# Look for a bull run in 2024.  Start the first two values with the current price
# bnb_price_movement = [bnb.usd_value, bnb.usd_value, 275, 300, 325, 350, 375, 400, 500, 600,
#                      650, 700, 725, 750, 650, 625, 700, 750, 800, 800, 750, 800]
bnb_price_movement = [bnb.usd_value, bnb.usd_value, 275, 300, 325, 350, 375, 400, 500, 600, 650, 700]
# bnb_price_movement = [250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250]
if sparse_range.size != bnb_price_movement.__len__():
    raise Exception("BNB Price range does not match date range")
temp_bnb_s = pd.Series(bnb_price_movement, index=sparse_range)
bnb_price_s = pd.Series(temp_bnb_s, index=full_range).interpolate()  # interpolate to get a daily price increase

# Run Model
for run in range(int(run_days)):

    # Daily Bertha Support ---------------------------------------------------------------------
    average_ele_price = (ele_busd_lp.price + (ele_bnb_lp.price * bnb.usd_value)) / 2  # Should really be weighted, but
    # ...won't make a significant difference
    daily_bertha_support_usd = bertha * average_ele_price * (redemption_support_apr + trunk_support_apr)
    em_assets_day_start = bertha * average_ele_price + trunk_busd_lp.token_bal['BUSD'] \
                          + ele_busd_lp.token_bal['BUSD'] + ele_bnb_lp.token_bal['WBNB'] * bnb.usd_value \
                          + busd_treasury + trunk_treasury * trunk_busd_lp.price

    # Handle Treasuries ---------------------------------------------------------------------
    # ------ BwB ------
    ele_bought = bsc.elephant_buy(buy_w_b * incoming_funds, ele_busd_lp, ele_bnb_lp, bnb.usd_value)
    bertha += ele_bought * 0.08  # 8% tax to Bertha
    # ------ SwB ------
    ele_sold = sell_w_b / average_ele_price
    # 92% of Elephant sold goes to LP, 8% to Bertha
    busd_removed = bsc.elephant_sell(ele_sold * 0.92, ele_busd_lp, ele_bnb_lp, bnb.usd_value)
    bertha += ele_sold * 0.08
    # ------ Farmer's Depot and Peanuts ------
    busd_treasury += (farm_depot + peanuts) * incoming_funds
    # TODO: Elephant Market Buy
    # TODO: Elephant Market Sell

    # Handle Governance ---------------------------------------------------------------------
    # ------ Buybacks for Bertha ------
    buyback_funds = busd_treasury * elephant_buyback_apr  # In USD
    busd_treasury -= buyback_funds  # Remove funds
    ele_bought = bsc.elephant_buy(buyback_funds, ele_busd_lp, ele_bnb_lp, bnb.usd_value)
    bertha += ele_bought  # All of these funds go to bertha

    # ------ Redemptions ------
    redemption_funds = bertha * redemption_support_apr  # Daily funds in ELEPHANT
    bertha -= redemption_funds  # Update bertha balance
    busd_received = bsc.elephant_sell(redemption_funds, ele_busd_lp, ele_bnb_lp, bnb.usd_value)  # Sell Elephant
    redeem_wait_days = int(redemption_queue / busd_received) + 1
    redemption_pool += busd_received  # Add BUSD funds to the redemption pool
    if redemption_queue >= redemption_pool:
        redemption_queue -= redemption_pool  # Payout as much of queue as possible
        redemptions_paid += redemption_pool
        redemption_pool = 0  # Pool is now drained
    else:
        redemption_pool -= redemption_queue  # Payout remainder of redemption queue
        redemptions_paid += redemption_queue
        redemption_queue = 0  # Queue is now at 0

    # ------ Trunk Support ------
    support_funds = bertha * trunk_support_apr  # Daily funds in ELEPHANT
    bertha -= support_funds  # Update Bertha balance
    busd_received = bsc.elephant_sell(support_funds, ele_busd_lp, ele_bnb_lp, bnb.usd_value)
    trunk_support_pool += busd_received  # Add BUSD funds to the trunk support pool
    if trunk_busd_lp.price < 1:
        trunk_busd_lp.update_lp('BUSD', trunk_support_pool)  # Buy Trunk off PCS
        trunk_treasury += trunk_busd_lp.tokens_removed  # Trunk is deposited in the trunk treasury for further use
        trunk_support_pool = 0
    else:
        pass  # support pool just grows if Trunk is already at Peg

    # Handle Yield and Sales/Redemptions (all in Trunk) ----------------------------------------------------------------
    # ------ Calculate Available Yield ------ #
    stk_yield = staking_balance * staking_apr  # In Trunk
    fm_yield = em_farm_tvl * em_farms_max_apr * trunk_busd_lp.price
    if stampede_owed > 0:  # Make sure Max Payout hasn't occurred yet
        stp_yield = stampede_bonds * (stampede_max_apr * trunk_busd_lp.price)  # In Trunk
    else:
        stp_yield = 0
    daily_available_yield = stk_yield + fm_yield + stp_yield

    # ------ Stampede tracking and Remaining Yield ------
    action = roll_claim.pop()
    if action == 'roll':
        stampede_bonds += stp_yield  # yield rolled back into stampede
        stampede_owed += stp_yield * 2.05  # Rolling will increase the stampede payout owed
        kept_yield = stk_yield + fm_yield
    else:  # Claim Day
        stampede_owed -= stp_yield  # Trunk paid out from Stampede, reducing debt
        kept_yield = stk_yield + fm_yield + stp_yield
    if trunk_treasury > 0 + kept_yield:  # Yield will be paid from Trunk treasury, or else minted
        trunk_treasury -= kept_yield

    # ------ Determine community Peg support and sales amount ------
    if peg_trunk and trunk_busd_lp.price < 1:
        trunk_sales = daily_bertha_support_usd / 2  # By looking at only USD, will keep selling low while $trunk is low
    elif peg_trunk:
        trunk_sales = (1 - 0.9 ** 0.5) * trunk_busd_lp.token_bal['TRUNK']  # Allow up to 10% drop in Trunk Price
    else:
        trunk_sales = kept_yield * yield_sales

    # ------ Yield Redemption/Sales ------
    if redeem_wait_days <= 14:  # This can be adjusted, just guessing
        redemption_queue += trunk_sales
    else:
        trunk_busd_lp.update_lp('TRUNK', trunk_sales)
    kept_yield -= trunk_sales  # depending on whether this is positive or negative will determine sales vs hold

    # ------ Update balances based on kept yield ------
    # --- Buys off PCS - included here so that it can use the same deposit ratios defined
    # Once Peg is hit, this is the same as minting
    trunk_busd_lp.update_lp('BUSD', buy_trunk_pcs * incoming_funds)  # purchase trunk
    kept_yield += trunk_busd_lp.tokens_removed
    # --- Update Balances ---
    if kept_yield > 0:
        staking_balance += kept_yield * yield_to_stake
        trunk_held_wallets += kept_yield * yield_to_hold
        em_farm_tvl += kept_yield * yield_to_farm  # TVL still goes up by total amount, assume bringing pair token
        trunk_liquid_debt = staking_balance + em_farm_tvl / 2 + trunk_held_wallets  # Update liquid debt
        stampede_bonds += kept_yield * yield_to_bond

    # ------ Arbitrage Trunk LP with Redemption Pool or Minting ------
    # TODO: This can be made a function or class
    # SQRT(CP) will give perfect split.
    delta = (trunk_busd_lp.const_prod ** 0.5 - trunk_busd_lp.token_bal['BUSD'])
    if trunk_busd_lp.price <= 1.00 and redeem_wait_days < 30:  # No arbitrage until queue is reasonable.
        trunk_busd_lp.update_lp('BUSD', delta * 0.1)  # Arbitrage 10% per day
        redemption_queue += delta * 0.1
    elif trunk_busd_lp.price > 1.00:  # Trunk is over $1.  "Delta" will be negative
        trunk_busd_lp.update_lp('TRUNK', abs(delta))  # Sell trunk on PCS
        busd_treasury += abs(delta)  # Arber would need to mint trunk from the protocol
        if trunk_treasury > abs(delta):
            trunk_treasury -= abs(delta)  # Comes from Trunk Treasury if there are funds
    else:
        pass

    # Incoming Funds ---------------------------------------------------------------------
    # --- Peanuts ---
    stampede_bonds += peanuts * incoming_funds / max(trunk_busd_lp.price, 0.25)
    # --- Farmer's Depot ---
    # Split depot between farm and staking (say 70/30?)  Worst case would be all in farm due to higher yields
    depot_buy = farm_depot * incoming_funds / max(trunk_busd_lp.price, 0.25)
    depot_deposits += depot_buy  # Need to track both the total deposits and what is remaining
    depot_balance += depot_buy
    # --- Distribute Depot Funds ---
    if depot_balance > depot_deposits / 30:  # Depot pays out 3.33% per day
        em_farm_tvl += depot_deposits / 30 * 2  # TVL goes up by double what was put in
        depot_balance -= depot_deposits / 30
        if trunk_treasury > depot_deposits / 30:  # Take funds from trunk treasury if available
            trunk_treasury -= depot_deposits / 30
    else:
        em_farm_tvl += depot_balance * 2  # TVL goes up by double what was put in
        if trunk_treasury > depot_balance:
            trunk_treasury -= depot_balance
        depot_balance = 0  # depot should now be empty

    # Handle Liquid Trunk Selling/Redeeming ---------------------------------------------------------------------
    if peg_trunk and trunk_busd_lp.price > 0.99:  # Allow some selling
        trunk_to_sell = trunk_busd_lp.token_bal['BUSD'] - (trunk_busd_lp.const_prod * 0.9) ** 0.5
    elif peg_trunk:
        trunk_to_sell = 0
    else:
        trunk_to_sell = trunk_liquid_debt * daily_liquid_trunk_sales
    # Split between Redeem and Sell
    if redeem_wait_days <= 14:  # Redemption Queue at one week time to payout
        redemption_queue += trunk_to_sell  # Redeem Trunk
    else:
        trunk_busd_lp.update_lp('TRUNK', trunk_to_sell)  # Sell Trunk
    # Decide where sold trunk should come from.  Use a weighted % of holdings
    wallet_ratio = trunk_held_wallets / trunk_liquid_debt
    trunk_held_wallets -= wallet_ratio * trunk_to_sell
    stake_ratio = staking_balance / trunk_liquid_debt
    staking_balance -= stake_ratio * trunk_to_sell
    farm_ratio = em_farm_tvl / 2 / trunk_liquid_debt
    em_farm_tvl -= farm_ratio * trunk_to_sell * 2

    # ------ Handle Daily Raffle ------
    stampede_bonds += trunk_treasury * 0.1  # 10% of the trunk treasury is paid out to raffle winners
    trunk_treasury *= 0.9  # remove trunk from treasury paid to raffle winners

    # ------- Update assets and debts ----------
    em_assets = bertha * average_ele_price + trunk_busd_lp.token_bal['BUSD'] \
                + ele_busd_lp.token_bal['BUSD'] + ele_bnb_lp.token_bal['WBNB'] * bnb.usd_value \
                + busd_treasury + trunk_treasury * trunk_busd_lp.price
    em_income = em_assets - em_assets_day_start  # How much did the asset sheet grow
    daily_yield_usd = daily_available_yield * trunk_busd_lp.price
    em_liquidity = em_income - daily_yield_usd
    trunk_liquid_debt = trunk_held_wallets + em_farm_tvl / 2 + staking_balance
    trunk_total_debt = trunk_liquid_debt + stampede_owed
    usd_liquid_debt = trunk_liquid_debt * trunk_busd_lp.price
    usd_total_debt = trunk_total_debt * trunk_busd_lp.price
    running_income_funds += (buy_w_b - starting_bwb) * incoming_funds  # Extra funds from BwB
    running_income_funds += incoming_funds  # Keep a running total of all funds into the system

    # Output Results
    daily_snapshot = {
        "$em_assets/m": em_assets / 1E6,
        "$em_income": em_income,
        "$em_liquidity": em_liquidity,
        "$funds_in/m": running_income_funds / 1E6,
        "bertha/T": bertha / 1E12,
        "$bertha/m": bertha * average_ele_price / 1E6,
        "$elephant/m": average_ele_price * 1E6,
        "$trunk": trunk_busd_lp.price,
        "$BNB": bnb.usd_value,
        "$bertha_payouts/m": daily_bertha_support_usd / 1E6,
        "$daily_yield/m": daily_yield_usd / 1E6,
        "$liquid_debt/m": usd_liquid_debt / 1E6,
        "liquid_debt/m": trunk_liquid_debt / 1E6,
        "$total_debt/m": usd_total_debt / 1E6,
        "total_debt/m": trunk_total_debt / 1E6,
        "total_debt_ratio": bertha * average_ele_price / usd_total_debt,
        "liquid_debt_ratio": bertha * average_ele_price / usd_liquid_debt,
        "daily_debt_ratio": daily_bertha_support_usd / daily_yield_usd,  # Bertha payouts vs yield
        "redemption_queue": redemption_queue,
        "busd_treasury": busd_treasury,
        "trunk_treasury": trunk_treasury,
        "trunk_support_pool": trunk_support_pool,
        "redemption_pool": redemption_pool,
        "$redemptions_paid/m": redemptions_paid / 1E6,
        "staking_balance/m": staking_balance / 1E6,
        "trunk_wallets/m": trunk_held_wallets / 1E6,
        'farm_tvl/m': em_farm_tvl / 1E6,
        "redemption_queue_wait": redeem_wait_days,
    }

    # Make daily updates and model increases in interest as protocol grows
    day += pd.Timedelta("1 day")
    bnb.usd_value = bnb_price_s[day]  # Update BNB value
    elephant_gain = average_ele_price / starting_ele_price
    buy_w_b = min(starting_bwb * ((elephant_gain - 1) / 5 + 1), starting_bwb * 3)  # Represent FOMO into Elephant Token
    bnb_gain = bnb.usd_value / starting_bnb_price
    incoming_funds = starting_incoming * bnb_gain  # Incoming funds increasing with market (represented by BNB gain)
    if bertha * average_ele_price > trunk_liquid_debt * 2:  # Respond to growth by increasing support payouts
        redemption_support_apr *= 1.003
        trunk_support_apr *= 1.003
    em_data_time[day] = daily_snapshot
    em_data_funds[running_income_funds / 1E6] = daily_snapshot  # Alternate view in millions in

    # for debug, setting break point
    # if run >= 800:
    #    print(day)
    # TODO: Add individual stampede and Elephant bag tracking

em_dataframe_time = pd.DataFrame(em_data_time).T
em_dataframe_funds = pd.DataFrame(em_data_funds).T
em_dataframe_time.to_csv('output_time.csv')
em_dataframe_funds.to_csv('output_funds.csv')
em_plot_time(em_dataframe_time)
# em_plot_funds(em_dataframe_funds)
print("Done")
