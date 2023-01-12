import bsc_classes as bsc
import pandas as pd

daily = bsc.BUSDFuturesEngine(10000)
weekly = bsc.BUSDFuturesEngine(10000)
monthly = bsc.BUSDFuturesEngine(10000)
one_hundred = bsc.BUSDFuturesEngine(10000)
no_claim = bsc.BUSDFuturesEngine(10000)
claimed = {'daily': [0],
           'weekly': [0],
           'monthly': [0],
           'one_hundred': [0],
           'wait_200d': [0]}
w_cnt = 0
m_cnt = 0
for i in range(365):
    daily.pass_days(1)
    claimed['daily'].append(daily.claim() + claimed['daily'][-1])
    weekly.pass_days(1)
    if w_cnt == 7:
        claimed['weekly'].append(weekly.claim() + claimed['weekly'][-1])
        w_cnt = 0
    else:
        claimed['weekly'].append(claimed['weekly'][-1])
        w_cnt += 1
    monthly.pass_days(1)
    if m_cnt == 30:
        claimed['monthly'].append(monthly.claim() + claimed['monthly'][-1])
        m_cnt = 0
    else:
        claimed['monthly'].append(claimed['monthly'][-1])
        m_cnt += 1
    one_hundred.pass_days(1)
    if i == 100:
        claimed['one_hundred'].append(one_hundred.claim() + claimed['one_hundred'][-1])
    elif i > 100:
        claimed['one_hundred'].append(one_hundred.claim() + claimed['one_hundred'][-1])
    else:
        claimed['one_hundred'].append(claimed['one_hundred'][-1])
    no_claim.pass_days(1)
    if i == 201:
        claimed['wait_200d'].append(no_claim.claim() + claimed['wait_200d'][-1])
    else:
        claimed['wait_200d'].append(claimed['wait_200d'][-1])

df = pd.DataFrame(claimed)
df.plot(title="BUSD Futures Payout vs Claim Schedule",
        xlabel='Days', ylabel='$USD', figsize=(14, 9), grid=True)

print("Done")
