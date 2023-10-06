# Elephant Money Modeler
import numpy as np
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
model_setup = setup_run('2026-10-01', em_data['bnb'].usd_value)
# --- initialize variables
futures = em_data['futures']
stampede = em_data['stampede']
redemptions_paid = 0
cum_futures_payouts = 0
running_inflows = 0
running_outflows = 0
model_output = {}
em_cashflow = bsc.EMCashflow()
futures_done = False
sunset_futures = False
new_buffer_pool_apr = 0.05 / 365

# Create and Run Model
for run in range(int(model_setup['run_days'])):
    # Initialize Variables
    del em_cashflow  # probably not necessary
    em_cashflow = bsc.EMCashflow()
    trunk_yield = 0
    stp_rate = min(0.005, 0.005 * em_data['trunk_busd_lp'].price)
    today = model_setup['day']
    tomorrow = model_setup['day'] + pd.Timedelta(1, "d")
    yesterday = model_setup['day'] - pd.Timedelta("1d")
    # Daily Bertha Support ---------------------------------------------------------------------
    average_ele_price = bsc.get_ave_ele(em_data['ele_busd_lp'], em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
    daily_bertha_support_usd = em_data['bertha'] * average_ele_price * (model_setup['bertha_outflows'] +
                                                                        new_buffer_pool_apr)
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
    depot_buy_usd = model_setup['buy_depot'][today]  # Don't want to directly modify the starting value
    if em_data['trunk_busd_lp'].price < 0.98:  # 10% of funds auto purchase market Trunk if below $0.98
        em_data['trunk_treasury'] += em_data['trunk_busd_lp'].update_lp('BUSD', depot_buy_usd * 0.1)
        depot_buy_usd *= 0.9
    depot_buy = depot_buy_usd / max(em_data['trunk_busd_lp'].price, 0.25)  # Convert to Trunk
    em_data['farmers_depot'].deposit(depot_buy)
    em_data['busd_treasury'] += depot_buy_usd  # funds go to busd treasury
    '''
    # --- new Futures stakes ---
    wallets = int(model_setup['f_new_wallets'][today])
    deposit = model_setup['f_new_deposit'][today]
    for _ in range(wallets):
        if sunset_futures is True and begin_trunk_price >= 0.98 or futures_done is True:
            futures_done = True
            trunk = em_data['trunk_busd_lp'].update_lp("BUSD", deposit)  # Fresh deposits need to buy trunk
            stampede.append(bsc.YieldEngineV6(trunk, 0.005 * begin_trunk_price))
            em_cashflow.in_trunk += deposit
        else:
            em_data['futures_busd_pool'] += deposit * 0.1
            em_data['busd_treasury'] += deposit * 0.9
            futures.append(bsc.YieldEngineV6(deposit, 0.005))  # create new stake
            em_cashflow.in_futures += deposit
    # --- NFT Mints ---
    mint_funds = model_setup['nft_mint_volume'][today]
    mint_price = em_data['nft'].price
    em_data['nft'].mint(int(mint_funds / (mint_price * begin_bnb_price)))
    em_cashflow.in_nft += mint_funds
    ele_bought = bsc.elephant_buy(mint_funds, em_data['ele_busd_lp'], em_data['ele_bnb_lp'], begin_bnb_price)
    em_data['bertha'] += ele_bought  # bertha gets full amount of mint volume
    # --- NFT Marketplace Sales ---
    # Market sells are 90% of the current mint price and Bertha gets a 30% cut of that
    sell_funds = model_setup['nft_sales_revenue'][today]
    em_cashflow.in_nft += sell_funds
    ele_bought = bsc.elephant_buy(sell_funds, em_data['ele_busd_lp'], em_data['ele_bnb_lp'], begin_bnb_price)
    em_data['bertha'] += ele_bought  # bertha gets full amount of mint volume

    # Handle Elephant Buy/Sell ---------------------------------------------------------------------
    # ------ BwB ------
    ele_bought = bsc.elephant_buy(model_setup['bwb_volume'][today], em_data['ele_busd_lp'],
                                  em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
    em_cashflow.in_buy_volume += model_setup['bwb_volume'][today]
    em_cashflow.in_taxes += model_setup['bwb_volume'][today] * 0.08
    em_data['bertha'] += ele_bought * 0.08  # 8% tax to Bertha
    # ------ SwB ------
    ele_sold = model_setup['swb_volume'][today] / average_ele_price
    em_data['elephant_wallets'] += ele_bought - ele_sold
    # 92% of Elephant sold goes to LP, 8% to Bertha
    bsc.elephant_sell(ele_sold * 0.92, em_data['ele_busd_lp'], em_data['ele_bnb_lp'],
                      em_data['bnb'].usd_value)
    em_data['bertha'] += ele_sold * 0.08
    em_cashflow.in_taxes += model_setup['swb_volume'][today] * 0.08
    em_cashflow.out_sell_volume = model_setup['swb_volume'][today]
    average_ele_price = bsc.get_ave_ele(em_data['ele_busd_lp'], em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
    # TODO: Create class for Elephant containing LPs and automatically keeping the price up to date

    # ------ Market Buys / Sells ------
    tax_ele = 0
    buys_usd = model_setup['market_buy_volume'][today]
    em_cashflow.in_buy_volume += buys_usd
    sells_ele = model_setup['market_sell_volume'][today] / average_ele_price
    tax_ele += sells_ele * 0.1
    buys_ele = bsc.elephant_buy(buys_usd, em_data['ele_busd_lp'], em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
    tax_ele += buys_ele * 0.1
    sells_usd = bsc.elephant_sell(sells_ele, em_data['ele_busd_lp'], em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
    em_cashflow.out_sell_volume += sells_usd
    em_data['elephant_wallets'] += buys_ele - sells_ele
    tax_usd = tax_ele * em_data['ele_busd_lp'].price  # Use just BUSD price to get best pairing for liquidity
    average_ele_price = bsc.get_ave_ele(em_data['ele_busd_lp'], em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
    # Add liquidity to BUSD pool TODO: Confirm whether BUSD or BNB pool
    em_data['ele_busd_lp'].add_liquidity('ELEPHANT', tax_ele / 2, 'BUSD', tax_usd / 2)
    # Handle major reflections
    em_data['graveyard'] += tax_ele / 2 * (em_data['graveyard'] / 1E15)
    reflect_to_bertha = tax_ele / 2 * (em_data['bertha'] / 1E15)
    em_data['bertha'] += reflect_to_bertha
    em_cashflow.in_taxes += reflect_to_bertha * average_ele_price
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
    em_cashflow.out_trunk += busd_received
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
    em_cashflow.out_trunk += busd_received
    trunk_purchased = em_data['trunk_busd_lp'].update_lp('BUSD', busd_received)  # Buy Trunk off PCS
    minted = em_data['trumpet'].mint_trumpet(trunk_purchased)  # Mint trumpet and burn it
    em_data['trumpet'].burn_trumpet(minted)

    # ------ NFT Royalties ------
    # tokens are distributed directly to stakers
    daily_royalty = em_data['bertha'] * model_setup['nft_royalty_apr']
    em_data['bertha'] -= daily_royalty
    em_cashflow.out_nft += daily_royalty * average_ele_price

    # ------ Performance Fund ------
    # Fund outflows go to Deployer wallet, just assume they are spent
    perf_payout_ele = em_data['bertha'] * model_setup['performance_support_apr']
    em_data['bertha'] -= perf_payout_ele
    em_cashflow.out_perf += perf_payout_ele * average_ele_price

    # ------ New Buffer Pool ------
    # Goal of this is to increase the BUSD buffer pool with a slow payout of Elephant APR governance
    # This should smooth out the growth and avoid significant sell-offs to pay futures debt later on
    # This is not treated as cashflow because it's still part of the treasury value
    new_buffer_payout_ele = em_data['bertha'] * new_buffer_pool_apr
    em_data['futures_busd_pool'] += bsc.elephant_sell(new_buffer_payout_ele, em_data['ele_busd_lp'],
                                                      em_data['ele_bnb_lp'],
                                                      em_data['bnb'].usd_value)

    # Handle Yield Engines -------------------------------------------------------------------------------------------
    # ------ Process Futures Stakes ------
    # Set up a randomized claim / deposit process based on a 2:1 ratio and 21 day cycle
    futures_claimed = 0
    futures_available = 0
    futures_tvl = 0
    futures_debt = 0
    limiter = 0
    cnt = 0
    # progress current stakes
    for stake in futures:  # Need to process each separate futures stake
        stake.pass_days(1)
        if stake.available < 0:
            raise Exception('Futures available is negative!')
        rand = random.randint(1, 21)
        deposit = model_setup['f_compound_usd']
        if rand == 1 or stake.balance >= 0.9 * stake.max_balance:  # Claim unless stake is too new, then deposit
            if stake.total_days > model_setup['f_claim_wait']:
                futures_claimed += stake.claim()
            else:
                stake.deposit(deposit)
                em_data['futures_busd_pool'] += deposit * 0.1
                em_data['busd_treasury'] += deposit * 0.9
                em_cashflow.in_futures += deposit
        elif rand == 2 or rand == 3:
            stake.deposit(deposit)
            em_data['futures_busd_pool'] += deposit * 0.1
            em_data['busd_treasury'] += deposit * 0.9
            em_cashflow.in_futures += deposit
        else:
            futures_available += stake.available
        futures_tvl += stake.balance
        futures_debt += stake.debt_burden
        limiter += stake.rate_limiter
        cnt += 1
    avg_futures_yield = limiter / cnt * 0.005 * 100  # Find the average daily yield rate (Based on limiters)
    # Payout futures and replenish buffer pool if needed
    em_cashflow.out_futures += futures_claimed
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
        if stake.available < 0:
            raise Exception('Stampede available is negative!')
        if em_data['trunk_busd_lp'].price >= 0.9:
            wait_days = 18
        else:
            wait_days = 18 / min(1, (1 - em_data['trunk_busd_lp'].price) / 2)
        rand = random.randint(1, wait_days + 3)
        stake.pass_days(1, stp_rate)
        if rand == 1 or stake.balance >= 0.9 * stake.max_balance:
            claimed = stake.claim()
            trunk_yield += claimed  # All claims will add to the day's "trunk yield"
            trunk_tvl += stake.debt_burden
        elif rand == 2 or rand == 3:
            trunk_deposited += 200
            stake.deposit(200)
            trunk_tvl += stake.debt_burden
        else:
            trunk_available += stake.available  # let rewards accrue, track total available
            trunk_tvl += stake.debt_burden

    # ------ Calculate Remainder Daily Trunk Yield ------
    trunk_yield += max(0, em_data['farm_info']['tvl'] * em_data['farms_max_apr'] * em_data['trunk_busd_lp'].price)
    presale_daily_yield = trunk_yield

    # ------ Process Trunk Deposits into Stampede (first take from yield, then purchase if necessary) ------
    if trunk_yield >= trunk_deposited:
        trunk_yield -= trunk_deposited  # Assume yield was used to make stampede deposits
    else:
        trunk_deposited -= trunk_yield
        trunk_yield = 0
        busd_needed = (trunk_deposited + 400) * em_data['trunk_busd_lp'].price  # The 400 is for the raffle winners
        em_cashflow.in_trunk += busd_needed
        em_data['trunk_busd_lp'].update_lp('busd', busd_needed)  # trunk is purchased off the market
    if em_data['trunk_treasury'] >= trunk_yield:  # Yield will be paid from Trunk treasury, or else minted
        em_data['trunk_treasury'] -= trunk_yield
    else:  # trunk must be minted and remaining treasury is bled dry
        em_data['trunk_supply'] += trunk_yield - em_data['trunk_treasury']
        em_data['trunk_treasury'] = 0

    # Handle Sales/Redemptions (all in Trunk) ----------------------------------------------------------------
    # ------ Determine community Peg support and sales amount ------
    if model_setup['peg_trunk'] and em_data['trunk_busd_lp'].price < 1:
        trunk_sales = daily_bertha_support_usd  # By looking at only USD, will keep selling low while $trunk is low
    elif model_setup['peg_trunk']:  # Allow up to 10% drop in Trunk Price
        trunk_sales = (1 - 0.9 ** 0.5) * em_data['trunk_busd_lp'].token_bal['TRUNK']
    else:
        trunk_sales = trunk_yield * model_setup['yield_sales'] * em_data['trunk_busd_lp'].price ** 2
    if trunk_sales > trunk_yield:
        trunk_sales = trunk_yield  # Never try to sell more than the actual yield

    # ------ Yield Redemption/Sales ------
    if redeem_wait_days <= 30 and em_data['trunk_busd_lp'].price < 0.95:  # This can be adjusted, just guessing
        em_data['redemption_queue'] += trunk_sales
        em_data['trunk_supply'] -= trunk_sales
    else:
        em_data['trunk_busd_lp'].update_lp('TRUNK', trunk_sales)
    trunk_yield -= trunk_sales  # depending on whether this is positive or negative will determine sales vs hold

    # ------ Update balances based on unsold yield ------
    # --- Buys off PCS - included here so that it can use the same deposit ratios defined
    # Once Peg is hit, this is the same as minting
    trunk_yield += em_data['trunk_busd_lp'].update_lp('BUSD', model_setup['buy_trunk_pcs'][today])
    em_cashflow.in_trunk += model_setup['buy_trunk_pcs'][today]
    # --- Update Balances ---
    if trunk_yield > 0:
        # Mint Trumpet
        em_data['trumpet'].mint_trumpet(trunk_yield * model_setup['yield_to_trumpet'])
        em_data['trunk_held_wallets'] += trunk_yield * model_setup['yield_to_hold']
        # Farm TVL still goes up by total amount, assume bringing pair token
        em_data['farm_info']['tvl'] += trunk_yield * model_setup['yield_to_farm'] * 2
        em_data['trunk_liquid_debt'] = em_data['trumpet'].backing + em_data['farm_info']['tvl'] / 2 + \
                                       em_data['trunk_held_wallets']  # Update liquid debt

    # ------ Arbitrage Trunk LP with Redemption Pool or Minting ------
    # SQRT(CP) will give perfect split.
    delta = (em_data['trunk_busd_lp'].const_prod ** 0.5 - em_data['trunk_busd_lp'].token_bal['BUSD'])
    in_funds = em_data['bertha'] * model_setup['redemption_support_apr'] * average_ele_price
    # Keep redemptions lower when price is down and never to exceed 2x the amount of support
    to_redeem = min(delta * em_data['trunk_busd_lp'].price ** 4, in_funds * 2)
    if em_data['trunk_busd_lp'].price <= 1.00 and redeem_wait_days <= 45:  # No arbitrage until queue is reasonable.
        em_data['trunk_busd_lp'].update_lp('BUSD', to_redeem)
        em_data['redemption_queue'] += to_redeem
        em_cashflow.in_trunk = to_redeem
        em_data['trunk_supply'] -= to_redeem  # Redeemed Trunk is taken out of circulation
    elif em_data['trunk_busd_lp'].price > 1.00:  # Trunk is over $1.  "Delta" will be negative
        em_data['trunk_busd_lp'].update_lp('TRUNK', abs(delta))  # Sell trunk on PCS
        em_data['busd_treasury'] += abs(delta)  # Arber would need to mint trunk from the protocol
        if em_data['trunk_treasury'] > abs(delta):
            em_data['trunk_treasury'] -= abs(delta)  # Comes from Trunk Treasury if there are funds
        else:
            em_data['trunk_supply'] += abs(delta)  # Trunk Minted
    else:
        pass

    # ------ Handle Liquid Trunk Selling/Redeeming ------
    # Allow Trunk to drop by X% when at Peg.  Adjust downwards when below Peg
    # Sell up to 75% of redemption pool funds
    max_pct_drop = 0.1 * min(1, em_data['trunk_busd_lp'].price)
    trunk_to_sell = ((1 + max_pct_drop) ** 0.5 - 1) * em_data['trunk_busd_lp'].token_bal['TRUNK'] + \
                    0.75 * em_data['redemption_pool']
    sold = 0
    # Where do sales come from.  Don't sell more than 10% of any holding in a day
    # Loose trunk in wallets first
    if em_data['trunk_held_wallets'] * 0.1 <= trunk_to_sell:
        em_data['trunk_held_wallets'] *= 0.9
        trunk_to_sell -= em_data['trunk_held_wallets'] * 0.1
        sold += em_data['trunk_held_wallets'] * 0.1
    # Then Trumpet (only 5%)
    if em_data['trumpet'].backing * 0.05 <= trunk_to_sell:
        redeem = em_data['trumpet'].backing / em_data['trumpet'].price * 0.05
        trunk_to_sell -= em_data['trumpet'].backing * 0.05
        em_data['trumpet'].redeem_trumpet(redeem)
        sold += em_data['trumpet'].backing * 0.05
    # Then Farms
    if em_data['farm_info']['tvl'] / 2 * 0.05 <= trunk_to_sell:
        em_data['farm_info']['tvl'] *= 0.95
        trunk_to_sell -= em_data['farm_info']['tvl'] / 2 * 0.05
        sold += em_data['farm_info']['tvl'] / 2 * 0.05
    # Split between Redeem and Sell
    if redeem_wait_days <= 30:  # Redemption Queue at one week time to payout
        em_data['redemption_queue'] += sold  # Redeem Trunk
    else:
        em_data['trunk_busd_lp'].update_lp('TRUNK', sold)  # Sell Trunk

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
    em_market_cap = 1E15 * average_ele_price
    em_growth = em_assets - em_assets_day_start  # How much did the asset sheet grow
    daily_yield_usd = presale_daily_yield * em_data['trunk_busd_lp'].price + futures_available
    em_data['trunk_liquid_debt'] = em_data['trunk_held_wallets'] + em_data['farm_info']['balance'] + \
                                   em_data['trumpet'].backing + trunk_available
    trunk_total_debt = em_data['trunk_liquid_debt'] + trunk_tvl
    usd_liquid_debt = em_data['trunk_liquid_debt'] * em_data['trunk_busd_lp'].price + futures_available
    usd_total_debt = trunk_total_debt * em_data['trunk_busd_lp'].price + futures_debt
    running_inflows += em_cashflow.in_total
    running_outflows += em_cashflow.out_total

    # Output Results
    daily_snapshot = {
        "$em_market_cap/m": em_market_cap / 1E6,
        "$em_assets/m": em_assets / 1E6,
        "$em_asset_growth/m": em_growth / 1E6,
        "%em_asset_growth": em_growth / em_assets * 100,
        "$em_cashflow": em_cashflow.cashflow,
        "$em_income": em_cashflow.in_total,
        "$em_outflow": em_cashflow.out_total,
        "$funds_in/m": running_inflows / 1E6,
        "$funds_out/m": running_outflows / 1E6,
        "bertha/T": em_data['bertha'] / 1E12,
        "$bertha/m": em_data['bertha'] * average_ele_price / 1E6,
        "$elephant/m": average_ele_price * 1E6,
        "$trunk": em_data['trunk_busd_lp'].price,
        "trumpet": em_data['trumpet'].price,
        "trumpet_backing": em_data['trumpet'].backing,
        "trumpet_supply": em_data['trumpet'].supply,
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
        "futures_owed/m": futures_debt / 1E6,
        "avg_futures_yield": avg_futures_yield
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

    # Make daily updates and model increases in interest as protocol grows
    em_data['bnb'].usd_value = model_setup['bnb_price_s'][tomorrow]  # Update BNB value
    model_output[today] = daily_snapshot
    model_setup['day'] += pd.Timedelta("1 day")

# for debug, setting break point
# if run >= 800:
#    print(day)
# TODO: Elephant bag tracking

df_model_output = pd.DataFrame(model_output).T
df_model_output.to_csv('outputs/output_time.csv')
em_plot_time(df_model_output)
print("Done")
