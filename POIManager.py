import numpy as np
import random
import time

from mesa.datacollection import DataCollector
from mesa import Model
from mesa.time import BaseScheduler
from mesa_geo.geoagent import GeoAgent, AgentCreator
from mesa_geo import GeoSpace
from shapely.geometry import Point
import pandas as pd
import numpy as np


# Import PySwarms
#import pyswarms as ps

MAX_CAPACITY = 100
class POIAgent(GeoAgent):
    def __init__(self, unique_id, model, shape, 
init_infected, init_vaccinated, capacity=100, atype="home", hotspot_threshold=1):
        self.id = unique_id
        self.capacity = capacity
       # self.type = atype
        self.humans = []
        self.n_humans = 0
        self.infection_rate =  init_infected#0.0
        self.vaccinated_rate = init_vaccinated#00
        self.expose_rate = 0.0
        self.death_rate = 0.0
        self.workingHumans = 0
        self.capacity = MAX_CAPACITY
        self.need_Humans = False
        super().__init__(unique_id, model, shape)
        self.atype = atype
        self.regionID = None
   #     self.hotspot_threshold = (
     #       hotspot_threshold
     #   )  # When a neighborhood is considered a hot-spot
    #    self.color_hotspot()


            
    def setInfectionRate(self, infectRate):
        self.infection_rate = infectRate
    def getInfectionRate(self):
        return self.infection_rate
    def setExposeRate(self, exposeRate):
        self.expose_rate = exposeRate
    def getExposeRate(self):
        return self.expose_rate
    def setCapacity(self, number):
        self.capacity = number
    def getCapacity(self):
        return self.capacity
    def setDeathRate(self, deathRate):
        self.death_rate = deathRate
    def getDeathRate(self):
        return self.death_rate
    def setId(self, id):
        self.id = id
    def getId(self):
        return self.id
    def getType(self):
        return self.type
    def setRegionID(self, regionID):
        self.regionID = regionID
        
    def getRegionID(self):
        return self.regionID 
    def addHuman(self, humanId):
        if len(self.humans) < self.capacity:
            self.humans.append(humanId) #the list has only Id of human agent, not human class
            self.n_humans += 1

    def removeHuman(self, humanId):
        """
        Remove a human agent out of the list
        input: humanId:
        output: bool
        """
        if self.n_humans > 0:
            if humanId in self.humans:
                self.humans.remove(humanId)
                self.n_humans -= 1
                return True
            else:
                return False
        return False

    def getHumanList(self):
        return self.humans

    def needHumans(self):
        """"
        Check whether the workforce needs recruiting
        output: true: need more humans agent
                false: no need more humans agent
        """
        if self.type != "home":
            if (self.workingHumans / self.capacity) < 0.7:
                self.need_Humans = True
            else:
                self.need_Humans = False

        return self.need_Humans
            

    def calRates(self, n_humans, n_susceptible, n_exposed, n_infected, n_hospitalized, n_recovered, n_death, n_vaccinated):
        """
        input:
             listAgents: the list of HumanAgents which is made in Infrasructure Manager by using self.humans
        output:
              susceptible rate of a facility
              expose rate of a facility
              infection rate of a facility
              hospitalized rate of a facility
              recovered rate of a facility
              death rate of a facility
        
        """

        susceptRate = n_susceptible / n_humans
        exposedRate = (n_exposed + n_infected + n_hospitalized + n_recovered + n_death) / n_humans
        infectedRate = (n_infected + n_hospitalized + n_recovered + n_death) / n_humans
        hospitalizedRate = n_hospitalized / n_humans
        if (( n_recovered + n_infected + n_hospitalized + n_death ) > 0):
            recoveredRate = n_recovered / ( n_recovered + n_infected + n_hospitalized + n_death )
            deathRate = n_death / ( n_recovered + n_infected + n_hospitalized + n_death )
        
        #update rate
        self.workingHumans = n_susceptible + n_exposed + n_recovered + n_vaccinated
        self.setExposeRate(exposedRate)
        self.setDeathRate(deathRate)
        self.setInfectionRate(infectedRate)
       # return susceptRate, exposedRate, infectedRate, hospitalizedRate, recoveredRate, deathRate
    
    def step(self):
        
        if self.atype != "home":
            neighbors = self.model.grid.get_intersecting_agents(self)
            humans = [human for human in neighbors if human.atype == "susceptible" or human.atype=="infected"
                      or human.atype == "exposed" or human.atype== "hospitalized" or human.atype=="dead" 
                      or human.atype=="vaccinated"]
            poi_humans = [
                 human for human in humans if human.groupID == self.id
             ]
            if len(poi_humans) > 0:
                infected_humans = [ human for human in poi_humans if human.atype == "infected"]
                susceptible_humans = [ human for human in poi_humans if human.atype == "susceptible"]
                exposed_humans = [ human for human in poi_humans if human.atype == "exposed"]
                hospitalized_humans = [ human for human in poi_humans if human.atype == "hospitalized"]
                dead_humans = [ human for human in poi_humans if human.atype == "dead"]
                recovered_humans = [ human for human in poi_humans if human.atype == "recovered"]
                vaccinated_humans = [ human for human in poi_humans if human.atype == "vaccinated"]
                n_susceptible = len(susceptible_humans)
                n_exposed = len(exposed_humans)
                n_infected = len(infected_humans)
                n_hospitalized = len(hospitalized_humans)
                n_recovered = len(recovered_humans)
                n_death = len(dead_humans)   
                n_vaccinated =  len(vaccinated_humans)
                self.calRates(len(poi_humans), n_susceptible, 
                              n_exposed, n_infected, n_hospitalized, 
                              n_recovered, n_death, n_vaccinated)
                if self.model.steps % (12) == 0:
                    if len(infected_humans) > 0:
                        if self.expose_rate > self.model.expose_rate:
                            for human in poi_humans:
                        #        human.setExposeRate(self.expose_rate)
                                human.setInfectionRate(self.infection_rate)
                        else:
                            for human in poi_humans:
                          #      human.setExposeRate(self.model.expose_rate * 1.5)
                                human.setInfectionRate(self.model.infection_risk*1.5)
                if self.model.steps % (12*7) == 0:
                    for human in poi_humans:
                       # human.setExposeRate(self.model.expose_rate)
                        human.setInfectionRate(self.model.infection_risk)
              #  if 0 < self.infection_rate < self.model.infection_risk:
              #      for human in poi_humans:
              #          human.setInfectionRate(self.infection_rate)
              #  else:
              #      for human in poi_humans:
              #          human.setInfectionRate(self.model.infection_risk)
                    
  
                
        


        



class POIManager(GeoAgent):
    """Neighbourhood agent. Changes color according to number of infected inside it."""

    def __init__(self, unique_id, model, shape, agent_type ="safe", hotspot_threshold=2):
        """
        Create a new Neighbourhood agent.
        :param unique_id:   Unique identifier for the agent
        :param model:       Model in which the agent runs
        :param shape:       Shape object for the agent
        :param agent_type:  Indicator if agent is infected ("infected", "susceptible", "recovered" or "dead")
        :param hotspot_threshold:   Number of infected agents in region to be considered a hot-spot
        """
        super().__init__(unique_id, model, shape)
        self.atype = agent_type
        self.local_infected_rate = 0.0
        self.local_exposed_rate = 0.0
        self.local_dead_rate = 0.0
        self.hotspot_threshold = (
            hotspot_threshold
        )  # When a neighborhood is considered a hot-spot
        self.color_hotspot()

    def step(self):
        """Advance agent one step."""
        # daily update color
        if self.model.steps % 12 == 0:
            self.color_hotspot()
        
        self.model.counts[self.atype] += 1  # Count agent type
        # update local rate every 5 days- each step = 2 hours
       
        if self.model.steps % 60 == 0:
            self.calLocalRates()
            self.setHouseRates()
            
            

    def color_hotspot(self):
        # Decide if this region agent is a hot-spot (if more than threshold person agents are infected)
        neighbors = self.model.grid.get_intersecting_agents(self)
        infected_neighbors = [
            neighbor for neighbor in neighbors if neighbor.atype == "infected"
        ]
        if len(infected_neighbors) >= self.hotspot_threshold: #  and (self.local_infected_rate + self.local_dead_rate) >= 0.01:
            self.atype = "hotspot"
        else:
            self.atype = "safe"
            
    def calLocalRates(self):
        #calculate and update localrate
        neighbors = self.model.grid.get_intersecting_agents(self)
        infected_neighbors = [
            neighbor for neighbor in neighbors if neighbor.atype == "infected"
        ]
        exposed_neighbors = [
            neighbor for neighbor in neighbors if neighbor.atype == "exposed"
        ]
        dead_neighbors = [
            neighbor for neighbor in neighbors if neighbor.atype == "dead"
        ]
        
        
        pop_size = self.model.pop_size
        self.local_dead_rate = len(dead_neighbors) / pop_size
        self.local_infected_rate = len(infected_neighbors) / pop_size
        self.local_exposed_rate = len(exposed_neighbors) / pop_size
        
    def setHouseRates(self):
        neighbors = self.model.grid.get_intersecting_agents(self)
        houses = [house for house in neighbors if house.atype == "home"]
        for house in houses:
            house.setExposeRate(self.local_exposed_rate)
            house.setDeathRate(self.local_dead_rate)
            house.setInfectionRate(self.local_infected_rate)
                
        
                
 
    
        
        
    def __repr__(self):
        return "Neighborhood " + str(self.unique_id)



    