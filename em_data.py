"""
em_data.py
Use this file to initialize and track all starting or historical data on the EM Platform
"""

import addr_contracts
import bsc_classes as bsc
import addr_tokens
import datetime as dt
import pickle
import pandas as pd


def get_em_data(*, read_blockchain: bool = False):
    """
    This function initializes all the EM Platform data
    It will return a dictionary with all the parameter values
    """
    # initialize main dict
    em_data = {}

    if read_blockchain:  # Will Query the blockchain, takes a few seconds

        # get EM info (this can be done automatically)
        # set up tokens
        em_data['wbnb'] = bsc.Token(addr_tokens.WBNB, addr_tokens.cmc_bnb)
        em_data['trunk'] = bsc.Token(addr_tokens.Trunk, addr_tokens.cmc_trunk)
        em_data['busd'] = bsc.Token(addr_tokens.BUSD, addr_tokens.cmc_busd)
        em_data['elephant'] = bsc.Token(addr_tokens.Elephant, addr_tokens.cmc_elephant)
        em_data['btc'] = bsc.Token(addr_tokens.BTCB, addr_tokens.cmc_btc)
        em_data['usdc'] = bsc.Token(addr_tokens.USDC, addr_tokens.cmc_usdc)
        # get LPs
        em_data['ele_bnb_lp'] = bsc.CakeLP(addr_tokens.lp_ele_bnb, em_data['elephant'], em_data['wbnb'])
        em_data['ele_busd_lp'] = bsc.CakeLP(addr_tokens.lp_ele_busd, em_data['elephant'], em_data['busd'])
        em_data['trunk_busd_lp'] = bsc.CakeLP(addr_tokens.lp_trunk_busd, em_data['trunk'], em_data['busd'])
        em_data['trunk_bnb_lp'] = bsc.CakeLP(addr_tokens.lp_trunk_bnb, em_data['trunk'], em_data['wbnb'])
        em_data['trunk_usdc_lp'] = bsc.SolanaLP(addr_tokens.lp_trunk_usdc)
        # For ease, add Solana USDC-backed Trunk liquidity to the Trunk-BUSD LP
        em_data['trunk_busd_lp'].add_liquidity(em_data['trunk'], em_data['trunk_usdc_lp'].token_bal[em_data['trunk'].symbol],
                                               em_data['busd'], em_data['trunk_usdc_lp'].token_bal[em_data['usdc'].symbol])
        # Calculate and set starting values
        em_data['start_ele_price'] = em_data['elephant'].usd_value
        em_data['start_trunk_price'] = em_data['trunk'].usd_value
        em_data['start_bnb_price'] = em_data['wbnb'].usd_value
        em_data['start_btc_price'] = em_data['btc'].usd_value
        # get Treasury balances
        em_data['bertha'] = bsc.Wallet(addr_contracts.ele_bertha, em_data['elephant']).get_token_balance()
        em_data['graveyard'] = bsc.Wallet(addr_contracts.em_graveyard, em_data['elephant']).get_token_balance()
        em_data['bnb_reserve'] = bsc.Wallet(addr_contracts.bnb_reserve).bnb_balance
        em_data['rdf'] = bsc.Wallet(addr_contracts.futures_rdf_vault).bnb_balance
        em_data['btc_turbine'] = bsc.Turbine(addr_contracts.turbine_btc, em_data['btc'])
        em_data['trunk_turbine'] = bsc.Turbine(addr_contracts.turbine_trunk, em_data['trunk'])
        # Read Contract Info
        c_trumpet = bsc.ContractReader('chain_data/trumpet_abi.json', addr_contracts.trumpet_contract)
        temp = c_trumpet.get_trumpet_info()
        em_data['trumpet'] = bsc.Trumpet(temp['users'], temp['trunk'], temp['trumpet'])
        c_unlimited = bsc.ContractReader('chain_data/unlimited_abi.json', addr_contracts.nft_contract)
        em_data['nft'] = bsc.Unlimited(c_unlimited.call_read_single_obj('totalSupply'))
        em_data['elephant_wallets'] = 1E15 - em_data['graveyard'] - em_data['bertha'] - \
                                      em_data['ele_busd_lp'].token_bal['ELEPHANT'] - \
                                      em_data['ele_bnb_lp'].token_bal['ELEPHANT']
        # Write to csv
        df = pd.Series(em_data)
        df.to_csv('chain_data/emData_{0}.csv'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M')))
        # Write to pickle
        f1 = open('chain_data/emData_{0}.pkl'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M')), 'wb')
        pickle.dump(em_data, f1)
        f2 = open('chain_data/emData.pkl', 'wb')
        pickle.dump(em_data, f2)
        f1.close()
        f2.close()
    else:
        f_o = open('chain_data/emData.pkl', 'rb')
        em_data = pickle.load(f_o)
        f_o.close()

    return em_data


# data = get_em_data(read_blockchain=True)
