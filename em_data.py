"""
em_data.py
Use this file to initialize and track all starting or historical data on the EM Platform
"""

import addr_contracts
import bsc_classes as bsc
import addr_tokens
import datetime as dt
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
        # get Trumpet info
        em_data['trumpet_info'] = bsc.read_trumpet_info(addr_contracts.trumpet_contract)
        # get EM Farms info
        farms = bsc.read_em_farms_info(addr_contracts.elephant_farms)
        em_data['farm_tvl'] = farms['tvl']  # Yield is paid out on TVL
        em_data['farm_balance'] = farms['balance']  # This is the total trunk balance in the farms
        em_data['farms_max_apr'] = 1.25 / 365
        # get Futures and Stampede Info
        em_data['futures_info'] = bsc.read_yield_contract_info(addr_contracts.futures_contract)
        em_data['stampede_info'] = bsc.read_yield_contract_info(addr_contracts.stampede_contract)

        # get EM info (this has to be done manually - Updated Jan 06, 2023)
        em_data['trunk_support_pool'] = 0
        em_data['futures_busd_pool'] = 0  # Used to buffer Elephant sells
        em_data['redemption_queue'] = 2.61E6
        em_data['trunk_supply'] = 34.207E6
        em_data['trunk_held_wallets'] = em_data['trunk_supply'] * 0.09  # Estimate based off bscscan token holders:
        # https://bscscan.com/token/tokenholderchart/0xdd325C38b12903B727D16961e61333f4871A70E0
        em_data['trunk_liquid_debt'] = em_data['trumpet_info']['trunk'] + em_data['trunk_held_wallets'] + \
                                       em_data['farm_balance']

        # Calc total debt
        em_data['trunk_total_debt'] = em_data['trunk_liquid_debt'] + em_data['stampede_info']['balance']

        to_pickle = em_data
        f = open('chain_data/emData_{0}.pkl'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M')), 'wb')
        pickle.dump(to_pickle, f)
        f.close()
    else:
        f_o = open('chain_data/emData_2023-09-09 22:05.pkl', 'rb')  # TODO: figure out how to update this automatically
        em_data = pickle.load(f_o)
        f_o.close()

    return em_data


data = get_em_data(read_blockchain=True)
