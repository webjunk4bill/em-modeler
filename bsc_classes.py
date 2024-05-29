import time
import numpy as np
from api import bsc_url, cmc_key
from web3 import Web3
import json
import requests
import pandas as pd


class Token:
    def __init__(self, addr: str, cmc_id: int):
        self.cmc_id = cmc_id
        self.address = addr
        web3 = Web3(Web3.HTTPProvider(bsc_url))
        address = web3.to_checksum_address(addr)
        with open('chain_data/token_abi.json', 'r') as abi_file:
            contract_abi = json.load(abi_file)
        contract = web3.eth.contract(address=address, abi=contract_abi)
        self.name = contract.functions.name().call()
        self.symbol = contract.functions.symbol().call()
        self.usd_value = self.cmc_get_price()

    def cmc_get_price(self):
        # CoinMarketCap API URL
        url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

        # Parameters
        parameters = {
            'id': self.cmc_id,
            'convert': 'USD'
        }

        # Headers
        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': cmc_key,
        }

        try:
            response = requests.get(url, headers=headers, params=parameters)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            price = data['data'][str(self.cmc_id)]['quote']['USD']['price']
            return price
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"An error occurred: {err}")
            return None


class CakeLP:
    def __init__(self, pair_addr: str, token0: Token, token1: Token):
        self.pair_addr = pair_addr
        self.token_addr = [token0.address, token1.address]
        self.token_name = [token0.symbol, token1.symbol]
        self.token_bal = {}
        # Read Contract
        with open('chain_data/pcs_lp_abi.json', 'r') as abi_file:
            contract_abi = json.load(abi_file)
        web3 = Web3(Web3.HTTPProvider(bsc_url))
        pair = web3.eth.contract(address=self.pair_addr, abi=contract_abi)
        reserves = pair.functions.getReserves().call()
        if self.token_addr[0] == pair.functions.token0().call():
            self.token_bal[self.token_name[0]] = reserves[0] / 1E18
            self.token_bal[self.token_name[1]] = reserves[1] / 1E18
        elif self.token_addr[1] == pair.functions.token0().call():
            self.token_bal[self.token_name[1]] = reserves[0] / 1E18
            self.token_bal[self.token_name[0]] = reserves[1] / 1E18
        else:
            raise Exception('Token address does not match!')
        # Check if it's Elephant
        if self.token_name[0] == 'ELEPHANT':
            self.token_bal[self.token_name[0]] *= 1E9
        elif self.token_name[1] == 'ELEPHANT':
            self.token_bal[self.token_name[1]] *= 1E9
        else:
            pass
        self.const_prod = self.token_bal[self.token_name[0]] * self.token_bal[self.token_name[1]]

    def get_price(self, token: Token):
        """ Get token price in the other token"""
        if self.token_bal[token.symbol]:
            other_key = (set(self.token_bal.keys()) - {token.symbol}).pop()
            price = self.token_bal[token.symbol] / self.token_bal[other_key]
        else:
            raise Exception('Token Symbol not found')
        return price

    def update_lp(self, token: Token, change):
        """
        Use this to update the token pair and price
        match token name, update the balances, re-calc the price
        """
        [first, second] = self.token_bal.keys()
        if first == token.symbol:
            old = self.token_bal[second]  # Get original "buy" token balance
            self.token_bal[first] += change  # Push in "sell" tokens
            self.token_bal[second] = self.const_prod / self.token_bal[first]  # Calc new "buy" token balance
            tokens_removed = old - self.token_bal[second]  # Cal number of tokens bought or removed
        else:  # This is just in the opposite order
            old = self.token_bal[first]
            self.token_bal[second] += change
            self.token_bal[first] = self.const_prod / self.token_bal[second]
            tokens_removed = old - self.token_bal[first]

        return tokens_removed

    def add_liquidity(self, token1: Token, amt1: float, token2: Token, amt2: float):
        self.token_bal[token1.symbol] += amt1
        self.token_bal[token2.symbol] += amt2
        self.const_prod = self.token_bal[token1.symbol] * self.token_bal[token2.symbol]


class Wallet:
    def __init__(self, addr, token: Token = None):
        """ Get the native balance (bnb) of the wallet.  Additionally, you can use the function
        get_token_balance for the balance of a non-native token"""
        self.token = token
        web3 = Web3(Web3.HTTPProvider(bsc_url))
        self.wallet_addr = web3.to_checksum_address(addr)  # ensure checksum is good
        # BNB balance is native to the chain and read differently
        self.bnb_balance = web3.eth.get_balance(self.wallet_addr) / 1E18

    def get_token_balance(self):
        web3 = Web3(Web3.HTTPProvider(bsc_url))
        with open('chain_data/token_abi.json', 'r') as abi_file:
            contract_abi = json.load(abi_file)
        contract = web3.eth.contract(address=self.token.address, abi=contract_abi)
        token_balance = contract.functions.balanceOf(self.wallet_addr).call()
        if self.token.symbol == "ELEPHANT":
            balance = token_balance / 1E9
        else:
            balance = token_balance / 1E18
        return balance


class ContractReader:
    def __init__(self, contract_abi, contract_address):
        self.web3 = Web3(Web3.HTTPProvider(bsc_url))
        with open(contract_abi, 'r') as abi_file:
            contract_abi = json.load(abi_file)
        self.contract = self.web3.eth.contract(address=contract_address, abi=contract_abi)
        self.result_obj = self.Info()

    class Info:
        pass

    def get_turbine_balance(self):
        function_name = 'balanceUnderlying'
        try:
            # Call the read function (constant function)
            result = self.contract.functions[function_name]().call()
        except Exception as e:
            print(f"Error calling {function_name}: {e}")
        balance = result / 1E18
        return balance

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


class YieldEngineV8:
    def __init__(self, deposit, rate=0.005):
        """
        This represents the new engine for BUSD Futures and Stampede
        Deposit in $.  Day Rate in %/day.  Max Payout as a multiplier of the deposit.
        Rate needs to be put in each day to calculate proper available
        V8 adds a variable rate plus a personal bonus based on deposit frequency
        """
        self.deposits = deposit
        self.balance = self.deposits
        self.compounds = 0
        self.rate_max = 0.005
        self.group_rate = rate
        self.rate_limiter = 1
        self.max_payout = 2500000
        self.max_balance = 1000000
        self.max_available = 50000
        self.available = 0
        self.claimed = 0
        self.daily_payout = deposit * rate
        self.days_since_action = 0
        self.days_since_deposit = 0
        self.total_days = 0
        self.last_action = 'deposit'
        self._debt_burden = None
        self._payout_remaining = None
        self.bonus_rate = 0.005
        self.decay_daily = self.bonus_rate / 45  # 45 day decay
        self._bonus = None
        self._rate = None

    @property
    def payout_remaining(self):
        return self.max_payout - self.claimed

    @property
    def debt_burden(self):
        return min(self.balance, self.payout_remaining)

    @property
    def bonus(self):
        return max(0.0, self.bonus_rate - self.decay_daily * self.days_since_deposit)

    @property
    def rate(self):
        return min(self.rate_max, self.group_rate + self.bonus)

    def pass_days(self, days, rate=0.005):
        """
        Update the available balances based on number of days passed and check all limits
        """
        if self.claimed > self.max_payout:  # Wallet is done
            pass
        self.days_since_action += days
        self.days_since_deposit += days
        self.group_rate = rate
        self.daily_payout = self.balance * self.rate * self.rate_limiter
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
            self.days_since_deposit = 0
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
        self.in_buybacks = 0
        self._in_total = None
        self._bertha_buys = None
        self.out_futures_sell = 0
        self.out_futures_buffer = 0
        self.out_nft = 0
        self.out_trunk = 0
        self.out_perf = 0
        self.out_sell_volume = 0
        self._out_total = None
        self._cashflow = None
        self._bertha_sells = None

    @property
    def in_total(self):
        return self.in_trunk + self.in_nft + self.in_taxes + self.in_futures + self.in_buy_volume

    @property
    def bertha_buys(self):
        return self.in_nft + self.in_buybacks

    @property
    def out_total(self):
        return self.out_nft + self.out_perf + self.out_futures_buffer + self.out_trunk + self.out_sell_volume

    @property
    def bertha_sells(self):
        return self.out_nft + self.out_perf + self.out_futures_sell + self.out_trunk

    @property
    def cashflow(self):
        return self.in_total - self.out_total

    def get_results(self):
        return {
            "in_futures": self.in_futures,
            "in_nft": self.in_nft,
            "in_taxes": self.in_taxes,
            "in_trunk": self.in_trunk,
            "$em_income": self.in_total,
            "buy_volume": self.in_buy_volume,
            "out_nft": self.out_nft,
            "out_perf": self.out_perf,
            "out_trunk": self.out_trunk,
            "sell_volume": self.out_sell_volume,
            "$em_outflow": self.out_total,
            "bertha_sells": self.bertha_sells,
            "bertha_buys": self.bertha_buys,
            "$em_cashflow": self.cashflow
        }


class Turbine:
    def __init__(self, addr, token: Token):
        contract = ContractReader('chain_data/turbine_abi.json', addr)
        self.token = token
        self.symbol = self.token.symbol
        self.balance = contract.get_turbine_balance()

    @property
    def usd_value(self):
        return self.token.usd_value * self.balance


class TrunkHandler:
    """
    Helper class for frequent Trunk operations, mainly handling buys, sells, and arbitrage properly
    """

    def __init__(self, bnb_lp: CakeLP, bnb_lp_backing: Token, busd_lp: CakeLP,
                 busd_lp_backing: Token, trunk: Token):
        self.bnb_lp = bnb_lp
        self.bnb_token = bnb_lp_backing
        self.busd_lp = busd_lp
        self.busd_token = busd_lp_backing
        self.trunk_token = trunk

    @property
    def bnb_usd_price(self):
        return get_lp_usd(self.bnb_token, self.bnb_lp)

    @property
    def bnb_usd_liquidity(self):
        return get_lp_liquidity_usd(self.bnb_token, self.bnb_lp)

    @property
    def busd_usd_price(self):
        return get_lp_usd(self.busd_token, self.busd_lp)

    @property
    def busd_usd_liquidity(self):
        return get_lp_liquidity_usd(self.busd_token, self.busd_lp)

    def protocol_buy(self, bnb_amt: float):
        """ protocol buys are always in BNB. """
        trunk_bought = self.bnb_lp.update_lp(self.bnb_token, bnb_amt)
        return trunk_bought

    def protocol_sell(self, trunk_amt: float):
        """ Protocol sells are always in the BNB LP.  Updates Treasury and LPs, returns BNB pulled from LP """
        bnb_bought = self.bnb_lp.update_lp(self.trunk_token, trunk_amt)
        return bnb_bought

    def pcs_buy(self, usd_amt: float):
        """
        Market buy will use PCS router for best price.  Always in USD
        Function returns the amount of trunk bought
        """
        if self.bnb_usd_price <= self.busd_usd_price:
            bnb_amt = usd_amt / self.bnb_token.usd_value
            return self.bnb_lp.update_lp(self.bnb_token, bnb_amt)
        else:
            return self.busd_lp.update_lp(self.busd_token, usd_amt)

    def pcs_sell(self, trunk_amt: float):
        """
        Market sell will use PCS router for best price.
        Function returns the amount purchased in USD (regardless of pool)
        """
        if self.bnb_usd_price >= self.busd_usd_price:
            bnb_bought = self.bnb_lp.update_lp(self.trunk_token, trunk_amt)
            usd_bought = bnb_bought * self.bnb_token.usd_value
            return usd_bought
        else:
            usd_bought = self.busd_lp.update_lp(self.trunk_token, trunk_amt)
            return usd_bought

    def arbitrage_pools(self, buy_size=10000):
        """
        Function checks to see if the two LPs are within 1.5%, if so it passes, if not, it will perform a
        "market induced" arbitrage.  Returns the total USD amount of funds input into the lower priced pool
        """
        total_buys = 0
        profit = 0
        if self.bnb_usd_price <= self.busd_usd_price * 0.985:
            while self.bnb_usd_price < self.busd_usd_price:
                trunk_out = self.bnb_lp.update_lp(self.bnb_token, buy_size / self.bnb_token.usd_value)
                busd_out = self.busd_lp.update_lp(self.trunk_token, trunk_out)
                total_buys += buy_size
                profit += busd_out - buy_size
        elif self.busd_usd_price <= self.bnb_usd_price * 0.985:
            while self.busd_usd_price < self.bnb_usd_price:
                trunk_out = self.busd_lp.update_lp(self.busd_token, buy_size)
                bnb_out = self.bnb_lp.update_lp(self.trunk_token, trunk_out)
                total_buys += buy_size
                profit += bnb_out * self.bnb_token.usd_value - buy_size
        else:
            pass
        return {'$buys': total_buys, '$profit': profit}


class ElephantHandler:
    """
    Helper class for frequent Elephant operations, mainly handling buys and sells properly
    """

    def __init__(self, bnb_lp: CakeLP, bnb_lp_backing: Token, busd_lp: CakeLP,
                 busd_lp_backing: Token, elephant: Token, bertha: float, graveyard: float):
        self.bnb_lp = bnb_lp
        self.bnb_token = bnb_lp_backing
        self.busd_lp = busd_lp
        self.busd_token = busd_lp_backing
        self.elephant_token = elephant
        self.bertha = bertha
        self.graveyard = graveyard

    @property
    def bnb_usd_price(self):
        return get_lp_usd(self.bnb_token, self.bnb_lp)

    @property
    def bnb_usd_liquidity(self):
        return get_lp_liquidity_usd(self.bnb_token, self.bnb_lp)

    @property
    def busd_usd_price(self):
        return get_lp_usd(self.busd_token, self.busd_lp)

    @property
    def busd_usd_liquidity(self):
        return get_lp_liquidity_usd(self.busd_token, self.busd_lp)

    @property
    def bertha_usd_value(self):
        return self.bertha * self.bnb_usd_price

    @property
    def ele_in_wallets(self):
        return (1E15 - self.graveyard - self.bertha - self.bnb_lp.token_bal['ELEPHANT'] -
                self.busd_lp.token_bal['ELEPHANT'])

    def protocol_buy(self, bnb_amt: float):
        """ protocol buys are always in BNB.  Updates treasury and LPs, does not return any values """
        ele_bought = self.bnb_lp.update_lp(self.bnb_token, bnb_amt)
        self.bertha += ele_bought
        return

    def protocol_sell(self, ele_amt: float):
        """ Protocol sells are always in the BNB LP.  Updates Treasury and LPs, returns BNB pulled from LP """
        bnb_bought = self.bnb_lp.update_lp(self.elephant_token, ele_amt)
        self.bertha -= ele_amt
        return bnb_bought

    def pcs_buy(self, usd_amt: float):
        """ Market buy will use PCS router for best price.  Always in USD """
        if self.bnb_usd_price <= self.busd_usd_price:
            bnb_amt = usd_amt / self.bnb_token.usd_value
            ele_bought = self.bnb_lp.update_lp(self.bnb_token, bnb_amt)
            reflections = ele_bought * 0.05  # 5% to reflections
            to_bertha = self.bertha / 1E15 * reflections  # Bertha's cut based on ownership
            to_graveyard = self.graveyard / 1E15 * reflections  # Graveyard's cut
            self.bertha += to_bertha
            self.graveyard += to_graveyard
            # 5% added as liquidity
            self.bnb_lp.add_liquidity(self.elephant_token, ele_bought * 0.025, self.bnb_token, bnb_amt * 0.025)
            return ele_bought * 0.9  # 10% tax
        else:
            ele_bought = self.busd_lp.update_lp(self.busd_token, usd_amt)
            reflections = ele_bought * 0.05
            to_bertha = self.bertha / 1E15 * reflections  # Bertha's cut based on ownership
            to_graveyard = self.graveyard / 1E15 * reflections  # Graveyard's cut
            self.bertha += to_bertha
            self.graveyard += to_graveyard
            bnb_amt = usd_amt / self.bnb_token.usd_value
            # liquidity is always added to BNB LP (I think)
            self.bnb_lp.add_liquidity(self.elephant_token, ele_bought * 0.025, self.bnb_token, bnb_amt * 0.025)
            return ele_bought * 0.9

    def pcs_sell(self, usd_amt: float):
        """
        Normally a sale would start with the amount of elephant, but for tracking purposes,
        the model just handles the amount of market sells based in USD
        In and OUT is always USD
        """
        if self.bnb_usd_price >= self.busd_usd_price:
            ele_amt = usd_amt / self.bnb_usd_price
            reflections = ele_amt * 0.05
            to_bertha = self.bertha / 1E15 * reflections  # Bertha's cut based on ownership
            to_graveyard = self.graveyard / 1E15 * reflections  # Graveyard's cut
            self.bertha += to_bertha
            self.graveyard += to_graveyard
            bnb_bought = self.bnb_lp.update_lp(self.elephant_token, ele_amt * 0.9)
            bnb_amt = usd_amt / self.bnb_token.usd_value
            self.bnb_lp.add_liquidity(self.elephant_token, ele_amt * 0.025, self.bnb_token, bnb_amt * 0.025)
            usd_bought = bnb_bought * self.bnb_token.usd_value
            return usd_bought
        else:
            ele_amt = usd_amt / self.busd_usd_price
            reflections = ele_amt * 0.05
            to_bertha = self.bertha / 1E15 * reflections  # Bertha's cut based on ownership
            to_graveyard = self.graveyard / 1E15 * reflections  # Graveyard's cut
            self.bertha += to_bertha
            self.graveyard += to_graveyard
            usd_bought = self.busd_lp.update_lp(self.elephant_token, ele_amt * 0.9)
            bnb_amt = usd_amt / self.bnb_token.usd_value
            self.bnb_lp.add_liquidity(self.elephant_token, ele_amt * 0.025, self.bnb_token, bnb_amt * 0.025)
            return usd_bought

    def bwb_buy(self, bnb_amt: float):
        ele_bought = self.bnb_lp.update_lp(self.bnb_token, bnb_amt)
        self.bertha += ele_bought * 0.08  # 8% goes to treasure
        return ele_bought * 0.915  # 91.5% returned to buyer

    def bwb_sell(self, usd_amt: float):
        """ In and Out is always USD """
        ele_amt = usd_amt / self.bnb_usd_price
        self.bertha += ele_amt * 0.08
        bnb_bought = self.bnb_lp.update_lp(self.elephant_token, ele_amt * 0.915)  # only 91.5% is sold to LP
        usd_bought = bnb_bought * self.bnb_token.usd_value
        return usd_bought


class FuturesModel:
    """ Model of futures using a 3rd order polynomials for the aggregate functions of deposits, compounds,
    and withdrawals.  Coefficients should be entered as a list: [3rd, 2nd, 1st, 0].
    The dependent variable is days passed the start of the data collection
    """

    def __init__(self, d_coef=None, w_coef=None, c_coef=None, start_date=pd.to_datetime('2023-12-02')):
        if c_coef is None:
            c_coef = [3.0379, -567.23, 98922, 1E7]
        if w_coef is None:
            w_coef = [0.6847, -76.35, 47600, 3E6]
        if d_coef is None:
            d_coef = [3.5509, -823.19, 86748, 2E7]
        self.deposit_coef = d_coef
        self.withdrawal_coef = w_coef
        self.compound_coef = c_coef
        self.start_date = start_date
        self.today = pd.to_datetime(pd.Timestamp.today().date())

    @property
    def delta_days(self):
        return (self.today - self.start_date).days

    @property
    def deposits(self):
        return poly3_calc(self.deposit_coef, self.delta_days)

    @property
    def deposit_delta(self):
        return self.deposits - poly3_calc(self.deposit_coef, self.delta_days - 1)

    @property
    def withdrawals(self):
        return poly3_calc(self.withdrawal_coef, self.delta_days)

    @property
    def withdrawal_delta(self):
        return self.withdrawals - poly3_calc(self.withdrawal_coef, self.delta_days - 1)

    @property
    def compounds(self):
        return poly3_calc(self.compound_coef, self.delta_days)

    @property
    def tvl(self):
        return self.deposits + self.compounds - self.withdrawals

    @property
    def claims(self):
        return self.compounds + self.withdrawals


def get_lp_usd(backing: Token, lp: CakeLP):
    """
    For tokens not paired with a stable coin, use this to know the usd value in that particular lp
    """
    native_price = lp.get_price(backing)
    usd = native_price * backing.usd_value
    return usd


def get_lp_liquidity_usd(backing: Token, lp: CakeLP):
    """
    return the usd value of the total liquidity in the LP
    This will only work with v2 LPs where the tokens are balanced in value
    TODO: write function to handle v3 LPs
    """
    balance = lp.token_bal[backing.symbol]
    return backing.usd_value * balance * 2


def poly3_calc(coef: list, days: int):
    return coef[0] * days ** 3 + coef[1] * days ** 2 + coef[2] * days + coef[3]