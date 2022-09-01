###
"""This is the database module
   This file stores only parameters, nothing else
"""

###

### For Simulator Manager
###### general parameters - enter straight to UI
pop_size = 10000
poi_size = 1000

exposure_distance = 100
init_infected = 0.006 # % of initial infected population = current infected cases/ total population
init_vaccinated = 0.548 # % of initial vaccinated population, at November 31, 2021, Houston
exposure_distance = 100 
n_days = 30
weather = 2 
policy=2

#information for shapefile
geojson_name = "houston.geojson" #"nyu-2451-34561-geojson.json"#"city_of_houston.json"#"houston.geojson"#"TorontoNeighbourhoods.geojson" # change  to houston city geojson file later
MAP_COORDS =  [29.749907, -95.358421] # [40.730610, -73.935242]#[43.741667, -79.373333]  # Toronto   #change to houston city later [29.749907, -95.358421]
unique_id = "cartodb_id" #"OBJECTID"#"HOODNUM"  # "BG_ID"

###### Distribution of Citizens
    ## distribution of Human agents based on Profession, including max age and min age
student_df = [4, 30, 0.45] # min_age, max_age, percentage
employed_df = [18, 70, 0.43]
healthcare_df = [25, 70, 0.04]
unemployed_df = [10, 81, 0.08]
    ## distribution of Human agents based on Gender
male = 0.499
female = 0.501
    ## Distribution of Human agents based on age
age = [0.233, 0.337, 0.276, 0.154] # 0-15, 16-34, 35-54, 55
age_range = [[0,15],[16,34],[35,54],[55,100]]
family_size = 10
group_size = 100
income = [0.1, 0.7, 0.2]  #1 rich, 2 medium, 3 poor
####### distribution of POI agent types
school_prob = 0.003
hospital_prob = 0.003
house_prob = 0.97
workPlace_prob = 0.012
service_prob =  0.012


####### Extracted parameters from COVID19 data for SEIHRD framework
#https://github.com/nytimes/covid-19-data
#https://healthdata.gov/Hospital/COVID-19-Reported-Patient-Impact-and-Hospital-Capa/g62h-syeh
#Initial infection rate
infection_risk= 0.0000 # 259 /2300000 ; totally 4580 infected cases in july 2021
#Initial death rate
death_risk = 0.0000075# total deaths = 10945 / total population= 2000000/(365 *2)
#Initial exposed rate or exposed rate of the first month= positive rate
expose_rate = 0.22
#hospitalized rate- remain constant
hosp_rate = 0.000158 #0.14# hospital rate in 2021
#vaccinated rate
vaccination_rate=0.00012 
#initial recovery rate
recovery_rate = 0.01
        #dataset
#exposed-to-infected rate
#https://www.tmc.edu/coronavirus-updates/covid-19-testing-metrics-for-tmc-hospital-systems/
e_i_rate = 0.0374#0.879#1.3#0.879834 
#infected-to-hospital rate
i_h_rate = 0.057584 
#infected-to-death_rate
i_d_rate = 0.000013  #4488/457853/(365*2)
#hospitalized-to-dead rate
h_d_rate = 0.118  #: https://arxiv.org/pdf/2007.13811.pdf 
                  #page 6: hospitalization lead to dead
# hospital-to-recovered rate   
h_r_rate = 0.1 
lambda_gamma_delta = 0.217 #https://arxiv.org/pdf/2007.13811.pdf
#infected-to-recovered rate
i_r_rate = 0.0013 #440290/4578530.002/(365*2)#policy/4






######## Other parameters in Simulator Manager
mobility_range= 10000
MIN_DEATH = 0.00001
MIN_INFECT = 0.00001
HOSP_RATE = 0.000408
step_hour = 2
day_length = 12


      ######for healthcare quality in SEIHRD computation
p1 = 0.7
p2 = 0.5
p3 = 0.2
pi1 = 0.2
pi2 = 0.5
pi3 = 0.8

wait_time = 30 #15 ## each step lasts 15 seconds : 300 = 12 * 15




### For Human Manager
protection_level_threshold = 0.4
protection_level_threshold = 0.4
infection_probebility = 0.55
action_infect_threshold = 0.45
action_affecting_prob = 0.55
action_occurring_prob = 0.55

###### For computing Protection Level and Resistance Level
protection_parameters = [1, 1, 0.5, 1, 1, 1, 1, 0.5, 0.5]
weather_policy = [1, 0.5]
MOBILITY_RANGE = 10000


gender_prob = {"male": [0.125, 0.0049, 0.0157] , "female":[0.125, 0.0033, 0.0127]}
income_prob = { 1: [0.09, 0.002, 0.007], 2: [0.096, 0.003, 0.012], 3: [0.11, 0.004, 0.016]}
age_prob = {15: [0.0857, 0.0008, 0.0117], 34: [0.346, 0.0108, 0.0994], 54: [0.3, 0.0867, 0.2083], 100: [0.268, 0.9017, 0.6806]}

pregnant_percent = 90

resistance_threshold = 0.1
protection_threshold = 0.2
#constant in computing Protection level and resistance level
k1 = 0.5
k2 = 10
k3 = 0.5
k4 = 1
k5 = 0.5
k6 = 0.2
###### for other parameters
# list of available service place
service_number = 10
#for protection level and resistance level
age1 = 55
age2 = 35
age3 = 16
# for exposed() method
e1 = 60 # 12*5
e2 = 0.95
e3 = 0.85
ep1 = 0.7
e4 = 0.95
ep2 = 0.5
e5 = 0.8
e6 = 0.6

#for infected() method
i1 = 0.9
#for go_to_hospital()
h1 = 0.99
