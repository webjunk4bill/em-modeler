# Wallet Holdings
import time

from moralis import evm_api
import numpy as np
from api import api_key, bsc_url
from web3 import Web3
import json


class Token:
    def __init__(self, tok_name, tok_addr):
        self.name = tok_name
        self.address = tok_addr
        self.usd_value = self.get_price()

    def get_price(self):
        params1 = {
            "address": self.address,
            "chain": "bsc"
        }

        result = evm_api.token.get_token_price(
            api_key=api_key,
            params=params1,
        )

        # print(self.name + ' Token, Price = ' + str(result["usdPrice"]) + " USD")
        return result["usdPrice"]


class TokenYield:
    def __init__(self, token, amount, apr):
        self.token = token
        self.max_apr = apr
        self.amount = amount

        if self.token.name == 'Trunk':  # Trunk yield is adjusted by open-market price
            self.apr = self.max_apr * self.token.usd_value
        else:
            self.apr = self.max_apr

        self.daily_yield = self.amount * self.apr / 365
        self.weekly_yield = self.daily_yield * 7
        self.monthly_yield = self.daily_yield * 365 / 12
        self.yearly_yield = self.daily_yield * 365


class CakeLP:
    def __init__(self, addr1, addr2):
        self.token_addr = [addr1, addr2]
        self.token_name = []
        self.token_bal = {}
        self.pair_addr = ''
        self.get_pair_info()
        self.const_prod = self.token_bal[self.token_name[0]] * self.token_bal[self.token_name[1]]
        self.price = self.get_price()
        self.tokens_removed = 0

    def get_pair_info(self):
        # Get Pair Metadata
        params1 = {
            "exchange": "pancakeswapv2",
            "token0_address": self.token_addr[0],
            "token1_address": self.token_addr[1],
            "chain": "bsc"
        }
        metadata = evm_api.defi.get_pair_address(
            api_key=api_key,
            params=params1,
        )
        self.token_name = [metadata["token0"]["symbol"], metadata["token1"]["symbol"]]
        self.pair_addr = metadata["pairAddress"]

        # Get Pair Token Balances
        params2 = {
            "pair_address": self.pair_addr,
            "chain": "bsc"
        }
        reserves = evm_api.defi.get_pair_reserves(
            api_key=api_key,
            params=params2
        )

        # Format token balances to floats.  All divide by 1E18 except ELEPHANT
        for i in [0, 1]:
            if self.token_name[i] == "ELEPHANT":
                self.token_bal[self.token_name[i]] = float(reserves["reserve{0}".format(i)]) / 1E9
            else:
                self.token_bal[self.token_name[i]] = float(reserves["reserve{0}".format(i)]) / 1E18
        return self

    def get_price(self):
        # Get Token Price based on LP info
        # Price should be in BUSD unless paired with WBNB, so [BUSD or WBNB] / Token
        [first, second] = self.token_bal.keys()
        if first != 'BUSD' and first != 'WBNB':
            price = self.token_bal[second] / self.token_bal[first]  # first token is desired in USD
        elif first == 'WBNB' and second == 'BUSD':
            price = self.token_bal[second] / self.token_bal[first]  # this is WBNB/BUSD LP
        else:
            price = self.token_bal[first] / self.token_bal[second]  # second token is desired in USD
        return price

    def update_lp(self, t_name, change):
        # Use this to update the token pair and price
        # match token name, update the balances, re-calc the price
        [first, second] = self.token_bal.keys()
        if first == t_name:
            old = self.token_bal[second]  # Get original "buy" token balance
            self.token_bal[first] += change  # Push in "sell" tokens
            self.token_bal[second] = self.const_prod / self.token_bal[first]  # Calc new "buy" token balance
            self.tokens_removed = old - self.token_bal[second]  # Cal number of tokens bought or removed
        else:  # This is just in the opposite order
            old = self.token_bal[first]
            self.token_bal[second] += change
            self.token_bal[first] = self.const_prod / self.token_bal[second]
            self.tokens_removed = old - self.token_bal[first]
        self.price = self.get_price()

        return self.tokens_removed

    def add_liquidity(self, t_name1, amt1, t_name2, amt2):
        self.token_bal[t_name1] += amt1
        self.token_bal[t_name2] += amt2
        self.const_prod = self.token_bal[t_name1] * self.token_bal[t_name2]
        self.price = self.get_price()


class GetWalletBalance:
    def __init__(self, addr, token_addr):
        params = {
            "address": addr,
            "chain": "bsc",
            "token_addresses": [token_addr],
        }

        result = evm_api.token.get_wallet_token_balances(
            api_key=api_key,
            params=params,
        )
        # Format token balance to floats.  All divide by 1E18 except ELEPHANT
        if result[0]["symbol"] == "ELEPHANT":
            self.balance = float(result[0]["balance"]) / 1E9
        else:
            self.balance = float(result[0]["balance"]) / 1E18


class ContractReader:
    def __init__(self, contract_abi, contract_address):
        self.web3 = Web3(Web3.HTTPProvider(bsc_url))
        with open(contract_abi, 'r') as abi_file:
            contract_abi = json.load(abi_file)
        self.contract = self.web3.eth.contract(address=contract_address, abi=contract_abi)
        self.result_obj = self.Info()

    class Info:
        pass

    def get_futures_info(self):
        self.call_read_function_new('getInfo')
        data = {
            'users': self.result_obj.total_users,
            'balance': self.result_obj.current_balance,
            'compounds': self.result_obj.total_compound_deposited,
            'claimed': self.result_obj.total_claimed
        }
        return data

    def get_farm_info(self):
        self.call_read_function_old('getInfo')
        data = {
            'users': self.result_obj.total_users,
            'tvl': self.result_obj.current_balance,
            'balance': self.result_obj.current_balance / 2
        }
        return data

    def get_trumpet_info(self):
        self.call_read_function_old('getInfo')
        data = {
            'users': self.result_obj.users,
            'trunk': self.result_obj.underlyingSupply,
            'price': self.result_obj.price,
            'trumpet': self.result_obj.supply
        }
        return data

    def call_read_function_new(self, function_name):
        """This is for a "newer" style of contract readout (outputs have "components") """
        try:
            # Call the read function (constant function)
            result = self.contract.functions[function_name]().call()

            # Iterate through the ABI to find the function definition
            function_definition = self.contract.get_function_by_name(function_name)
            func_outputs = function_definition.abi['outputs'][0]['components']
            for item, result in zip(func_outputs, result):
                if result > 100000:  # Distinguish between standard number and "solidity float" number
                    setattr(self.result_obj, item['name'], result / 1E18)
                else:
                    setattr(self.result_obj, item['name'], result)
        except Exception as e:
            print(f"Error calling {function_name}: {e}")

    def call_read_function_old(self, function_name):
        try:
            # Call the read function (constant function)
            result = self.contract.functions[function_name]().call()

            if len(result) == 1:
                setattr(self.result_obj, function_name, result)
                return

            # Iterate through the ABI to find the function definition
            function_definition = self.contract.get_function_by_name(function_name)
            func_outputs = function_definition.abi['outputs']
            for item, result in zip(func_outputs, result):
                name = item['name'].lstrip('_')
                if result > 100000:  # Distinguish between standard number and "solidity float" number
                    setattr(self.result_obj, name, result / 1E18)
                else:
                    setattr(self.result_obj, name, result)
        except Exception as e:
            print(f"Error calling {function_name}: {e}")

    def call_read_single_obj(self, function_name):
        result = self.contract.functions[function_name]().call()
        setattr(self.result_obj, function_name, result)
        return result


def elephant_buy(funds, busd_lp, bnb_lp, bnb_price):
    """This function figures out the best pool to buy ELEPHANT from and returns the number of tokens removed"""
    if busd_lp.price > bnb_lp.price * bnb_price:
        bnb_lp.update_lp('WBNB', funds / bnb_price)
        tok_removed = bnb_lp.tokens_removed
    else:
        busd_lp.update_lp('BUSD', funds)
        tok_removed = busd_lp.tokens_removed
    return tok_removed


def elephant_sell(funds, busd_lp, bnb_lp, bnb_price):
    """This function figures out the best pool to sell ELEPHANT into and returns the amount of BUSD removed"""
    if busd_lp.price < bnb_lp.price * bnb_price:
        bnb_lp.update_lp('ELEPHANT', funds)
        tok_removed = bnb_lp.tokens_removed * bnb_price  # Always return BUSD, not BNB
    else:
        busd_lp.update_lp('ELEPHANT', funds)
        tok_removed = busd_lp.tokens_removed
    return tok_removed


def get_ave_ele(busd_lp, bnb_lp, bnb_price):
    """This function determines the weighted average USD price of Elephant based on the two LPs"""
    busd_ele = busd_lp.token_bal['ELEPHANT']
    bnb_ele = bnb_lp.token_bal['ELEPHANT']
    busd_weight = busd_ele / (busd_ele + bnb_ele)
    bnb_weight = bnb_ele / (busd_ele + bnb_ele)
    ave_price = busd_lp.price * busd_weight + bnb_lp.price * bnb_price * bnb_weight

    return ave_price


class DepotEngine:
    def __init__(self, deposit, day_rate, max_payout):
        """
        This represents the new engine based on Farm Depot and Elephant Futures
        Deposit in $.  Day Rate in %/day.  Max Payout as a multiplier of the deposit.
        """
        self.deposits = deposit
        self.deposit_base = deposit  # Deposit base is needed to properly keep track of yield payout rates
        self.max_payout = max_payout
        self.balance = deposit * self.max_payout
        self.rate = day_rate
        self.available = 0
        self.claimed = 0
        self.daily_payout = self.deposit_base * self.rate

    def pass_days(self, days):
        """
        Update the engine balances based on number of days passed
        """
        if self.balance >= self.daily_payout * days:
            self.available += self.daily_payout * days
            self.balance -= self.daily_payout * days
        else:
            self.available += self.balance
            self.balance = 0

    def claim(self):
        """
        Perform a claim of the available balance
        """
        claimed = self.available
        self.claimed += claimed
        self.available = 0

        return claimed

    def deposit(self, deposit):
        """
        Perform a new deposit
        """
        self.deposit_base = self.balance / self.max_payout + deposit
        self.deposits += deposit
        self.balance += deposit * self.max_payout
        self.daily_payout = self.deposit_base * self.rate


class StampedeEngineV5:
    """
    This was Stampede v5, but now deprecated in favor of the "futures" style engine
    EM Stampede Engine
    Initializes with a starting deposit
    Actions require trunk price to get the peg adjusted yield rate
    self.accumulated will show how much is waiting to be claimed at a later date and can be claimed with "drain" command
    accumulated divs should be added to total liquid debt
    """

    def __init__(self, deposit):
        self.bonds = deposit
        self.maturity = deposit * 2.05
        self.available = 0
        self.accumulated_days = 0
        self.rate = 0.0056
        self.total_claims = 0
        self.claimed = 0
        self._owed = None
        self._accumulated = None
        self.trunk_price = 1

    @property
    def owed(self):
        self._owed = self.maturity - self.total_claims
        return self._owed

    @property
    def accumulated(self):
        daily_yield = self.bonds * self.rate * self.trunk_price
        self._accumulated = min(self.accumulated_days * daily_yield, self.owed)  # Can't accumulate more than owed
        return self._accumulated

    def update(self, action, trunk_price=1.0):
        """
        This function assumes that a day passes for every call to update
        It returns the claimed amount of trunk if claimed
        Draining will claim out the accumulated balance
        """
        self.trunk_price = trunk_price
        self.claimed = 0
        self.available = self.bonds * self.rate * trunk_price
        if self.owed >= self.available:
            if action == 'roll':
                self.bonds += self.available
                self.maturity += self.available * 2.05
                self.total_claims += self.available
                self.available = 0
                self.claimed = 0
            elif action == 'claim':
                self.total_claims += self.available
                self.claimed = self.available
                self.available = 0
            elif action == 'hold':  # this is where people let the divs accumulate
                self.accumulated_days += 1
                self.available = 0
                self.claimed = 0
            elif action == 'drain':
                self.total_claims += self.accumulated
                self.claimed = self.accumulated
                self.available = 0
                self.accumulated_days = 0
            else:
                raise Exception("Improper action passed to Stampede Engine")
        else:
            self.available = 0
            pass

        return self.claimed

    def bond(self, deposit):
        """
        Bond Additional Funds
        """
        self.bonds += deposit
        self.maturity += deposit * 2.05


class YieldEngineV6:
    def __init__(self, deposit, rate=0.005):
        """
        This represents the new engine for BUSD Futures and Stampede
        Deposit in $.  Day Rate in %/day.  Max Payout as a multiplier of the deposit.
        Rate needs to be put in each day to calculate proper available
        """
        self.deposits = deposit
        self.balance = self.deposits
        self.compounds = 0
        self.rate = rate
        self.rate_limiter = 1
        self.max_payout = 2500000
        self.max_balance = 1000000
        self.max_available = 50000
        self.available = 0
        self.claimed = 0
        # self.claimed_pretax = 0
        self.daily_payout = deposit * rate
        self.days_since_action = 0
        self.total_days = 0
        self.last_action = 'deposit'
        self._debt_burden = None
        self._payout_remaining = None

    @property
    def payout_remaining(self):
        return self.max_payout - self.claimed

    @property
    def debt_burden(self):
        return min(self.balance, self.payout_remaining)

    def pass_days(self, days, rate=0.005):
        """
        Update the available balances based on number of days passed and check all limits
        """
        if self.claimed > self.max_payout:  # Wallet is done
            pass
        self.rate = rate
        self.daily_payout = self.balance * self.rate * self.rate_limiter
        self.days_since_action += days
        self.total_days += days
        self.available = min(
            self.daily_payout * self.days_since_action,
            self.payout_remaining,  # Can't exceed max payout
            self.balance,  # Can't exceed balance
            self.max_available  # Can't exceed max available
        )

    def claim(self):
        """
        Perform a claim of the available balance
        """
        self.last_action = 'claim'
        claimed = self.available
        self.claimed += claimed
        if self.balance >= claimed:
            self.balance -= claimed
        else:
            self.balance = 0
        self.available = 0
        self.days_since_action = 0

        return claimed

    def deposit(self, deposit):
        """
        Perform a new deposit
        """
        self.last_action = 'deposit'
        if self.balance > self.max_balance:
            pass
        else:
            self.compounds += self.available  # Track how much has been compounded
            self.balance += deposit + self.available
            if self.balance > self.max_balance:
                self.balance = self.max_balance
            self.available = 0
            self.days_since_action = 0
            self.deposits += deposit
            self.update_rate_limiter()

    def update_rate_limiter(self):
        """Determines the interest rate based on compounded balance and updates the daily payout"""
        if self.compounds < 50000:
            self.rate_limiter = 1
        elif 50000 <= self.compounds < 249999:
            self.rate_limiter = 0.9
        elif 250000 <= self.compounds < 499999:
            self.rate_limiter = 0.85
        elif 500000 <= self.compounds < 749999:
            self.rate_limiter = 0.75
        elif 750000 <= self.compounds < 999999:
            self.rate_limiter = 0.65
        elif self.compounds >= 1000000:
            self.rate_limiter = 0.5


class Trumpet:
    """This Class defines the function of Trumpet"""

    def __init__(self, users, backing, supply):
        self.users = users
        self.backing = backing
        self.supply = supply
        self._price = None

    @property
    def price(self):
        if self.supply > 0:
            return self.backing / self.supply
        else:
            return 1

    def mint_trumpet(self, trunk):
        old_price = self.price
        self.backing += trunk
        minted = trunk / old_price * 0.95
        self.supply += minted
        return minted

    def burn_trumpet(self, trumpet):
        self.supply -= trumpet

    def redeem_trumpet(self, trumpet):
        old_price = self.price
        self.supply -= trumpet
        redeemed = trumpet * old_price * 0.95
        self.backing -= redeemed
        return redeemed


class Unlimited:
    """This class defines the function of NFTs"""

    def __init__(self, supply):
        self.supply = supply
        self._price = None

    @property
    def price(self):
        return 2 ** (int(self.supply / 10000))

    def mint(self, number):
        self.supply += number

    def mint_and_get_usd(self, number, bnb_price):
        usd_value = 0
        for _ in range(number):  # process each NFT individually in case of price crossover
            usd_value += self.price * bnb_price
            self.supply += 1
        return usd_value


class EMCashflow:
    """Helper class to keep track of EM DAILY inflows and outflows better"""

    def __init__(self):
        self.in_futures = 0
        self.in_nft = 0
        self.in_taxes = 0
        self.in_trunk = 0
        self.in_buy_volume = 0
        self._in_total = None
        self.out_futures = 0
        self.out_nft = 0
        self.out_trunk = 0
        self.out_perf = 0
        self.out_bertha = 0
        self.out_sell_volume = 0
        self._out_total = None
        self._cashflow = None

    @property
    def in_total(self):
        return self.in_trunk + self.in_nft + self.in_taxes + self.in_futures + self.in_buy_volume

    @property
    def out_total(self):
        return self.out_nft + self.out_perf + self.out_futures + self.out_trunk + self.out_sell_volume

    @property
    def cashflow(self):
        return self.in_total - self.out_total

    def get_results(self):
        return {
            "in_futures": self.in_futures,
            "in_nft": self.in_nft,
            "in_taxes": self.in_taxes,
            "in_trunk": self.in_trunk,
            "buy_volume": self.in_buy_volume,
            "out_futures": self.out_futures,
            "out_nft": self.out_nft,
            "out_perf": self.out_perf,
            "out_trunk": self.out_trunk,
            "sell_volume": self.out_sell_volume,
            "bertha_sells": self.out_bertha
        }
