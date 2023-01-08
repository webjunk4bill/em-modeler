import pandas as pd
import matplotlib.pyplot as plt
import addr_contracts
import bsc_classes as bsc
import addr_tokens
from datetime import date
import pickle

# Get LP and Token Info
f_o = open('chainData_2022-12-28.pkl', 'rb')
from_pickle = pickle.load(f_o)
f_o.close()


def parabolic_bertha(bertha, funds_in, support_apr, bnb_lp, busd_lp, bnb_price, days):
    b_tok = {}
    b_val = {}
    running_funds = 0
    futures = bsc.YieldEngine(0, 0.01, 2)
    for i in range(int(days)):
        claimed = futures.claim()
        running_funds += funds_in
        futures.deposit(funds_in)
        tokens_out = bsc.elephant_buy(funds_in, busd_lp, bnb_lp, bnb_price)
        ave_ele_price = (bnb_lp.price * bnb_price + busd_lp.price) / 2
        bertha += tokens_out
        sales = bertha * support_apr / 365 + claimed / ave_ele_price
        bertha -= sales
        bsc.elephant_sell(sales, busd_lp, bnb_lp, bnb_price)
        bertha_usd = bertha * busd_lp.price
        b_tok[running_funds / 1E6] = bertha / 1E12
        b_val[running_funds / 1E6] = bertha_usd / 1E6
        futures.pass_days(1)
        funds_in *= 1.0046

    return b_tok, b_val


def plot_funds(frame):
    fig, axes = plt.subplots(figsize=[14, 9], nrows=1, ncols=1)
    frame.plot(ax=axes, ylabel='Bertha $USD (millions)', xlabel='Funds in $USD Millions',
               title='Elephant Futures', sharex=False, sharey=False,
               grid=True)
    plt.show()


[ele_bnb_lp, ele_busd_lp, trunk_busd_lp, bnb, bertha, busd_treasury, trunk_treasury] = from_pickle
ele_bnb_ele = ele_bnb_lp.token_bal['ELEPHANT']
ele_bnb_bnb = ele_bnb_lp.token_bal['WBNB']
ele_busd_ele = ele_busd_lp.token_bal['ELEPHANT']
ele_busd_busd = ele_busd_lp.token_bal['BUSD']
bertha_start = bertha
run1_tok, run1_val = parabolic_bertha(bertha, 100000, 0.0, ele_bnb_lp, ele_busd_lp, 300, 730)

bertha = bertha_start
ele_bnb_lp.token_bal['ELEPHANT'] = ele_bnb_ele
ele_bnb_lp.token_bal['WBNB'] = ele_bnb_bnb
ele_bnb_lp.price = ele_bnb_lp.get_price()
ele_busd_lp.token_bal['ELEPHANT'] = ele_busd_ele
ele_busd_lp.token_bal['BUSD'] = ele_busd_busd
ele_busd_lp.price = ele_busd_lp.get_price()
run2_tok, run2_val = parabolic_bertha(bertha, 100000, 0.1, ele_bnb_lp, ele_busd_lp, 300, 730)

df = pd.DataFrame([run1_val, run2_val])
dft = df.T
plot_funds(dft)

print("Done")
