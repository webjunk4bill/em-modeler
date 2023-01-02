"""
This script reads a directory of bscscan exports and calculates the total gas fees paid
Useful for taxes if you haen't been keeping track during the year
"""

import pandas as pd
import os
import glob
import numpy as np
import re

path = '  '  # Enter your path here
csv_files = glob.glob(os.path.join(path, "export*.csv"))
fees = {}
for f in csv_files:
    wallet = re.search(r"-(.*)\.csv", f).group(1)
    df = pd.read_csv(f, index_col=False)
    df['fee_usd'] = np.multiply(df['TxnFee(BNB)'], df['Historical $Price/BNB'])
    fees[wallet] = {'USD': np.sum(df['fee_usd']), 'BNB': np.sum(df['TxnFee(BNB)'])}

df_fee = pd.DataFrame(fees)
total_fees = np.sum(df_fee.iloc[0])
total_bnb = np.sum(df_fee.iloc[1])
df_fee['total'] = [total_fees, total_bnb]
df_fee.T.to_csv(os.path.join(path, "total_fees.csv"))
print(total_fees)
