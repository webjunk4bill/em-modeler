import pandas as pd
import addr_contracts
import bsc_classes as bsc
import addr_tokens
from datetime import date
from plotting import em_plot_time
from plotting import em_plot_funds
import pickle

# Get LP and Token Info
f_o = open('../chainData_2022-12-28.pkl', 'rb')
from_pickle = pickle.load(f_o)
f_o.close()


def parabolic_bertha(bertha, funds_in, support_apr, bnb_lp, busd_lp, bnb_price, days):
    b_tok = {}
    b_val = {}
    running_funds = 0
    for i in range(int(days)):
        running_funds += funds_in
        tokens_out = bsc.elephant_buy(funds_in, busd_lp, bnb_lp, bnb_price)
        bertha += tokens_out
        sales = bertha * support_apr / 365
        bertha -= sales
        bsc.elephant_sell(sales, busd_lp, bnb_lp, bnb_price)
        bertha_usd = bertha * busd_lp.price
        b_tok[running_funds / 1E6] = bertha / 1E12
        b_val[running_funds / 1E6] = bertha_usd / 1E6

    return b_tok, b_val


[ele_bnb_lp, ele_busd_lp, trunk_busd_lp, bnb, bertha, busd_treasury, trunk_treasury] = from_pickle
ele_bnb_ele = ele_bnb_lp.token_bal['ELEPHANT']
ele_bnb_bnb = ele_bnb_lp.token_bal['WBNB']
ele_busd_ele = ele_busd_lp.token_bal['ELEPHANT']
ele_busd_busd = ele_busd_lp.token_bal['BUSD']
bertha_start = bertha
run1_tok, run1_val = parabolic_bertha(bertha, 250000, 0.0, ele_bnb_lp, ele_busd_lp, 300, 730)

bertha = bertha_start
ele_bnb_lp.token_bal['ELEPHANT'] = ele_bnb_ele
ele_bnb_lp.token_bal['WBNB'] = ele_bnb_bnb
ele_bnb_lp.price = ele_bnb_lp.get_price()
ele_busd_lp.token_bal['ELEPHANT'] = ele_busd_ele
ele_busd_lp.token_bal['BUSD'] = ele_busd_busd
ele_busd_lp.price = ele_busd_lp.get_price()
run2_tok, run2_val = parabolic_bertha(bertha, 250000, 0.1, ele_bnb_lp, ele_busd_lp, 300, 730)

df = pd.DataFrame([run1_val, run2_val])
df.T.plot()

print("Done")
