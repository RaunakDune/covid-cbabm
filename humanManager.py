"""
   This is the class of human agent. it has basic main characters of all human agent types
   it will create object called human agent.

"""

from mesa.datacollection import DataCollector
from mesa import Model
from mesa.time import BaseScheduler
from mesa_geo.geoagent import GeoAgent, AgentCreator
from mesa_geo import GeoSpace
from shapely.geometry import Point
import pandas as pd
import numpy as np
import random
import csv

from DatabaseAdaptor.database_adaptor import loadHumanNeed, generateTasks
import DatabaseAdaptor.database as db



class HumanAgent(GeoAgent):
    """Person Agent."""

    def __init__(
        self,
        unique_id,
        model,
        shape,
        init_vaccinated,
        profession,
        profession_df,
        agent_type="susceptible",
        mobility_range = db.MOBILITY_RANGE,
        expose_rate = db.expose_rate, #positive rate = possitive test rate https://www.beckershospitalreview.com/public-health/states-ranked-by-covid-19-test-positivity-rates-july-14.html
        recovery_rate= db.recovery_rate,
        death_risk= db.death_risk,#5.1*10^(-6)
        init_infected= db.init_infected
    ):
        """
        Create a new person agent.
        :param unique_id:   Unique identifier for the agent
        :param model:       Model in which the agent runs
        :param shape:       Shape object for the agent
        :param agent_type:  Indicator if agent is infected ("infected", "exposed", "susceptible", "recovered" or "dead")
        :param mobility_range:  Range of distance to move in one step
        """
        super().__init__(unique_id, model, shape)
        # Agent parameters
        self.atype = agent_type
        self.mobility_range = db.MOBILITY_RANGE
        self.expose_rate = db.expose_rate
        self.recovery_rate = db.recovery_rate
        self.death_risk = db.death_risk
        self.vaccination_rate = db.vaccination_rate
        self.infection_risk = db.infection_risk
        self.profession = profession
        
        self.familyID = ""
        self.groupID = ""
        self.regionID = None
        self.markets = []
        self.houseAddress = []
        self.workAddress = []
        self.hospitals = []
        self.gender = 0 # 0 male, 1 female
        self.age = 0
        self.income = 0 # [1, 2, 3] = [rich, medium, poor]
        self.day_act = 0
        self.day_act1 = 0
        
        
        #task of agents
        self.current_task = []
        self.current_task_duration = 0
        self.current_task_timer = 0
        self.current_market = []
        self.current_place = None
        self.timeday = 0
        
        ##############
        self.protection_level = 0.0
        self.awareness_level = 0.0
        self.resistance_level = 0.0
        self.is_hospitalized  = False
     
        self.hospital_days = 0
        self.infection_level = 0.0 # 0.0: nothing, 0.2: early, 0.5: medium after 2 days, 1: heavy
        self.infected_days = 0
        self.clock = 0
        

        # Random choose if infected
        if self.random.random() < init_infected*1 and self.profession != "Healthcare":
            self.atype = "infected"
            self.infected_days = round(14 * self.random.random())
           # self.infection_level = 1
            self.model.counts["infected"] += 1  # Adjust initial counts
            self.model.counts["susceptible"] -= 1
        if self.random.random()<  init_vaccinated and self.atype != "infected":
            n_susceptible = self.model.pop_size * (1 - init_infected - init_vaccinated)
            if self.model.counts["susceptible"] >= n_susceptible:
                self.atype = "vaccinated"
                self.model.counts["vaccinated"] += 1
                self.model.counts["susceptible"] -= 1
        #get preference_df
        preference_df = getPreferences(self.profession)#generateTasks()
        self.tasks = preference_df
    
    def setExposeRate(self, expose_rate):
        self.expose_rate = expose_rate
        
    def setInfectionRate(self, infected_rate):
        self.infection_risk = infected_rate
        
    def setCurrentTask(self, currentTask):
        self.current_task = currentTask
    def setFamilyID(self, family_id):
        self.familyID = family_id
    
    def getFamilyID(self):
        return self.familyID
        
    def setHouseAddress(self, house_address):
        self.houseAddress = house_address
    
    def getHouseAddress(self):
        return self.houseAddress
        
    def setGroupID(self, group_id):
        self.groupID = group_id
        
    def getGroupID(self):
        return self.groupID
        
    def setWorkAddress(self, work_address):
        self.workAddress = work_address
        
    def getWorkAddress(self):
        return self.workAddress
    
    def setRegionID(self, regionID):
        self.regionID = regionID
    
    def distance_computing(self, x1,x2,y1,y2):
        return  ((((x2 - x1 )**2) + ((y2-y1)**2) )**0.5)
                                   
    def setServiceAddress(self, markets):
        house_distance = [ self.distance_computing(p[0], self.houseAddress[0], p[1], self.houseAddress[1])
                           for p in markets]
        work_distance = [ self.distance_computing(p[0], self.workAddress[0], p[1], self.workAddress[1])
                           for p in markets]
        totalDistance = []
        for i in range(len(work_distance)):
            total = work_distance[i] + house_distance[i]
            totalDistance.append(total)
    
        number = db.service_number
        count = 0
        newMarkets = []
        while count < number:
            minDis = float("inf")
            index = -1
            for i in range(len(totalDistance)):
                if minDis > totalDistance[i]:
                    minDis = totalDistance[i]
                    index = i
            newMarkets.append(markets[index])
            totalDistance[index] = float("inf")
            count += 1
            
    
        self.markets = newMarkets
        
    def getMarkets(self):
        return self.markets
    
    def setMobilityRange(self, mobility_range):
        self.mobility_range = mobility_range
        
    def setAge(self, age_person):
        self.age = age_person
        
    def setGender(self, gender):
        self.gender = gender
        
    def setIncome(self, income):
        self.income = income
        
    def setHospitals(self, hospitals):
        self.hospitals = hospitals
        
    def getProtectionLevel(self):
        return self.protection_level
     
    def setProtection(self):
        #infected, death, hospitalized
        gender_prob = db.gender_prob 
        income_prob = db.income_prob 
        age_prob = db.age_prob
        c1, c2, c3, c4, c5, c6, c7, c8, c9 = db.protection_parameters #1, 1, 0.5, 1, 1, 1, 1, 0.5, 0.5
                
                
        age_infected = 0.0
        age_hospitalized = 0.0
        age_death = 0.0
        income_infected = 0.0
        income_hospitalized = 0.0
        income_death = 0.0
        gender_infected = 0.0
        gender_hospitalized = 0.0
        gender_death = 0.0
        
        if self.age >= db.age1 : #55:
            age_infected = age_prob[100][0] #elderly easy to get covid
            age_death = age_prob[100][1]
            age_hospitalized = age_prob[100][2]
        elif self.age >= db.age2 : #35:
            age_infected = age_prob[54][0] 
            age_death = age_prob[54][1]
            age_hospitalized = age_prob[54][2]
        elif self.age >= db.age3 : #16:
            age_infected = age_prob[34][0] 
            age_death = age_prob[34][1]
            age_hospitalized = age_prob[34][2]
        else:
            age_infected = age_prob[15][0] 
            age_death = age_prob[15][1]
            age_hospitalized = age_prob[15][2]
            
        income_infected = income_prob[self.income][0]
        income_death = income_prob[self.income][1]
        income_hospitalized = income_prob[self.income][2]
        if self.gender == 0:
            gender_infected = gender_prob["male"][0]
            gender_death = gender_prob["male"][1]
            gender_hospitalized = gender_prob["male"][2]
        else:
            gender_infected = gender_prob["male"][0]
            gender_death = gender_prob["male"][1]
            gender_hospitalized = gender_prob["male"][2]
        
            

        self.protection_level = (1 - c1*age_infected)*(1 - c2*income_infected)*(1 - c3*gender_infected)
        self.resistance_level = (1- c4*age_death + c5*age_hospitalized)*(1- c6*income_death + c7*income_hospitalized)*(1 - c8*gender_death + c9*gender_hospitalized)
        
        if self.gender == 1:
            pregnant = random.random()*100
            if pregnant > db.pregnant_percent:# 90:
                if self.atype != "vaccinated": 
                    #self.protection_level = 0.0
                    self.resistance_level *= db.k1 #0.5 # pregnant women cannot have vaccine
        if self.profession == "Healthcare":
            self.protection_level *= db.k2 #10
        if self.atype == "infected":
            self.protection_level = 0
            if self.random.random() < self.death_risk :
                self.resistance_level = db.resistance_threshold # threshold
            else:
                self.resistance_level *= db.k3 #0.5
         #considering effect of policy and weather
        if self.profession != "Healthcare":
            self.protection_level *= (1 - db.k4 * (self.model.weather) + db.k5 *(self.model.policy))
            self.resistance_level *= (1 - db.k6 *(self.model.weather))
            
    def exposed(self):
        if self.atype == "vaccinated":
            print("healthy " + self.profession)
        elif self.atype == "susceptible":
            self.atype = "exposed"
            
        if self.profession == "Healthcare":
            if self.model.steps % (db.e1) == 0:
                if self.model.policy >= 0.5:
                    self.protection_level *= db.e2
                else:
                    self.protection_level *= db.e3
                    
            if self.protection_level >= 1:
                self.atype = "susceptible"
        else:
            if self.model.policy >= db.ep1:
                self.protection_level *= db.e4
            elif self.model.policy >= db.ep2:
                self.protection_level *= db.e5
            else:
                self.protection_level *= db.e6
        
       
    def vaccinated(self):
        if self.random.random() < self.model.vaccination_rate and self.atype != "infected":
            if self.random.random() < self.model.policy: # good healthcare policy means more people are vaccinated
                if self.gender == 1:
                    pregnant = random.random()*100
                    if pregnant < db.pregnant_percent:
                        self.atype = "vaccinated"
                      #  self.setProtection()
                else:
                    self.atype = "vaccinated"
                  #  self.setProtection()
                            
    #    else:
    #        self.atype = "susceptible"
        
    def infected(self):
        if self.atype == "infected":
            self.clock += db.step_hour
            if self.clock % db.day_length == 0:
                self.clock = 0
                self.infected_days += 1
                self.resistance_level *= db.i1 #0.9
               # self.hospital_days += 1
                if self.infected_days > 2:
                    self.infection_level = 0.5
                if self.infected_days > 5:
                    self.infection_level = 1
                if self.infected_days > 7:
                    if self.model.policy >= 0.5:
                        self.shape = Point( self.houseAddress[0], self.houseAddress[1])
                
            return

       # if self.expose_rate > 0.2:  #for other function
        #    if random.random()<0.5:
         #       return

 
        
        if self.atype == "exposed" or self.atype == "susceptible":
            self.protection_level = 0 # without vaccine, the infected people will not have protection from virus
            self.atype = "infected"
            
           
            
           # self.go_to_hospital()
 #       else:
 #           self.expose_rate *= 10 #with vaccine, the person potentially spreads virus to other people due to moving-> method later
 #           prob = np.random.rand()
  #          if prob > 0.95:
  #              self.atype = "infected"
 
    def go_to_hospital(self):
        #count the hospital days
        if self.atype == "hospitalized":
            self.clock += db.step_hour #2 # each step is 2 hours
            if self.clock % db.day_length == 0: #after 24 hours, 
                self.clock = 0  # the clock is reset to 0
                self.infected_days += 1 # increase number of infected days
                self.hospital_days += 1
                self.resistance_level *= db.h1 #0.99
              #  if self.infected_days > 2:
              #      self.infection_level = 0.5
              #  if self.infected_days > 5:
              #      self.infection_level = 1
            
        
        if self.age < 10 or self.age > 55:
            self.atype = "hospitalized"
            
        if 10 <= self.age <= 55:
            if self.infected_days > 3:
                h = self.model.counts["hospitalized"]
                p  = self.model.pop_size
                if (h/p) <= 0.05:
                    self.atype = "hospitalized"
            
        if self.income <= 2: #medium -1, rich-0,
            self.atype = "hospitalized"
            
        if self.is_hospitalized == False:
            h = self.model.counts["hospitalized"]
            p  = self.model.pop_size
            if (h/p) <= 0.05:
                self.is_hospitalized = True

                hospitalAddress = random.choice(self.hospitals)
                #check capacity of hospital later
                self.shape = Point(hospitalAddress[0], hospitalAddress[1])
            
    def recovered(self):
        if self.atype == "hospitalized":
            self.recovery_rate = self.model.recovery_rate
            self.clock += 2
            if self.clock % 12 == 0:
                self.clock = 0
                self.infected_days += 1
                self.hospital_days += 1
                self.resistance_level *= 0.9
                if self.infected_days > 2:
                    self.infection_level = 0.5
                if self.infected_days > 5:
                    self.infection_level = 1
                    
        if self.atype == "infected":
            self.recovery_rate = self.model.i_r_rate#infected to recovery rate
        #check the recovery
        if self.infected_days >= 14:
            
            if self.random.random() < self.recovery_rate:
                if self.day_act1 == 0:
                    if self.resistance_level > db.resistance_threshold:
                        self.atype = "recovered"
                        self.setProtection()
                        self.infection_level = 0
                        self.infected_days = 0
                    self.day_act1 = 1
                    
            

    def dead(self):
        if self.atype == "infected":
            self.death_risk = self.model.death_risk
        if self.atype == "hospitalized":
            self.death_risk = self.model.h_d_rate
        if self.atype != "recovered":
            if self.age >= 55 or self.age <= 12:
                if self.day_act1 == 0:
                    if self.random.random() < self.death_risk:
                        if self.resistance_level < db.resistance_threshold and self.infection_level == 1:
                            self.atype = "dead"  
                            self.resistance_level = 0
                            self.day_act1 = 1
            else:
                #if self.infected_days >= 7:
                
                if self.random.random() < self.death_risk:
                    if self.day_act1 == 0:
                        if self.resistance_level < db.resistance_threshold:
                            if self.infected_days > 6:
                                self.atype = "dead"  
                                self.resistance_level = 0
                        self.day_act1 = 1
                    
                    

    def move_point(self, dx, dy):
        """
        Move a point by creating a new one
        :param dx:  Distance to move in x-axis
        :param dy:  Distance to move in y-axis
        """
        return Point(self.shape.x + dx, self.shape.y + dy)

    def step(self):
        """Advance one step."""
        # If susceptible, check if exposed
        checkTime = 12 # the times that a human agebt will approach Covid virus
        if self.model.policy >= 0.7:
            checkTime = 24
        elif self.model.policy >= 0.5:
            checkTime = 12
        else:
            checkTime = 6
        if self.model.steps % checkTime == 0:
            self.day_act = 0
            self.day_act1 = 0
            
        if self.atype == "susceptible":

            neighbors = self.model.grid.get_neighbors_within_distance(
                            self, self.model.exposure_distance
                             )
            for neighbor in neighbors:
                if ( neighbor.atype == "infected"
                           and self.random.random() < self.expose_rate):
                    if self.day_act == 0:
                        self.exposed()
                        self.day_act = 1
                        break
             #       elif ( neighbor.atype == "hospitalized"):
               #         if self.random.random() < self.expose_rate:
               #             if self.model.policy < 0.5:
               #                 self.exposed()
               #                 break
              #      elif (neighbor.atype == "exposed" and self.random.random() < self.expose_rate): 
              #          p = neighbor.getProtectionLevel()
               #         if p < 0.5:
               ##             self.exposed()
               #             break
                            
            #vaccinated # check daily
            if self.model.steps % 12 == 0 and self.protection_level > 0.5:
                if self.random.random() < self.model.vaccination_rate:
                    if self.random.random() < self.model.policy: # good healthcare policy means more people are vaccinated if they follow
                        if self.gender == 1:
                            pregnant = random.random()*100
                            if pregnant < 90:
                                self.atype = "vaccinated"
                        else:
                             self.atype = "vaccinated"
                        if self.age < 10:
                             if self.atype == "vaccinated":
                                self.atype = "susceptible"
          
        # If exposed, check if it recovers or if it dies
        elif self.atype == "exposed":
            neighbors = self.model.grid.get_neighbors_within_distance(
                            self, self.model.exposure_distance
                             )
            for neighbor in neighbors:
                if ( neighbor.atype == "infected"
                           and self.random.random() < self.expose_rate):
                    if self.day_act == 0:
                        self.exposed()
                        self.day_act = 1

            if self.protection_level < db.protection_threshold:
                
                if self.random.random() < self.model.infection_risk:
                    if self.day_act1 == 0:
                        self.infected()
                        self.day_act1 = 1
            else:
                if self.day_act1 == 0 and self.protection_level > db.protection_threshold:
                    self.vaccinated()
                    self.day_act1 = 1
                    if self.age < 5: # young children cannot get vaccine
                        if self.atype == "vaccinated":
                            self.exposed()
          
        # If infected, check if it recovers or if it dies
        elif self.atype == "infected":
            self.infected()
            #hospitalize
            if self.day_act == 0:
               # hospital_choice = self.random.random()#random.choice([True, False])
                if self.random.random() < self.model.hosp_rate:
                    #if self.infected_days > 3:
                    self.go_to_hospital() 
                    self.day_act = 1
            self.recovered()
            self.dead()
        elif self.atype == "hospitalized":
            self.recovered()
            self.dead()
        elif self.atype == "recovered":
            neighbors = self.model.grid.get_neighbors_within_distance(
                            self, self.model.exposure_distance
                             )
            for neighbor in neighbors:
                if ( neighbor.atype == "infected"
                           and self.random.random() < self.expose_rate):
                    if self.day_act == 0:
                        self.exposed()
                        self.day_act = 1
                        break
             #       elif ( neighbor.atype == "hospitalized"):
               #         if self.random.random() < self.expose_rate:
               #             if self.model.policy < 0.5:
               #                 self.exposed()
               #                 break
              #      elif (neighbor.atype == "exposed" and self.random.random() < self.expose_rate): 
              #          p = neighbor.getProtectionLevel()
               #         if p < 0.5:
               ##             self.exposed()
               #             break
                            
            #vaccinated # check daily
            if self.model.steps % 12 == 0 and self.protection_level > 0.5:
                if self.random.random() < self.model.vaccination_rate:
                    if self.random.random() < self.model.policy: # good healthcare policy means more people are vaccinated if they follow
                        if self.gender == 1:
                            pregnant = random.random()*100
                            if pregnant < 90:
                                self.atype = "vaccinated"
                        else:
                             self.atype = "vaccinated"
                        if self.age < 10:
                             if self.atype == "vaccinated":
                                self.atype = "susceptible"

        # If not dead, not hospitalized, move
        if self.atype != "dead" and self.atype != "hospitalized" and (self.infected_days < 7):
            timer = self.model.steps % 12
            timer = timer*2
            #print(timer)
            currentTask = [self.tasks[0][1], int(self.tasks[0][2]), int(self.tasks[0][4]), float(self.tasks[0][-1])]
            for task in self.tasks:
                begin = int(task[2])
                end = random.choice([ begin + int(task[4]), begin + int(task[5])])
                if end >= 23:
                    end = 24
                if begin <= timer <= end:
                    currentTask = [task[1], begin, end, float(max(task[-2], task[-1]))] #task name, begin, end,probability of infection
                    break
           # if self.current_task == None
            if self.current_task == []:
                self.setCurrentTask(currentTask)
            # if a new task
          
            if ((currentTask[0] != self.current_task[0]) or (currentTask[1] > (self.current_task[1] + 2))):
                self.setCurrentTask(currentTask)
            else:
                currentTask = self.current_task
            #check if the task is at the begining: do the task
         
            
            if currentTask[1] == timer or currentTask[1] == (timer-1):
                self.current_task_duration = currentTask[2] - currentTask[1]
                self.current_task_timer = 1
                if currentTask[0] == "go home" or currentTask[0]== "stay home":
                    #self.shape = Point( self.houseAddress[0], self.houseAddress[1])
                    #check current location
                    current_location = [self.shape.x, self.shape.y]
                    
                    #check distance
                    distanceX = abs(self.houseAddress[0] - self.shape.x)
                    distanceY = abs(self.houseAddress[1] - self.shape.y)
                    distance = max(distanceX, distanceY)
                    if distance < self.mobility_range or self.current_task_duration <= 2:
                        self.shape = Point( self.houseAddress[0], self.houseAddress[1])
                    else:
                        neighbors = self.model.grid.get_intersecting_agents(self)
                        houses = [
                               neighbor for neighbor in neighbors if neighbor.atype == "house"
                                 ]
                                            
                    #check on paths to go
                    
                        paths = []
                        for house in houses:
                            place = [house.shape.x, house.shape.y]
                            if (current_location[0] < place[0] < self.houseAddress[0]) or (current_location[0] > place[0] > self.houseAddress[0]):
                                if (current_location[1] < place[1] < self.houseAddress[1]) or (current_location[1] > place[1] > self.houseAddress[1]):
                                        paths.append(place)
                        destination = [1/2*(self.shape.x + self.houseAddress[0]),
                                       1/2*(self.shape.y + self.houseAddress[1])]
                        minDistance = distance
                        chosenMidPoint = destination
                        for p in paths:
                            d = self.distance_computing( p[0], destination[0],p[1],destination[2])
                            if d < minDistance:
                                minDistance = d
                                chosenMidPoint = p
                        #move
                        self.shape = Point( chosenMidPoint[0], chosenMidPoint[1])
                        
                        
                                       
                elif (currentTask[0] == "go to work" 
                    or currentTask[0] == "go to school" 
                    or currentTask[0] == "go to hospital"):
                    #self.shape = Point( self.workAddress[0], self.workAddress[1])
                   
                    #check current location
                    current_location = [self.shape.x, self.shape.y]
                    
                    #check distance
                    distanceX = abs(self.workAddress[0] - self.shape.x)
                    distanceY = abs(self.workAddress[1] - self.shape.y)
                    distance = max(distanceX, distanceY)
                    if distance < self.mobility_range or self.current_task_duration <= 2:
                        self.shape = Point( self.workAddress[0], self.workAddress[1])
                    else:
                        self.moveMidPoint(current_location, self.workAddress, distance)
                        
                elif (currentTask[0] == "meeting" or currentTask[0] == "dating" or currentTask[0] == "go to market"):
                    marketAddress = random.choice(self.markets)
                    self.shape = Point( marketAddress[0], marketAddress[1])
                    #check current location
                    current_location = [self.shape.x, self.shape.y]
                    
                    #check distance
                    distanceX = abs(marketAddress[0] - self.shape.x)
                    distanceY = abs(marketAddress[1] - self.shape.y)
                    distance = max(distanceX, distanceY)
                    if distance < self.mobility_range or self.current_task_duration <= 2:
                        self.shape = Point(marketAddress[0], marketAddress[1])
                    else:
                        self.moveMidPoint(current_location, marketAddress , distance)
                        self.current_market = marketAddress
            else:
                if  self.current_task_duration > 2 and self.current_task_timer == 1:
                    if currentTask[0] == "go home" or currentTask[0]== "stay home":
                        self.shape = Point( self.houseAddress[0], self.houseAddress[1])
                    elif (currentTask[0] == "go to work" 
                        or currentTask[0] == "go to school" 
                         or currentTask[0] == "go to hospital"):
                        self.shape = Point( self.workAddress[0], self.workAddress[1])
                    elif (currentTask[0] == "meeting" or currentTask[0] == "dating" or currentTask[0] == "go to market"):
                        if self.current_market != []:
                           # marketAddress = random.choice(self.markets)
                            self.shape = Point( self.current_market[0], self.current_market[1])
                        #reset self.currentMarket to []
                            self.current_market = []
                    #reset  current_task_timer to 0 to avoid errors
                    self.current_task_timer = 0
                    
            ##################        
                
        #    move_x = self.random.randint(-self.mobility_range, self.mobility_range)
        #    move_y = self.random.randint(-self.mobility_range, self.mobility_range)
        #    self.shape = self.move_point(move_x, move_y)  # Reassign shape

        self.model.counts[self.atype] += 1  # Count agent type
        
        
    def moveMidPoint(self, current_location, destination, distance):
        neighbors = self.model.grid.get_intersecting_agents(self)
        houses = [neighbor for neighbor in neighbors if neighbor.atype == "house"]
                                            
        #check on paths to go
                    
        paths = []
        for house in houses:
            place = [house.shape.x, house.shape.y]
            if (current_location[0] < place[0] < destination[0]) or (current_location[0] > place[0] > destination[0]):
                if (current_location[1] < place[1] < destination[1]) or (current_location[1] > place[1] > destination[1]):
                    paths.append(place)
        des = [1/2*(self.shape.x + destination[0]),
                                       1/2*(self.shape.y + destination[1])]
        minDistance = distance
        chosenMidPoint = des
        for p in paths:
            d = self.distance_computing( p[0], des[0],p[1],des[2])
            if d < minDistance:
                minDistance = d
                chosenMidPoint = p
                        #move
        self.shape = Point( chosenMidPoint[0], chosenMidPoint[1])

    def __repr__(self):
        return "Person " + str(self.unique_id)
    

def getPreferences(string):
    people = []
    urls = ['DatabaseAdaptor/preferences1.csv',
             'DatabaseAdaptor/preferences2.csv',
             'DatabaseAdaptor/preferences3.csv',
             'DatabaseAdaptor/preferences4.csv',
             'DatabaseAdaptor/preferences5.csv']
    url = random.choice(urls)
    with open(url) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0

        for row in csv_reader:
            if line_count == 0:
                pass #skips the column headers
                line_count += 1
            else: 
                if row[6] == string:
                    people.append(row)
   # preference_df = pd.read_csv('DatabaseAdaptor/preferences.csv')#generateTasks()
   # agentPreference = preference_df[preference_df["profession"] == string]
   # records = agentPreference.to_records(index=False)
 #   result = list(records)
  #  print(result)
  #  return result
   # self.preference_df = preference_df[preference_df["profession"] == self.profession]
    return people #agentPreference