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
    f_o = open('chainData_2022-12-28.pkl', 'rb')  # TODO: figure out how to update this automatically
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
buy_w_b = 0.25
buy_trunk_pcs = 0.05  # Trunk buys off PCS.  Assume goes to wallets for arbitrages, swing trading
farm_depot = 0.4  # Also used for Minting
peanuts = 0.3
if buy_w_b + buy_trunk_pcs + farm_depot + peanuts != 1:
    raise Exception("Incoming fund split needs to equal 100%")

# Handle Platform Sales
sell_w_b = 0  # In USD
# ele_market_buy = 0
# ele_market_sell = 0
daily_liquid_trunk_sales = 0.025  # % of outstanding liquid trunk sold daily at PEG.  Will be PEG-adjusted when off.

# Yield Behavior (needs to add up to 100%) - only for "claim" days
# Set these values for a fully running system.  Will be modified based on Trunk price during recovery.
yield_to_hold = 0.05
yield_to_stake = 0.5
yield_to_farm = 0.45
if yield_to_hold + yield_to_stake + yield_to_farm != 1:
    raise Exception("Yield behavior must add to 100%")

# Setup Run
# schedule = ['roll', 'roll', 'roll', 'roll', 'claim', 'claim', 'claim']
# schedule = ['roll', 'roll', 'roll', 'roll', 'roll', 'roll', 'roll', 'claim', 'claim']  # 7/1/1
# schedule = ['claim']
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
starting_ele_price = ele_busd_lp.price
starting_trunk_price = trunk_busd_lp.price
starting_bnb_price = bnb.usd_value
starting_bwb = buy_w_b
starting_incoming = incoming_funds

# ------ Set up BNB changes ------
# TODO: Turn this into a function.  it can definitely be cleaned up.
start = date(2022, 10, 1)  # Use the previous quarter start
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
    # Update the System

    # ------ Daily Bertha Support ------
    average_ele_price = (ele_busd_lp.price + (ele_bnb_lp.price * bnb.usd_value)) / 2  # Should really be weighted, but
    # ...won't make a significant difference
    redemption_bertha_support = bertha * average_ele_price * redemption_support_apr
    daily_bertha_support = bertha * average_ele_price * (redemption_support_apr + trunk_support_apr)

    # Handle Treasuries
    # ------ BwB ------
    ele_bought = bsc.elephant_buy(buy_w_b * incoming_funds, ele_busd_lp, ele_bnb_lp, bnb.usd_value)
    bertha += ele_bought * 0.08  # 8% tax to Bertha
    # ------ SwB - make simple and assume always sell into BUSD pool ------
    ele_sold = sell_w_b / average_ele_price
    # 92% of Elephant sold goes to LP, 8% to Bertha
    busd_removed = bsc.elephant_sell(ele_sold * 0.92, ele_busd_lp, ele_bnb_lp, bnb.usd_value)
    bertha += ele_sold * 0.08
    # ------ Minting, Depot, and Peanuts ------
    busd_treasury += (farm_depot + peanuts) * incoming_funds
    # TODO: Elephant Market Buy
    # TODO: Elephant Market Sell

    # Handle Governance
    # ------ Buybacks for Bertha ------
    buyback_funds = busd_treasury * elephant_buyback_apr  # In USD
    busd_treasury -= buyback_funds  # Remove funds
    ele_bought = bsc.elephant_buy(buyback_funds, ele_busd_lp, ele_bnb_lp, bnb.usd_value)
    bertha += ele_bought  # All of these funds go to bertha

    # ------ Redemptions ------
    redemption_funds = bertha * redemption_support_apr  # Daily funds in ELEPHANT
    bertha -= redemption_funds  # Update bertha balance
    busd_received = bsc.elephant_sell(redemption_funds, ele_busd_lp, ele_bnb_lp, bnb.usd_value)  # Sell Elephant
    redemption_pool += busd_received  # Add BUSD funds to the redemption pool
    if redemption_queue >= redemption_pool:
        redemption_queue -= redemption_pool  # Payout as much of queue as possible
        redemption_pool = 0  # Pool is now drained
    else:
        redemption_pool -= redemption_queue  # Payout remainder of redemption queue
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

    # ------ Arbitrage Trunk LP with Redemption Pool (if available) or Minting ------
    # SQRT(CP) will give perfect split.  don't arbitrage more than 25%/day
    delta = (trunk_busd_lp.const_prod ** 0.5 - trunk_busd_lp.token_bal['BUSD']) * 0.25
    if trunk_busd_lp.price < 1:
        if redemption_pool < 10000:  # Give it some buffer to smooth things
            pass
        elif redemption_pool > delta:
            trunk_busd_lp.update_lp('BUSD', delta)
            redemption_pool -= delta
        else:
            trunk_busd_lp.update_lp('BUSD', redemption_pool)
            redemption_pool = 0
    elif trunk_busd_lp.price > 1:  # Delta should be negative in this case
        trunk_busd_lp.update_lp('TRUNK', abs(delta))  # Sell trunk on PCS
        if trunk_treasury > abs(delta):
            trunk_treasury -= abs(delta)  # Comes from Trunk Treasury if there are funds

    # Handle Yields and Trunk Debt
    # ------ Calculate Trunk Yield and add to liquid trunk ------ #
    stk_yield = staking_balance * staking_apr  # In Trunk
    fm_yield = em_farm_tvl * em_farms_max_apr * trunk_busd_lp.price
    if stampede_owed > 0:  # Make sure Max Payout hasn't occurred yet
        stp_yield = stampede_bonds * (stampede_max_apr * trunk_busd_lp.price)  # In Trunk
    else:
        stp_yield = 0
    # Stampede debt tracking
    action = roll_claim.pop()
    if action == 'roll':
        stampede_bonds += stp_yield  # yield rolled back into stampede
        stampede_owed += stp_yield * 2.05  # Rolling will increase the stampede payout owed
        kept_yield = stk_yield + fm_yield
    else:  # Claim Day
        stampede_owed -= stp_yield  # Trunk paid out from Stampede, reducing debt
        kept_yield = stk_yield + fm_yield + stp_yield
    # Decide where yield are held (worst case, assume put into yield generation vs just held in a wallet)
    staking_balance += kept_yield * yield_to_stake
    trunk_held_wallets += kept_yield * yield_to_hold
    # To farm, assume need to sell half of yield to purchase a pairing token
    trunk_busd_lp.update_lp('TRUNK', kept_yield * yield_to_farm / 2)  # Sell half of trunk to pair
    em_farm_tvl += kept_yield * yield_to_farm  # TVL still goes up by total amount
    # Update Trunk Treasury Balance
    if trunk_treasury > 0 + kept_yield:
        trunk_treasury -= kept_yield  # Yield will be paid from Trunk treasury, or else minted
    trunk_liquid_debt = staking_balance + em_farm_tvl / 2 + trunk_held_wallets  # Update liquid debt
    daily_yield = (stp_yield + stk_yield + fm_yield) * trunk_busd_lp.price  # Daily yield paid in USD ...
    # ... On roll days, the stampede yield would technically not be added, but this is just to keep a tally ...
    # ... of the average required payout by the system in yield

    # ------ Trunk added from Peanuts, Depot, and PCS buys  -------
    # Minting is treated as buys off PCS until PEG since DEPOT is immediate instead of vested
    # Peanuts goes to stampede, but no TRUNK is actually created at this point
    stampede_bonds += peanuts * incoming_funds / max(trunk_busd_lp.price, 0.25)
    # Buys off PCS stop at Peg and money instead goes to depot funds
    if trunk_busd_lp.price < 1:
        trunk_busd_lp.update_lp('BUSD', buy_trunk_pcs * incoming_funds)  # purchase trunk
        trunk_held_wallets += trunk_busd_lp.tokens_removed  # add trunk to wallets
    else:
        farm_depot += buy_trunk_pcs  # At Peg, assume folks don't buy, but mint/depot instead
    # Split depot between farm and staking (say 70/30?)  Worst case would be all in farm due to higher yields
    depot_buy = farm_depot * incoming_funds / max(trunk_busd_lp.price, 0.25)
    depot_deposits += depot_buy  # Need to track both the total deposits and what is remaining
    depot_balance += depot_buy
    if trunk_treasury > depot_buy:
        trunk_treasury -= depot_buy  # use trunk treasury to pay out or else new trunk is minted
    if depot_balance > depot_deposits * 1/30:  # Depot pays out 3.33% per day
        em_farm_tvl += depot_deposits * 1/30 * 0.7 * 2  # TVL goes up by double what was put in
        staking_balance += depot_deposits * 1/30 * 0.3  # split 70/30 with farms
        depot_balance -= depot_deposits * 1/30
    else:
        em_farm_tvl += depot_balance * 0.7 * 2  # TVL goes up by double what was put in
        staking_balance += depot_balance * 0.3  # split 70/30 with farms
        depot_balance = 0  # depot should now be empty
    stampede_bonds += trunk_treasury * 0.1  # 10% of the trunk treasury is paid out to raffle winners
    trunk_treasury *= 0.9  # remove trunk from treasury paid to raffle winners

    # ------ Handle Trunk Selling/Redeeming ------
    # Model behavior to limit selling to close to what Bertha can actually support, based on Trunk Price
    daily_bertha_support_trunk = daily_bertha_support / trunk_busd_lp.price
    max_trunk_to_sell = trunk_liquid_debt * daily_liquid_trunk_sales
    # Figure out how much trunk to actually sell based on Trunk price - lower price, reduce selling
    if redemption_queue < 25000:  # Limit selling while servicing redemption queue
        trunk_to_sell = min(max_trunk_to_sell, daily_bertha_support_trunk / 2)
    else:
        trunk_to_sell = max_trunk_to_sell * trunk_busd_lp.price
    # Split between Redeem and Sell
    if redemption_queue < redemption_bertha_support * 14:  # Redemption Queue at two weeks time to payout
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

    # ------- Update total debts ----------
    trunk_liquid_debt = trunk_held_wallets + em_farm_tvl/2 + staking_balance
    trunk_total_debt = trunk_liquid_debt + stampede_owed
    usd_liquid_debt = trunk_liquid_debt * trunk_busd_lp.price
    usd_total_debt = trunk_total_debt * trunk_busd_lp.price
    running_income_funds += incoming_funds  # Keep a running total of all funds into the system

    # Output Results
    daily_snapshot = {
        "$funds_in/m": running_income_funds / 1E6,
        "bertha/T": bertha / 1E12,
        "$bertha/m": bertha * average_ele_price / 1E6,
        "$elephant/m": average_ele_price * 1E6,
        "$trunk": trunk_busd_lp.price,
        "$BNB": bnb.usd_value,
        "$bertha_payouts/m": daily_bertha_support / 1E6,
        "$daily_yield/m": daily_yield / 1E6,
        "$liquid_debt/m": usd_liquid_debt / 1E6,
        "liquid_debt/m": trunk_liquid_debt / 1E6,
        "$total_debt/m": usd_total_debt / 1E6,
        "total_debt/m": trunk_total_debt / 1E6,
        "total_debt_ratio": bertha * average_ele_price / usd_total_debt,
        "liquid_debt_ratio": bertha * average_ele_price / usd_liquid_debt,
        "daily_debt_ratio": daily_bertha_support / daily_yield,  # Bertha payouts vs yield
        "redemption_queue": redemption_queue,
        "trunk_treasury": trunk_treasury,
        "staking_balance/m": staking_balance / 1E6,
        "trunk_wallets/m": trunk_held_wallets / 1E6,
        'farm_tvl/m': em_farm_tvl / 1E6
    }

    # Make daily updates
    day += pd.Timedelta("1 day")
    bnb.usd_value = bnb_price_s[day]  # Update BNB value
    elephant_gain = average_ele_price / starting_ele_price
    # buy_w_b = starting_bwb * ((elephant_gain-1) / 5) + 1  # Represent FOMO into Elephant Token
    bnb_gain = bnb.usd_value / starting_bnb_price
    incoming_funds = starting_incoming * bnb_gain  # Incoming funds increasing with market (represented by BNB gain)
    em_data_time[day] = daily_snapshot
    em_data_funds[running_income_funds / 1E6] = daily_snapshot  # Alternate view in millions in

    # for debug, setting break point
    # if run >= 800:
    #    print(day)
    # TODO: Model increases/decreases in governance APRs
    # TODO: Add individual stampede and Elephant bag tracking

em_dataframe_time = pd.DataFrame(em_data_time).T
em_dataframe_funds = pd.DataFrame(em_data_funds).T
em_dataframe_time.to_csv('output_time.csv')
em_dataframe_funds.to_csv('output_funds.csv')
em_plot_time(em_dataframe_time)
# em_plot_funds(em_dataframe_funds)
print("Done")
