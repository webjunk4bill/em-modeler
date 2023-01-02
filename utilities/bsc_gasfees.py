"""
This script reads a directory of bscscan exports and calculates the total gas fees paid
Useful for taxes if you haen't been keeping track during the year
"""

import pandas as pd
import os
import glob
import numpy as np
import re

path = ''  # Enter your path here
csv_files = glob.glob(os.path.join(path, "*.csv"))
fees = {}
for f in csv_files:
    wallet = re.search(r"-(.*)\.csv", f).group(1)
    df = pd.read_csv(f, index_col=False)
    df['fee_usd'] = np.multiply(df['TxnFee(BNB)'], df['Historical $Price/BNB'])
    fees[wallet] = np.sum(df['fee_usd'])

df_fee = pd.Series(fees)
total_fees = np.sum(df_fee)
df_fee['total'] = total_fees
df_fee.to_csv(os.path.join(path, "total_fees.csv"))
print(total_fees)
