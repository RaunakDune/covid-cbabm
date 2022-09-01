from mesa_geo.visualization.ModularVisualization import ModularServer
from mesa.visualization.modules import ChartModule, TextElement
from mesa.visualization.UserParam import UserSettableParameter
from simulatorManager import SimulatorManager#InfectedModel, PersonAgent
from humanManager import HumanAgent
from POIManager import POIAgent, POIManager
from mesa_geo.visualization.MapModule import MapModule
import DatabaseAdaptor.database as db


class InfectedText(TextElement):
    """
    Display a text count of how many steps have been taken
    """

    def __init__(self):
        pass

    def render(self, model):
        return "Steps: " + str(model.steps)

#https://www.tmc.edu/coronavirus-updates/daily-new-covid-19-positive-cases-for-the-greater-houston-area/  => 0.001 initial infection is 0.005
model_params = {
    #"pop_size": UserSettableParameter("slider", "Population size", 10000, 1000, 1000000, 90),
   # "poi_size": UserSettableParameter('slider', 'Number of Points of Interest', 1000, 100, 100000, 90),
    "pop_size": UserSettableParameter('number', 'Population size', value=db.pop_size),
    "poi_size": UserSettableParameter('number', 'Number of Points of Interest', value=db.poi_size),
    "n_days": UserSettableParameter('number', 'Days of simulation', value=30),
    "weather": UserSettableParameter('number', 'Weather effect(from 1 to 4)', value=db.weather), #no effect=1, normal=2, strong=3, very strong=4
    "policy": UserSettableParameter('number', 'Intervence Policy (from 1 to 4)', value=db.policy),#no policy =1, good policy=2, very good policy= 3, strict and lockdown = 4
    "init_infected": UserSettableParameter(
        "slider", "Fraction initial infection", db.init_infected, 0.00, 1.0, 0.005   #0.01
    ),   #https://covidactnow.org/us/new_york-ny/?s=31661989
    "init_vaccinated": UserSettableParameter(
        "slider", "Fraction initial vaccination", db.init_vaccinated, 0.00, 1.0, 0.005   
    ),
    "exposure_distance": UserSettableParameter(
        "slider", "Exposure distance", db.exposure_distance, 100, 10000, 100
    ),
}


def infected_draw(agent):
    """
    Portrayal Method for canvas
    """
    portrayal = dict()
    if isinstance(agent, HumanAgent):
        portrayal["radius"] = "2"
    if agent.atype in ["hotspot", "infected"]:
        portrayal["color"] = "Red"
    elif agent.atype in ["safe", "susceptible"]:
        portrayal["color"] = "Green"
    elif agent.atype in ["exposed"]:
        portrayal["color"] = "Yellow"
    elif agent.atype in ["hospitalized"]:
        portrayal["color"] = "Purple"
    elif agent.atype in ["recovered"]:
        portrayal["color"] = "Blue"
    elif agent.atype in ["dead"]:
        portrayal["color"] = "Black"
    elif agent.atype in ["vaccinated"]:
        portrayal["color"] = "Gray"
    return portrayal


infected_text = InfectedText()
map_element = MapModule(infected_draw, SimulatorManager.MAP_COORDS, 10, 500, 500)
infected_chart = ChartModule(
    [
        {"Label": "infected", "Color": "Red"},
        {"Label": "susceptible", "Color": "Green"},
        {"Label": "exposed", "Color": "Yellow"},
        {"Label": "hospitalized", "Color": "Purple"},
        {"Label": "recovered", "Color": "Blue"},
        {"Label": "dead", "Color": "Black"},
     #   {"Label": "vaccinated", "Color": "Gray"},
    ]
)

closedUp_chart = ChartModule(
    [
        {"Label": "infected", "Color": "Red"},
       # {"Label": "susceptible", "Color": "Green"},
      #  {"Label": "exposed", "Color": "Yellow"},
        {"Label": "hospitalized", "Color": "Purple"},
        {"Label": "recovered", "Color": "Blue"},
        {"Label": "dead", "Color": "Black"},
     #   {"Label": "vaccinated", "Color": "Gray"},
    ]
)

full_chart = ChartModule(
    [
        {"Label": "infected", "Color": "Red"},
        {"Label": "susceptible", "Color": "Green"},
        {"Label": "exposed", "Color": "Yellow"},
        {"Label": "hospitalized", "Color": "Purple"},
        {"Label": "recovered", "Color": "Blue"},
        {"Label": "dead", "Color": "Black"},
        {"Label": "vaccinated", "Color": "Gray"},
    ]
)
server = ModularServer(
    SimulatorManager,
    [map_element, infected_text, infected_chart, closedUp_chart, full_chart],
    "Basic agent-based SEIHRD model",
    model_params,
)
server.launch()