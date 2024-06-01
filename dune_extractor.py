import bsc_classes as bsc
import datetime as dt
import pickle
import pandas as pd
import numpy as np
from api import dune_api
from dune_client.client import DuneClient
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures


def build_model(x, y, poly_degree):
    # Set up polynomial regression model
    poly = PolynomialFeatures(degree=poly_degree)
    x_poly = poly.fit_transform(x.reshape(-1, 1))
    model = LinearRegression()
    model.fit(x_poly, y)
    # Check the model predictions relative to truth and look at extrapolation for 180 days
    prediction = []
    for value in range(0, model_days + 180, 1):
        j = [0]
        for i in range(poly_degree):
            j.append(value ** (i + 1))
        day = np.array(j).reshape(1, -1)
        prediction.append(model.predict(day)[0])
    out = pd.DataFrame([y, prediction])
    out.T.plot()
    return model


# -- Start Dune Client --
dune = DuneClient(dune_api)
download = False
downloaded_data = {}
dune_data = {}

# -- Set up Futures --
if download:
    f = open('chain_data/futures_overview.pkl', 'wb')
    fut_overview = dune.get_latest_result(3317877)
    pickle.dump(fut_overview, f)
    f.close()
else:
    f = open('chain_data/futures_overview.pkl', 'rb')
    fut_overview = pickle.load(f)
    f.close()
df = pd.DataFrame(fut_overview.result.rows).sort_values('date')
# Choose a subset of days if desired
model_days = 180  # for full range use df.shape[0]
slicer = df.shape[0] - model_days
subset = df[slicer:]
start_date = subset['date'][model_days - 1]
# dependent variable (feature) in the model is number of days from the start
days = np.linspace(0, model_days - 1, model_days)  # Want first day to be the 0 intercept
deposits = subset['cumdeposit'].values
compounds = subset['cumcompound'].values
withdrawals = subset['cumwithdraw'].values
# Need to iterate this for the model_days and the polynomial degrees to try and find the best fit for extrapolation
d_model = build_model(days, deposits, 2)
c_model = build_model(days, compounds, 2)
w_model = build_model(days, withdrawals, 2)
dune_data['futures_model'] = bsc.FuturesModel(d_model, w_model, c_model, start_date)

# -- Get Buy Volume --
if download:
    f = open('chain_data/em_dex_buy.pkl', 'wb')
    em_dex_buy = dune.get_latest_result(3322390)
    pickle.dump(em_dex_buy, f)
    f.close()
else:
    f = open('chain_data/em_dex_buy.pkl', 'rb')
    em_dex_buy = pickle.load(f)
    f.close()
df_buy = pd.DataFrame(em_dex_buy.result.rows).pivot_table(index='category', values='value_usd', aggfunc='mean')
dune_data['pcs_buy_volume'] = df_buy['value_usd']['PCS']
dune_data['bwb_volume'] = df_buy['value_usd']['BWB']
dune_data['Buyback'] = df_buy['value_usd']['BuyBack']
dune_data['nft_sell_taxes'] = df_buy['value_usd']['NFT Royalties']
dune_data['total_buy_volume'] = df_buy['value_usd'].values.sum()
dune_data['nft_mint_volume'] = 0

# -- Get Sell Volume --
if download:
    f = open('chain_data/em_dex_sell.pkl', 'wb')
    em_dex_sell = dune.get_latest_result(3322391)
    pickle.dump(em_dex_sell, f)
    f.close()
else:
    f = open('chain_data/em_dex_sell.pkl', 'rb')
    em_dex_sell = pickle.load(f)
    f.close()
df_sell = pd.DataFrame(em_dex_sell.result.rows).pivot_table(index='category', values='value_usd', aggfunc='mean')
dune_data['pcs_sell_volume'] = df_sell['value_usd']['PCS']
dune_data['swb_volume'] = df_sell['value_usd']['BWB']
dune_data['futures_payouts'] = df_sell['value_usd']['Other']
dune_data['trunk_buys'] = df_sell['value_usd']['PegSupport']
dune_data['total_sell_volume'] = (df_sell['value_usd'].values.sum() -
                                  df_sell['value_usd']['Deployer'])  # ignore Deployer sales

# -- Calcs --
dune_data['em_cashflow'] = dune_data['total_buy_volume'] - dune_data['total_sell_volume']
dune_data['market_cashflow'] = dune_data['pcs_buy_volume'] + dune_data['bwb_volume'] - \
                               dune_data['pcs_sell_volume'] - dune_data['swb_volume']
dune_data['bertha_cashflow'] = dune_data['em_cashflow'] - dune_data['market_cashflow']
dune_data['%buy_bwb'] = dune_data['bwb_volume'] / dune_data['total_buy_volume'] * 100
dune_data['%buy_pcs'] = dune_data['pcs_buy_volume'] / dune_data['total_buy_volume'] * 100

# -- Save Data --
df = pd.Series(dune_data)
df.to_csv('chain_data/DuneData_{0}.csv'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M')))
f1 = open('chain_data/DuneData_{0}.pkl'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M')), 'wb')
f2 = open('chain_data/DuneData.pkl', 'wb')
pickle.dump(dune_data, f1)
pickle.dump(dune_data, f2)
f1.close()
f2.close()

print("Done")
