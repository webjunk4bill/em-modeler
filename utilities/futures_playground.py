import bsc_classes as bsc
import pandas as pd
import pickle

funds_in = 0
group_rate = 0.34 / 365
engine = bsc.YieldEngineV8(funds_in, group_rate)
engine.balance = 168996
engine.deposits = 61080
website_claimed = 240346
engine.claimed = (engine.deposits + website_claimed - engine.balance) / 2  # to get this from the website values:
# Different from how I track
# web: Withdrawls = (Deposits + Claimed - TVL)/2, so Compounds = Claimed - Withdrawls
# Website shows combined claims and compounds.  A true claim is added to claimed and subtracted from balance
engine.compounds = website_claimed - engine.claimed
# engine.daily_payout = engine.balance * group_rate
data = {'claimed': [engine.claimed],
        'balance': [engine.balance],
        'deposits': [engine.deposits],
        'realized_gains': [engine.claimed / engine.deposits],
        'available': [0],
        'compounded': [engine.compounds]
        }
deposit = 200
count = 0
initial_count = 0
deposit_after_claim = False

schedule = {  # Start from T = 0, always deposit first, than claim, then will reset
    "initial": 0,
    "dep": 4,
    "claim": 8,
}
days = round(365 * 1)
cycles = round(days / len(schedule)) + 1
roll_claim = []
i = 1
find = True

for i in range(days):
    engine.pass_days(1, group_rate)
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
            if deposit_after_claim:
                engine.deposit(deposit)
            count = 0

    data['balance'].append(engine.balance)
    data['deposits'].append(engine.deposits)
    data['available'].append(engine.available)
    data['claimed'].append(engine.claimed)
    data['compounded'].append(engine.compounds)
    data['realized_gains'].append(engine.claimed / engine.deposits)

    if (engine.claimed / engine.deposits) > 1.98 and find:
        print(schedule, '=> gains:', (engine.claimed / engine.deposits), 'balance:', engine.balance,
              'days passed:', engine.total_days, 'daily:', engine.balance * engine.rate * engine.rate_limiter)
        find = False

# to_pickle = engine
# f = open('engine.pkl', 'wb')
# pickle.dump(to_pickle, f)
# f.close()

df = pd.DataFrame(data)
df.to_csv('temp.csv')
df.plot(title="{1} Investment BUSD Futures, {2} Deposit every {0} days, Claim monthly after 3 months"\
        .format(schedule['dep'], funds_in, deposit),
        xlabel='Days', ylabel='$USD', figsize=(14, 9), grid=True)

print("Done")
