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

# Get LP related data
# This is from https://dune.com/elephantmoney/liquidity-pools-detailed
df_buy = pd.read_csv('chain_data/em_dex_buy_vol.csv', index_col='category')
df_sell = pd.read_csv('chain_data/em_dex_sell_vol.csv', index_col='category')
df_buy_size = len(df_buy['value_usd']['BWB'])
df_sell_size = len(df_sell['value_usd']['BWB'])
dune_data['pcs_buy_volume'] = df_buy['value_usd']['PCS'].sum() / df_buy_size
dune_data['pcs_sell_volume'] = df_sell['value_usd']['PCS'].sum() / df_sell_size
dune_data['bwb_volume'] = df_buy['value_usd']['BWB'].sum() / df_buy_size
dune_data['swb_volume'] = df_sell['value_usd']['BWB'].sum() / df_sell_size
dune_data['total_buy_volume'] = df_buy['value_usd'].sum() / df_buy_size
dune_data['total_sell_volume'] = df_sell['value_usd'].sum() / df_sell_size
dune_data['futures_payouts'] = df_sell['value_usd']['Other'].sum() / df_sell_size
dune_data['trunk_buys'] = df_sell['value_usd']['PegSupport'].sum() / df_sell_size
dune_data['nft_sell_taxes'] = df_buy['value_usd']['NFT Royalties'].sum() / df_buy_size
dune_data['Buyback'] = df_buy['value_usd']['BuyBack'].sum() / df_buy_size
dune_data['em_cashflow'] = dune_data['total_buy_volume'] - dune_data['total_sell_volume']
dune_data['market_cashflow'] = dune_data['pcs_buy_volume'] + dune_data['bwb_volume'] - \
                               dune_data['pcs_sell_volume'] - dune_data['swb_volume']
dune_data['bertha_cashflow'] = dune_data['em_cashflow'] - dune_data['market_cashflow']
dune_data['%buy_bwb'] = dune_data['bwb_volume'] / dune_data['total_buy_volume'] * 100
dune_data['%buy_pcs'] = dune_data['pcs_buy_volume'] / dune_data['total_buy_volume'] * 100
df_fut = pd.read_csv('chain_data/futures_overview.csv', index_col='Date', parse_dates=True)
# df_fut['%withdrawal'] = (df_fut['Withdrawals [USD]'].apply(convert_currency_string_to_numeric) /
#                         df_fut['TVL [USD]'].apply(convert_currency_string_to_numeric) * 100).mean()
dune_data['$fut_daily_tot_withdrawal'] = df_fut['Withdrawals [USD]'].apply(convert_currency_string_to_numeric).mean()
dune_data['%fut_daily_tot_withdrawal'] = (df_fut['Withdrawals [USD]'].apply(convert_currency_string_to_numeric) /
                                          df_fut['TVL [USD]'].apply(convert_currency_string_to_numeric) * 100).mean()

# TODO: Fix NFT Mint volme
'''
df = pd.read_csv('chain_data/bertha_in_30.csv', index_col='Date', parse_dates=True)
sums = df.pivot(columns='category', values='daily')[:data_period].sum()  # Take a slice
bwb_taxes = sums['BWB'] / sums.sum() * bertha_in_usd
nft_mint_volume = sums['NFT Mint'] / sums.sum() * bertha_in_usd
nft_sell_taxes = sums['NFT Royalties'] / sums.sum() * bertha_in_usd
buyback = sums['BuyBack'] / sums.sum() * bertha_in_usd
'''
dune_data['nft_mint_volume'] = 0

# Create Futures Stakes
# Data has missing entries, and needs cleanup
f_data = pd.read_csv('chain_data/futures_dune.csv', index_col='Wallet')
# Clean Text
f_data['Bal [USD]'] = f_data['Bal [USD]'].apply(convert_currency_string_to_numeric)
f_data['Comp [USD]'] = f_data['Comp [USD]'].apply(convert_currency_string_to_numeric)
f_data['Wd [USD]'] = f_data['Wd [USD]'].apply(convert_currency_string_to_numeric)
f_data['1st Dep [d]'] = f_data['1st Dep [d]'].fillna(0)
f_data['Last Wd [d]'] = f_data['Last Wd [d]'].fillna(0)
f_data['Last Comp [d]'] = f_data['Last Comp [d]'].fillna(0)
# dune_data['futures_tvl'] = f_data['Bal [USD]'].sum()

futures = []
i = 0
tvl = 0
for row in f_data.iterrows():
    if row[1]['Bal [USD]'] <= 0:
        pass
    futures.append(bsc.YieldEngineV6(row[1]['Bal [USD]'], 0.005))
    if not m.isnan(row[1]['Comp [USD]']):
        futures[i].compounds = row[1]['Comp [USD]']
    if not m.isnan(row[1]['Wd [USD]']):
        futures[i].claimed = row[1]['Wd [USD]']

    futures[i].total_days = row[1]['1st Dep [d]']
    futures[i].update_rate_limiter()
    futures[i].deposits = futures[i].balance + futures[i].claimed - futures[i].compounds
    futures[i].pass_days(min(row[1]['Last Wd [d]'], row[1]['Last Comp [d]']))
    if m.isnan(futures[i].available):
        raise Exception('NaN found!')
    tvl += row[1]['Bal [USD]']
    i += 1

dune_data['futures_tvl'] = tvl
df = pd.Series(dune_data)
df.to_csv('chain_data/DuneData_{0}.csv'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M')))
dune_data['futures'] = futures

f1 = open('chain_data/DuneData_{0}.pkl'.format(dt.datetime.now().strftime('%Y-%m-%d %H:%M')), 'wb')
f2 = open('chain_data/DuneData.pkl', 'wb')
pickle.dump(dune_data, f1)
pickle.dump(dune_data, f2)
f1.close()
f2.close()

print()
