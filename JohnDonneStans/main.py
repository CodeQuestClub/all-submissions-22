from distutils.spawn import spawn
from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import DepositEvent, DieEvent, ProductionEvent, ZoneActiveEvent, ZoneDeactivateEvent, \
    SpawnEvent, QueenAttackEvent, TeamDefeatedEvent, FoodTileActiveEvent, FoodTileDeactivateEvent
from codequest22.server.requests import GoalRequest, SpawnRequest
import random


# hello
def get_team_name():
    return f"JohnDonneStans"


my_index = None


def read_index(player_index, n_players):
    global my_index
    my_index = player_index


my_energy = stats.general.STARTING_ENERGY
map_data = {}
spawns = [None] * 4
food = []
zone = []
closest_sites = None
closest_site = None
active_zone = None
distance = []
distancc = {}
total_ants = 0
worker_ants = []
fighter_ants = []
settler_ants = []
queenHealth = [stats.general.QUEEN_HEALTH] * 4
alive_spawn_indexes = []
tick = 0
wrker_cnt_new = 0
wrker_cnt_rtrn = 0
energy_info = None
j = 0
ener = []
hill = 0
max_cost = max(stats.ants.Worker.COST, stats.ants.Settler.COST, stats.ants.Fighter.COST)


def read_map(md, ei):
    global map_data, spawns, food, distance, closest_sites, zone, alive_spawn_indexes, energy_info, max_cost, closest_site
    map_data = md
    energy_info = ei
    for y in range(len(map_data)):
        for x in range(len(map_data[0])):
            if map_data[y][x] == "F":
                food.append((x, y))
            if map_data[y][x] == "Z":
                # adds the hill twice to represent that it has two activations
                zone.append((x, y))
                zone.append((x, y))
            if map_data[y][x] in "RBYG":
                spawns["RBYG".index(map_data[y][x])] = (x, y)
    # Read map is called after read_index
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
        for a, b in [(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)]:
            if 0 <= a < h and 0 <= b < w and map_data[a][b] != "W":
                adj[(x, y)].append((b, a, 1))
    # Step 2: Run Dijkstra's
    closest_sites = []
    #Performs the same events for all teams locations
    for index, position in enumerate(spawns):
        # Find the distance for everything from spawn
        distance.append(Dijkstra(position, points, idx, adj))
        # only keeps food sites who's value is higher then the value of a worker
        eligible_food = [i for i in food if (energy_info[i]*stats.ants.Worker.TRIPS) >= max_cost]
        # Finds the highest cost food_sites i.e. cost = energy/distance
        closest_sites.append(list(sorted(eligible_food, key=lambda prod: energy_info[prod] / distance[index][prod], reverse=True)))
    # Makes a list of alive enemy'
    alive_spawn_indexes = list(range(len(spawns)))
    
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
        distancc[(a, b)] = d
        # Look at all neighbours
        for j, k, d2 in adj[(a, b)]:
            if not expanded[idx[(j, k)]]:
                heapq.heappush(queue, (
                    d + d2,
                    (j, k)
                ))
    # Now I can calculate the closest food site.
    food_sites = list(sorted(food, key=lambda prod: distancc[prod]))
    closest_site = food_sites[0]

def Dijkstra(startpoint, points, idx, adj):
    result = {}
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
        result[(a, b)] = d
        # Look at all neighbours
        for j, k, d2 in adj[(a, b)]:
            if not expanded[idx[(j, k)]]:
                heapq.heappush(queue, (
                    d + d2,
                    (j, k)
                ))
    return result

def handle_failed_requests(requests):
    global my_energy
    for req in requests:
        if req.player_index == my_index:
            print(f"Request {req.__class__.__name__} failed. Reason: {req.reason}.")
            raise ValueError()


def handle_events(events):
    global my_energy, total_ants, tick, active_zone, queenHealth, zone, spawns, alive_spawn_indexes, wrker_cnt_new, \
        wrker_cnt_rtrn, closest_sites, max_cost, hill, togo, go, tick, j, closest_site
    requests = []
    help_please = 0
    for ev in events:
        if isinstance(ev, DieEvent):
            if ev.player_index == my_index:
                # One of my workers just died :(
                total_ants -= 1
                if ev.ant_id in settler_ants:
                    settler_ants.remove(ev.ant_id)
                elif ev.ant_id in worker_ants:
                    worker_ants.remove(ev.ant_id)
                elif ev.ant_id in fighter_ants:
                    fighter_ants.remove(ev.ant_id)
        elif isinstance(ev, TeamDefeatedEvent):
            if ev.defeated_index-1 != my_index:
                spawns[ev.defeated_index] = spawns[ev.defeated_index-1]
            else:
                spawns[ev.defeated_index] = spawns[ev.defeated_index-2]
    for ev in events:
        if isinstance(ev, DepositEvent):
            if ev.player_index == my_index:
                # One of my worker ants just made it back to the Queen! Let's send them back to the food site.
                requests.append(GoalRequest(ev.ant_id, closest_sites[my_index][wrker_cnt_rtrn % len(closest_sites)]))
                wrker_cnt_rtrn += 1
                # Additionally, let's update how much energy I've got.
                my_energy = ev.cur_energy
        elif isinstance(ev, ProductionEvent):
            if ev.player_index == my_index:
                # One of my worker ants just made it to the food site! Let's send them back to the Queen.
                requests.append(GoalRequest(ev.ant_id, spawns[my_index]))
        elif isinstance(ev, SpawnEvent):
            if ev.player_index == my_index:
                # One of my workers just spawned :D
                if ev.ant_type == AntTypes.SETTLER:
                    settler_ants.append(ev.ant_id)
                elif ev.ant_type == AntTypes.WORKER:
                    worker_ants.append(ev.ant_id)
                elif ev.ant_type == AntTypes.FIGHTER:
                    fighter_ants.append(ev.ant_id)
        elif isinstance(ev, ZoneActiveEvent):
            hill = 1
            togo = ev.points
            active_zone = (random.choice(ev.points), stats.hill.MAX_ZONE_TIME + tick -1)
            # iterates through all the worker ants and makes its goal the active hill
            for ant in fighter_ants:
                # randomly selects a position on the hill for the ant to go to
                requests.append(GoalRequest(ant, random.choice(ev.points)))
            for ant_id in settler_ants:
                # randomly selects a position on the hill for the ant to go to
                requests.append(GoalRequest(ant_id, random.choice(ev.points)))
        elif isinstance(ev, ZoneDeactivateEvent):
            hill = 0
            active_zone = None
            # removes 1 instance of all the hills
            # current implementation decreases the probability of picking the hill with less instances
            for i in ev.points:
                if i in zone:
                    zone.remove(i)
            for ant_id in settler_ants:
                if zone:
                    # randomly selects another hill for the ant to go to
                    requests.append(GoalRequest(ant_id, random.choice(zone)))
        elif isinstance(ev, QueenAttackEvent):
            if len(fighter_ants) == 0:
                help_please = 1
            if ev.queen_player_index == my_index:
                for ant_id in fighter_ants:
                    # brings all ants to the teams queen ant
                    requests.append(GoalRequest(ant_id, spawns[my_index]))
            queenHealth[ev.queen_player_index] = ev.queen_hp
        elif isinstance(ev, TeamDefeatedEvent):
            if ev.defeated_index in alive_spawn_indexes:
                alive_spawn_indexes.remove(ev.defeated_index)
        elif isinstance(ev, FoodTileActiveEvent):
            if energy_info[ev.pos]*ev.multiplier*stats.ants.Worker.TRIPS >= max_cost:
                for i in range(len(closest_sites)):
                    if energy_info[ev.pos]*stats.ants.Worker.TRIPS >= max_cost:
                        closest_sites[i].remove(ev.pos)
                    l = 0
                    r = len(closest_sites[i]) - 1
                    x = (energy_info[ev.pos]*ev.multiplier) / distance[i][ev.pos]
                    while l <= r:
                        mid = l + (r - l) // 2
                        if energy_info[closest_sites[i][mid]] / distance[i][closest_sites[i][mid]] == x:
                            closest_sites[i].insert(mid, ev.pos)
                        elif energy_info[closest_sites[i][mid]] / distance[i][closest_sites[i][mid]] < x:
                            r = mid - 1
                        else:
                            l = mid + 1
                    else:
                        closest_sites[i].insert(l, ev.pos)
        elif isinstance(ev, FoodTileDeactivateEvent):
            if (energy_info[ev.pos]*2*stats.ants.Worker.TRIPS) >= max_cost:
                for i in range(len(closest_sites)):
                    closest_sites[i].remove(ev.pos)
                    if energy_info[ev.pos]*stats.ants.Worker.TRIPS >= max_cost:
                        l = len(closest_sites[i]) - 1
                        r = 0
                        x = energy_info[ev.pos] / distance[i][ev.pos]
                        while l <= r:
                            mid = l + (r - l) // 2
                            if energy_info[closest_sites[i][mid]] / distance[i][closest_sites[i][mid]] == x:
                                closest_sites[i].insert(mid, ev.pos)
                            elif energy_info[closest_sites[i][mid]] / distance[i][closest_sites[i][mid]] < x:
                                r = mid - 1
                            else:
                                l = mid + 1
                        else:
                            closest_sites[i].insert(l, ev.pos)


    if hill == 1:
        for ant in settler_ants:
            # randomly selects a position on the hill for the ant to go to
            requests.append(GoalRequest(ant, random.choice(togo)))
    if my_energy > 450:
        go = 1
    elif my_energy < 200:
        go = 0   
        j = random.randint(0, len(spawns))
    
    if j == my_index:
        j -= 1
    
    # Can I spawn ants?
    spawned_this_tick = 0
    if tick % 2:
        wrker_cnt_new = 0
        wrker_cnt_rtrn = 0
    while (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Worker.COST
    ):
        spawned_this_tick += 1
        total_ants += 1
        # ticks less than hill grace period just spawn workers
        if my_energy <= 30:
            requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal= closest_site))
            wrker_cnt_new += 1
            my_energy -= stats.ants.Worker.COST
        else:
            if tick < stats.hill.GRACE_PERIOD:
                requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=closest_sites[my_index][wrker_cnt_new%len(closest_sites)]))
                wrker_cnt_new += 1
                my_energy -= stats.ants.Worker.COST
            elif help_please:
                # guards our queen
                goal = spawns[my_index]
                requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=goal))
                my_energy -= stats.ants.Fighter.COST
            elif hill == 1:
                goal = random.choice(zone)
                # Sends the ant to the active zone if it gets there before the zone ends
                if active_zone is not None and (distance[my_index][active_zone[0]] / stats.ants.Settler.SPEED) + tick <= \
                        active_zone[1]:
                    goal = active_zone[0]
                requests.append(SpawnRequest(AntTypes.SETTLER, id= None, color=(111,111,111), goal = goal))
                my_energy -= stats.ants.Settler.COST
            elif go == 1:
                goal = [i for i in spawns if i != my_index]
                requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=goal[j-1]))
                my_energy -= stats.ants.Fighter.COST
            else:
                # Spawn a random type of ant
                match random.randint(1, 3):
                    case 1:
                        requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal= closest_sites[my_index][wrker_cnt_new%len(closest_sites)]))
                        wrker_cnt_new += 1
                        my_energy -= stats.ants.Worker.COST
                    case 2:
                        goal = None
                        # Chooses a random goal for the fighter
                        fight_type = random.randint(1, 5)
                        match fight_type:
                            case 1:
                                # guards our queen
                                goal = spawns[my_index]
                            case 2:
                                # attacks the closest queen with the lowest health
                                enemy_spawns = [spawns[i] for i in alive_spawn_indexes if i != my_index]
                                queen_sites = list(sorted(enemy_spawns, key=lambda prod: queenHealth[spawns.index(prod)]
                                                                                            / distance[my_index][prod], reverse=True))
                                goal = queen_sites[0]
                            case 3:
                                # protect worker ant's
                                goal = closest_sites[my_index][random.randrange((wrker_cnt_new % len(closest_sites)) + 1)]
                            case 4:
                                # attack the closest food tiles to alive enemy's
                                goal = closest_sites[random.choice(alive_spawn_indexes)][0]
                            case 5:
                                if zone:
                                    goal = random.choice(zone)
                                    # Sends the ant to the active zone if it gets there before the zone ends
                                    if active_zone is not None and (
                                            distance[my_index][active_zone[0]] / stats.ants.Settler.SPEED) + tick <= \
                                            active_zone[1]:
                                        goal = active_zone[0]
                        requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=goal))
                        my_energy -= stats.ants.Fighter.COST
                    case 3:
                        if zone:
                            goal = random.choice(zone)
                            # Sends the ant to the active zone if it gets there before the zone ends
                            if active_zone is not None and (distance[my_index][active_zone[0]] / stats.ants.Settler.SPEED) + tick <= \
                                    active_zone[1]:
                                goal = active_zone[0]
                            requests.append(SpawnRequest(AntTypes.SETTLER, id=None, color=None, goal=goal))
                            my_energy -= stats.ants.Settler.COST
                
    tick += 1
    return requests
