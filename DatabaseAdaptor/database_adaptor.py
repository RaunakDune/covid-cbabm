import pandas as pd
from random import randrange
import random
from random import choice
import math
import time

def connectDb():

    pass

def choosePlace(n, list_val):
    # declaring the list 
    # new_list is a set of list1  
    res_list = list_val 
    if n > 0:
        for i in range(0,n-1):
            res_list.remove(max(res_list, key = lambda i : i[1]))
    
    result = max(res_list, key = lambda i : i[1])
    return result
    
def loadPreferences():
    database = pd.read_csv('database/Preferences.csv')
    return database

def loadThresholds():
    database = pd.read_csv('database/Thresholds.csv')
    return database


def loadProfessions():

    database = pd.read_csv('database/Professions.csv')
    return database

def loadAges():

    database = pd.read_csv('database/Ages.csv')
    return database

def loadIncomes():

    database = pd.read_csv('database/Genders.csv')
    return database

def loadIncomes():

    database = pd.read_csv('database/Incomes.csv')
    return database
    
def loadTasks():

    database = pd.read_csv('database/Tasks.csv')

    return database



def loadActions():

    database = pd.read_csv('database/Actions.csv')
    return database

def loadHumanNeed():
    student = pd.read_excel('database/human/student.xlsx')
    employed = pd.read_excel('database/human/employed.xlsx')
    unemployed = pd.read_excel('database/human/unemployed.xlsx')
    healthcare = pd.read_excel('database/human/healthcare.xlsx')
    return employed, unemployed, student, healthcare



def generateTasks():

    df = []
    employed, unemployed, student, healthcare = loadHumanNeed()
    agentType = ["Student", "Employed", "Unemployed", "Healthcare"]
    headers = ["task", "min_start_time" , "max_start_time" , "min_duration" , "max_duration" , "profession", "min_prob" , "max_prob" ]
    for p in agentType:
        profession = p
        if p == "Student":
            data = student
        if p == "Employed":
            data = employed
        if p == "Unemployed":
            data = unemployed
        if p == "Healthcare":
            data = healthcare

        
        firstRow = data.iloc[0]
        currentP = firstRow["start"]
   
        nextP = firstRow["start"]
        duration = 0
        currentTime = randrange(12)

        timeCount = 0
        row = firstRow
        prob = 0.5
        nextTask = ""
        while timeCount < 24:
            min_start_time = currentTime
            max_start_time = round (random.choice([currentTime,currentTime + 2*random.random()]))
            currentP = nextP
            if currentP == "home":
                taskName = "stay home"
                minProb = prob
                maxProb = random.random()
                if maxProb < minProb:
                    maxProb = minProb
                if prob > 0.4:
                    duration = 4 + round(4 * random.random())
                else:
                    duration = 1 + round(2 * random.random())
                maxduration = random.choice([duration, duration+1])
            
            elif currentP == "work":
                taskName = "work"
                minProb = prob
                maxProb = random.random()
                if maxProb < minProb:
                    maxProb = minProb
                if prob > 0.4:
                    duration = 4 + round(4 * random.random())
                else:
                    duration = 1 + round( random.random())
                maxduration = random.choice([duration, duration+1])
              
            elif currentP == "hospital":
                taskName = "treat patients"
                minProb = prob
                maxProb = random.random()
                if maxProb < minProb:
                    maxProb = minProb
                if prob > 0.4:
                    duration = 6 + round(2 * random.random())
                else:
                    duration = 2 + round(2 * random.random())
                maxduration = random.choice([duration, duration+1])
               
            elif currentP == "market":
                minProb = prob
                maxProb = random.random()
                if maxProb < minProb:
                    maxProb = minProb
                if prob > 0.4:
                    duration = 2 + round(2 * random.random())
                    taskName = random.choice([ "meeting","attending event","relaxation","dating"])
                else:
                    duration = 1 + round(random.random())
                    taskName = random.choice(["shopping", "eating"])
                maxduration = random.choice([duration, duration+1])
            
            elif currentP == "school":
                minProb = prob
                maxProb = random()
                if maxProb < minProb:
                    maxProb = minProb
                if prob > 0.4:
                    taskName = random.choice(["class time", "researching" ])
                    duration = 3 + round(5 * random.random())
                else:
                    taskName = random.choice(["groupwork", "homework" ])
                    duration = 2 + round(2 * random.random())
                maxduration = random.choice([duration, duration+1])
            

            #update currentTime and timeCount, adjust duration
            if (timeCount + duration) >= 22:
                duration = 24 - timeCount
            currentTime = currentTime + duration
            timeCount = timeCount + duration
      
            df.append([taskName, min_start_time, max_start_time, duration, maxduration, p, minProb, maxProb])
            if currentTime >= 24:
                currentTime -= 24 # set currentime if it is above 24 hour clock
              #if there is not enough time left, stay in the same place
            if timeCount > 23:
                continue
            #next activity  
            row = data.loc[data['start'] == currentP]
           # currentP = row["start"].value
            chooseList = []
            for place in ["home", "work", "hospital", "market", "school"]:
                if float(row[place]) > 0:
                    chooseList.append((place,float(row[place])))
            selectNumber = 0
            nextProb = prob
            while (nextP == currentP) and (nextProb == prob):
                #n1 = math.floor(random.random()* len(chooseList))
                #selectNumber = random.choice([0, n1])
                place = choosePlace(selectNumber, chooseList)
                nextP = place[0]
                nextProb = place[1]
                selectNumber += 1
            prob = nextProb
            if nextP == currentP:
                currentP = nextP
                continue
                
            if nextP == "home":
                nextTask = "go home"
            elif nextP == "work":
                nextTask = "go to work"
            elif nextP == "hospital":
                nextTask = "go to Hospital"
            elif nextP == "school":
                nextTask = "go to school"
            else:
                nextTask = "go to market"
            minProb = random.random()* prob
            maxProb = random.random()* prob
            if maxProb < minProb:
                maxProb = minProb
            duration = round (1 + random.random())
            min_start_time = currentTime
            max_start_time = round( random.choice([currentTime,currentTime + random.random()]))
            #update currentTime and timeCount, adjust duration
            if (timeCount + duration) >= 24:
                duration = 24 - timeCount
            currentTime = currentTime + duration
            timeCount = timeCount + duration
            df.append([nextTask, min_start_time, max_start_time, duration, duration, p, minProb, maxProb])

            if currentTime >= 24:
                currentTime -= 24 # set currentime if it is above 24 hour clock    
           # time.sleep(5)

    database = pd.DataFrame(df, columns=[headers])  
    database.to_csv("preferences.csv")

    return database


