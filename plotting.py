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
    em_df['daily_debt_ratio'] = np.multiply((em_df['daily_debt_ratio']), 100)  # for better plotting
    em_df['asset_debt_ratio'] = np.multiply(np.divide(em_df['$em_assets/m'], em_df['$liquid_debt/m']), 100)

    fig1, axes = plt.subplots(figsize=[14, 9], nrows=2, ncols=2)
    em_df[['$bertha/m',
           '$liquid_debt/m',
           '$funds_in/m']].plot(ax=axes[0, 0], ylabel='$USD (millions)',
                                title='Treasury, Debt, and Incoming Funds', sharex=False, sharey=False, grid=True)
    em_df[['$bertha_payouts/m',
           '$daily_yield/m']].plot(ax=axes[1, 1], ylabel='$USD (millions)',
                                   title='Earned Yield and Bertha Payouts', sharex=False, sharey=False, grid=True)
    em_df[['$trunk', '$elephant/m']].plot(ax=axes[0, 1], ylabel='$USD (ele/m)', title='Token Prices',
                                          sharex=False, sharey=False, grid=True)
    em_df[['$funds_in/m', '$redemptions_paid/m']].plot(ax=axes[1, 0], ylabel='USD (millions)',
                                                       title='In and Outgoing Funds',
                                                       sharex=False, sharey=False, grid=True)
    plt.show()
    fig1.savefig('outputs/fig1_{0}.png'.format(dt.datetime.today()))

    fig2, axes = plt.subplots(figsize=[14, 9], nrows=2, ncols=2)
    em_df[['$em_assets/m',
           '$liquid_debt/m']].plot(ax=axes[0, 0], ylabel='$USD (millions)',
                                   title='EM Assets and Current Liabilities', sharex=False, sharey=False, grid=True)
    em_df['$em_liquidity'].plot(ax=axes[0, 1], ylabel='$USD', title='Elephant Money Liquidity (income v yield)',
                                sharex=False, sharey=False, grid=True)
    em_df['asset_debt_ratio'].plot(ax=axes[1, 0], ylabel='% Assets/Debts',
                                   title='EM Total Assets to Debt', sharex=False, sharey=False, grid=True)
    em_df['daily_debt_ratio'].plot(ax=axes[1, 1], ylabel='% Serviceable Yields',
                                   title='% of Yield Covered by Bertha APRs',
                                   sharex=False, sharey=False, grid=True)
    plt.show()
    fig2.savefig('outputs/fig2_{0}.png'.format(dt.datetime.today()))

    fig3, axes = plt.subplots(figsize=[14, 9], nrows=2, ncols=3)
    em_df['trunk_treasury'].plot(ax=axes[1, 2], ylabel='Treasury (Trunk)', title='Trunk Treasury Size',
                                 sharex=False, sharey=False, grid=True)
    em_df['redemption_queue'].plot(ax=axes[0, 1], ylabel='Redemption Queue USD', title='Redemption Queue Size',
                                   sharex=False, sharey=False, grid=True)
    em_df['staking_balance/m'].plot(ax=axes[1, 0], ylabel='Trunk (millions)', title='Staking Balance')
    em_df['trunk_wallets/m'].plot(ax=axes[1, 1], ylabel='Trunk (millions)', title='Trunk Held in Wallets')
    em_df['farm_tvl/m'].plot(ax=axes[0, 2], title='EM Farms TVL', ylabel='Trunk (millions)')
    em_df['bertha/T'].plot(ax=axes[0, 0], ylabel='Trillion Tokens', title='Bertha Size (Trillion Tokens)',
                           sharex=False, sharey=False, grid=True)
    plt.show()
    fig3.savefig('outputs/fig3_{0}.png'.format(dt.datetime.today()))


# df = pd.read_csv('outputs/output_time.csv', index_col=0, parse_dates=True)
# df = pd.read_csv('outputs/output_funds.csv', index_col=0)
# em_plot_time(df)
# em_plot_funds(df)
