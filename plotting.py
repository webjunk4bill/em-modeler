import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import datetime as dt

plt.close("all")


def em_plot_time_old(em_df):
    fig, axes = plt.subplots(figsize=[14, 9], nrows=2, ncols=2)
    em_df[['$bertha/m', '$liquid_debt/m', '$total_debt/m']].plot(ax=axes[0, 0], ylabel='$USD (millions)',
                                                                 title='Treasury and Debt', sharex=True, sharey=False,
                                                                 grid=True, xlabel=None)
    em_df['$trunk'].plot(ax=axes[1, 0], ylabel='$USD', title='Trunk PEG', sharex=True, sharey=False, grid=True,
                         xlabel=None)
    em_df[['$bertha', 'funds_in']].plot(ax=axes[0, 1], ylabel='$USD', title='Bertha growth vs Incoming Funds',
                                        sharex=True, sharey=False, grid=True, xlabel=None)
    em_df['$elephant/m'].plot(ax=axes[1, 1], ylabel='$Elephant/m', title='Elephant USD Price per million',
                              sharex=True, sharey=False, grid=True, xlabel=None)
    plt.xlabel(None)
    plt.show()


def em_plot_funds(em_df):
    em_df['daily_debt_ratio'] = np.multiply((em_df['daily_debt_ratio']), 100)

    fig, axes = plt.subplots(figsize=[14, 9], nrows=2, ncols=2)
    em_df[['$bertha/m', '$liquid_debt/m', '$total_debt/m']].plot(ax=axes[0, 0], ylabel='$USD (millions)',
                                                                 title='Treasury and Debt', sharex=False, sharey=False,
                                                                 grid=True)
    em_df[['$trunk', '$elephant/m']].plot(ax=axes[1, 0], ylabel='$USD (ele/m)', title='Token Prices',
                                          sharex=False, sharey=False, grid=True, xlabel='$Funds Incoming (millions)')
    em_df['bertha/T'].plot(ax=axes[0, 1], ylabel='Trillion Tokens', title='Bertha Size (Trillion Tokens)',
                           sharex=False, sharey=False, grid=True)
    # em_df[['$bertha_payouts', '$daily_yield']].plot(ax=axes[1, 1], ylabel='$USD (millions)',
    #                                                title='Daily Platform Yields and Payouts',
    #                                               sharex=True, sharey=False, grid=True,
    #                                             xlabel='$Funds Incoming (millions)')
    em_df['daily_debt_ratio'].plot(ax=axes[1, 1], ylabel='% Serviceable Yields',
                                   title='% of Yield that can be Serviced Daily',
                                   sharex=False, sharey=False, grid=True,
                                   xlabel='$Funds Incoming (millions)')
    plt.show()


def em_plot_time(em_df):
    # em_df['daily_debt_ratio'] = np.multiply((em_df['daily_debt_ratio']), 100)  # for better plotting
    em_df['asset_debt_ratio'] = np.multiply(np.divide(em_df['$em_assets/m'], em_df['$liquid_debt/m']), 100)
    # --- Overview
    fig1, axes = plt.subplots(figsize=[14, 9], nrows=2, ncols=2)
    em_df[['$bertha/m',
           '$liquid_debt/m']].plot(ax=axes[0, 0], ylabel='$USD (millions)',
                                   title='Treasury Value and Liquid Debt', sharex=False, sharey=False, grid=True)
    em_df[['$funds_in/m', '$funds_out/m']].plot(ax=axes[1, 0], ylabel='$USD (millions)',
                                                title='Elephant Money total funds in/out', sharex=False, sharey=False,
                                                grid=True)
    em_df['$BNB'].plot(ax=axes[0, 1], ylabel='$USD', title="BNB Price",
                       sharex=False, sharey=False, grid=True)
    em_df[['$elephant/m', '$trunk', 'trumpet']].plot(ax=axes[1, 1], ylabel='$USD', title='Token Price',
                                                     sharex=False, sharey=False, grid=True)
    plt.tight_layout()
    plt.show()
    fig1.savefig('outputs/fig1_{0}.png'.format(dt.datetime.today()))

    # --- cashflow
    fig2, axes = plt.subplots(figsize=[14, 9], nrows=2, ncols=2)
    em_df[['$em_market_cap/m']].plot(ax=axes[0, 0], ylabel='$ millions',
                                     title='EM Market Cap', sharex=False, sharey=False, grid=True)
    em_df['$em_cashflow'].plot(ax=axes[0, 1], ylabel='$USD', title='Elephant Money Cashflow',
                               sharex=False, sharey=False, grid=True)
    em_df['%total_debt_ratio'].plot(ax=axes[1, 0], ylabel='%',
                                    title='EM Treasury to Total Debt Ratio', sharex=False, sharey=False, grid=True)
    em_df['%liquid_debt_ratio'].plot(ax=axes[1, 1], ylabel='% Serviceable Yields',
                                     title='EM Treasury to Liquid Debt Ratio',
                                     sharex=False, sharey=False, grid=True)
    plt.tight_layout()
    plt.show()
    fig2.savefig('outputs/fig2_{0}.png'.format(dt.datetime.today()))

    # debts
    fig3, axes = plt.subplots(figsize=[14, 9], nrows=2, ncols=3)
    em_df['futures_owed/m'].plot(ax=axes[0, 0], ylabel='$millions', title='Futures TVL',
                                 sharex=False, sharey=False, grid=True)
    em_df['stampede_owed/m'].plot(ax=axes[0, 1], ylabel='Trunk (millions)', title='Stampede TVL (Trunk)',
                                  sharex=False, sharey=False, grid=True)
    em_df['trunk_liquid_debt/m'].plot(ax=axes[0, 2], ylabel='Trunk (millions)', title='Trunk Liquid Debt',
                                      grid=True)
    em_df['$trunk'].plot(ax=axes[1, 1], ylabel='$USD', title='Trunk Price', grid=True)
    em_df['futures_liquid_debt/m'].plot(ax=axes[1, 0],
                                        title='Futures Liquid Debt', ylabel='$millions', grid=True)
    em_df['queue_wait'].plot(ax=axes[1, 2], ylabel='Days', title='Redemption Queue Payout Wait',
                             sharex=False, sharey=False, grid=True)
    plt.tight_layout()
    plt.show()
    fig3.savefig('outputs/fig3_{0}.png'.format(dt.datetime.today()))

    # --- Daily in/out detail
    fig4, axes = plt.subplots(figsize=[14, 9], nrows=2, ncols=3)
    em_df[['in_futures', 'out_futures']].plot(ax=axes[0, 0], ylabel='$USD', title='Daily Futures In/Out',
                                              sharex=False, sharey=False, grid=True)
    em_df[['in_nft', 'out_nft']].plot(ax=axes[0, 1], ylabel='$USD', title='Daily NFTs In/Out',
                                      sharex=False, sharey=False, grid=True)
    em_df[['in_trunk', 'out_trunk']].plot(ax=axes[0, 2], ylabel='$USD', title='Daily Trunk In/Out (support)',
                                          sharex=False, sharey=False, grid=True)
    em_df[['in_taxes']].plot(ax=axes[1, 1], ylabel='$USD', title='Daily Taxes Collected',
                             sharex=False, sharey=False, grid=True)
    em_df[['buy_volume', 'sell_volume']].plot(ax=axes[1, 0], ylabel='$USD', title='Daily Buy/Sell Volume',
                                              sharex=False, sharey=False, grid=True)
    em_df[['out_perf']].plot(ax=axes[1, 2], ylabel='$USD', title='Daily Performance Fund',
                             sharex=False, sharey=False, grid=True)

    plt.tight_layout()
    plt.show()
    fig4.savefig('outputs/fig4_{0}.png'.format(dt.datetime.today()))


'''
    fig4, axes = plt.subplots(figsize=[14, 9], nrows=2, ncols=2)
    em_df['bertha/T'].plot(ax=axes[0, 0], ylabel='Trillion Tokens', title='Bertha Size (Trillion Tokens)',
                           sharex=False, sharey=False, grid=True)
    em_df['daily_ele_growth'].plot(ax=axes[0, 1], ylabel='% Growth', title='Daily Elephant Purchase Growth',
                                   sharex=False, sharey=False, grid=True)
    em_df['daily_futures_growth'].plot(ax=axes[1, 0], ylabel='% Growth',
                                       title='Daily Futures Growth', grid=True)
    em_df['daily_total_growth'].plot(ax=axes[1, 1], ylabel='% Growth', title='Total Platform Daily Growth', grid=True)

    plt.show()
    fig4.savefig('outputs/fig4_{0}.png'.format(dt.datetime.today()))
'''
# df = pd.read_csv('outputs/output_time.csv', index_col=0, parse_dates=True)
# df = pd.read_csv('outputs/output_funds.csv', index_col=0)
# em_plot_time(df)
# em_plot_funds(df)
