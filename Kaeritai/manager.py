import random
import math

import codequest22.stats as stats
from codequest22.server.ant import AntTypes
from codequest22.server.requests import GoalRequest, SpawnRequest
from codequest22.server.events import (
    SpawnEvent, 
    MoveEvent, 
    DieEvent, 
    AttackEvent, 
    DepositEvent, 
    ProductionEvent, 
    ZoneActiveEvent, 
    ZoneDeactivateEvent, 
    FoodTileActiveEvent, 
    FoodTileDeactivateEvent, 
    SettlerScoreEvent, 
    QueenAttackEvent, 
    TeamDefeatedEvent
)

class Manager():

    def __init__(self):
        self.index = None
        self.hills = None
        self.startpoint = None
        self.energy = stats.general.STARTING_ENERGY
        self.max_ants = stats.general.MAX_ANTS_PER_PLAYER
        self.max_spawn_per_tick = stats.general.MAX_SPAWNS_PER_TICK
        self.spawned_this_tick = 0

        self.tick = 0

        self.enemies = None

        self.zones = {} # Active Zones

        self.objectives = []

        self.max_workers = int(self.max_ants)*.5
        self.max_settlers = 0
        self.max_fighters = int(self.max_ants)*.5 - self.max_settlers
    
        self.ants_type = {
            "WORKER": AntTypes.WORKER,
            "FIGHTER": AntTypes.FIGHTER,
            "SETTLER": AntTypes.SETTLER
        }

        self.ants = {
            "WORKER": {},
            "FIGHTER": {},
            "SETTLER": {}
        }

        self.cost = {
            "WORKER": stats.ants.Worker.COST,
            "FIGHTER": stats.ants.Fighter.COST,
            "SETTLER": stats.ants.Settler.COST
        }

        self.objectives = {AntType: [] for AntType in AntTypes}


    def len(self):
        return sum([len(self.ants[ant_type]) for ant_type in self.ants])

    def updateWorkerGoal(self, ant_id, new_energy, objective):
        self.energy += new_energy
        self.ants["WORKER"][ant_id] = objective
        return GoalRequest(ant_id, objective)

    def returnWorker(self, ant_id):
        return GoalRequest(ant_id, self.startpoint)

    def updateDeath(self, ant_id):
        for ant_type in self.ants:
            if ant_id in self.ants[ant_type]:
                self.ants[ant_type].pop(ant_id)      

    def generate_ant(self, requests, type, objetive):
        self.spawned_this_tick += 1
        id = type + str(0)
        i = 0
        while id in self.ants[type]:
            i+=0
            id = type + str(random.randint(0, 100*self.max_ants))
        self.ants[type][id] = objetive 
        self.energy -= self.cost[type]
        ant = SpawnRequest(self.ants_type[type], id=id, color=None, goal=objetive)
        return ant


    def updateFighters(self):
        requests = []

        if not self.objectives:
            return requests

        for i, fighter in enumerate(self.ants["FIGHTER"]):
            objective = math.floor(i * len(self.objectives)/len(self.ants["FIGHTER"]))
            self.ants["FIGHTER"][fighter] = self.objectives[objective]
            requests.append(GoalRequest(fighter, self.objectives[objective]))
        return requests


    def getObjective(self, type):
        if type=="SETTLER":
            for point in self.zones:
                if not self.hills[point] in self.ants["SETTLER"].values():
                    return self.hills[point] 
        elif type=="FIGHTER":
            if not self.ants["FIGHTER"]:
                return self.objectives[0]
            objectives = {}
            for ant in self.ants["FIGHTER"]:
                if self.ants["FIGHTER"][ant] in objectives:
                    objectives[self.ants["FIGHTER"][ant]] += 1
                else:
                    objectives[self.ants["FIGHTER"][ant]] = 1

            objective = min(objectives, key=objectives.get)
            return objective

    def spawn(self, objetive):
        requests = []
        self.spawned_this_tick = 0
        while (
            self.len() < self.max_ants and 
            self.spawned_this_tick < self.max_spawn_per_tick and
            self.energy >= self.cost["FIGHTER"] 
        ):

            if (len(self.ants["SETTLER"]) < self.max_settlers and 
                len(self.ants["WORKER"]) > 10 and 
                self.energy >= self.cost["SETTLER"]):
                requests.append(self.generate_ant(
                    requests, "SETTLER", self.getObjective("SETTLER")))
                continue

            if (len(self.ants["WORKER"]) < self.max_workers and 
                self.energy >= self.cost["WORKER"]):
                requests.append(self.generate_ant(requests, "WORKER", objetive))
                continue


            if (len(self.ants["FIGHTER"]) < self.max_fighters and 
                len(self.ants["WORKER"]) > 10 and 
                self.energy >= self.cost["FIGHTER"]):
                requests.append(self.generate_ant(requests, "FIGHTER", self.getObjective("FIGHTER")))
                continue


        return requests



    def run(self, events, closest_goal):
        requests = []

        # UPDATE THE STATE
        for event in events:
            
            if isinstance(event, DepositEvent):
                if event.player_index == self.index:
                    requests.append(self.updateWorkerGoal(event.ant_id, event.energy_amount, closest_goal))
            elif isinstance(event, ProductionEvent):
                if event.player_index == self.index:
                    requests.append(self.returnWorker(event.ant_id))
            elif isinstance(event, DieEvent):
                if event.player_index == self.index:
                    self.updateDeath(event.ant_id)
            elif isinstance(event, ZoneActiveEvent):
                self.zones[event.zone_index] = {True}
                self.max_settlers+=2
                self.objectives = [self.hills[zone] for zone in self.zones]
                requests+=self.updateFighters()

            elif isinstance(event, ZoneDeactivateEvent):
                if self.hills[event.zone_index] in self.objectives:
                    self.objectives.remove(self.hills[event.zone_index])
                self.zones.pop(event.zone_index)
                self.max_settlers-=2
                requests+=self.updateFighters()

            elif isinstance(event, ZoneDeactivateEvent):
                pass

            elif isinstance(event, QueenAttackEvent):
                self.objectives = [self.startpoint]
                requests+=self.updateFighters()
            else:
                pass


        # SPAWN THE ANTS
        requests+=self.spawn(closest_goal)

        return requests
            
            







    