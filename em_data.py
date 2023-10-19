"""
em_data.py
Use this file to initialize and track all starting or historical data on the EM Platform
"""

import addr_contracts
import api
import bsc_classes as bsc
import addr_tokens
import datetime as dt
import pickle
import pandas as pd
import math as m


def get_em_data(*, read_blockchain: bool = False):
    """
    This function initializes all the EM Platform data
    It will return a dictionary with all the parameter values
    """
    # initialize main dict
    em_data = {}

    if read_blockchain:  # Will use the moralis APIs to query the blockchian.  Takes 10 sec or so.
        # Get Dune Data
        f_o = open('chain_data/DuneData_2023-10-19 09:12.pkl', 'rb')
        dune = pickle.load(f_o)
        f_o.close()

        # Check to ensure Futures starting wallets are in line with current contract balance
        c_futures = bsc.ContractReader('chain_data/stampede_abi.json', addr_contracts.futures_contract)
        em_data['futures_info'] = c_futures.get_futures_info()
        if dune['futures_tvl'] < 0.975 * em_data['futures_info']['balance']:
            raise Exception('Dune futures info is stale.  TVL on Dune is more than 2.5% below contract read.')
        em_data['futures'] = dune['futures']

        # get EM info (this can be done automatically)
        # TODO: Convert Moralis calls to web3 module.  Seems a lot faster.
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
        em_data['futures_busd_pool'] = bsc.GetWalletBalance(addr_contracts.busd_buffer_pool, addr_tokens.BUSD).balance
        # em_data['deployer'] = bsc.GetWalletBalance(addr_contracts.deployer_contract, addr_tokens.Elephant).balance
        # Calculate and set starting values
        ave_ele_price = bsc.get_ave_ele(em_data['ele_busd_lp'], em_data['ele_bnb_lp'], em_data['bnb'].usd_value)
        em_data['start_ele_price'] = ave_ele_price
        em_data['start_trunk_price'] = em_data['trunk_busd_lp'].price
        em_data['start_bnb_price'] = em_data['bnb'].usd_value
        # Read Contract Info
        c_stampede = bsc.ContractReader('chain_data/stampede_abi.json', addr_contracts.stampede_contract)
        em_data['stampede_info'] = c_stampede.get_futures_info()
        c_farms = bsc.ContractReader('chain_data/farms_abi.json', addr_contracts.elephant_farms)
        em_data['farm_info'] = c_farms.get_farm_info()
        c_trumpet = bsc.ContractReader('chain_data/trumpet_abi.json', addr_contracts.trumpet_contract)
        temp = c_trumpet.get_trumpet_info()
        em_data['trumpet'] = bsc.Trumpet(temp['users'], temp['trunk'], temp['trumpet'])
        c_unlimited = bsc.ContractReader('chain_data/unlimited_abi.json', addr_contracts.nft_contract)
        em_data['nft'] = bsc.Unlimited(c_unlimited.call_read_single_obj('totalSupply'))
        em_data['elephant_wallets'] = 1E15 - em_data['graveyard'] - em_data['bertha'] - \
                                      em_data['ele_busd_lp'].token_bal['ELEPHANT'] - em_data['ele_bnb_lp'].token_bal['ELEPHANT']

        # Set up Stampede Stakes - Data imported from Dune
        s_data = pd.read_csv('chain_data/stampede_dune.csv')
        if s_data['TVL'].sum() < 0.975 * em_data['stampede_info']['balance']:
            raise Exception('Dune stampede info is stale.  TVL on Dune is more than 2.5% below contract read.')
        stampede = []
        i = 0
        for row in s_data.itertuples():
            if row.TVL <= 0:  # Seeing some negative depsoit data in Dune
                break
            stampede.append(bsc.YieldEngineV6(row.TVL, 0.005 * em_data['start_trunk_price']))
            if not m.isnan(row.compound_value):
                stampede[i].compounds = row.compound_value
            if not m.isnan(row.claim_value):
                stampede[i].claimed = row.claim_value * -1
            if not m.isnan(row.since_first_deposit):
                stampede[i].total_days = row.since_first_deposit
            stampede[i].update_rate_limiter()
            if not m.isnan(row.since_last_withdrawal) and m.isnan(row.since_last_compound):
                stampede[i].pass_days(min(row.since_last_withdrawal, row.since_last_compound))
            if m.isnan(stampede[i].available):
                raise Exception('NaN found!')
            i += 1
        em_data['stampede'] = stampede

        # get EM Manual Info
        em_data['farms_max_apr'] = 1.25 / 365
        em_data['trunk_support_pool'] = 0
        em_data['redemption_queue'] = 2.61E6
        em_data['trunk_supply'] = 34.207E6
        em_data['trunk_held_wallets'] = em_data['trunk_supply'] * 0.09  # Estimate based off bscscan token holders:
        # https://bscscan.com/token/tokenholderchart/0xdd325C38b12903B727D16961e61333f4871A70E0
        em_data['trunk_liquid_debt'] = em_data['trumpet'].backing + em_data['trunk_held_wallets'] + \
                                       em_data['farm_info']['balance']

        # Calc total debt
        em_data['trunk_total_debt'] = em_data['trunk_liquid_debt'] + em_data['stampede_info']['balance']

        to_pickle = em_data
        f = open('chain_data/emData_{0}.pkl'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M')), 'wb')
        pickle.dump(to_pickle, f)
        f.close()
    else:
        f_o = open('chain_data/emData_2023-10-19 09:13.pkl', 'rb')  # TODO: figure out how to update this automatically
        em_data = pickle.load(f_o)
        f_o.close()

    return em_data


# data = get_em_data(read_blockchain=True)
