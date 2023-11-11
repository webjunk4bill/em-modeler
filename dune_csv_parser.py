import pandas as pd
import math as m
import datetime as dt
import pickle
import bsc_classes as bsc


# Function to convert currency strings to numeric values
def convert_currency_string_to_numeric(currency_string):
    if currency_string.endswith('k'):
        # Remove 'k' and '$' and convert to float
        return float(currency_string.replace('-', '').replace('$', '').replace('k', '')) * 1E3
    elif currency_string.endswith('m'):
        # Remove 'm' and '$' and convert to float
        return float(currency_string.replace('-', '').replace('$', '').replace('m', '')) * 1E6
    elif currency_string.endswith('b'):
        # Remove 'm' and '$' and convert to float
        return float(currency_string.replace('-', '').replace('$', '').replace('b', '')) * 1E9
    elif currency_string.endswith('T'):
        # Remove 'm' and '$' and convert to float
        return float(currency_string.replace('-', '').replace('$', '').replace('T', '')) * 1E12
    elif currency_string.endswith('t'):
        # Remove 'm' and '$' and convert to float
        return float(currency_string.replace('-', '').replace('$', '').replace('t', '')) * 1E12
    else:
        # Remove '$' and convert to float
        return float(currency_string.replace('-', '').replace('$', '').replace(',', ''))


# When collecting data, use median values for the past 30 days
# This removes any wild swings that can SKU the data when looking at long-term trends
# Actually, better to do everything in the sum of 30 days and then take the average at the end
# Coming up with negative data sometimes

dune_data = {}
data_period = 30  # number of days, can't be more than 30

# Get LP related data
df = pd.read_csv('chain_data/lp_dune.csv', index_col='DAY', parse_dates=True)
last_day = df.index[0]
# Need to convert the values in the table to numerics
df['BUY VOL'] = df['BUY VOL'].apply(convert_currency_string_to_numeric)
df['SELL VOL'] = df['SELL VOL'].apply(convert_currency_string_to_numeric)
# df[['BUY VOL', 'SELL VOL']].plot(title='LP Data', grid=True)
buy_vol = df['BUY VOL'][:data_period].sum()  # Get most recent 30 days
sell_vol = df['SELL VOL'][:data_period].sum()
total_vol = sell_vol + buy_vol

# get 30d Governance data
df = pd.read_csv('chain_data/governance_dune.csv', index_col='Day', parse_dates=True)
bertha_out_usd = df['Daily OUT.1'].apply(convert_currency_string_to_numeric).sum()
bertha_in_usd = df['Daily IN.1'].apply(convert_currency_string_to_numeric).sum()
# bertha_in_ele = convert_currency_string_to_numeric(df['Total IN'][0])  # First entry is the 30d total
# bertha_in_usd = convert_currency_string_to_numeric(df['Total IN.1'][0])
# bertha_out_usd = convert_currency_string_to_numeric(df['Total OUT.1'][0])
avg_treasury = df['Treasury'].apply(convert_currency_string_to_numeric).mean()  # Get Average Treasury Value

df = pd.read_csv('chain_data/ele_out_pie.csv', index_col='category')
dune_data['trunk_support_apr'] = df['balance']['PegSupport'] / avg_treasury / data_period
dune_data['redemption_support_apr'] = df['balance']['Redemption'] / avg_treasury / data_period

df = pd.read_csv('chain_data/bertha_in_30.csv', index_col='Date', parse_dates=True)
sums = df.pivot(columns='category', values='daily')[:data_period].sum()  # Take a slice
bwb_taxes = sums['BWB'] / sums.sum() * bertha_in_usd
nft_mint_volume = sums['NFT Mint'] / sums.sum() * bertha_in_usd
nft_sell_taxes = sums['NFT Royalties'] / sums.sum() * bertha_in_usd
buyback = sums['BuyBack'] / sums.sum() * bertha_in_usd

# Calculate various parameters
market_buy_volume = buy_vol - buyback - nft_mint_volume
market_sell_volume = sell_vol - bertha_out_usd
market_total_volume = market_sell_volume + market_buy_volume
bwb_volume = bwb_taxes / 0.08 * (market_buy_volume / market_total_volume)
swb_volume = bwb_taxes / 0.08 * (market_sell_volume / market_total_volume)
dune_data['pcs_buy_volume'] = (market_buy_volume - bwb_volume) / data_period
dune_data['pcs_sell_volume'] = (market_sell_volume - swb_volume) / data_period
dune_data['bwb_volume'] = bwb_volume / data_period
dune_data['swb_volume'] = swb_volume / data_period
dune_data['total_buy_volume'] = buy_vol / data_period
dune_data['total_sell_volume'] = sell_vol / data_period
dune_data['nft_mint_volume'] = nft_mint_volume / data_period
dune_data['nft_sell_taxes'] = nft_sell_taxes / data_period
dune_data['%buy_bertha'] = (buyback + nft_mint_volume) / buy_vol * 100
dune_data['%buy_bwb'] = dune_data['bwb_volume'] / dune_data['total_buy_volume'] * 100
dune_data['%buy_pcs'] = dune_data['pcs_buy_volume'] / dune_data['total_buy_volume'] * 100

# Create Futures Stakes
# Data has missing entries, and needs cleanup
f_data = pd.read_csv('chain_data/futures_dune.csv', index_col='Wallet')
# Clean Text
f_data['Bal [BUSD]'] = f_data['Bal [BUSD]'].apply(convert_currency_string_to_numeric)
f_data['Comp [BUSD]'] = f_data['Comp [BUSD]'].apply(convert_currency_string_to_numeric)
f_data['Wd [BUSD]'] = f_data['Wd [BUSD]'].apply(convert_currency_string_to_numeric)
f_data['1st Dep [d]'] = f_data['1st Dep [d]'].fillna(0)
f_data['Last Wd [d]'] = f_data['Last Wd [d]'].fillna(0)
f_data['Last Comp [d]'] = f_data['Last Comp [d]'].fillna(0)
dune_data['futures_tvl'] = f_data['Bal [BUSD]'].sum()

df = pd.Series(dune_data)
df.to_csv('chain_data/DuneData_{0}.csv'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M')))

futures = []
i = 0
for row in f_data.iterrows():
    if row[1]['Bal [BUSD]'] <= 0:
        pass
    futures.append(bsc.YieldEngineV6(row[1]['Bal [BUSD]'], 0.005))
    if not m.isnan(row[1]['Comp [BUSD]']):
        futures[i].compounds = row[1]['Comp [BUSD]']
    if not m.isnan(row[1]['Wd [BUSD]']):
        futures[i].claimed = row[1]['Wd [BUSD]']

    futures[i].total_days = row[1]['1st Dep [d]']
    futures[i].update_rate_limiter()
    futures[i].deposits = futures[i].balance + futures[i].claimed - futures[i].compounds
    futures[i].pass_days(min(row[1]['Last Wd [d]'], row[1]['Last Comp [d]']))
    if m.isnan(futures[i].available):
        raise Exception('NaN found!')
    i += 1
dune_data['futures'] = futures

f1 = open('chain_data/DuneData_{0}.pkl'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M')), 'wb')
f2 = open('chain_data/DuneData.pkl', 'wb')
pickle.dump(dune_data, f1)
pickle.dump(dune_data, f2)
f1.close()
f2.close()

print()
