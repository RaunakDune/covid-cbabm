import pandas as pd
from random import randrange
import random
from random import choice
import math
import time

from database_adaptor import loadHumanNeed, generateTasks

df = generateTasks()
print(df)