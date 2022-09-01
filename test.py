import pandas as pd
import numpy as np
import random


def getPreferences(string):
    preference_df = pd.read_csv('DatabaseAdaptor/preferences.csv')#generateTasks()
    agentPreference = preference_df[preference_df["profession"] == string]
    records = agentPreference.to_records(index=False)
    result = list(records)
    print(result)
    return result


#df = getPreferences("Student")
#print(df)

import DatabaseAdaptor.database as db
income = db.income
print (income)