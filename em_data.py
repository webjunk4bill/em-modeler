"""
em_data.py
Use this file to initialize and track all starting or historical data on the EM Platform
"""
import addr_contracts
import bsc_classes as bsc
import addr_tokens
from datetime import date
import pickle


def get_em_data(*, read_blockchain: bool = False):
    """
    This function initializes all the EM Platform data
    It will return a dictionary with all the parameter values
    """
    em_data = {}
    if read_blockchain:  # Will use the moralis APIs to query the blockchian.  Takes 10 sec or so.
        # get EM info (this can be done automatically)
        # get LPs
        em_data['ele_bnb_lp'] = bsc.CakeLP(addr_tokens.Elephant, addr_tokens.BNB)
        em_data['ele_busd_lp'] = bsc.CakeLP(addr_tokens.Elephant, addr_tokens.BUSD)
        em_data['trunk_busd_lp'] = bsc.CakeLP(addr_tokens.Trunk, addr_tokens.BUSD)
        # get Tokens used
        em_data['bnb'] = bsc.Token('BNB', addr_tokens.BNB)
        # get Treasury balances
        em_data['bertha'] = bsc.GetWalletBalance(addr_contracts.ele_bertha, addr_tokens.Elephant).balance
        em_data['busd_treasury'] = bsc.GetWalletBalance(addr_contracts.ele_busd_treasury, addr_tokens.BUSD).balance
        em_data['trunk_treasury'] = bsc.GetWalletBalance(addr_contracts.trunk_treasury, addr_tokens.Trunk).balance
        em_data['redemption_pool'] = bsc.GetWalletBalance(addr_contracts.redemption_pool, addr_tokens.BUSD).balance
        em_data['graveyard'] = bsc.GetWalletBalance(addr_contracts.em_graveyard, addr_tokens.Elephant).balance
        # Calculate and set starting values
        ave_ele_price = bsc.get_ave_ele(em_data['ele_busd_lp'], em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
        em_data['start_ele_price'] = ave_ele_price
        em_data['start_trunk_price'] = em_data['trunk_busd_lp'].price
        em_data['start_bnb_price'] = em_data['bnb'].usd_value

        # get EM info (this has to be done manually - Updated Jan 06, 2023)
        em_data['trunk_support_pool'] = 0
        em_data['futures_busd_pool'] = 0  # Used to buffer Elephant sells
        em_data['staking_apr'] = 0.3 / 365
        em_data['farms_max_apr'] = 1.25 / 365
        em_data['redemption_queue'] = 1.45E6
        em_data['trunk_supply'] = 30.676E6
        em_data['staking_balance'] = 9.105E6
        stampede_bonds = 55.98E6
        stampede_payouts = 59.58E6
        em_data['farm_tvl'] = 7.384E6  # Yield is paid out on TVL
        em_data['farm_balance'] = em_data['farm_tvl'] / 2  # This is the total trunk balance in the farms
        farm_depot_tvl = 262915  # In Trunk, TODO: should be able to read this automatically
        farm_depot_claimed = 782911  # In Trunk
        em_data['trunk_held_wallets'] = em_data['trunk_supply'] * 0.0355  # Estimate based off bscscan token holders:
        # https://bscscan.com/token/tokenholderchart/0xdd325C38b12903B727D16961e61333f4871A70E0
        em_data['trunk_liquid_debt'] = em_data['staking_balance'] + em_data['trunk_held_wallets'] + \
                                       em_data['farm_balance']

        # Set Up Yield Engines
        em_data['farmers_depot'] = bsc.YieldEngine(farm_depot_tvl + farm_depot_claimed, 1 / 30, 1)  # Farmer's Depot
        em_data['farmers_depot'].balance = farm_depot_tvl
        em_data['farmers_depot'].claimed = farm_depot_claimed  # need to do a manual update of what has happened to date
        em_data['em_futures'] = bsc.BUSDFuturesEngine(0)  # Create futures engine
        em_data['stampede'] = bsc.StampedeEngine(stampede_bonds)  # Create stampede engine
        em_data['stampede'].total_claims = stampede_payouts  # Update initial values

        # Calc total debt
        em_data['trunk_total_debt'] = em_data['trunk_liquid_debt'] + em_data['stampede'].owed

        to_pickle = em_data
        f = open('chain_data/emData_{0}.pkl'.format(date.today()), 'wb')
        pickle.dump(to_pickle, f)
        f.close()
    else:
        f_o = open('chain_data/emData_2023-01-11.pkl', 'rb')  # TODO: figure out how to update this automatically
        em_data = pickle.load(f_o)
        f_o.close()

    return em_data


# data = get_em_data(read_blockchain=True)
