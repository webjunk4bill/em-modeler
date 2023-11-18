import bsc_classes as bsc
import pandas as pd
import pickle

funds_in = 0
engine = bsc.YieldEngineV6(funds_in, 0.005)
engine.balance = 29178
engine.deposits = 8200
engine.claimed = 0
# Website shows combined claims and compounds.  A true claim is added to claimed and subtracted from balance
engine.compounds = (engine.deposits + engine.claimed - engine.balance) / 2
engine.daily_payout = engine.balance * 0.005
data = {'claimed': [0],
        'balance': [0],
        'deposits': [0],
        'realized_gains': [0],
        'available': [0],
        'compounded': [0]
        }
deposit = 200
count = 0
initial_count = 0

# schedule = ['dep', 'dep', 'dep', 'dep', 'claim', 'claim', 'claim']
schedule = {  # Start from T = 0, always deposit first, than claim, then will reset
    "initial": 0,
    "dep": 15,
    "claim": 25,
}
days = round(365 * 2)
cycles = round(days / len(schedule)) + 1
roll_claim = []
i = 1

for i in range(days):
    engine.pass_days(1)
    count += 1
    initial_count += 1
    if count == schedule["dep"]:
        if engine.claimed < engine.max_payout:
            engine.deposit(deposit)
        if initial_count < schedule["initial"]:
            count = 0
    elif count == schedule["claim"]:
        if initial_count < schedule["initial"]:
            count = 0
            pass
        else:
            engine.claim()
            count = 0

    data['balance'].append(engine.balance)
    data['deposits'].append(engine.deposits)
    data['available'].append(engine.available)
    data['claimed'].append(engine.claimed)
    data['compounded'].append(engine.compounds)
    data['realized_gains'].append(engine.claimed / engine.deposits)

to_pickle = engine
f = open('engine.pkl', 'wb')
# pickle.dump(to_pickle, f)
f.close()

df = pd.DataFrame(data)
df.to_csv('temp.csv')
df.plot(title="{1} Investment BUSD Futures, {2} Deposit every {0} days, Claim monthly after 3 months"\
        .format(schedule['dep'], funds_in, deposit),
        xlabel='Days', ylabel='$USD', figsize=(14, 9), grid=True)

print("Done")
