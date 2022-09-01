from mesa.datacollection import DataCollector
from mesa import Model
from mesa.time import BaseScheduler
from mesa_geo.geoagent import GeoAgent, AgentCreator
from mesa_geo import GeoSpace
from shapely.geometry import Point
from POIManager import POIAgent, POIManager
from humanManager import HumanAgent #, HumanManager
import DatabaseAdaptor.database as db #the database

import pandas as pd
import numpy as np
import random
import time

#MIN_DEATH = 0.00001
#MIN_INFECT = 0.00001
#HOSP_RATE = 0.000408

class SimulatorManager(Model):
    """Model class for a simplistic infection model."""

    # Geographical parameters for desired map
    MAP_COORDS = db.MAP_COORDS # [40.730610, -73.935242]#[43.741667, -79.373333]  # Toronto   #change to houston city later [29.749907, -95.358421]
    geojson_regions = db.geojson_name #"nyu-2451-34561-geojson.json"#"city_of_houston.json"#"houston.geojson"#"TorontoNeighbourhoods.geojson" # change  to houston city geojson file later
    unique_id = db.unique_id #"id" #"OBJECTID"#"HOODNUM"  # "BG_ID"

    def __init__(self, pop_size = db.pop_size, 
                 poi_size = db.poi_size, 
                 init_infected = db.init_infected, 
                 init_vaccinated = db.init_vaccinated, 
                 exposure_distance= db.exposure_distance, 
                 n_days = db.n_days, 
                 infection_risk= 0.0015, vaccination_rate=0.098, death_risk = 0.0000015, weather=1, policy=2): ##https://covidactnow.org/us/new_york-ny/?s=31661989
        #https://covidactnow.org/covid-risk-levels-metrics#infection-rate
        #https://covidactnow.org/us/new_york-ny/?s=31661989
        #in the paper, a sick person infects 1.16 people, or 0.86~0.87 infection rate in SEIHRD model #0.879834
        #death_risk = 5.1*10^(-6)
        """
        Create a new InfectedModel
        :param pop_size:        Size of population
        :param init_infected:   Probability of a person agent to start as infected
        :param exposure_distance:   Proximity distance between agents to be exposed to each other
        :param infection_risk:      Probability of agent to become infected, if it has been exposed to another infected
        """
        self.schedule = BaseScheduler(self)
        self.grid = GeoSpace()
        self.steps = 0
        self.counts = None
        self.day_records = list()
        self.hour2_records = list()
        self.rates_records = list() #record rates
        self.rates_record_o = list()#daily record rates
        self.reset_counts()
        
        self.mobility_range= 10000
     
        
       #POI information

        # probability of POI agent types
        self.school_prob = db.school_prob 
        self.hospital_prob = db.hospital_prob 
        self.house_prob = db.house_prob 
        self.workPlace_prob = db.workPlace_prob 
        self.service_prob = db.service_prob 
        
        school_num = int(poi_size * self.school_prob)
        hospital_num = int(poi_size * self.hospital_prob)
        workPlace_num = int(poi_size * self.workPlace_prob)
        service_num = int(poi_size * self.service_prob)
        house_num = poi_size - (school_num + hospital_num + workPlace_num + service_num)
        #age, family size, group size
        self.student_df = db.student_df 
        self.employed_df = db.employed_df 
        self.healthcare_df = db.healthcare_df 
        self.unemployed_df = db.unemployed_df 
        self.male = db.male #0.477
        self.female = db.female # 0.523
        self.age =  db.age  #age distribution
        self.age_range = db.age_range #[[0,12],[13,34],[35,54],[55,100]]
        self.family_size = db.family_size 
        self.group_size = db.group_size
        self.poverty = db.income #[0.1, 0.7, 0.2]  #1 rich, 2 medium, 3 poor
        
        
        # SEIHRD model parameters        
        #dataset
        self.e_i_rate = db.e_i_rate #exposed to infected rate
        self.i_h_rate = db.i_h_rate  #infected to hospital rate
        self.i_d_rate = db.i_d_rate  #infected to death_rate
        self.h_d_rate = db.h_d_rate # hospitalized to dead rate
        self.h_r_rate = db.h_r_rate # hospital to recover
        self.lambda_gamma_delta = db.lambda_gamma_delta #https://arxiv.org/pdf/2007.13811.pdf
        self.i_r_rate = db.i_r_rate #policy/4
       
    
        self.exposure_distance = exposure_distance
        #Initial infection rate
        self.infection_risk = db.infection_risk
        #Initial death rate
        self.death_risk = db.death_risk
        self.initial_death_risk = db.death_risk
        self.initial_infected_risk= db.infection_risk
        #vaccination rate
        self.vaccination_rate = db.vaccination_rate
        #initial exposed rate
        self.expose_rate = db.expose_rate 
        #hospitalized rate
        self.hosp_rate = db.hosp_rate #0.14# hospital rate in 2021
        #initial recovered rate of infected people
        self.recovery_rate = db.recovery_rate 
        self.weather = weather/4
        self.policy = policy/4
        
        
        self.daily_infectious_rate = db.infection_risk
        self.daily_death_rate = db.death_risk
        self.n_days = n_days
        # a step = 2 hours, can change to hourly by switching 12 to 24
        self.n_steps = n_days * db.day_length #12 #24 
        self.pop_size = pop_size
        self.poi_size = poi_size
        self.counts["susceptible"] = pop_size #* (1 - init_infected - init_vaccinated)
     
      #  self.counts["susceptible"] = pop_size * (1 - init_infected - init_vaccinated)
       # self.counts["vaccinated"] = pop_size * init_vaccinated

        
        self.previous_population = {"s": [pop_size * (1 - init_infected - init_vaccinated)],
                                    "i": [pop_size * init_infected],
                                    "e": [0],
                                    "h": [0],
                                    "r": [0],
                                    "d": [0],
                                    "v": [pop_size * init_vaccinated]
                                     }
        self.rates_record = {"infected_rate": [], "hospitalized_rate": [],
                             "exposure_rate": [], "dead_rate": [], "vaccinated_rate": []}
     
       
        self.running = True
        self.datacollector = DataCollector(
            {
                "infected": get_infected_count,
                "susceptible": get_susceptible_count,
                "exposed": get_exposed_count,
                "hospitalized": get_hospitalized_count,
                "recovered": get_recovered_count,
                "dead": get_dead_count,
                "vaccinated": get_vaccinated_count,
              #  "student": get_student_count,
             #   "healthcare": get_health_count,
            #    "employed": get_employed_count,
            #    "unemployed": get_unemployed_count,
            #    "male": get_male_count
            }
        )

        # Set up the Neighbourhood (POI managers) patches for every region in file (add to schedule later)
        AC = AgentCreator(POIManager, {"model": self})
        neighbourhood_agents = AC.from_file(
            self.geojson_regions, unique_id=self.unique_id
        )
        self.grid.add_agents(neighbourhood_agents)

        # Generate HumanAgent population
        ac_student_population = AgentCreator(
            HumanAgent, {"model": self, "init_infected": init_infected, "init_vaccinated": init_vaccinated, "profession": "Student", "profession_df": self.student_df }
        )
        ac_healthcare_population = AgentCreator(
            HumanAgent, {"model": self, "init_infected": init_infected, "init_vaccinated": init_vaccinated, "profession": "Healthcare", "profession_df": self.healthcare_df}
        )
        ac_employed_population = AgentCreator(
            HumanAgent, {"model": self, "init_infected": init_infected, "init_vaccinated": init_vaccinated, "profession": "Employed", "profession_df": self.employed_df}
        )
        ac_unemployed_population = AgentCreator(
            HumanAgent, {"model": self, "init_infected": init_infected, "init_vaccinated": init_vaccinated, "profession": "Unemployed", "profession_df": self.unemployed_df}
        )
        # Generate POI Agents
        ac_home_poi = AgentCreator(
            POIAgent, {"model": self, "init_infected": init_infected, "init_vaccinated": init_vaccinated, "atype": "home"}
        )
        ac_service_poi = AgentCreator(
            POIAgent, {"model": self, "init_infected": init_infected, "init_vaccinated": init_vaccinated, "atype": "service"}
        )
        ac_workplace_poi = AgentCreator(
            POIAgent, {"model": self, "init_infected": init_infected, "init_vaccinated": init_vaccinated, "atype": "workplace"}
        )
        ac_school_poi = AgentCreator(
            POIAgent, {"model": self, "init_infected": init_infected, "init_vaccinated": init_vaccinated, "atype": "school"}
        )
        ac_hospital_poi = AgentCreator(
            POIAgent, {"model": self, "init_infected": init_infected, "init_vaccinated": init_vaccinated, "atype": "hospital"}
        )

            
        # Generate random location, add poi agent to grid and scheduler
        
        #####store POI agents in dictionary
        self.POI_agents = {"school": [], 
                           "hospital": [], 
                           "house": [], 
                           "service": [], 
                           "workplace": []}
        for i in range(school_num):
            this_neighbourhood = self.random.randint(
                0, len(neighbourhood_agents) - 1
            )  # Region where agent starts
            center_x, center_y = neighbourhood_agents[
                this_neighbourhood
            ].shape.centroid.coords.xy
            this_bounds = neighbourhood_agents[this_neighbourhood].shape.bounds
            spread_x = int(
                this_bounds[2] - this_bounds[0]
            )  # Heuristic for agent spread in region
            spread_y = int(this_bounds[3] - this_bounds[1])
            this_x = center_x[0] + self.random.randint(0, spread_x) - spread_x / 2
            this_y = center_y[0] + self.random.randint(0, spread_y) - spread_y / 2
            
            regionID = neighbourhood_agents[this_neighbourhood].unique_id
            this_poi = ac_school_poi.create_agent(
                Point(this_x, this_y), "Pschool" + str(i)
            )
            this_poi.setRegionID(regionID)
            self.grid.add_agents(this_poi)
            self.schedule.add(this_poi)
            self.POI_agents["school"].append([this_x, this_y, "Pschool"+str(i), 0, this_poi])
            
        for i in range(service_num):
            this_neighbourhood = self.random.randint(
                0, len(neighbourhood_agents) - 1
            )  # Region where agent starts
            center_x, center_y = neighbourhood_agents[
                this_neighbourhood
            ].shape.centroid.coords.xy
            this_bounds = neighbourhood_agents[this_neighbourhood].shape.bounds
            spread_x = int(
                this_bounds[2] - this_bounds[0]
            )  # Heuristic for agent spread in region
            spread_y = int(this_bounds[3] - this_bounds[1])
            this_x = center_x[0] + self.random.randint(0, spread_x) - spread_x / 2
            this_y = center_y[0] + self.random.randint(0, spread_y) - spread_y / 2
            
            regionID = neighbourhood_agents[this_neighbourhood].unique_id
            this_poi = ac_service_poi.create_agent(
                Point(this_x, this_y), "Pservice" + str(i)
            )
            this_poi.setRegionID(regionID)
            self.grid.add_agents(this_poi)
            self.schedule.add(this_poi)
            self.POI_agents["service"].append([this_x, this_y, "Pservice"+str(i), 0 , this_poi])
            
        for i in range(workPlace_num):
            this_neighbourhood = self.random.randint(
                0, len(neighbourhood_agents) - 1
            )  # Region where agent starts
            center_x, center_y = neighbourhood_agents[
                this_neighbourhood
            ].shape.centroid.coords.xy
            this_bounds = neighbourhood_agents[this_neighbourhood].shape.bounds
            spread_x = int(
                this_bounds[2] - this_bounds[0]
            )  # Heuristic for agent spread in region
            spread_y = int(this_bounds[3] - this_bounds[1])
            this_x = center_x[0] + self.random.randint(0, spread_x) - spread_x / 2
            this_y = center_y[0] + self.random.randint(0, spread_y) - spread_y / 2
            regionID = neighbourhood_agents[this_neighbourhood].unique_id
            this_poi = ac_workplace_poi.create_agent(
                Point(this_x, this_y), "Pwork" + str(i)
            )
            this_poi.setRegionID(regionID)
            self.grid.add_agents(this_poi)
            self.schedule.add(this_poi)
            self.POI_agents["workplace"].append([this_x, this_y, "Pwork"+str(i), 0, this_poi])
        for i in range(hospital_num):
            this_neighbourhood = self.random.randint(
                0, len(neighbourhood_agents) - 1
            )  # Region where agent starts
            center_x, center_y = neighbourhood_agents[
                this_neighbourhood
            ].shape.centroid.coords.xy
            this_bounds = neighbourhood_agents[this_neighbourhood].shape.bounds
            spread_x = int(
                this_bounds[2] - this_bounds[0]
            )  # Heuristic for agent spread in region
            spread_y = int(this_bounds[3] - this_bounds[1])
            this_x = center_x[0] + self.random.randint(0, spread_x) - spread_x / 2
            this_y = center_y[0] + self.random.randint(0, spread_y) - spread_y / 2
            regionID = neighbourhood_agents[this_neighbourhood].unique_id
            this_poi = ac_hospital_poi.create_agent(
                Point(this_x, this_y), "Phos" + str(i)
            )
            this_poi.setRegionID(regionID)
            self.grid.add_agents(this_poi)
            self.schedule.add(this_poi)
            self.POI_agents["hospital"].append([this_x, this_y, "Phos"+str(i), 0, this_poi])
    
        for i in range(house_num):
            this_neighbourhood = self.random.randint(
                0, len(neighbourhood_agents) - 1
            )  # Region where agent starts
            center_x, center_y = neighbourhood_agents[
                this_neighbourhood
            ].shape.centroid.coords.xy
            this_bounds = neighbourhood_agents[this_neighbourhood].shape.bounds
            spread_x = int(
                this_bounds[2] - this_bounds[0]
            )  # Heuristic for agent spread in region
            spread_y = int(this_bounds[3] - this_bounds[1])
            this_x = center_x[0] + self.random.randint(0, spread_x) - spread_x / 2
            this_y = center_y[0] + self.random.randint(0, spread_y) - spread_y / 2
            
            regionID = neighbourhood_agents[this_neighbourhood].unique_id
            this_poi = ac_home_poi.create_agent(
                Point(this_x, this_y), "Phouse" + str(i)
            )
            this_poi.setRegionID(regionID)
            self.grid.add_agents(this_poi)
            self.schedule.add(this_poi)
            self.POI_agents["house"].append([this_x, this_y, "Phouse"+str(i), 0,  this_poi])
            
        #################################################    
         # Generate random location, add human agent to grid and scheduler
         #
        n_student = int(self.student_df[2] * pop_size)
        n_healthcare = int(self.healthcare_df[2] * pop_size)
        n_unemployed = int(self.unemployed_df[2] * pop_size)
        n_employed = pop_size - (n_student + n_healthcare + n_unemployed )
        n_men = int(self.male * pop_size)
        n_women = pop_size - n_men
        n_age = [int(pop_size * age) for age in self.age]
        n_poverty = [int(pop_size * income) for income in self.poverty]
        age_counts = [0 for _ in range(len(self.age))]
        poverty_counts = [0,0,0]
        gender_counts = [0, 0]
        house_counts = [0 for _ in range(len(self.POI_agents["house"]))]
        current_house = 0
        self.human_agents = {"student": [], 
                           "healthcare": [], 
                           "unemployed": [],  
                           "employed": []}
        self.human_info = {"student": [], 
                           "healthcare": [], 
                           "unemployed": [],  
                           "employed": []}
        
        school_counts = [0 for _ in range(len(self.POI_agents["school"]))]
        current_school = 0
        for p in range(n_student):
            #age
            age_person = self.random.randint(
                self.student_df[0], self.student_df[1])
            if self.age_range[0][0] <= age_person <= self.age_range[0][1]:
                if age_counts[0] >= n_age[0]:
                    age_person = self.random.randint(
                         self.age_range[1][0], self.student_df[1])
                else:
                    age_counts[0] += 1
            if self.age_range[1][0] <= age_person <= self.age_range[2][1]:
                if age_counts[1] >= n_age[1]:
                    age_person = self.random.randint(
                         self.age_range[2][0], self.student_df[1])
                else:
                    age_counts[1] += 1
            if self.age_range[2][0] <= age_person <= self.age_range[2][1]:
                if age_counts[2] >= n_age[2]:
                    age_person = self.random.randint(
                         self.age_range[3][0], self.student_df[1])
                else:
                    age_counts[2] += 1 
            if self.age_range[3][0] <= age_person <= self.age_range[3][1]:
                if age_counts[3] >= n_age[3]:
                    age_person = self.random.randint(
                         self.age_range[0][0], self.student_df[1])
                else:
                    age_counts[2] += 1 
             #gender       
            gender = random.choice([0, 1])
            if gender == 0:
                if gender_counts[0] >= n_men:
                    gender = 1
                    gender_counts[1] += 1
                else:
                    gender_counts[0] += 1
            #poverty
            income = random.choice([1,2,3]) #
            if income == 1:
                if poverty_counts[0] < n_poverty[0]:
                    poverty_counts[0] += 1
                else:
                    income = 2
            if income == 2:
                if poverty_counts[1] < n_poverty[1]:
                    poverty_counts[1] += 1
                else:
                    income = 3
            if income == 3:
                if poverty_counts[2] < n_poverty[2]:
                    poverty_counts[2] += 1
                else:
                    income = 1
                    if poverty_counts[0] < n_poverty[0]:
                        poverty_counts[0] += 1
                    else:
                        income = 2
                
            
            #family group ID
            if house_counts[current_house] < self.family_size:
                familyID = self.POI_agents["house"][current_house][2]
                this_x = self.POI_agents["house"][current_house][0]
                this_y = self.POI_agents["house"][current_house][1]
                regionID = self.POI_agents["house"][current_house][4].getRegionID()
                self.POI_agents["house"][current_house][3] += 1
                house_counts[current_house] += 1
            elif current_house < len(house_counts)-1:
                current_house += 1
                familyID = self.POI_agents["house"][current_house][2]
                this_x = self.POI_agents["house"][current_house][0]
                this_y = self.POI_agents["house"][current_house][1]
                regionID = self.POI_agents["house"][current_house][4].getRegionID()
                self.POI_agents["house"][current_house][3] += 1
                house_counts[current_house] += 1
            else:
                idx = self.random.randint( 0, len(house_counts) - 1)
                familyID = self.POI_agents["house"][idx][2]
                this_x = self.POI_agents["house"][idx][0]
                this_y = self.POI_agents["house"][idx][1]
                regionID = self.POI_agents["house"][idx][4].getRegionID()
                self.POI_agents["house"][idx][3] += 1
             #group id   
            groupID = ""
            groupIndex = 0
            if school_counts[current_school] < self.group_size:
                groupID = self.POI_agents["school"][current_school][2]
                groupIndex = current_school
                self.POI_agents["school"][current_school][3] += 1
                school_counts[current_school] += 1
            elif current_school < len(school_counts)-1:
                current_school += 1
                groupID = self.POI_agents["school"][current_school][2]
                groupIndex = current_school
                self.POI_agents["school"][current_school][3] += 1
                school_counts[current_school] += 1
            else:
                if len(school_counts) >= 1:
                    idx = self.random.randint( 0, len(school_counts) - 1)
                    groupID = self.POI_agents["school"][idx][2]
                    groupIndex = idx
                    self.POI_agents["school"][idx][3] += 1
            
            #x, y, family ID, group ID, group indx gender, age, income, regionID
            self.human_info["student"].append([this_x, this_y, familyID, groupID, groupIndex, gender, age_person, income, regionID])  
                    
                    
        for p in range(n_unemployed):
            #age
            age_person = self.random.randint(
                self.unemployed_df[0], self.unemployed_df[1])
            if self.age_range[0][0] <= age_person <= self.age_range[0][1]:
                if age_counts[0] >= n_age[0]:
                    age_person = self.random.randint(
                         self.age_range[1][0], self.unemployed_df[1])
                else:
                    age_counts[0] += 1
            if self.age_range[1][0] <= age_person <= self.age_range[2][1]:
                if age_counts[1] >= n_age[1]:
                    age_person = self.random.randint(
                         self.age_range[2][0], self.unemployed_df[1])
                else:
                    age_counts[1] += 1
            if self.age_range[2][0] <= age_person <= self.age_range[2][1]:
                if age_counts[2] >= n_age[2]:
                    age_person = self.random.randint(
                         self.age_range[3][0], self.unemployed_df[1])
                else:
                    age_counts[2] += 1 
            if self.age_range[3][0] <= age_person <= self.age_range[3][1]:
                if age_counts[3] >= n_age[3]:
                    age_person = self.random.randint(
                         self.age_range[0][0], self.unemployed_df[1])
                else:
                    age_counts[2] += 1 
             #gender       
            gender = random.choice([0, 1])
            if gender == 0:
                if gender_counts[0] >= n_men:
                    gender = 1
                    gender_counts[1] += 1
                else:
                    gender_counts[0] += 1
                    
            #poverty
            income = random.choice([1,2,3]) #
            if income == 1:
                if poverty_counts[0] < n_poverty[0]:
                    poverty_counts[0] += 1
                else:
                    income = 2
            if income == 2:
                if poverty_counts[1] < n_poverty[1]:
                    poverty_counts[1] += 1
                else:
                    income = 3
            if income == 3:
                if poverty_counts[2] < n_poverty[2]:
                    poverty_counts[2] += 1
                else:
                    income = 1
                    if poverty_counts[0] < n_poverty[0]:
                        poverty_counts[0] += 1
                    else:
                        income = 2
                
            #family group ID
            if house_counts[current_house] < self.family_size:
                familyID = self.POI_agents["house"][current_house][2]
                this_x = self.POI_agents["house"][current_house][0]
                this_y = self.POI_agents["house"][current_house][1]
                regionID = self.POI_agents["house"][current_house][4].getRegionID()
                self.POI_agents["house"][current_house][3] += 1
                house_counts[current_house] += 1
            elif current_house < len(house_counts)-1:
                current_house += 1
                familyID = self.POI_agents["house"][current_house][2]
                this_x = self.POI_agents["house"][current_house][0]
                this_y = self.POI_agents["house"][current_house][1]
                regionID = self.POI_agents["house"][current_house][4].getRegionID()
                self.POI_agents["house"][current_house][3] += 1
                house_counts[current_house] += 1
            else:
                idx = self.random.randint( 0, len(house_counts) - 1)
                familyID = self.POI_agents["house"][idx][2]
                this_x = self.POI_agents["house"][idx][0]
                this_y = self.POI_agents["house"][idx][1]
                regionID = self.POI_agents["house"][idx][4].getRegionID()
                self.POI_agents["house"][idx][3] += 1
            #x, y, family ID, group ID, gender, age
            self.human_info["unemployed"].append([this_x, this_y, familyID, familyID, current_house, gender, age_person, income, regionID])                 
         
        
        hospital_counts = [0 for _ in range(len(self.POI_agents["hospital"]))]
        current_hospital = 0
        for p in range(n_healthcare):
            #age
            age_person = self.random.randint(
                self.healthcare_df[0], self.healthcare_df[1])
            if self.age_range[0][0] <= age_person <= self.age_range[0][1]:
                if age_counts[0] >= n_age[0]:
                    age_person = self.random.randint(
                         self.age_range[1][0], self.healthcare_df[1])
                else:
                    age_counts[0] += 1
            if self.age_range[1][0] <= age_person <= self.age_range[2][1]:
                if age_counts[1] >= n_age[1]:
                    age_person = self.random.randint(
                         self.age_range[2][0], self.healthcare_df[1])
                else:
                    age_counts[1] += 1
            if self.age_range[2][0] <= age_person <= self.age_range[2][1]:
                if age_counts[2] >= n_age[2]:
                    age_person = self.random.randint(
                         self.age_range[3][0], self.healthcare_df[1])
                else:
                    age_counts[2] += 1 
            if self.age_range[3][0] <= age_person <= self.age_range[3][1]:
                if age_counts[3] >= n_age[3]:
                    age_person = self.random.randint(
                         self.age_range[0][0], self.healthcare_df[1])
                else:
                    age_counts[2] += 1 
             #gender       
            gender = random.choice([0, 1])
            if gender == 0:
                if gender_counts[0] >= n_men:
                    gender = 1
                    gender_counts[1] += 1
                else:
                    gender_counts[0] += 1
            #poverty
            income = random.choice([1,2,3]) #
            if income == 1:
                if poverty_counts[0] < n_poverty[0]:
                    poverty_counts[0] += 1
                else:
                    income = 2
            if income == 2:
                if poverty_counts[1] < n_poverty[1]:
                    poverty_counts[1] += 1
                else:
                    income = 3
            if income == 3:
                if poverty_counts[2] < n_poverty[2]:
                    poverty_counts[2] += 1
                else:
                    income = 1
                    if poverty_counts[0] < n_poverty[0]:
                        poverty_counts[0] += 1
                    else:
                        income = 2
                
            #family group ID
            
            if house_counts[current_house] < self.family_size:
                familyID = self.POI_agents["house"][current_house][2]
                this_x = self.POI_agents["house"][current_house][0]
                this_y = self.POI_agents["house"][current_house][1]
                regionID = self.POI_agents["house"][current_house][4].getRegionID()
                self.POI_agents["house"][current_house][3] += 1
                house_counts[current_house] += 1
            elif current_house < len(house_counts)-1:
                current_house += 1
                familyID = self.POI_agents["house"][current_house][2]
                this_x = self.POI_agents["house"][current_house][0]
                this_y = self.POI_agents["house"][current_house][1]
                regionID = self.POI_agents["house"][current_house][4].getRegionID()
                self.POI_agents["house"][current_house][3] += 1
                house_counts[current_house] += 1
            else:
                idx = self.random.randint( 0, len(house_counts) - 1)
                familyID = self.POI_agents["house"][idx][2]
                this_x = self.POI_agents["house"][idx][0]
                this_y = self.POI_agents["house"][idx][1]
                regionID = self.POI_agents["house"][idx][4].getRegionID()
                self.POI_agents["house"][idx][3] += 1
                
            #professional group ID
            groupID = ""
            groupIndex = 0
            if current_hospital < len(hospital_counts):
                if hospital_counts[current_hospital] < self.group_size:
                    groupID = self.POI_agents["hospital"][current_hospital][2]
                    groupIndex = current_hospital
                    self.POI_agents["hospital"][current_hospital][3] += 1
                    hospital_counts[current_hospital] += 1
                elif current_hospital < len(hospital_counts)-1:
                    current_hospital += 1
                    groupID = self.POI_agents["hospital"][current_hospital][2]
                    groupIndex = current_hospital
                    self.POI_agents["hospital"][current_hospital][3] += 1
                    hospital_counts[current_hospital] += 1
            else:
                if len(hospital_counts) >= 1:
                    idx = self.random.randint( 0, len(hospital_counts)-1)
                    print("Test " + str(idx))
                    print(len(self.POI_agents["hospital"]))
                    groupID = self.POI_agents["hospital"][idx][2]
                    groupIndex = idx
                    self.POI_agents["hospital"][idx][3] += 1
            
            #x, y, family ID, group ID, gender, age
            self.human_info["healthcare"].append([this_x, this_y, familyID, groupID, groupIndex, gender, age_person, income, regionID])                    
 
        work_counts = [0 for _ in range(len(self.POI_agents["workplace"]))]
        current_work = 0
        for p in range(n_employed):
            #age
            age_person = self.random.randint(
                self.employed_df[0], self.employed_df[1])
            if self.age_range[0][0] <= age_person <= self.age_range[0][1]:
                if age_counts[0] >= n_age[0]:
                    age_person = self.random.randint(
                         self.age_range[1][0], self.employed_df[1])
                else:
                    age_counts[0] += 1
            if self.age_range[1][0] <= age_person <= self.age_range[2][1]:
                if age_counts[1] >= n_age[1]:
                    age_person = self.random.randint(
                         self.age_range[2][0], self.employed_df[1])
                else:
                    age_counts[1] += 1
            if self.age_range[2][0] <= age_person <= self.age_range[2][1]:
                if age_counts[2] >= n_age[2]:
                    age_person = self.random.randint(
                         self.age_range[3][0], self.employed_df[1])
                else:
                    age_counts[2] += 1 
            if self.age_range[3][0] <= age_person <= self.age_range[3][1]:
                if age_counts[3] >= n_age[3]:
                    age_person = self.random.randint(
                         self.age_range[0][0], self.employed_df[1])
                else:
                    age_counts[2] += 1 
             #gender       
            gender = random.choice([0, 1])
            if gender == 0:
                if gender_counts[0] >= n_men:
                    gender = 1
                    gender_counts[1] += 1
                else:
                    gender_counts[0] += 1
            #poverty
            income = random.choice([1,2,3]) #
            if income == 1:
                if poverty_counts[0] < n_poverty[0]:
                    poverty_counts[0] += 1
                else:
                    income = 2
            if income == 2:
                if poverty_counts[1] < n_poverty[1]:
                    poverty_counts[1] += 1
                else:
                    income = 3
            if income == 3:
                if poverty_counts[2] < n_poverty[2]:
                    poverty_counts[2] += 1
                else:
                    income = 1
                    if poverty_counts[0] < n_poverty[0]:
                        poverty_counts[0] += 1
                    else:
                        income = 2
                
            #family group ID
            if current_house < len(house_counts)-1:
                if house_counts[current_house] < self.family_size:
                    familyID = self.POI_agents["house"][current_house][2]
                    this_x = self.POI_agents["house"][current_house][0]
                    this_y = self.POI_agents["house"][current_house][1]
                    regionID = self.POI_agents["house"][current_house][4].getRegionID()
                    self.POI_agents["house"][current_house][3] += 1
                    house_counts[current_house] += 1
                else: #current_house < len(house_counts):
                    current_house += 1
                    familyID = self.POI_agents["house"][current_house][2]
                    this_x = self.POI_agents["house"][current_house][0]
                    this_y = self.POI_agents["house"][current_house][1]
                    regionID = self.POI_agents["house"][current_house][4].getRegionID()
                    self.POI_agents["house"][current_house][3] += 1
                    house_counts[current_house] += 1
            else:
                idx = self.random.randint( 0, len(house_counts) - 1)
                familyID = self.POI_agents["house"][idx][2]
                this_x = self.POI_agents["house"][idx][0]
                this_y = self.POI_agents["house"][idx][1]
                regionID = self.POI_agents["house"][idx][4].getRegionID()
                self.POI_agents["house"][idx][3] += 1
                
            #professional group ID
            groupID = ""
            groupIndex = 0
            if work_counts[current_work] < self.group_size:
                groupID = self.POI_agents["workplace"][current_work][2]
                groupIndex = current_work
                self.POI_agents["workplace"][current_work][3] += 1
                work_counts[current_work] += 1
            elif current_work < len(work_counts)-1:
                current_work += 1
                groupID = self.POI_agents["workplace"][current_work][2]
                groupIndex = current_work
                self.POI_agents["workplace"][current_work][3] += 1
                work_counts[current_work] += 1
            else:
                if len(work_counts) >= 1:
                    idx = self.random.randint( 0, len(work_counts) - 1)
                    groupID = self.POI_agents["workplace"][idx][2]
                    groupIndex = idx
                    self.POI_agents["workplace"][idx][3] += 1
            
            #x, y, family ID, group ID, gender, age
            self.human_info["employed"].append([this_x, this_y, familyID, groupID, groupIndex, gender, age_person, income, regionID]) 
         
        
        #get list of markets's locations for shortest path
        markets = [[m[0], m[1]] for m in self.POI_agents["service"]] # add list into human agents
        hospitals = [[h[0], h[1]] for h in self.POI_agents["hospital"]] #add list into human agents
        
        #Generate Human Agents
        i = 0
        for human in self.human_info["student"]:
            x, y, familyID, groupID, groupIndex, gender, age_person, income, regionID = human
            houseAddress = [x,y]
            workAddress = [self.POI_agents["school"][groupIndex][0],
                          self.POI_agents["school"][groupIndex][1]]
            this_person = ac_student_population.create_agent(Point(x, y), "P" + str(i))
            this_person.setFamilyID(familyID)
            this_person.setHouseAddress(houseAddress)
            this_person.setGroupID(groupID)
            this_person.setWorkAddress(workAddress)
            this_person.setServiceAddress(markets)
            this_person.setHospitals(hospitals)
            this_person.setRegionID(regionID)
            
            this_person.setAge(age_person)
            this_person.setGender(gender)
            this_person.setIncome(income)
            this_person.setProtection()
            self.human_agents["student"].append([this_person, familyID, groupID])
            self.grid.add_agents(this_person)
            self.schedule.add(this_person)
            i += 1
            
        for human in self.human_info["healthcare"]:
            x, y, familyID, groupID, groupIndex, gender, age_person, income, regionID = human
            houseAddress = [x,y]
            workAddress = [self.POI_agents["hospital"][groupIndex][0],
                          self.POI_agents["hospital"][groupIndex][1]]
            this_person = ac_healthcare_population.create_agent(Point(x, y), "P" + str(i))
            this_person.setFamilyID(familyID)
            this_person.setHouseAddress(houseAddress)
            this_person.setGroupID(groupID)
            this_person.setWorkAddress(workAddress)
            this_person.setServiceAddress(markets)
            this_person.setHospitals(hospitals)
            this_person.setRegionID(regionID)
            
            this_person.setAge(age_person)
            this_person.setGender(gender)
            this_person.setIncome(income)
            this_person.setProtection()
            self.human_agents["healthcare"].append([this_person, familyID, groupID])
            self.grid.add_agents(this_person)
            self.schedule.add(this_person)
            i += 1
    
        for human in self.human_info["employed"]:
            x, y, familyID, groupID, groupIndex, gender, age_person, income, regionID = human
            this_person = ac_employed_population.create_agent(Point(x, y), "P" + str(i))
            houseAddress = [x,y]
            workAddress = [self.POI_agents["workplace"][groupIndex][0],
                          self.POI_agents["workplace"][groupIndex][1]]
            this_person = ac_healthcare_population.create_agent(Point(x, y), "P" + str(i))
            this_person.setFamilyID(familyID)
            this_person.setHouseAddress(houseAddress)
            this_person.setGroupID(groupID)
            this_person.setWorkAddress(workAddress)
            this_person.setServiceAddress(markets)
            this_person.setHospitals(hospitals)
            this_person.setRegionID(regionID)
  
            this_person.setAge(age_person)
            this_person.setGender(gender)
            this_person.setIncome(income)
            this_person.setProtection()
            self.human_agents["employed"].append([this_person, familyID, groupID])
            self.grid.add_agents(this_person)
            self.schedule.add(this_person)
            i += 1

        for human in self.human_info["unemployed"]:
            x, y, familyID, groupID, groupIndex, gender, age_person, income, regionID = human
            this_person = ac_unemployed_population.create_agent(Point(x, y), "P" + str(i))
            houseAddress = [x,y]
            workAddress = [x,y]
            this_person.setFamilyID(familyID)
            this_person.setHouseAddress(houseAddress)
            this_person.setGroupID(groupID)
            this_person.setWorkAddress(workAddress)
            this_person.setServiceAddress(markets)
            this_person.setHospitals(hospitals)
            this_person.setRegionID(regionID)
            
            this_person.setAge(age_person)
            this_person.setGender(gender)
            this_person.setIncome(income)
            this_person.setProtection()
            ## always set workaddress and houseaddress before set market##
            self.human_agents["unemployed"].append([this_person, familyID, groupID])
            self.grid.add_agents(this_person)
            self.schedule.add(this_person)
            i += 1
           
        # Add the neighbourhood agents to schedule AFTER person agents,
        # to allow them to update their color by using BaseScheduler
        for agent in neighbourhood_agents:
            self.schedule.add(agent)

        self.datacollector.collect(self)

    def reset_counts(self):
        self.counts = {
            "susceptible": 0,
            "exposed": 0,
            "infected": 0,
            "hospitalized": 0,
            "recovered": 0,
            "dead": 0,
            "vaccinated": 0,
            "safe": 0,
            "hotspot": 0,
        }
        
    def updateRates(self):
        #https://arxiv.org/pdf/2007.13811.pdf
        #self.e_i_rate = 0.879834 #exposed to infected rate= alpha
       # self.i_h_rate = 0.057584  #infected to hospital rate
       # self.i_d_rate = 0.02073   #infected to death_rate
       # self.h_d_rate = 0.1 #https://arxiv.org/pdf/2007.13811.pdf 
        #page 6: hospitalization lead to dead
       # self.lambda_gamma_delta = 0.217 #https://arxiv.org/pdf/2007.13811.pdf
        #self.h_r_rate = 0.1 # hospital to recover
        seihrd_parameter = [ ]
        i = self.counts["infected"]
        e = self.counts["exposed"]
        s = self.counts["susceptible"]
        h = self.counts["hospitalized"]
        r = self.counts["recovered"]
        d = self.counts["dead"]
        v = self.counts["vaccinated"]
        pop_size = i + e + s + h + r + d +v
        #get previous status
        previous_susceptible = self.previous_population['s'][-1]
        previous_infected = self.previous_population['i'][-1]
        previous_exposed = self.previous_population['e'][-1]
        previous_hospitalized = self.previous_population['h'][-1]
        previous_dead = self.previous_population['d'][-1]
        previous_recovered = self.previous_population['r'][-1]
        previous_vaccinated = self.previous_population['v'][-1]
        d_suscept = s - previous_susceptible
        d_infect = i - previous_infected
       # infection_rate = d_infect / self.pop_size
        d_exposed = e - previous_exposed
       # exposed_rate = d_exposed / self.pop_size
        d_dead = d - previous_dead
        d_recovered = r - previous_recovered
        d_hosp = h - previous_hospitalized
       # dead_rate = d_dead/ self.pop_size
        d_vaccinated = v - previous_vaccinated

        #calculate rates
        #exposed Rate
        if (s*i) != 0:
            exposed_rate = abs(d_exposed * pop_size /((s+v) * i))
        else:
            exposed_rate = self.e_i_rate #self.expose_rate
        if exposed_rate == 0:
            exposed_rate = db.expose_rate #0.5
        #Infected rate
        if e > 0:
            infection_rate = abs (( (exposed_rate*(s+v)*i)/pop_size - d_exposed)/ e)
            if infection_rate == 0:
                infection_rate = self.initial_infected_risk * (self.random.random()+0.5)#self.e_i_rate
        else:
            infection_rate = self.initial_infected_risk*(self.random.random()+0.1)
        if infection_rate > 1.0:
            #infection_rate = 0.1 * (self.random.random()+0.1)
            if self.steps < (db.day_length * 7):
                infection_rate = self.initial_infected_risk * (self.random.random()+0.1)
            else:
                if self.policy > db.p1:
                    infection_rate = (db.pi1)*infection_rate
                elif self.policy > db.p2:
                    infection_rate = (db.pi2)*infection_rate
                elif self.policy > db.p3:
                    infection_rate = (db.pi3)*infection_rate
                else:
                    infection_rate = infection_rate
        if infection_rate == self.initial_infected_risk:
            infection_rate = self.initial_infected_risk*(self.random.random()+0.1)
            
        #hospitalized rate
      #  if i > 0:
    #        hosp_rate = abs((h/i)*self.lambda_gamma_delta)
    #    else:
    #        hosp_rate = abs(self.i_h_rate * self.lambda_gamma_delta)
        hosp_rate = db.HOSP_RATE #### in hosprate-by-modzcta
        #recovery rate
        h_r_rate = self.h_r_rate
        if i > 0:
            i_r_rate =  abs((d_recovered - h_r_rate*h)/i)
        else:
            i_r_rate = self.h_r_rate
        self.i_r_rate = i_r_rate #update self.i_r_rate
        recovery_rate = abs(i_r_rate)
        #death rate 
        hospital_dead_rate = self.h_d_rate
        if i > 0:
            if (d_dead - hospital_dead_rate*h) > 0:
                infected_dead_rate = abs((d_dead - hospital_dead_rate*h)/i)
            else:
                infected_dead_rate = 0 #self.death_risk*0.5
                
        else:
            infected_dead_rate = self.initial_death_risk * (self.random.random()+0.1)# self.death_risk 
        dead_rate = abs(infected_dead_rate)
        if dead_rate == 0:
            dead_rate = self.initial_death_risk * (self.random.random()+0.1)
        # vaccination rate
        if self.steps < 36:
            vaccinated_rate = self.vaccination_rate
      #  else:
       #     vaccinated_rate = abs(d_vaccinated / (s+e) )      
        #update rates
        self.infection_risk = infection_rate
        self.expose_rate = exposed_rate
        #self.vaccination_rate = vaccinated_rate
        self.death_risk = dead_rate
        self.hosp_rate = hosp_rate
        self.recovery_rate = recovery_rate
        
        
        self.previous_population['s'].append(s)
        self.previous_population['e'].append(e)
        self.previous_population['i'].append(i)
        self.previous_population['h'].append(h)
        self.previous_population['r'].append(r)
        self.previous_population['d'].append(d)
        self.previous_population['v'].append(v)
        ##### calculate rates records
      
        daily_infectious_rate = abs(-d_suscept - d_exposed - d_vaccinated) / 10000 #pop_size
      
        daily_dead_rate = d_dead/ 10000#pop_size
        
        if daily_infectious_rate == 0:
            daily_infectious_rate = db.MIN_INFECT
        if daily_dead_rate == 0:
            daily_dead_rate = db.MIN_DEATH
            
      #  print(daily_infectious_rate)
      #  print(daily_dead_rate)
        self.rates_record["infected_rate"].append(self.infection_risk)
        self.rates_record["exposure_rate"].append(self.expose_rate)
        self.rates_record["dead_rate"].append(self.death_risk)
        self.rates_record["vaccinated_rate"].append(self.vaccination_rate)
        ##########
        self.daily_infectious_rate = daily_infectious_rate
        self.daily_death_rate = daily_dead_rate
        
       # self.rates_record_o["infected_rate"].append(daily_infectious_rate) 
        #self.rates_record_o["dead_rate"].append(daily_dead_rate)
       # self.rates_record["hospitalized_rate"]
     #   = {"infected_rate": [], "hospitalized_rate": [].
      #                       "exposure_rate": [], "dead_rate": [], "vaccinated_rate": []}

    def step(self):
        """Run one step of the model."""
        self.steps += 1
        self.reset_counts()
        self.schedule.step()
        self.grid._recreate_rtree()  # Recalculate spatial tree, because agents are moving
        
        time.sleep(db.wait_time) # each step lasts 5 minute : 300
        
        self.datacollector.collect(self)
     #   time.sleep(600) # each step lasts 10 minute
        
        i = self.counts["infected"]
        e = self.counts["exposed"]
        s = self.counts["susceptible"]
        h = self.counts["hospitalized"]
        r = self.counts["recovered"]
        d = self.counts["dead"]
        v = self.counts["vaccinated"]
        
        self.hour2_records.append([self.steps, s, e, i, h, r, d, v])
        if self.steps % db.day_length == 0:  #12 #24
            dayth = self.steps / db.day_length #12 #24
            self.day_records.append([dayth, s, e, i, h, r, d, v])
            #if self.steps != 0:
            self.updateRates()
            self.rates_records.append([dayth, self.infection_risk, self.death_risk])
            self.rates_record_o.append([dayth, self.daily_infectious_rate, self.daily_death_rate])
            print(f"Finish day {dayth}th!")

      #  time.sleep(600) # each step lasts 1 minute
        # Run until no one is infected
     #   if self.counts["infected"] == 0:  
     #       if self.counts["hospitalized"]== 0:
      #          if self.counts["exposed"] == 0:
      #              self.running = False
      #              data_transposed = self.day_records
       #             df = pd.DataFrame(data_transposed, columns=['day','s', 'e', 'i', 'h', 'r', 'd', 'v'])
       #             df.to_csv("output/day_records.csv")
       #             data_transposed1 = self.hour2_records
       #             df1 = pd.DataFrame(data_transposed1, columns=['step','s', 'e', 'i', 'h', 'r', 'd', 'v'])
        #            df1.to_csv("output/hour2_records.csv")
        #            # print("Save data output! Done!")
        ##            rate_records = self.rates_records
        #            rates_df = pd.DataFrame(rate_records, columns =['day','infection_rate','dead_rate'])
        #            rates_df.to_csv("output/infect_dead_rates.csv")
                    #df1.to_csv("output/hour2_records.csv")
                    # print("Save data output! Done!")
                    
         #           rate_record = self.rates_record_o
          #          rates_df = pd.DataFrame(rate_record, columns =['day','infection_rate','dead_rate'])
           #         rates_df.to_csv("output/daily_rates.csv")
           #         print("Save data output! Done!")
                    
        if self.steps >= self.n_steps:
            self.running = False
            data_transposed = self.day_records
            df = pd.DataFrame(data_transposed, columns=['day','s', 'e', 'i', 'h', 'r', 'd', 'v'])
            df.to_csv("output/day_records_1.csv")
            data_transposed1 = self.hour2_records
            df1 = pd.DataFrame(data_transposed1, columns=['step','s', 'e', 'i', 'h', 'r', 'd', 'v'])
            df1.to_csv("output/hour2_records_1.csv")
            
            rate_records = self.rates_records
            rates_df = pd.DataFrame(rate_records, columns=['day','infection_rate','dead_rate'])
            rates_df.to_csv("output/infect_dead_rates.csv")
            
            rate_record = self.rates_record_o
            rates_df = pd.DataFrame(rate_record, columns =['day','infection_rate','dead_rate'])
            rates_df.to_csv("output/daily_rates.csv")
            print("Save data output! Done!")
            


# Functions needed for datacollector
def get_infected_count(model):
    return model.counts["infected"]

def get_exposed_count(model):
    return model.counts["exposed"]


def get_susceptible_count(model):
    return model.counts["susceptible"]

def get_hospitalized_count(model):
    return model.counts["hospitalized"]

def get_recovered_count(model):
    return model.counts["recovered"]

def get_dead_count(model):
    return model.counts["dead"]

def get_vaccinated_count(model):
    return model.counts["vaccinated"]


    