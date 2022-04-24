################################# IMPORTS ########################################
from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import SpawnEvent, MoveEvent, DieEvent, AttackEvent, DepositEvent, ProductionEvent, \
    ZoneActiveEvent, ZoneDeactivateEvent, FoodTileActiveEvent, FoodTileDeactivateEvent, SettlerScoreEvent, \
    QueenAttackEvent, TeamDefeatedEvent  # '\' used to continue code onto a new line
from codequest22.server.requests import GoalRequest, SpawnRequest
from random import randint


######################################## CODE #####################################

def get_team_name():
    return f"We Need A <br>"


my_index = None


def read_index(player_index, n_players):
    global my_index
    my_index = player_index


ticks = 0  # Set a variable to count the ticks
my_energy = stats.general.STARTING_ENERGY  # Defines our starting energy
map_data = {}  # Will hold map data, updated later in the read_map() function
spawns = [None] * 4  # Will hold spawn locations, updated in read_map() function
food = []  # holds location of all food
distance = {}
closest_site = None  # Gets closest food site
total_ants = 0  # Gives the total ants we've spawned
closest_food_sites = []  # Holds closest 3 food sites
supercharged_site = []  # Holds data on the supercharged sites
hills = []  # variable to hold the position of all hills
future_spawn = []  # use this to define any spawns you deprioritise

#Try using dictionary to store value of different ant ids
#For each different ant, include [ant_id, goal]
ants = {
    "total": 0,
    "Worker": [],
    "Settler": [],
    "Fighter": []

}

closest_spawn_sites = []
attack_queen = None


#Different Maps: assymetric.json, claustrophobic.json, cornered.json, open.json, small.json


def read_map(md, energy_info):
    # Use global to access variables outside scope
    global map_data, spawns, food, distance, closest_site, closest_food_sites, hills, attack_queen, closest_spawn_sites
    map_data = md
    for y in range(len(map_data)):
        for x in range(len(map_data[0])):
            # Get any Food tiles
            if map_data[y][x] == "F":
                food.append((x, y))

            # Get any spawn locations
            if map_data[y][x] in "RBYG":
                spawns["RBYG".index(map_data[y][x])] = (x, y)

            # Read spawn locations
            if map_data[y][x] == "Z":
                hills.append((x, y))  # append the locations to the hills list

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
        for a, b in [(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)]:
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
    closest_food_sites = food_sites[:3]
    closest_spawn_sites = list(sorted(spawns, key=lambda prod: distance[prod]))
    attack_queen = closest_spawn_sites[1]





def handle_failed_requests(requests):
    global my_energy
    for req in requests:
        if req.player_index == my_index:
            print(req)
            print(f"Request {req.__class__.__name__} failed. Reason: {req.reason}.")
            raise ValueError()


def handle_events(events):
    global my_energy, total_ants, ticks, map_data, supercharged_site, future_spawn, closest_spawn_sites, attack_queen, ants

    requests = [] #Requests, updated as an empty list each tick
    spawned_this_tick = 0  # Use spawned this tick and reset every time we handle events
    ticks += 1  # increment ticks

    # Pre-Game
        #- Send worker ants out
        #- Plan to send 3 workers and 1 fighter if possible, else 4 workers
    if (ticks < 100):
        for i in range(4):
            if i == 3:
                if (total_ants < stats.general.MAX_ANTS_PER_PLAYER and spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and my_energy > stats.ants.Fighter.COST):
                    #requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=attack_queen))
                    #spawned_this_tick += 1
                    #total_ants += 1
                    requests.append(spawn_fighter(attack_queen))
                    spawned_this_tick +=1

                elif (total_ants < stats.general.MAX_ANTS_PER_PLAYER and spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and my_energy > stats.ants.Worker.COST):
                    # Spawn an ant, give it some id, no color, and send it to the closest site.
                    # I will pay the base cost for this ant, so cost=None.
                    # requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=closest_site))
                    # my_energy -= stats.ants.Worker.COST
                    # total_ants += 1
                    requests.append(spawn_worker(closest_site))
                    spawned_this_tick += 1

            elif (total_ants < stats.general.MAX_ANTS_PER_PLAYER and spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and my_energy > stats.ants.Worker.COST):
                # requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=closest_site))
                # my_energy -= stats.ants.Worker.COST
                # total_ants += 1
                requests.append(spawn_worker(closest_site))
                spawned_this_tick += 1

    # Early-Game
        #- Start sending fighter ants out to attack
        #- Send settlers & fighters when hill zones activate
        #- Send worker ants when required
        #- Figure out ratio of energy collected and fighter ant cost
    elif (ticks >= 100 and ticks < 750):

        #Want to have a good amount of energy to use, so send workers if energy < 350 and we don't have any active workers
        if my_energy <= 350 and len(ants['Worker']) < 5:
            requests.append(spawn_worker(closest_site))
            spawned_this_tick += 1 #increment spawned_this_tick

        #When the number of ticks is divisible by 50 and parameters are good enough to send out a fighter
        if (ticks%50 == 0 and total_ants < stats.general.MAX_ANTS_PER_PLAYER and spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and my_energy > stats.ants.Fighter.COST):
            #Send a fighter to attack closest queen
            requests.append(spawn_fighter(attack_queen))
            spawned_this_tick += 1 #increment spawned_this_tick

    # End-Game ( 750 > ticks)
        #- Send out more fighters
        #- Continue to send settlers (less than during midgame)
        #- Send enough workers to sustain fighters
    else:

        #Want to have a good amount of energy to use, so send workers if energy < 350 and we don't have any active workers
        if my_energy <= 350 and len(ants['Worker']) < 5:
            requests.append(spawn_worker(closest_site))
            spawned_this_tick += 1 #increment spawned_this_tick

        #When the number of ticks is divisible by 30 and parameters are good enough to send out a fighter
        if (ticks%30 == 0 and total_ants < stats.general.MAX_ANTS_PER_PLAYER and spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and my_energy > stats.ants.Fighter.COST):
            #Send a fighter to attack closest queen
            requests.append(spawn_fighter(attack_queen))
            spawned_this_tick += 1 #increment spawned_this_tick


    for ev in events:

        # ANT DIES, need this first to process any deaths and reactions
        if isinstance(ev, DieEvent):
            #Check if the player index is my index and dies of old age
            if ev.player_index == my_index and ev.old_age:
                # One of my workers just died :(
                total_ants -= 1

                # Remove the ant id from the dictionary
                # Worker
                if ev.ant_id[0] == "W":
                    for i in range(len(ants['Worker'])):
                        if ev.ant_id == ants['Worker'][i][0]:
                            ants['Worker'].pop(i)
                            break
                # Settler
                elif ev.ant_id[0] == "S":
                    for i in range(len(ants['Settler'])):
                        if ev.ant_id == ants['Settler'][i][0]:
                            ants['Settler'].pop(i)
                            break
                # Fighter
                elif ev.ant_id[0] == "F":
                    for i in range(len(ants['Fighter'])):
                        if ev.ant_id == ants['Fighter'][i][0]:
                            ants['Fighter'].pop(i)
                            break

            # Checks if player index is my index and if killed (not old age)
            elif ev.player_index == my_index and ev.old_age == False:

                # If a worker is attacked, then that means food supply is in danger, so we must send a fighter out
                # If it is a Worker, we want to get their goal an send a fighter their way
                if ev.ant_id[0] == "W":
                    location = None  # get a location
                    for i in range(len(ants['Worker'])):
                        if ev.ant_id == ants['Worker'][i][0]:
                            location = ants['Worker'][i][1]
                            ants['Worker'].pop(i)
                            break

                    #COMMENTED OUT BECAUSE WE CAN"T GUARANTEE THAT THE FIGHTER IS ALIVE
                    # Check if we have any active fighters, we will only send one if we have an available fighter
                    # if len(ants['Fighter']) != 0:
                    #     for i in range(len(ants['Fighter'])):
                    #         # As long as the worker isn't guarding the queen
                    #         if ants['Fighter'][i][1] != spawns[my_index]:
                    #             # Make a request to change the fighter's goal
                    #             requests.append(GoalRequest(ants['Fighter'][i][0], location))
                    #             # Update goal in our ants dictionary
                    #             ants['Fighter'][i][1] = location
                    #             break

                    # If we don't have any active fighters, make a request for a fighter
                    if (total_ants < stats.general.MAX_ANTS_PER_PLAYER and spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and my_energy >= stats.ants.Fighter.COST):
                        requests.append(spawn_fighter(location))  # Make request for fighter
                        spawned_this_tick += 1  # increment the number spawned this tick
                        my_energy -= stats.ants.Fighter.COST  # decrement the cost of fighter


                # In cases of settler and fighter, its not worth sending a fighter out
                # Settler
                elif ev.ant_id[0] == "S":
                    for i in range(len(ants['Settler'])):
                        if ev.ant_id == ants['Settler'][i][0]:
                            ants['Settler'].pop(i)
                            break
                # Fighter
                elif ev.ant_id[0] == "F":
                    for i in range(len(ants['Fighter'])):
                        if ev.ant_id == ants['Fighter'][i][0]:
                            ants['Fighter'].pop(i)
                            break

        #FOOD IS DEPOSITED AT QUEEN
        elif isinstance(ev, DepositEvent):
            if ev.player_index == my_index:
                # One of my worker ants just made it back to the Queen! Let's send them back to the food site.
                requests.append(GoalRequest(ev.ant_id, closest_site))
                for i in range(len(ants['Worker'])):
                    if ev.ant_id == ants['Worker'][i][0]:
                        ants['Worker'][i][1] == closest_site
                        break
                # Additionally, let's update how much energy I've got.
                my_energy = ev.cur_energy

        #FOOD IS COLLECTED
        elif isinstance(ev, ProductionEvent):
            if ev.player_index == my_index:
                # One of my worker ants just made it to the food site! Let's send them back to the Queen.
                requests.append(GoalRequest(ev.ant_id, spawns[my_index]))
                for i in range(len(ants['Worker'])):
                    if ev.ant_id == ants['Worker'][i][0]:
                        ants['Worker'][i][1] == spawns[my_index]
                        break

        #FOOD TILE IS ACTIVE
        elif isinstance(ev, FoodTileActiveEvent):
            # Find location of supercharged site
            supercharged_site = ev.pos
            multiplier = ev.multiplier  # how much more food does this site have?
            # Check distance to site
            dist = DijkstraAlg(spawns[my_index], map_data)  # distances from start
            dist_to_supercharged = dist[supercharged_site]
            # Check if its worth going to the supercharged site
            if (dist_to_supercharged <= multiplier * dist[closest_site]):
                #requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=supercharged_site))
                requests.append(spawn_worker(supercharged_site))
                spawned_this_tick += 1

        
        #ZONE ACTIVATION
        elif isinstance(ev, ZoneActiveEvent):
            # points are the coordinates of the hill and num_ticks are how long it goes for

            # first get location of the active zone
            location = ev.points  # location of active zone
            time = ev.num_ticks  # time it stays on for

            # check if it is feasible to send an ant there, speed of settler is 1.5
            dist = DijkstraAlg(spawns[my_index], map_data)  # distances from start
            closest_hills = list(sorted(location, key=lambda prod: dist[prod]))  # sort locations by distance away
            dist_to_hill = dist[closest_hills[0]]  # get the closest active square

            # if it is feasible to send it, we spawn an ant
            if ((time > dist_to_hill / stats.ants.Settler.SPEED) and total_ants < stats.general.MAX_ANTS_PER_PLAYER): #and my_energy >= stats.ants.Settler.COST + stats.ants.Fighter.COST):
                # check if there are more than 3 spawns this tick
                if spawned_this_tick > 3:
                    #Loop through all the elements in request
                    for i in range(len(requests)):
                        #If the number we spawn is at 3, ignore the rest of the elements
                        if spawned_this_tick == 3:
                            continue

                        #if not, we check if the element has the key 'SpawnRequest' and that the request is for 'WORKER'
                        elif 'SpawnRequest' in requests[i] and requests[i]['SpawnRequest'][0] == 'WORKER':
                            #if it is:
                            my_energy += stats.ants.Worker.COST #Add cost of worker to our energy
                            spawned_this_tick -= 1 #decrement num spawned this tick
                            total_ants -= 1 #decrement the number of ants
                            for j in range(len(ants['Worker'])):
                                if ants['Worker'][j][0] == requests[i]['SpawnRequest'][1]:
                                    ants['Worker'].pop(j) #remove the id of ant we wanted to spawn
                                    break
                            requests.pop(i) #remove the request at the index i

                #Check if we can spawn both a settler and fighter now
                if (my_energy >= stats.ants.Settler.COST + stats.ants.Fighter.COST):
                    requests.append(spawn_settler(closest_hills[0]))
                    requests.append(spawn_fighter(closest_hills[0]))
                    spawned_this_tick += 2

                #if we can't check if we can spawn 2 settlers
                elif (my_energy >= stats.ants.Settler.COST + stats.ants.Settler.COST):
                    requests.append(spawn_settler(closest_hills[0]))
                    requests.append(spawn_settler(closest_hills[0]))
                    spawned_this_tick += 2

                #if we can't check if we can spawn a settler and worker
                elif (my_energy >= stats.ants.Settler.COST + stats.ants.Worker.COST):
                    requests.append(spawn_settler(closest_hills[0]))
                    requests.append(spawn_fighter(closest_food_sites[0]))
                    spawned_this_tick += 2

                #if we can't check if we can just spawn a settler
                elif (my_energy >= stats.ants.Settler.COST):
                    requests.append(spawn_settler(closest_hills[0]))
                    spawned_this_tick += 1

                #if not respawn 2 workers
                elif (my_energy >= stats.ants.Worker.COST + stats.ants.Worker.COST):
                    requests.append(spawn_settler(closest_hills[0]))
                    requests.append(spawn_settler(closest_hills[0]))
                    spawned_this_tick += 2

        #SPAWNING
        elif isinstance(ev, SpawnEvent):
            #print(f'Ant type: {ev.ant_type}')
            #print(f'Player index: {ev.player_index}')
            #print(f'Goal {ev.goal}')
            pass

        #MOVE EVENT
        elif isinstance(ev, MoveEvent):
            pass

        #QUEEN ATTACKED
        elif isinstance(ev, QueenAttackEvent):
            if ev.queen_player_index == my_index:
                #requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=spawns[my_index]))
                #my_energy -= stats.ants.Fighter.COST
                requests.append(spawn_fighter(spawns[my_index]))
                spawned_this_tick += 1

        elif isinstance(ev, AttackEvent):
            pass

        #TEAM IS DEFEATED
        elif isinstance(ev, TeamDefeatedEvent):
            if spawns[ev.defeated_index] == attack_queen and ev.by_index != my_index:
                attack_queen = spawns[ev.by_index]
            else:
                closest_spawn_sites.remove(attack_queen)
                attack_queen = closest_spawn_sites[1]

    #print(f'Player: {my_index}, Total Ants: {total_ants}, Spawned this Tick: {spawned_this_tick}, Energy: {my_energy}')
    #print(ants)
    #print(f'Player: {my_index}')
    #print(f'Energy: {my_energy}')
    #print(f'Requests: {requests}')
    return requests





def spawn_worker(goal: tuple):
    """
    Will return a SpawnRequest for a worker.
    :param goal: A tuple of coordinates that indicates the goal of the ant.
    :return: returns SpawnRequest
    """
    global total_ants, my_energy
    total_ants += 1
    my_energy -= stats.ants.Worker.COST
    ants["total"] += 1
    ids = 'W'+str(ants["total"])
    ants["Worker"].append([ids, goal])
    return SpawnRequest(AntTypes.WORKER, id=ids, color=None, goal=goal)


def spawn_fighter(goal: tuple):
    """
    Will return a SpawnRequest for a fighter.
    :param goal: A tuple of coordinates that indicates the goal of the ant.
    :return: returns SpawnRequest
    """
    global total_ants, my_energy
    total_ants += 1
    my_energy -= stats.ants.Fighter.COST
    ants["total"] += 1
    ids = 'F' + str(ants["total"])
    ants["Fighter"].append([ids, goal])
    return SpawnRequest(AntTypes.FIGHTER, id=ids, color=None, goal=goal)


def spawn_settler(goal: tuple):
    """
    Will return a SpawnRequest for a settler.
    :param goal: A tuple of coordinates that indicates the goal of the ant.
    :return: returns SpawnRequest
    """
    global total_ants, my_energy
    total_ants += 1
    my_energy -= stats.ants.Settler.COST
    ants["total"] += 1
    ids = 'S' + str(ants["total"])
    ants["Settler"].append([ids, goal])
    return SpawnRequest(AntTypes.SETTLER, id=ids, color=None, goal=goal)


def DijkstraAlg(startpoint, map_data):
    """
    Function that return the distance to each point from a given start point.
    :param startpoint: A tuple containing the coordinates of the point you want to start from.
    :param map_data: A list of lists, that contains map elements, given to us by the server.
    :return: returns a dictionary where each point has its given distance defined from the start point.
    """

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
    return distance



####################################################################################################
#################################### EXTRA CODE ####################################################
####################################################################################################

"""
    if (ticks == 10):
        #for i in range(5):
        total_ants += 1
        # Spawn an ant, give it some id, no color, and send it to the closest site.
        # I will pay the base cost for this ant, so cost=None.
        requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=closest_site))
        requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=closest_site))
        my_energy -= (stats.ants.Worker.COST + stats.ants.Fighter.COST)

    if (ticks == 40):
        # Find location of closest spawn point
        dist = DijkstraAlg(spawns[my_index], map_data) #distances from start
        closest_spawn_sites = list(sorted(spawns, key=lambda prod: dist[prod]))
        attack_queen = closest_spawn_sites[1]
        # Send fighter ant to attack queen
        requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=attack_queen))
        #print(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=closest_spawn_sites[1]) == "SpawnRequest")
        my_energy -= stats.ants.Fighter.COST
        total_ants += 1


    if (ticks%40 == 0):
        for i in range(5):
            total_ants += 1
            # Spawn an ant, give it some id, no color, and send it to the closest site.
            # I will pay the base cost for this ant, so cost=None.
            requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=closest_site))
            my_energy -= stats.ants.Worker.COST


    #We will spawn worker ants in the first 30 ticks of the game and subsequently every 30 ticks
    if ((ticks <= 30) or (ticks % 30 == 0)): #need a constant flow of energy, so spawn in first 30 seconds and every 30 seconds

        #SHOULD WE MAYBE INSTEAD ONLY SPAWN 2 OR 3 WORKERS EVERY 30, TO NOT REACH MAX ANTS?

        spawned_this_tick = 0 #Counts how many we've spawned this tick
        while (
                total_ants < stats.general.MAX_ANTS_PER_PLAYER and
                spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
                my_energy >= stats.ants.Worker.COST
        ):
            spawned_this_tick += 1
            total_ants += 1
            # Spawn an ant, give it some id, no color, and send it to the closest site.
            # I will pay the base cost for this ant, so cost=None.
            requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=closest_site))
            my_energy -= stats.ants.Worker.COST

    # Can I spawn ants?
    spawned_this_tick = 0
    while (
        total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
        spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
        my_energy >= stats.ants.Worker.COST
    ):
        spawned_this_tick += 1
        total_ants += 1
        # Spawn an ant, give it some id, no color, and send it to the closest site.
        # I will pay the base cost for this ant, so cost=None.
        requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=closest_site))
        my_energy -= stats.ants.Worker.COST

        #requests.append(SpawnRequest(AntTypes.SETTLER, id=None, color=None, goal=test_site))
        #my_energy -= stats.ants.Settler.COST

    def SpawnWorkers(num=0):
        global requests, total_ants, my_energy #Access the globals
        # Can I spawn ants?
        spawned_this_tick = 0
        while (
            spawned_this_tick <= num and
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Worker.COST
        ):
            spawned_this_tick += 1
            total_ants += 1
            # Spawn an ant, give it some id, no color, and send it to the closest site.
            # I will pay the base cost for this ant, so cost=None.
            requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=closest_site))
            my_energy -= stats.ants.Worker.COST
"""