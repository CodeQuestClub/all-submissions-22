from asyncio.proactor_events import _ProactorBaseWritePipeTransport
from calendar import SATURDAY
from re import I
from typing_extensions import Self
from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import *
from codequest22.server.requests import *
import math

class Queue():
    #Not really a queue just a circular thing that overwrites itself
    #Used for keeping track of the last 30 food locations a team got food from
    def __init__(self, size):
        self.size = size
        self.arr = [-1] * size
        self.front = 0

    def add(self, val):
        self.arr[self.front] = val
        self.front += 1
        self.front %= self.size

    def count(self, val):
        count = 0
        for i in range(len(self.arr)):
            if self.arr[i] == val:
                count += 1
        return count

class TeamStats():
    def __init__(self):
        self.alive = True
        self.spawn = None
        self.hill_score = 0
        self.energy = stats.general.STARTING_ENERGY
        self.total_ants = 0
        self.total_workers = 0
        self.total_settlers = 0
        self.total_fighters = 0
        self.ants = {} #Ant dictionary- key, value = ant_id, [ant_type, party, position]
        self.foodlocations = Queue(15)

def get_team_name():
    return "🐸FROG🐸⚙COG⚙"

my_index = None
def read_index(player_index, n_players):
    global my_index
    my_index = player_index
total_ants_spawned = 0
teams = [TeamStats() for i in range(4)]
map_data = {}
spawns = [None]*4

food_sites = []
food_energies = []
food_activations = []
distance = {}
closest_site = None
active_hill_location = (0, 0)
map_distances = [[]] #A version of the map with distances to all the tiles
active_parties = []

def read_map(md, energy_info):
    #to do in future, also do dijstra from every other team's spawn so you can sabotage their optimal food location or something idk
    global map_data, spawns, distance, closest_site, map_distances, active_parties, food_sites, food_energies, food_activations, targeting_index
    food = []
    map_data = md
    for y in range(len(map_data)):
        for x in range(len(map_data[0])):
            if map_data[y][x] == "F":
                food.append((x, y))
            if map_data[y][x] in "RBYG":
                spawns["RBYG".index(map_data[y][x])] = (x, y)
    # Read map is called after read_index
    startpoint = spawns[my_index]
    # Dijkstra's Algorithm: Find the shortest path from your spawn to each food zone.
    # Step 1: Generate edges - for this we will just use orthogonally connected cells.
    adj = {}
    h, w = len(map_data), len(map_data[0])
    # A list of all points in the grid
    points = []
    # Mapping every point to a number
    idx = {}
    counter = 0
    for y in range(h):
        for x in range(w):
            adj[(x, y)] = []
            if map_data[y][x] == "W": continue
            points.append((x, y))
            idx[(x, y)] = counter
            counter += 1
    for x, y in points:
        for a, b in [(y+1, x), (y-1, x), (y, x+1), (y, x-1)]:
            if 0 <= a < h and 0 <= b < w and map_data[a][b] != "W":
                adj[(x, y)].append((b, a, 1))
    # Step 2: Run Dijkstra's
    import heapq
    # What nodes have we already looked at?
    expanded = [False] * len(points)
    # What nodes are we currently looking at?
    queue = []
    # What is the distance to the startpoint from every other point?
    heapq.heappush(queue, (0, startpoint))
    while queue:
        d, (a, b) = heapq.heappop(queue)
        if expanded[idx[(a, b)]]: continue
        # If we haven't already looked at this point, put it in expanded and update the distance.
        expanded[idx[(a, b)]] = True
        distance[(a, b)] = d
        # Look at all neighbours
        for j, k, d2 in adj[(a, b)]:
            if not expanded[idx[(j, k)]]:
                heapq.heappush(queue, (
                    d + d2,
                    (j, k)
                ))
    # Now I can calculate the closest food site.
    food_sites = list(sorted(food, key=lambda prod: distance[prod]))
    closest_site = food_sites[0]
    map_distances = [[float('inf') for _ in range(len(map_data[0]))] for _ in range(len(map_data))]
    for key in distance:
        map_distances[key[1]][key[0]] = distance[key] #idk why its [1][0 ]but it just works for some reason
    for i in range(len(food_sites)):
        food_energies += [energy_info[food_sites[i]]]    
    food_activations = [False] * len(food_sites)
    if my_index == 0:
        targeting_index = 1

def handle_failed_requests(requests):
    for req in requests:
        if req.player_index == my_index:
            print(f"Request {req.__class__.__name__} failed. Reason: {req.reason}.")
            raise ValueError()
maxants = 0
food_priorities = []

def handle_events(events):
    global active_hill_location, teams, maxants, current_tick_energy, food_priorities, targeting_index, targeting_queens
    food_priorities = food_priority()

    if teams[my_index].total_ants > maxants:
        maxants = teams[my_index].total_ants
        #print(maxants)
    requests = []
    for ev in events:
        if isinstance(ev, SpawnEvent):
            requests += HandleSpawnEvent(ev)
        elif isinstance(ev, MoveEvent):
            requests += HandleMoveEvent(ev)
        elif isinstance(ev, DieEvent):
            requests += HandleDieEvent(ev)
        elif isinstance(ev, AttackEvent):
            requests += HandleAttackEvent(ev)
        elif isinstance(ev, DepositEvent):
            requests += HandleDepositEvent(ev)
        elif isinstance(ev, ProductionEvent):
            requests += HandleProductionEvent(ev)
        elif isinstance(ev, ZoneActiveEvent):
            requests += HandleZoneActiveEvent(ev)
        elif isinstance(ev, ZoneDeactivateEvent):
            requests += HandleZoneDeactivateEvent(ev)
        elif isinstance(ev, FoodTileActiveEvent):
            requests += HandleFoodTileActiveEvent(ev)
        elif isinstance(ev, FoodTileDeactivateEvent):
            requests += HandleFoodTileDeactivateEvent(ev)
        elif isinstance(ev, SettlerScoreEvent):
            requests += HandleSettlerScoreEvent(ev)
        elif isinstance(ev, QueenAttackEvent):
            requests += HandleQueenAttackEvent(ev)
        elif isinstance(ev, TeamDefeatedEvent):
            requests += HandleTeamDefeatedEvent(ev)
    requests += NewSpawnAnts()
    current_tick_energy = 0

    print(targeting_index)
    print(teams[targeting_index].total_ants)
    print(teams[targeting_index].energy)
    previoustarget = targeting_index
    if (teams[targeting_index].total_ants == 0 and teams[targeting_index].energy < stats.ants.Worker.COST) or teams[targeting_index].hill_score == -1:
        print('awawawa')
        #Move onto the next ant
        for i in range(4):
            if i == my_index:
                continue
            if teams[i].total_ants == 0 and teams[i].energy < stats.ants.Worker.COST:
                continue
            targeting_index = i
            break
        if previoustarget == targeting_index:
            #If no teams can produce ants anymore, target the queens
            print('asdetfohui')
            targeting_queens = True

    return requests

current_tick_energy = 0
targeting_index = 0
targeting_queens = False
def NewSpawnAnts():
    global current_tick_energy, targeting_index, targeting_queens
    




    requests = []
    spawned_this_tick = 0
    #Ok so split ant spawns between workers and fighters
    #if current_tick_energy <= 200:
    if teams[my_index].total_workers < 15:#idk if 30 is a good number or not
        #Spawn more workers
        #Send it to the currently most optimal food location
        while teams[my_index].total_ants < stats.general.MAX_ANTS_PER_PLAYER and spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and teams[my_index].energy >= stats.ants.Worker.COST:
            requests += [SpawnRequest(AntTypes.WORKER, id = None, color = None, goal = food_sites[argmax(food_priorities)])]
            teams[my_index].energy -= stats.ants.Worker.COST
            spawned_this_tick += 1
    else:
        #Spawn more fighters
        #Send it to the most popular food location for the targeting_index team
        while teams[my_index].total_ants < stats.general.MAX_ANTS_PER_PLAYER and spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and teams[my_index].energy >= stats.ants.Fighter.COST:
            if not targeting_queens:
                popular = popular_food_sites(targeting_index)[0]
                requests += [SpawnRequest(AntTypes.FIGHTER, id = None, color = None, goal = popular[0])]
            else:
                requests += [SpawnRequest(AntTypes.FIGHTER, id = None, color = None, goal = spawns[targeting_index])]
            teams[my_index].energy -= stats.ants.Fighter.COST
            spawned_this_tick += 1
    return requests

def HandleSpawnEvent(ev):
    global active_parties
    #Update data for all teams
    player = ev.player_index
    teams[player].total_ants += 1
    type = ev.ant_type
    if type == AntTypes.WORKER:
        teams[player].total_workers += 1
        teams[player].energy -= stats.ants.Worker.COST
    elif type == AntTypes.SETTLER:
        teams[player].total_settlers += 1
        teams[player].energy -= stats.ants.Settler.COST
    elif type == AntTypes.FIGHTER:
        teams[player].total_fighters += 1
        teams[player].energy -= stats.ants.Fighter.COST
    teams[player].ants[ev.ant_id] = [ev.ant_type, None, ev.position]
    if teams[player].spawn == None:
        teams[player].spawn = ev.position
    return []
    
def HandleMoveEvent(ev):
    teams[ev.player_index].ants[ev.ant_id][2] = ev.position
    return []

def HandleDieEvent(ev):
    #Update data for all teams
    player = ev.player_index
    teams[player].total_ants -= 1
    type = teams[player].ants[ev.ant_id][0]
    if type == AntTypes.WORKER:
        teams[player].total_workers -= 1
    elif type == AntTypes.SETTLER:
        teams[player].total_settlers -= 1
    elif type == AntTypes.FIGHTER:
        teams[player].total_fighters -= 1

    #Pop the ant from the corresponding team's ant list
    ant = teams[player].ants.pop(ev.ant_id)

    return []

def HandleAttackEvent(ev):
    return []

def HandleDepositEvent(ev):
    global food_priorities, current_tick_energy
    player = ev.player_index
    current_tick_energy += (ev.total_energy - teams[player].energy)
    #Update the amount of energy the team whose ant deposited now has
    teams[player].energy = ev.total_energy
    #If it was our worker ant that deposited, send him back off
    if player == my_index:
        goal = food_sites[argmax(food_priorities)]
        return [GoalRequest(ev.ant_id, goal)]
    return []

def HandleProductionEvent(ev):
    #Update the last 15 food sites this team has visited
    foodpos = teams[ev.player_index].ants[ev.ant_id][2]
    foodpos = (int(foodpos[0]), int(foodpos[1]))
    for i in range(len(food_sites)):
        if food_sites[i] == foodpos:
            teams[ev.player_index].foodlocations.add(food_sites[i])
            break


    if ev.player_index == my_index:
        # One of my worker ants just made it to the food site! Let's send them back to the Queen.
        return [GoalRequest(ev.ant_id, spawns[my_index])]
    return []


def HandleZoneActiveEvent(ev):
    #lmao literally just ignoring this shit now
    return []

def HandleZoneDeactivateEvent(ev):
    #lmao literally just ignoring this shit now
    return []

def HandleFoodTileActiveEvent(ev):
    global food_sites, food_activations
    for i in range(len(food_sites)):
        if ev.pos == food_sites[i]:
            food_activations[i] = True
    return []
def HandleFoodTileDeactivateEvent(ev):
    global food_sites, food_activations
    for i in range(len(food_sites)):
        if ev.pos == food_sites[i]:
            food_activations[i] = False
    return []
def HandleSettlerScoreEvent(ev):
    teams[ev.player_index].hill_score += ev.score_amount
    return []
def HandleQueenAttackEvent(ev):
    #Target the player that's attacking us
    global targeting_index
    if ev.queen_player_index == my_index:
        targeting_index = ev.ant_player_index
    return []
def HandleTeamDefeatedEvent(ev):
    global targeting_index
    teams[ev.defeated_index].hill_score = -1
    teams[ev.by_index] = ev.new_hill_score
    if ev.defeated_index == targeting_index:
        for i in range(4):
            if teams[i].hill_score > teams[my_index].hill_score and i != my_index:
                targeting_index = i
    return []


def popular_food_sites(team_index):
    #Returns list of food sites visited by a team, sorted by popularity
    visited = []
    for i in range(len(food_sites)):
        visited += [(food_sites[i], teams[team_index].foodlocations.count(food_sites[i]))]
    visited.sort(key = lambda x:x[1], reverse = True)
    return visited

def food_priority():
    global  teams, food_energies, food_sites, food_activations
    priority = []
    for i in range(len(food_sites)):
        food_yield = food_energies[i] * (food_activations[i] + 1)
        distance_index = i #maybe replace this with actual distance in the future idk
        other_team_popularity = (
            teams[0].foodlocations.count(food_sites[i]) +
            teams[1].foodlocations.count(food_sites[i]) + 
            teams[2].foodlocations.count(food_sites[i]) + 
            teams[3].foodlocations.count(food_sites[i]) ) - teams[my_index].foodlocations.count(food_sites[i]) #Number between 0 (not popular) and 90 (way more popular than should be possible)
        saturation = teams[my_index].foodlocations.count(food_sites[i]) #Number between 0 and 15, we want this to become a number between 0 and 1, representing something like 10 to 20 ants having gone to a thing
        #saturation = min(1, (-1/21) * saturation + (31/21)) #don't ask
        saturation = min(0.999, (saturation + 1) / 15)
        saturation = 1 - saturation

        #also there should be some bool that checks if there are enemy fighters at a food location, and if so  don't send workers there
        priority += [(food_yield / (distance_index + 1)) * ((45 - other_team_popularity) // 45) * (saturation**2)]

    #To compute the priority of a certain location, we take into account some things:
    #1. Distance from player spawn
    #2. Popularity for other teams
    #3. Its yield
    #4. How saturated it is (idk how to compute this rn maybe ill do it later)

    return priority

def argmax(arr):
    max = arr[0]
    maxindex = 0
    for i in range(1, len(arr)):
        if arr[i] > max:
            max = arr[i]
            maxindex = i
    return maxindex