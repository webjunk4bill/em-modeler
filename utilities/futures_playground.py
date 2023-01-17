import bsc_classes as bsc
import pandas as pd
import pickle

funds_in = 25000
engine = bsc.BUSDFuturesEngine(funds_in, 0.005)
data = {'claimed': [0],
        'balance': [0],
        'deposits': [0],
        'realized_gains': [0],
        'available': [0],
        'compounded': [0]
        }
c_cnt = 0
deposit = 200
rolled = 0
count = 0
interval = 21
first_claim = 300
# schedule = ['dep', 'dep', 'dep', 'dep', 'claim', 'claim', 'claim']
schedule = ['dep', 'dep', 'claim']
days = 365 * 4
cycles = round(days / len(schedule)) + 1
roll_claim = []
i = 1
while i <= cycles:  # Create full schedule for rolls and claims
    for j in schedule:
        roll_claim.append(j)
    i += 1

for i in range(days):
    engine.pass_days(1)
    if count == interval:
        action = roll_claim.pop(0)
        if c_cnt < first_claim:
            action = 'dep'
            c_cnt += 1
        if action == 'dep':
            if engine.claimed < engine.max_payout:
                engine.deposit(deposit)
            count = 0
        elif action == 'claim':
            engine.claim()
            first_claim = interval
            count = 0
            c_cnt = 0
    else:
        c_cnt += 1
        count += 1
    data['balance'].append(engine.balance)
    data['deposits'].append(engine.deposits)
    data['available'].append(engine.available)
    data['claimed'].append(engine.claimed)
    data['compounded'].append(engine.compounds)
    data['realized_gains'].append(engine.claimed / engine.deposits * 100000)

to_pickle = engine
f = open('engine.pkl', 'wb')
# pickle.dump(to_pickle, f)
f.close()

df = pd.DataFrame(data)
df.to_csv('temp.csv')
df.plot(title="{1} Investment BUSD Futures, {2} Deposit every {0} days, Claim monthly after 3 months"\
        .format(interval, funds_in, deposit),
        xlabel='Days', ylabel='$USD', figsize=(14, 9), grid=True)

print("Done")
