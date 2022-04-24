from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import DepositEvent, DieEvent, ProductionEvent, ZoneActiveEvent, ZoneDeactivateEvent, FoodTileActiveEvent, FoodTileDeactivateEvent, QueenAttackEvent,TeamDefeatedEvent, SpawnEvent, MoveEvent
from codequest22.server.requests import GoalRequest, SpawnRequest
from collections import defaultdict
import math
import random

def get_team_name():
    return f"Joe"

my_energy = stats.general.STARTING_ENERGY

map_data = {}
spawns = [None]*4
food = []
distance = {}
total_ants = 0

zones = []

# init players
num_players = None
my_index = None


worker = {}
# worker = {
#     "{id}":{
#         "site":Tuple(Coords),
#     }
# }

# food_sites_best_props = {
#     "coords": [], # dont change except in DepositEvent!!
#     "efficiency": [],
#     "closest_to_enemy": [],
# }
food_sites_best_props = {}
# food_sites_best = [(efficiency,(coords))]
food_sites_best = None
# food_sites_props = {
#     "tuple(coords)":{
#         "energy":int,
#         "distance":int,
#         "efficiency":float,
#     },
#     "tuple(coords)"...
# }

# food_sites_active = {
#     "tuple(coords)":{
#         "max_workers":int,
#         "current_workers":int,
#     },...
# }

enemy_near_in_order = [0] * 4

food_sites_active = {}
def read_index(player_index, n_players):
    global my_index, num_players
    my_index = player_index
    num_players = n_players

def read_map(md, energy_info):
    global map_data, closest_site, food_sites, food_sites_active, food_sites_best_props, food_sites_best, danger_zone, enemy_near_in_order, enemies
    map_data = md

    # make it load just once
    row_size = range(len(map_data[0]))

    for y in range(len(map_data)):
        for x in row_size:
            if map_data[y][x] == "F":
                food.append((x,y))
            elif map_data[y][x] == "Z":
                zones.append((x, y))
            elif map_data[y][x] in "RBYG":
                spawns["RBYG".index(map_data[y][x])] = (x,y)
    
    danger_zone = math.floor(len(food)/4)
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
    players = [i for i in range(num_players)]
    players.insert(0, players.pop(players.index(my_index)))
    enemies = [i for i in range(num_players)]
    enemies.pop(my_index)
    for player in players:
        startpoint = spawns[player]
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
        food_sites = list(sorted(food, key=lambda prod: distance[prod]))
        if player == my_index:
            enemy_near_in_order = sorted(spawns[:num_players], key=lambda kv: distance[kv])
            # print(enemy_near_in_order)
        if(player in enemies):
            for how_close in range(danger_zone):
                index = food_sites_best_props[food_sites[how_close]]["closest_to_enemy"]
                if(how_close < food_sites_best_props[food_sites[how_close]]["closest_to_enemy"]):
                    food_sites_best_props[food_sites[how_close]]["closest_to_enemy"] = how_close
            for site in food_sites_best_props:
                if(food_sites_best_props[site]["nearest_distance_to_enemy"] > distance[site]):
                    food_sites_best_props[site]["nearest_distance_to_enemy"] = distance[site]
        else:
            # assign properties
            for site in food_sites:
                food_sites_best_props[site] = {
                    "timey": distance[site]*2 / ((stats.ants.Worker.SPEED + stats.ants.Worker.ENCUMBERED_RATE) / 2),
                    "energy": energy_info[site],
                    "closest_to_enemy": len(food_sites),
                    "distance": distance[site]*2
                }
                food_sites_best_props[site]["efficiency"] = food_sites_best_props[site]["energy"] / food_sites_best_props[site]["timey"]
                food_sites_best_props[site]["priority"] = food_sites_best_props[site]["efficiency"] 
                food_sites_best_props[site]["nearest_distance_to_enemy"] = 999999
                food_sites_active[site] = {
                    "max_workers": math.ceil(food_sites_best_props[site]["timey"] / 2),
                    "current_workers": 0
                }
    for site in food_sites_best_props:
        food_sites_best_props[site]["priority"] = getPriority(food_sites_best_props[site])
    food_sites_best = sorted(food_sites_best_props.items(), key=lambda x: x[1]["priority"],reverse=True)
def getPriority(site: dict) -> float:
    # max_distance = 0
    # for sitey in food_sites_best_props:
    #     if(food_sites_best_props[sitey]["nearest_distance_to_enemy"] > max_distance):
    #         max_distance = food_sites_best_props[sitey]["nearest_distance_to_enemy"]
    # priority = (site["efficiency"] / math.pow((max_distance - site["nearest_distance_to_enemy"] + 1),0.2))
    # if(site["closest_to_enemy"] != len(food)):
    #     priority /= ((danger_zone - site["closest_to_enemy"] + 2) / 2)
    priority = site["efficiency"] / site["distance"]
    return priority

def handle_failed_requests(requests):
    global my_energy
    for req in requests:
        if req.player_index == my_index:
            print(f"Request {req.__class__.__name__} failed. Reason: {req.reason}.")
            raise ValueError()

reiner = {} # kill settlers
bertolt = {} # protect ally food
suzaku = {} # protect the queen
annie = {} # infiltrate oponnent food and queen
settler = {}


zone_is_active = False
zone_tick = 0
current_tick = 0
queen_is_attacked = False
my_queen_tick = 0
active_hill = None

queen_alive = [True]*4

# enemy_food_sites = {
#     0: [],
#     1: [],
#     2: [],
#     3: [],
# }

enemy_food_sites = {
    0: {
        "ant_ids": [],
        "coords": []
    },
    1: {
        "ant_ids": [],
        "coords": []
    },
    2: {
        "ant_ids": [],
        "coords": []
    },
    3: {
        "ant_ids": [],
        "coords": []
    },
}

enemy_all_food_sites = {
    0: [],
    1: [],
    2: [],
    3: []
}

no_more_workers = [False]*4

all_technically_dead = True
already_half = False
already_half_zones = False

def attack_random_enemy():
    goal_found = False
    for spawn_coord in enemy_near_in_order[1:]:
        index = spawns.index(spawn_coord)
        goal = spawns[index]
        if queen_alive[index] and not no_more_workers[index]:
            for coord in enemy_food_sites[index]["coords"]:
                if coord != None:
                    goal = coord
                    goal_found = True
                    break
        if goal_found:
            break
    if all_technically_dead and already_half and already_half_zones:
        for enemy in enemies:
            if queen_alive[enemy]:
                goal = spawns[enemy]
                index = enemy
                break

    return goal, index

def go_protect_food_sites():
    choice = random.choice(list(worker.values()))
    return choice["site"]

latest_queen_death_index = None

at_least_one_reached = False

check_queen_death_once = False

no_more_workers_tick = [0]*4
NO_MORE_WORKERS_TIMEOUT = 50
save_up = False
will_send_settler = False
workers_current_tick = {}
workers_current_position = {}
workers_current_tick_state = {}
zone_count = 0
# maybe using in the future
def handle_events(events):
    global my_energy, total_ants, zones, worker, settler, food_sites_best, current_tick, zone_is_active, will_send_settler
    global zone_tick, queen_is_attacked, my_queen_tick, reiner, bertolt, suzaku, annie, queen_alive, my_index
    global active_hill, latest_queen_death_index, food_sites, enemy_food_sites, check_queen_death_once, save_up, no_more_workers, no_more_workers_tick
    global at_least_one_reached, workers_current_position, workers_current_tick, workers_current_tick_state, all_technically_dead, zone_count
    global already_half, already_half_zones
    requests = []
    current_tick += 1
    # print(current_tick, int(stats.general.SIMULATION_TICKS / 2))
    if current_tick > int(stats.general.SIMULATION_TICKS / 2):
        already_half = True

    if zone_count > int(len(zones) * stats.hill.NUM_ACTIVATIONS * 2 / 5):
        already_half_zones = True
    
    all_technically_dead = True
    for enemy in enemies:
        if not no_more_workers[enemy]:
            all_technically_dead = False
            no_more_workers_tick[enemy] += 1
            if no_more_workers_tick[enemy] >= NO_MORE_WORKERS_TIMEOUT:
                # print(no_more_workers[enemy])
                no_more_workers[enemy] = True

    for ev in events:
        if isinstance(ev, DepositEvent):
            if ev.player_index != my_index:
                no_more_workers_tick[ev.player_index] = 0
            if ev.player_index == my_index:
                # set returning site for request
                # change site to (current) most efficient site
                returning_site = worker[ev.ant_id]["site"]
                requests.append(GoalRequest(ev.ant_id, returning_site))
                
                # Additionally, let's update how much energy I've got.
                my_energy = ev.cur_energy
                
        elif isinstance(ev, SpawnEvent):
            if ev.player_index != my_index and ev.ant_type == AntTypes.WORKER:
                enemy_food_sites[ev.player_index]["ant_ids"].append(ev.ant_id)
                enemy_food_sites[ev.player_index]["coords"].append(None)

        elif isinstance(ev, ProductionEvent):
            if ev.player_index == my_index:
                # One of my worker ants just made it to the food site! Let's send them back to the Queen.
                requests.append(GoalRequest(ev.ant_id, spawns[my_index]))
                    
        elif isinstance(ev, FoodTileActiveEvent):
            # check if after overcharge is more efficient than any other tiles by sorting again after multiplying overcharged efficiency
            pos = ev.pos 
            food_sites_best_props[pos]["efficiency"] *= ev.multiplier
            food_sites_best_props[pos]["priority"] = getPriority(food_sites_best_props[pos])
            food_sites_best = sorted(food_sites_best_props.items(), key=lambda x: x[1]["priority"],reverse=True)

        elif isinstance(ev, FoodTileDeactivateEvent):
            # set back to original efficiency
            pos = ev.pos
            food_sites_best_props[pos]["efficiency"] = food_sites_best_props[pos]["energy"] / food_sites_best_props[pos]["timey"]
            food_sites_best_props[pos]["priority"] = getPriority(food_sites_best_props[pos])
            food_sites_best = sorted(food_sites_best_props.items(), key=lambda x: x[1]["priority"],reverse=True)
        
        elif isinstance(ev, ZoneActiveEvent):
            zone_tick = 0
            zone_is_active = True
            active_hill = zones[ev.zone_index]
            zone_count += 1

        elif isinstance(ev, QueenAttackEvent):
            if ev.queen_player_index == my_index:
                queen_is_attacked = True

        elif isinstance(ev, ZoneDeactivateEvent):
            for senshi in reiner:
                goal, _ = attack_random_enemy()
                reiner[senshi]["goal"] = goal
                requests.append(GoalRequest(senshi, goal))

        elif isinstance(ev, TeamDefeatedEvent):
            latest_queen_death_index = ev.defeated_index
            queen_alive[ev.defeated_index]= False
            check_queen_death_once = True
        
        elif isinstance(ev, DieEvent):
            if ev.player_index == my_index:
                # One of my workers just died :(
                if "worker" in ev.ant_id:
                    id = worker[ev.ant_id] 
                    # remove worker from food_sites_active to replace
                    food_sites_active[id["site"]]["current_workers"] -= 1
                    # if id["site"] != workers_current_position[ev.ant_id]:
                    #     food_sites_best_props[id["site"]]["efficiency"] = (food_sites_best_props[id["site"]]["energy"] / food_sites_best_props[id["site"]]["timey"]) / 10
                    #     food_sites_best_props[id["site"]]["priority"] = getPriority(food_sites_best_props[id["site"]])
                    #     food_sites_best = sorted(food_sites_best_props.items(), key=lambda x: x[1]["priority"],reverse=True)
                    #     workers_current_tick[id["site"]] = 0
                    #     workers_current_tick_state[id["site"]] = True
                    worker.pop(ev.ant_id)
                elif "settler" in ev.ant_id:
                    settler.pop(ev.ant_id)
                elif "reiner" in ev.ant_id:
                    reiner.pop(ev.ant_id)
                elif "bertolt" in ev.ant_id:
                    bertolt.pop(ev.ant_id)
                elif "suzaku" in ev.ant_id:
                    suzaku.pop(ev.ant_id)
                elif "annie" in ev.ant_id:
                    annie.pop(ev.ant_id)
                
                total_ants -= 1
            elif ev.ant_id in enemy_food_sites[ev.player_index]["ant_ids"]:
                    index = enemy_food_sites[ev.player_index]["ant_ids"].index(ev.ant_id)
                    del enemy_food_sites[ev.player_index]["ant_ids"][index]
                    del enemy_food_sites[ev.player_index]["coords"][index]
                
    if check_queen_death_once and latest_queen_death_index != None:
        check_queen_death_once = False
        for senshi in annie:
            if annie[senshi]["goal"] == spawns[latest_queen_death_index] or annie[senshi]["goal"] in enemy_food_sites[latest_queen_death_index]:
                goal, _ = attack_random_enemy()
                requests.append(GoalRequest(senshi, goal))
        for senshi in reiner:
            if reiner[senshi]["goal"] == spawns[latest_queen_death_index] or reiner[senshi]["goal"] in enemy_food_sites[latest_queen_death_index]:
                goal, _ = attack_random_enemy()
                requests.append(GoalRequest(senshi, goal))

    for ev in events:
        if isinstance(ev, MoveEvent):
            if ev.player_index == my_index:
                # if "bertolt" in ev.ant_id and ev.ant_id in bertolt:
                #     if ev.position == bertolt[ev.ant_id]["goal"]:
                #         requests.append(GoalRequest(ev.ant_id, spawns[my_index]))
                #     elif ev.position == spawns[my_index]:
                #         requests.append(GoalRequest(ev.ant_id, bertolt[ev.ant_id]["goal"]))

                if "worker" in ev.ant_id and ev.ant_id in worker:
                    workers_current_position[ev.ant_id] = ev.position

                elif "annie" in ev.ant_id and ev.ant_id in annie:
                    if ev.position == annie[ev.ant_id]["goal"]:
                        # print(spawns[annie[ev.ant_id]["enemy_queen"]])
                        requests.append(GoalRequest(ev.ant_id, spawns[annie[ev.ant_id]["enemy_queen"]]))
                    elif annie[ev.ant_id]["goal"] != spawns[annie[ev.ant_id]["enemy_queen"]] and ev.position == spawns[annie[ev.ant_id]["enemy_queen"]]:
                        requests.append(GoalRequest(ev.ant_id, annie[ev.ant_id]["goal"]))
                        
                elif "suzaku" in ev.ant_id and ev.ant_id in suzaku and queen_is_attacked == False:
                    if ev.position == suzaku[ev.ant_id]["goal"]:
                        requests.append(GoalRequest(ev.ant_id, spawns[my_index]))
                    elif ev.position == spawns[my_index]:
                        requests.append(GoalRequest(ev.ant_id, suzaku[ev.ant_id]["goal"]))
                        
            elif ev.ant_id in enemy_food_sites[ev.player_index]["ant_ids"] and ev.position in food_sites:
                enemy_food_sites[ev.player_index]["coords"][enemy_food_sites[ev.player_index]["ant_ids"].index(ev.ant_id)] = ev.position
                at_least_one_reached = True
    
    if zone_is_active:
        zone_tick += 1
        if zone_tick >= stats.hill.MIN_ZONE_TIME:
            zone_is_active = False
            active_hill = None

    # for key in workers_current_tick_state:
    #     if workers_current_tick_state[key]:
    #         workers_current_tick[key] += 1
    #         requests.append(GoalRequest(my_man, spawns[my_index]))
    #         if workers_current_tick[key] >= 10:
    #             for worker_name in worker:
    #                 if worker[worker_name]["site"] in workers_current_tick_state and workers_current_tick_state[worker[worker_name]["site"]]:
    #                     requests.append(GoalRequest(worker_name, worker[worker_name]["site"]))
    #             workers_current_tick_state[key] = False
    #             food_sites_best_props[key]["priority"] = getPriority(food_sites_best_props[key])
    #             food_sites_best = sorted(food_sites_best_props.items(), key=lambda x: x[1]["priority"],reverse=True)
    #         else:
    #             for worker_name in worker:
    #                 if worker[worker_name]["site"] in workers_current_tick_state and workers_current_tick_state[worker[worker_name]["site"]]:
    #                     requests.append(GoalRequest(worker_name, workers_current_position[worker_name]))

    if queen_is_attacked:
        for my_man in suzaku:
            requests.append(GoalRequest(my_man, spawns[my_index]))
        my_queen_tick += 1
        if my_queen_tick >= 5:
            queen_is_attacked = False
            my_queen_tick = 0
            for my_man in suzaku:
                if(len(worker) > 0):
                    goal = go_protect_food_sites()
                else:
                    goal = spawns[my_index]
                requests.append(GoalRequest(my_man, goal))
            
    # Can I spawn ants?
    spawned_this_tick = 0
    WORKER_SPAWN = int(stats.general.MAX_ANTS_PER_PLAYER / 2)
    ANNIE_BATCH_ATTACK_COUNT = (5 if 5 <= stats.general.MAX_SPAWNS_PER_TICK else stats.general.MAX_SPAWNS_PER_TICK)
    SETTLER_SPAWN = int(stats.general.MAX_ANTS_PER_PLAYER / 10) * 2
    target_settler_spawn_counter = 5
    TARGET_SETTLER_SPAWN_BATCH = 5
    # WARRIOR_SPAWN = int(stats.general.MAX_ANTS_PER_PLAYER / 2)
    # MAX_SETTLER_SPAWN_PER_TICK = int(stats.general.MAX_SPAWNS_PER_TICK / 5 * 3)
    # MAX_REINER_SPAWN_PER_TICK = stats.general.MAX_SPAWNS_PER_TICK - MAX_SETTLER_SPAWN_PER_TICK
    MAX_BERTOLT_SPAWN = 4
    # MAX_ANNIE_SPAWN = int(stats.general.MAX_ANTS_PER_PLAYER / 10) * 3
    # MAX_WORKER_SPAWN_PER_TICK = int(stats.general.MAX_SPAWNS_PER_TICK / 5 * 4)
    
    current_tick_annie_spawn = 0
    current_tick_worker_spawn = 0
    current_tick_settler_spawn = 0
    current_tick_reiner_spawn = 0
    current_tick_bertolt_spawn = 0
    MAX_BERTOLT_SPAWN_PER_TICK = 5
    REINER_SPAWN = 3
    
    while (
        total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
        spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK
    ):
        if len(worker) == WORKER_SPAWN:
            save_up = True
        if queen_is_attacked or len(worker) < math.ceil(WORKER_SPAWN/1.5) or len(bertolt) < MAX_BERTOLT_SPAWN:
            save_up = False
            will_send_settler = False
            target_settler_spawn_counter = 0
        
        if queen_is_attacked and my_energy >= stats.ants.Fighter.COST:
            id = 0
            while True:
                name = "suzaku-" + str(id)
                if name not in suzaku:
                    # print("SUZAKU KUN")
                    suzaku[name] = {
                        "id": id,
                        "goal": spawns[my_index]
                    }
                    # the_goal = calculateBattleField(id,food_sites_to_aim)
                    requests.append(SpawnRequest(AntTypes.FIGHTER, id=name, color=None, goal=spawns[my_index]))
                    my_energy -= stats.ants.Fighter.COST
                    spawned_this_tick += 1
                    total_ants += 1
                    break
                id += 1

        elif not queen_is_attacked and not save_up and my_energy >= stats.ants.Worker.COST and len(worker) < WORKER_SPAWN:
            for id in range(WORKER_SPAWN):
                name = "worker-" + str(id)
                if name not in worker:
                    worker_distributor(name)
                    requests.append(SpawnRequest(AntTypes.WORKER, id=name, color=None, goal=worker[name]["site"]))
                    my_energy -= stats.ants.Worker.COST
                    spawned_this_tick += 1
                    total_ants += 1
                    current_tick_worker_spawn += 1
                    break
        
        elif not queen_is_attacked and not save_up and my_energy >= stats.ants.Fighter.COST and len(bertolt) < MAX_BERTOLT_SPAWN and current_tick_bertolt_spawn < MAX_BERTOLT_SPAWN_PER_TICK:
            id = 0
            while True:
                name = "bertolt-" + str(id)
                if name not in bertolt:
                    goal = go_protect_food_sites()
                    bertolt[name] = {
                        "id": id,
                        "goal": goal
                    }
                    # print("I am bertolt")
                    current_tick_bertolt_spawn += 1
                    requests.append(SpawnRequest(AntTypes.FIGHTER, id=name, color=(0,0,0), goal=goal))
                    my_energy -= stats.ants.Fighter.COST
                    spawned_this_tick += 1
                    total_ants += 1
                    break
                id += 1
                
        elif not queen_is_attacked and not will_send_settler and save_up and my_energy >= ANNIE_BATCH_ATTACK_COUNT * stats.ants.Fighter.COST * 1.5 and at_least_one_reached and total_ants + ANNIE_BATCH_ATTACK_COUNT <= stats.general.MAX_ANTS_PER_PLAYER:
            id = 0
            goal, index = attack_random_enemy()
            while spawned_this_tick < ANNIE_BATCH_ATTACK_COUNT:
                name = "annie-" + str(id)
                if name not in annie:
                    annie[name] = {
                        "id": id,
                        "goal": goal,
                        "enemy_queen": index
                    }
                    requests.append(SpawnRequest(AntTypes.FIGHTER, id=name, color=(255,255,255,1), goal=goal))
                    my_energy -= stats.ants.Fighter.COST
                    spawned_this_tick += 1
                    total_ants += 1
                    current_tick_annie_spawn += 1
                id += 1
            if(zone_is_active):
                target_settler_spawn_counter = TARGET_SETTLER_SPAWN_BATCH
                will_send_settler = True
                save_up = True
            else:
                save_up = False
            break
        
        elif not queen_is_attacked and target_settler_spawn_counter > 0 and will_send_settler and my_energy >= stats.ants.Settler.COST and len(settler) < SETTLER_SPAWN:
            if not zone_is_active or zone_tick > stats.hill.MIN_ZONE_TIME:
                save_up = False
                will_send_settler = False
                break
            # spawn_reiner = 0
            # print("I got here")
            if not queen_is_attacked and target_settler_spawn_counter > 0 and will_send_settler and not(all_technically_dead and not (already_half and already_half_zones)):
                # while(my_energy >= stats.ants.Fighter.COST and len(reiner) < REINER_SPAWN and spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK) and spawn_reiner < 1 and total_ants < stats.general.MAX_ANTS_PER_PLAYER:
                #     id = 0
                #     while True:
                #         name = "reiner-" + str(id)
                #         if name not in reiner:
                #             reiner[name] = {
                #                 "goal": active_hill
                #             }
                #             requests.append(SpawnRequest(AntTypes.FIGHTER, id=name, color=(255,255,255), goal=active_hill))
                #             my_energy -= stats.ants.Fighter.COST
                #             spawned_this_tick += 1
                #             total_ants += 1
                #             spawn_reiner += 1
                #             break
                #         id += 1
                while(my_energy >= stats.ants.Settler.COST and len(settler) < SETTLER_SPAWN and spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK) and total_ants < stats.general.MAX_ANTS_PER_PLAYER:
                    for id in range(SETTLER_SPAWN):
                        name = "settler-" + str(id)
                        if name not in settler:
                            settler[name] = id
                            requests.append(SpawnRequest(AntTypes.SETTLER, id=name, color=(255,255,255), goal=active_hill))
                            my_energy -= stats.ants.Settler.COST
                            spawned_this_tick += 1
                            total_ants += 1
                            current_tick_settler_spawn += 1
                            target_settler_spawn_counter -= 1
                            break
                if target_settler_spawn_counter < 0:
                    save_up = False
                    will_send_settler = False
            elif all_technically_dead and not (already_half and already_half_zones):
                while(my_energy >= stats.ants.Settler.COST and spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and total_ants < stats.general.MAX_ANTS_PER_PLAYER):
                    id = 0
                    while True:
                        name = "settler-" + str(id)
                        if name not in settler:
                            settler[name] = id
                            requests.append(SpawnRequest(AntTypes.SETTLER, id=name, color=(255,255,255), goal=active_hill))
                            my_energy -= stats.ants.Settler.COST
                            spawned_this_tick += 1
                            total_ants += 1
                            current_tick_settler_spawn += 1
                            target_settler_spawn_counter -= 1
                            break
                        id += 1
            break
                
        else:
            break
        
    return requests

def worker_distributor(worker_name: str):
    i = 0
    coords = food_sites_best[i][0] # 
    props = food_sites_active[coords]
    while(props["current_workers"] >= props["max_workers"]):
        if(i >= len(food_sites) - 2):
            break
        i += 1
        coords = food_sites_best[i][0]
        props = food_sites_active[coords]
    if(worker_name in worker):
        food_sites_active[coords]["current_workers"] -= 1
    worker[worker_name] = {
        "site": coords,
    }
    food_sites_active[coords]["current_workers"] += 1
            