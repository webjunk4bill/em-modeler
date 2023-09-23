# Elephant Money Modeler

import pandas as pd
from numpy import random
import bsc_classes as bsc
from plotting import em_plot_time
from setup_run import setup_run
from em_data import get_em_data

# Get EM Protocol Data
# Some manual input is necessary in em_data.py due to inability to read some EM contracts
em_data = get_em_data(read_blockchain=False)  # False = pull from pickle vs query blockchain

# Run Model Setup (starting funds, run quarters, current BNB price)
# Edit parameters in setup_run.py to adjust model parameters
model_setup = setup_run('2025-12-31', em_data['bnb'].usd_value)
# --- initialize variables
# Set up current Futures Stakes (just take average of the total)
futures = []
avg_stake = em_data['futures_info']['balance'] / em_data['futures_info']['users']
avg_compounded = em_data['futures_info']['compounds'] / em_data['futures_info']['users']
avg_claimed = em_data['futures_info']['claimed'] / em_data['futures_info']['users']
i = 0
while i < em_data['futures_info']['users']:
    futures.append(bsc.YieldEngineV6(avg_stake, 0.005))
    futures[i].compounds = avg_compounded
    futures[i].claimed = avg_claimed
    days_passed = int(model_setup['f_claims_usd'] / futures[i].daily_payout) + 1
    futures[i].pass_days(days_passed)  # Need to build up the proper amount available to match daily claim total
    futures[i].total_days = model_setup['f_claim_wait'] + 1  # Assume all current wallets will start with actions
    i += 1
# Set up current Stampede Stakes
stampede = []
avg_stake = em_data['stampede_info']['balance'] / em_data['stampede_info']['users']
avg_compounded = em_data['stampede_info']['compounds'] / em_data['stampede_info']['users']
avg_claimed = em_data['stampede_info']['claimed'] / em_data['stampede_info']['users']
i = 0
stp_rate = 0.005 * em_data['trunk_busd_lp'].price
while i < em_data['stampede_info']['users']:
    stampede.append(bsc.YieldEngineV6(avg_stake, 0.005 * stp_rate))
    stampede[i].compounds = avg_compounded
    stampede[i].claimed = avg_claimed
    stampede[i].pass_days(random.randint(1, 180))  # this will set up a varying amount (to 6 months) of available
    i += 1
# Others
redemptions_paid = 0
cum_futures_payouts = 0
running_inflows = 0
running_outflows = 0
model_output = {}

# Create and Run Model
for run in range(int(model_setup['run_days'])):
    # Initialize Variables
    em_income = 0
    em_outflows = 0
    trunk_yield = 0
    stp_rate = 0.005 * em_data['trunk_busd_lp'].price
    today = model_setup['day']
    tomorrow = model_setup['day'] + pd.Timedelta(1, "d")
    yesterday = model_setup['day'] - pd.Timedelta("1d")
    # Daily Bertha Support ---------------------------------------------------------------------
    average_ele_price = bsc.get_ave_ele(em_data['ele_busd_lp'], em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
    daily_bertha_support_usd = em_data['bertha'] * average_ele_price * model_setup['bertha_outflows']
    em_assets_day_start = em_data['bertha'] * average_ele_price + em_data['trunk_busd_lp'].token_bal['BUSD'] + \
                          em_data['ele_busd_lp'].token_bal['BUSD'] + em_data['ele_bnb_lp'].token_bal['WBNB'] * \
                          em_data['bnb'].usd_value + em_data['busd_treasury'] + em_data['trunk_treasury'] * \
                          em_data['trunk_busd_lp'].price

    # Get Day Start Prices -----------------------------------------------------------------------
    begin_ele_price = average_ele_price
    begin_bnb_price = em_data['bnb'].usd_value
    begin_trunk_price = em_data['trunk_busd_lp'].price

    # Incoming Funds ---------------------------------------------------------------------
    # --- Farmer's Depot ---
    '''
    depot_buy_usd = model_setup['buy_depot'][model_setup['day']]  # Don't want to directly modify the starting value
    if em_data['trunk_busd_lp'].price < 0.98:  # 10% of funds auto purchase market Trunk if below $0.98
        em_data['trunk_treasury'] += em_data['trunk_busd_lp'].update_lp('BUSD', depot_buy_usd * 0.1)
        depot_buy_usd *= 0.9
    depot_buy = depot_buy_usd / max(em_data['trunk_busd_lp'].price, 0.25)  # Convert to Trunk
    em_data['farmers_depot'].deposit(depot_buy)
    em_data['busd_treasury'] += depot_buy_usd  # funds go to busd treasury
    '''
    # --- new Futures stakes ---
    wallets = int(model_setup['f_new_wallets'][model_setup['day']])
    deposit = model_setup['f_new_deposit'][model_setup['day']]
    for _ in range(wallets):
        em_data['futures_busd_pool'] += deposit * 0.1
        em_data['busd_treasury'] += deposit * 0.9
        futures.append(bsc.YieldEngineV6(deposit, 0.005))  # create new stake
        em_income += deposit
    # --- NFT Mints ---
    mint_funds = model_setup['nft_mint_volume'][model_setup['day']]
    mint_price = em_data['nft'].price
    em_data['nft'].mint(int(mint_funds / (mint_price * begin_bnb_price)))
    em_income += mint_funds
    ele_bought = bsc.elephant_buy(mint_funds, em_data['ele_busd_lp'], em_data['ele_bnb_lp'], begin_bnb_price)
    em_data['bertha'] += ele_bought  # bertha gets full amount of mint volume
    # --- NFT Marketplace Sales ---
    # Market sells are 90% of the current mint price and Bertha gets a 30% cut of that
    sell_funds = model_setup['nft_sales_revenue'][model_setup['day']]
    em_income += sell_funds
    ele_bought = bsc.elephant_buy(sell_funds, em_data['ele_busd_lp'], em_data['ele_bnb_lp'], begin_bnb_price)
    em_data['bertha'] += ele_bought  # bertha gets full amount of mint volume

    # Handle Elephant Buy/Sell ---------------------------------------------------------------------
    # ------ BwB ------
    ele_bought = bsc.elephant_buy(model_setup['bwb_volume'][model_setup['day']], em_data['ele_busd_lp'],
                                  em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
    em_income += model_setup['bwb_volume'][model_setup['day']]
    em_data['bertha'] += ele_bought * 0.08  # 8% tax to Bertha
    # ------ SwB ------
    ele_sold = model_setup['swb_volume'][model_setup['day']] / average_ele_price
    em_data['elephant_wallets'] += ele_bought - ele_sold
    # 92% of Elephant sold goes to LP, 8% to Bertha
    bsc.elephant_sell(ele_sold * 0.92, em_data['ele_busd_lp'], em_data['ele_bnb_lp'],
                      em_data['bnb'].usd_value)
    em_data['bertha'] += ele_sold * 0.08
    em_income += model_setup['swb_volume'][model_setup['day']] * 0.08
    average_ele_price = bsc.get_ave_ele(em_data['ele_busd_lp'], em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
    # TODO: Create class for Elephant containing LPs and automatically keeping the price up to date
    # ------ Market Buys / Sells ------
    tax_ele = 0
    buys_usd = model_setup['market_buy_volume'][model_setup['day']]
    sells_ele = model_setup['market_sell_volume'][model_setup['day']] / average_ele_price
    tax_ele += sells_ele * 0.1
    buys_ele = bsc.elephant_buy(buys_usd, em_data['ele_busd_lp'], em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
    tax_ele += buys_ele * 0.1
    sells_usd = bsc.elephant_sell(sells_ele, em_data['ele_busd_lp'], em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
    em_data['elephant_wallets'] += buys_ele - sells_ele
    tax_usd = tax_ele * em_data['ele_busd_lp'].price
    # Add liquidity to BUSD pool TODO: Confirm whether BUSD or BNB pool
    em_data['ele_busd_lp'].add_liquidity('ELEPHANT', tax_ele / 2, 'BUSD', tax_usd / 2)
    # Handle major reflections
    em_data['graveyard'] += tax_ele / 2 * (em_data['graveyard'] / 1E15)
    em_data['bertha'] += tax_ele / 2 * (em_data['bertha'] / 1E15)
    em_data['elephant_wallets'] += tax_ele / 2 * (em_data['elephant_wallets'] / 1E15)

    # Handle Governance ---------------------------------------------------------------------
    # ------ Graveyard Rebalance ------
    if em_data['graveyard'] >= 510E12:
        em_data['graveyard'] -= 10E12
        busd = bsc.elephant_sell(5E12, em_data['ele_busd_lp'], em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
        em_data['ele_busd_lp'].add_liquidity('ELEPHANT', 5E12, 'BUSD', busd)
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
    em_outflows += busd_received
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
    em_outflows += busd_received
    trunk_purchased = em_data['trunk_busd_lp'].update_lp('BUSD', busd_received)  # Buy Trunk off PCS
    minted = em_data['trumpet'].mint_trumpet(trunk_purchased)  # Mint trumpet and burn it
    em_data['trumpet'].burn_trumpet(minted)

    # ------ NFT Royalties ------
    # tokens are distributed directly to stakers
    daily_royalty = em_data['bertha'] * model_setup['nft_royalty_apr']
    em_data['bertha'] -= daily_royalty
    em_outflows += daily_royalty * average_ele_price

    # ------ Process Futures Stakes ------
    # Set up a randomized claim / deposit process based on a 2:1 ratio and 21 day cycle
    futures_claimed = 0
    futures_available = 0
    futures_tvl = 0
    # progress current stakes
    for stake in futures:  # Need to process each separate futures stake
        stake.pass_days(1)
        rand = random.randint(1, 21)
        if stake.total_days < model_setup['f_claim_wait']:  # stake too new, pass
            futures_available += stake.available
            futures_tvl += stake.debt_burden
        elif rand == 1 or stake.balance >= 0.9 * stake.max_balance:
            futures_claimed += stake.claim()
            futures_tvl += stake.debt_burden
        elif rand == 2 or rand == 3:
            stake.deposit(model_setup['f_compound_usd'])
            em_income += model_setup['f_compound_usd']
            futures_tvl += stake.debt_burden
        else:
            futures_available += stake.available
            futures_tvl += stake.debt_burden
    # Payout futures and replenish buffer pool if needed
    em_outflows += futures_claimed
    if em_data['futures_busd_pool'] >= futures_claimed:
        em_data['futures_busd_pool'] -= futures_claimed  # payout claims
    else:  # Sell Elephant to replenish pool.  Sell a 10% Buffer
        to_sell = futures_claimed * 1.1 / average_ele_price  # get num Elephant to sell
        em_data['bertha'] -= to_sell  # remove elephant from Bertha
        em_data['futures_busd_pool'] += bsc.elephant_sell(to_sell, em_data['ele_busd_lp'], em_data['ele_bnb_lp'],
                                                          em_data['bnb'].usd_value)  # sell ELEPHANT
        em_data['futures_busd_pool'] -= futures_claimed  # payout claims

    # ------ Process Stampede Stakes ------
    # At Peg, go with standard 2:1 strategy, but favor waiting while Trunk is under Peg
    # Comes to 18:2:1 ratio of wait, dep, claim
    # Increase wait time by dividing by half of the trunk price delta to Peg
    trunk_claimed = 0
    trunk_deposited = 0
    trunk_available = 0
    trunk_tvl = 0
    total_stakes = len(stampede)
    for stake in stampede:
        wait_days = 18 / min(1, (1 - em_data['trunk_busd_lp'].price) / 2)
        rand = random.randint(1, wait_days + 3)
        stake.pass_days(1, stp_rate)
        if rand == 1 or stake.balance >= 0.9 * stake.max_balance:
            trunk_yield += stake.claim()  # All claims will add to the days "trunk yield"
            trunk_tvl += stake.debt_burden
        elif rand == 2 or rand == 3:
            trunk_deposited += 200
            stake.deposit(200)
            trunk_tvl += stake.debt_burden
        else:
            trunk_available += stake.available  # let rewards accrue, track total available
            trunk_tvl += stake.debt_burden

    # Handle Yield and Sales/Redemptions (all in Trunk) ----------------------------------------------------------------
    # ------ Calculate Remainder Daily Trunk Yield ------ #
    trunk_yield += em_data['farm_info']['tvl'] * em_data['farms_max_apr'] * em_data['trunk_busd_lp'].price
    presale_daily_yield = trunk_yield
    # Process Trunk Deposits into Stampede (first take from yield, then purchase if necessary)
    if trunk_yield >= trunk_deposited:
        trunk_yield -= trunk_deposited  # Assume yield was used to make stampede deposits
    else:
        trunk_deposited -= trunk_yield
        trunk_yield = 0
        busd_needed = (trunk_deposited + 400) * em_data['trunk_busd_lp'].price  # The 400 is for the raffle winners
        em_income += busd_needed
        em_data['trunk_busd_lp'].update_lp('busd', busd_needed)  # trunk is purchased off the market
    if em_data['trunk_treasury'] >= trunk_yield:  # Yield will be paid from Trunk treasury, or else minted
        em_data['trunk_treasury'] -= trunk_yield
    else:  # trunk must be minted and remaining treasury is bled dry
        em_data['trunk_supply'] += trunk_yield - em_data['trunk_treasury']
        em_data['trunk_treasury'] = 0

    # ------ Determine community Peg support and sales amount ------
    if model_setup['peg_trunk'] and em_data['trunk_busd_lp'].price < 1:
        trunk_sales = daily_bertha_support_usd  # By looking at only USD, will keep selling low while $trunk is low
    elif model_setup['peg_trunk']:  # Allow up to 10% drop in Trunk Price
        trunk_sales = (1 - 0.9 ** 0.5) * em_data['trunk_busd_lp'].token_bal['TRUNK']
    else:
        trunk_sales = trunk_yield * model_setup['yield_sales'] * em_data['trunk_busd_lp'].price * 2
    if trunk_sales > trunk_yield:
        trunk_sales = trunk_yield  # Never try to sell more than the actual yield

    # ------ Yield Redemption/Sales ------
    if redeem_wait_days <= 30 and em_data['trunk_busd_lp'].price < 0.90:  # This can be adjusted, just guessing
        em_data['redemption_queue'] += trunk_sales
    else:
        em_data['trunk_busd_lp'].update_lp('TRUNK', trunk_sales)
    trunk_yield -= trunk_sales  # depending on whether this is positive or negative will determine sales vs hold

    # ------ Update balances based on unsold yield ------
    # --- Buys off PCS - included here so that it can use the same deposit ratios defined
    # Once Peg is hit, this is the same as minting
    trunk_yield += em_data['trunk_busd_lp'].update_lp('BUSD', model_setup['buy_trunk_pcs'][
        model_setup['day']])  # purchase trunk
    # --- Update Balances ---
    if trunk_yield > 0:
        # Mint Trumpet
        em_data['trumpet'].mint_trumpet(trunk_yield * model_setup['yield_to_trumpet'])
        em_data['trunk_held_wallets'] += trunk_yield * model_setup['yield_to_hold']
        # Farm TVL still goes up by total amount, assume bringing pair token
        em_data['farm_info']['tvl'] += trunk_yield * model_setup['yield_to_farm']
        em_data['trunk_liquid_debt'] = em_data['trumpet'].backing + em_data['farm_info']['balance'] + \
                                       em_data['trunk_held_wallets']  # Update liquid debt

    # ------ Arbitrage Trunk LP with Redemption Pool or Minting ------
    # SQRT(CP) will give perfect split.
    delta = (em_data['trunk_busd_lp'].const_prod ** 0.5 - em_data['trunk_busd_lp'].token_bal['BUSD'])
    if em_data['trunk_busd_lp'].price <= 1.00 and redeem_wait_days < 30:  # No arbitrage until queue is reasonable.
        em_data['trunk_busd_lp'].update_lp('BUSD', delta * 0.1)  # Don't arbitrage more than 10% of the delta in a day
        em_data['redemption_queue'] += delta * 0.1
        em_income = delta * 0.1
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
        trunk_to_sell = em_data['trunk_liquid_debt'] * model_setup['daily_liquid_trunk_sales'] * \
                        em_data['trunk_busd_lp'].price
    else:
        trunk_to_sell = 0
    # Split between Redeem and Sell
    # Need to ensure there is actually trunk left to sell
    if em_data['trunk_held_wallets'] > trunk_to_sell / 2 and \
            em_data['trumpet'].backing > trunk_to_sell / 2 and \
            em_data['farm_info']['balance'] > trunk_to_sell:
        if redeem_wait_days <= 30:  # Redemption Queue at one week time to payout
            em_data['redemption_queue'] += trunk_to_sell  # Redeem Trunk
        else:
            em_data['trunk_busd_lp'].update_lp('TRUNK', trunk_to_sell)  # Sell Trunk
        # Decide where sold trunk should come from.  Use a weighted % of holdings
        em_data['trunk_held_wallets'] -= max(0, em_data['trunk_held_wallets'] /
                                             em_data['trunk_liquid_debt'] * trunk_to_sell)
        em_data['trumpet'].backing -= max(0, em_data['trumpet'].backing / em_data['trunk_liquid_debt'] * trunk_to_sell)
        em_data['farm_info']['tvl'] -= max(0, em_data['farm_info']['tvl'] /
                                           em_data['trunk_liquid_debt'] * trunk_to_sell)
    else:
        trunk_to_sell = 0

    # ------ Handle Daily Raffle ------
    # 10% of the trunk treasury is paid out to raffle winners
    if em_data['trunk_treasury'] > 0:
        winner_one = random.randint(1, len(stampede))
        stampede[winner_one].deposit(em_data['trunk_treasury'] * 0.05)
        # could figure out to make this max deposit, but I think it's fine on average with just this
        winner_two = random.randint(1, len(stampede))
        stampede[winner_two].deposit(em_data['trunk_treasury'] * 0.05)
        em_data['trunk_treasury'] *= 0.9  # remove trunk from treasury paid to raffle winners

    # ------- Update assets and debts ----------
    average_ele_price = bsc.get_ave_ele(em_data['ele_busd_lp'], em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
    em_assets = em_data['bertha'] * average_ele_price + em_data['trunk_busd_lp'].token_bal['BUSD'] \
                + em_data['ele_busd_lp'].token_bal['BUSD'] + em_data['ele_bnb_lp'].token_bal['WBNB'] * em_data[
                    'bnb'].usd_value \
                + em_data['busd_treasury'] + em_data['trunk_treasury'] * em_data['trunk_busd_lp'].price
    em_growth = em_assets - em_assets_day_start  # How much did the asset sheet grow
    daily_yield_usd = presale_daily_yield * em_data['trunk_busd_lp'].price + futures_available
    em_cashflow = em_income - em_outflows
    em_data['trunk_liquid_debt'] = em_data['trunk_held_wallets'] + em_data['farm_info']['balance'] + \
                                   em_data['trumpet'].backing + trunk_available
    trunk_total_debt = em_data['trunk_liquid_debt'] + trunk_tvl
    usd_liquid_debt = em_data['trunk_liquid_debt'] * em_data['trunk_busd_lp'].price + futures_available
    usd_total_debt = trunk_total_debt * em_data['trunk_busd_lp'].price + futures_tvl
    running_inflows += em_income
    running_outflows += em_outflows

    # Output Results
    daily_snapshot = {
        "$em_assets/m": em_assets / 1E6,
        "$em_asset_growth/m": em_growth / 1E6,
        "%em_asset_growth": em_growth / em_assets * 100,
        "$em_income": em_income,
        "$em_cashflow": em_cashflow,
        "$funds_in/m": running_inflows / 1E6,
        "$funds_out/m": running_outflows / 1E6,
        "bertha/T": em_data['bertha'] / 1E12,
        "$bertha/m": em_data['bertha'] * average_ele_price / 1E6,
        "$elephant/m": average_ele_price * 1E6,
        "$trunk": em_data['trunk_busd_lp'].price,
        "trumpet": em_data['trumpet'].price,
        "$BNB": em_data['bnb'].usd_value,
        "$bertha_payouts/m": (daily_bertha_support_usd + futures_claimed) / 1E6,
        "daily_trunk_yield": presale_daily_yield,
        "futures_liquid_debt/m": futures_available / 1E6,
        "trunk_liquid_debt/m": em_data['trunk_liquid_debt'] / 1E6,
        "$daily_yield/m": daily_yield_usd / 1E6,
        "$liquid_debt/m": usd_liquid_debt / 1E6,
        "$total_debt/m": usd_total_debt / 1E6,
        "%total_debt_ratio": em_data['bertha'] * average_ele_price / usd_total_debt * 100,
        "%liquid_debt_ratio": em_data['bertha'] * average_ele_price / usd_liquid_debt * 100,
        "redemption_queue": em_data['redemption_queue'],
        "busd_treasury": em_data['busd_treasury'],
        "trunk_treasury": em_data['trunk_treasury'],
        "trunk_support_pool": em_data['trunk_support_pool'],
        "redemption_pool": em_data['redemption_pool'],
        "$redemptions_paid/m": redemptions_paid / 1E6,
        "trunk_wallets/m": em_data['trunk_held_wallets'] / 1E6,
        'farm_tvl/m': em_data['farm_info']['tvl'] / 1E6,
        "queue_wait": redeem_wait_days,
        "futures_busd_pool": em_data['futures_busd_pool'],
        "stampede_owed/m": trunk_tvl / 1E6,
        "$stampede_owed/m": trunk_tvl / 1E6 * em_data['trunk_busd_lp'].price,
        "futures_owed/m": futures_tvl / 1E6,
    }
    if yesterday in model_output:
        daily_snapshot['%em_income_growth'] = \
            (daily_snapshot['$em_income'] / model_output[yesterday]['$em_income'] - 1) * 100
        daily_snapshot['%em_cashflow_growth'] = \
            (daily_snapshot['$em_cashflow'] / model_output[yesterday]['$em_cashflow'] - 1) * 100

    # Make daily updates and model increases in interest as protocol grows
    em_data['bnb'].usd_value = model_setup['bnb_price_s'][tomorrow]  # Update BNB value
    model_output[model_setup['day']] = daily_snapshot
    model_setup['day'] += pd.Timedelta("1 day")

# for debug, setting break point
# if run >= 800:
#    print(day)
# TODO: Elephant bag tracking

df_model_output = pd.DataFrame(model_output).T
df_model_output.to_csv('outputs/output_time.csv')
em_plot_time(df_model_output)
print("Done")
