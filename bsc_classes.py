# Wallet Holdings
from moralis import evm_api
import numpy as np
from api import api_key


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


class YieldEngine:
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


# TODO: Create treasuries class to handle functions associated with BUSD, Bertha, Trunk treasuries
