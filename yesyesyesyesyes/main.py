from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import SpawnEvent, MoveEvent, DieEvent, AttackEvent, DepositEvent, ProductionEvent, ZoneActiveEvent, ZoneDeactivateEvent, FoodTileActiveEvent, FoodTileDeactivateEvent, SettlerScoreEvent, QueenAttackEvent, TeamDefeatedEvent
from codequest22.server.requests import GoalRequest, SpawnRequest

import random

def get_team_name():
    return f"yesyesyesyesyes"

my_index = None
number_of_players = None
enemy_index = [0, 1, 2, 3]
def read_index(player_index, n_players):
    global my_index, number_of_players, enemy_index
    my_index = player_index
    number_of_players = n_players
    enemy_index = enemy_index[:number_of_players]
    enemy_index.remove(my_index)

def handle_failed_requests(requests):
    global my_energy
    for req in requests:
        if req.player_index == my_index:
            print(f"Request {req.__class__.__name__} failed. Reason: {req.reason}.")
            raise ValueError()

my_energy = stats.general.STARTING_ENERGY 
map_data = {}
distance = {}
all_distances = {}
spawns = [None, None, None, None] 
all_ants_info = [{}, {}, {}, {}]
player_scores = [0, 0, 0, 0]
ant_count_data = [{"WorkerAnt": 0, "SettlerAnt": 0, "FighterAnt": 0, "All": 0}, {"WorkerAnt": 0, "SettlerAnt": 0, "FighterAnt": 0, "All": 0}, {"WorkerAnt": 0, "SettlerAnt": 0, "FighterAnt": 0, "All": 0}, {"WorkerAnt": 0, "SettlerAnt": 0, "FighterAnt": 0, "All": 0}]
current_tick = 0

food_sites = {}
food_sites_by_distance = []
sorted_food = []


is_zone = False
zone_time_left = -1
can_reach_all_teams = True
am_defeated = False

uid = 69420










def read_map(md, energy_info): # Read map is called after read_index
    global map_data, spawns, distance, enemy_index, food_sites, food_sites_by_distance, sorted_food, can_reach_all_teams
    map_data = md
    food = []
    for y in range(len(map_data)):
        for x in range(len(map_data[0])):
            if map_data[y][x] == "F":
                food.append((x, y))
            if map_data[y][x] in "RBYG":
                spawns["RBYG".index(map_data[y][x])] = (x, y)
    startpoint = spawns[my_index] # Dijkstra's Algorithm: Find the shortest path from your spawn to each food zone. Step 1: Generate edges - for this we will just use orthogonally connected cells.
    adj = {}
    h, w = len(map_data), len(map_data[0])
    points = [] # A list of all points in the grid
    idx = {} # Mapping every point to a number
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
    import heapq # Step 2: Run Dijkstra's
    expanded = [False] * len(points)
    queue = []
    heapq.heappush(queue, (0, startpoint))
    while queue:
        d, (a, b) = heapq.heappop(queue)
        if expanded[idx[(a, b)]]: continue
        expanded[idx[(a, b)]] = True
        distance[(a, b)] = d
        for j, k, d2 in adj[(a, b)]:
            if not expanded[idx[(j, k)]]:
                heapq.heappush(queue, (d + d2, (j, k)))
    if max([distance[spawns[i]] for i in enemy_index]) >= stats.ants.Fighter.LIFESPAN * stats.ants.Fighter.SPEED:
        can_reach_all_teams = False
    

    def create_map(sp): #i'm sorry i just copied the code from above lmfao
        global all_distances
        startpoint = (round(sp[1]), round(sp[0]))
        if startpoint in all_distances:
            return all_distances[startpoint]
        local_distance = {} # Dijkstra's Algorithm: Find the shortest path from your spawn to each food zone. Step 1: Generate edges - for this we will just use orthogonally connected cells.
        adj = {}
        h, w = len(map_data), len(map_data[0])
        points = [] # A list of all points in the grid
        idx = {} # Mapping every point to a number
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
        if map_data[startpoint[1]][startpoint[0]] == "W": #ORIGINAL CODE FROM HERE ON
            y = startpoint[1]
            x = startpoint[0]
            for a, b in [(y+1, x), (y-1, x), (y, x+1), (y, x-1), (y+1, x+1), (y-1, x-1), (y-1, x+1), (y+1, x-1)]:
                if map_data[a][b] != "W":
                    startpoint = (b, a)
                    break # NOT ORIGINAL CODE AFTER THIS LINE
        import heapq # Step 2: Run Dijkstra's
        expanded = [False] * len(points)
        queue = []
        heapq.heappush(queue, (0, startpoint))
        while queue:
            d, (a, b) = heapq.heappop(queue)
            if expanded[idx[(a, b)]]: continue
            expanded[idx[(a, b)]] = True
            local_distance[(a, b)] = d
            for j, k, d2 in adj[(a, b)]:
                if not expanded[idx[(j, k)]]:
                    heapq.heappush(queue, (d + d2, (j, k)))
        all_distances[startpoint] = local_distance
        return local_distance

    # Now I can calculate the closest food site.
    food_sites_by_distance = list(sorted(food, key=lambda prod: distance[prod]))
    for i in food:
        food_sites[i] = ({"amount": energy_info[i], "multiplier": 1, "enemy": 0, "assigned_ally": []}) # [[(x, y), energyinfo, active?], ...]
    def refresh_food():
        global sorted_food
        food_attractiveness = {}
        enemy_food_distance = [[], [], [], []]
        # for i in enemy_index:
        #     print(spawns[i])
        #     enemy_food_distance[i] = list(sorted(food, key=lambda prod: create_map(spawns[i])[prod]))
        for i in food_sites:
            food_attractiveness[i] = (distance[food_sites_by_distance[-1]] * 3 / 2 - distance[i] * 3 / 5) * food_sites[i]["multiplier"] * 9 / 10 * (1 + food_sites[i]["amount"] * 1/5) 
            # for j in enemy_food_distance:
            #     if i in j:
            #         if j.index(i) < 2:
            #             food_attractiveness[i] *= 2/3
            #             break
        food_attractiveness[food_sites_by_distance[0]] = 99999999
        for i in list(sorted(food_attractiveness, key=lambda x: food_attractiveness[x])):
            sorted_food.append(i)
        sorted_food.reverse()
        # SEE IF THIS IS BETTER
        # sorted_food = food_sites_by_distance
    refresh_food()
    
    







def handle_events(events):
    global my_energy
    global player_scores, all_ants_info, ant_count_data, am_defeated, can_reach_all_teams, current_tick
    global is_zone, zone_time_left, uid
    requests = []

    my_queen_under_attack = False
    my_ant_under_attack = False
    zone_time_left -= 1
    current_tick += 1
    moved_ants_this_round = [[], [], [], []]

    def refresh_food():
        global sorted_food
        food_attractiveness = {}
        for i in food_sites:
            food_attractiveness[i] = (distance[food_sites_by_distance[-1]] * 3 / 2 - distance[i] * 3 / 5) * food_sites[i]["multiplier"] * food_sites[i]["amount"]
        food_attractiveness[food_sites_by_distance[0]] = 99999
        for i in list(sorted(food_attractiveness, key=lambda x: food_attractiveness[x])):
            sorted_food.append(i)
        sorted_food.reverse()
        # SEE IF THIS IS BETTER
        # sorted_food = food_sites_by_distance
    def create_map(sp): #i'm sorry i just copied the code from above lmfao
        global all_distances
        startpoint = (round(sp[1]), round(sp[0]))
        if startpoint in all_distances:
            return all_distances[startpoint]
        local_distance = {} # Dijkstra's Algorithm: Find the shortest path from your spawn to each food zone. Step 1: Generate edges - for this we will just use orthogonally connected cells.
        adj = {}
        h, w = len(map_data), len(map_data[0])
        points = [] # A list of all points in the grid
        idx = {} # Mapping every point to a number
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
        if map_data[startpoint[1]][startpoint[0]] == "W": #ORIGINAL CODE FROM HERE ON
            y = startpoint[1]
            x = startpoint[0]
            for a, b in [(y+1, x), (y-1, x), (y, x+1), (y, x-1), (y+1, x+1), (y-1, x-1), (y-1, x+1), (y+1, x-1)]:
                if map_data[a][b] != "W":
                    startpoint = (b, a)
                    break # NOT ORIGINAL CODE AFTER THIS LINE
        import heapq # Step 2: Run Dijkstra's
        expanded = [False] * len(points)
        queue = []
        heapq.heappush(queue, (0, startpoint))
        while queue:
            d, (a, b) = heapq.heappop(queue)
            if expanded[idx[(a, b)]]: continue
            expanded[idx[(a, b)]] = True
            local_distance[(a, b)] = d
            for j, k, d2 in adj[(a, b)]:
                if not expanded[idx[(j, k)]]:
                    heapq.heappush(queue, (d + d2, (j, k)))
        all_distances[startpoint] = local_distance
        return local_distance

    for ev in events:
        if isinstance(ev, SpawnEvent): 
            all_ants_info[ev.player_index][ev.ant_id] = ev.ant_str
            ant_count_data[ev.player_index][ev.ant_str["classname"]] += 1
            ant_count_data[ev.player_index]["All"] += 1
        elif isinstance(ev, MoveEvent):
            all_ants_info[ev.player_index][ev.ant_id] = ev.ant_str
            moved_ants_this_round[ev.player_index].append(ev.ant_id)
        elif isinstance(ev, DieEvent):
            all_ants_info[ev.player_index].pop(ev.ant_id)
            ant_count_data[ev.player_index][ev.ant_str["classname"]] -= 1
            ant_count_data[ev.player_index]["All"] -= 1
            if ev.player_index == my_index:
                for i in food_sites:
                    if ev.ant_id in food_sites[i]["assigned_ally"]:
                        food_sites[i]["assigned_ally"].remove(ev.ant_id)
                        break
        elif isinstance(ev, AttackEvent):
            if ev.defender_id == my_index:
                my_ant_under_attack = True
        elif isinstance(ev, DepositEvent):
            if ev.player_index == my_index:
                target = sorted_food[0]
                for i in food_sites:
                    if ev.ant_id in food_sites[i]["assigned_ally"]:
                        food_sites[i]["assigned_ally"].remove(ev.ant_id)
                        break
                for i in sorted_food:
                    if len(food_sites[i]["assigned_ally"]) <= ((distance[i] / stats.ants.Worker.SPEED) + (distance[i] / (stats.ants.Worker.ENCUMBERED_RATE * stats.ants.Worker.SPEED))) * stats.energy.PER_TICK / stats.energy.DELAY * 1.5:
                        target = i 
                        break
                requests.append(GoalRequest(ev.ant_id, target))
                if target in food_sites:
                    food_sites[target]["assigned_ally"].append(ev.ant_id)
                my_energy = ev.total_energy
        elif isinstance(ev, ProductionEvent):
            if ev.player_index == my_index:
                requests.append(GoalRequest(ev.ant_id, spawns[my_index]))
        elif isinstance(ev, ZoneActiveEvent):
            is_zone = min(ev.points, key = lambda k : distance[k])
            zone_time_left = ev.num_ticks
        elif isinstance(ev, ZoneDeactivateEvent):
            is_zone = False
        elif isinstance(ev, FoodTileActiveEvent):
            food_sites[ev.pos]["multiplier"] = ev.multiplier
            refresh_food()
        elif isinstance(ev, FoodTileDeactivateEvent):
            food_sites[ev.pos]["multiplier"] = 1
            refresh_food()
        elif isinstance(ev, SettlerScoreEvent):
            player_scores[ev.player_index] += ev.score_amount
        elif isinstance(ev, QueenAttackEvent):
            if ev.queen_player_index == my_index and my_queen_under_attack == False:
                my_queen_under_attack = True
        elif isinstance(ev, TeamDefeatedEvent):
            if ev.defeated_index == my_index:
                am_defeated = True
            elif ev.defeated_index in enemy_index:
                enemy_index.remove(ev.defeated_index)
                player_scores[ev.defeated_index] = 0
                player_scores[ev.by_index] = ev.new_hill_score
    

    def spawn_shorthand(type, target=None):
        global my_energy, uid, all_ants_info, my_index
        nonlocal can_spawn, spawned
        ant_type_keywords = {"WorkerAnt": [AntTypes.WORKER, stats.ants.Worker], "SettlerAnt": [AntTypes.SETTLER, stats.ants.Settler], "FighterAnt": [AntTypes.FIGHTER, stats.ants.Fighter]}
        should_spawn = True
        if can_spawn <= 0 or spawned:
            should_spawn = False
        if my_energy < ant_type_keywords[type][1].COST:
            should_spawn = False
        if should_spawn:
            can_spawn -= 1
            my_energy -= ant_type_keywords[type][1].COST
            uid += 1
            requests.append(SpawnRequest(ant_type_keywords[type][0], id=uid, color=None, goal=target))
            spawned = True
            if type == "WorkerAnt":
                if target in food_sites:
                    food_sites[target]["assigned_ally"].append(uid)

    
    def ant_count_function(type = "All", index = my_index):
        if index == "Other":
            return sum([ant_count_data[i][type] for i in enemy_index])
        if index == "OtherList":
            return [ant_count_data[i][type] for i in enemy_index]
        return ant_count_data[index][type]

    can_spawn = min(stats.general.MAX_SPAWNS_PER_TICK, stats.general.MAX_ANTS_PER_PLAYER - ant_count_function())
    








    if max([distance[spawns[i]] for i in enemy_index]) <= 40 and min([distance[spawns[i]] for i in enemy_index]) <= 25:

        while can_spawn > 0:
            spawned = False
            if my_energy < min(stats.ants.Worker.COST, stats.ants.Settler.COST, stats.ants.Fighter.COST): # no energy then break
                break

            if my_queen_under_attack: # if under attack, (and with enough cost for at least one worker afterwards) fuck everything else and kill them
                if my_energy > stats.ants.Worker.COST + stats.ants.Fighter.COST or ant_count_function("WorkerAnt") > 3:
                    spawn_shorthand("FighterAnt", spawns[my_index])
            elif ant_count_function() == 0:
                spawn_shorthand("WorkerAnt", sorted_food[0])
            
            if min([distance[spawns[i]] for i in enemy_index]) < 30 and max([distance[spawns[i]] for i in enemy_index]) < 44:
                if min([distance[spawns[i]] for i in enemy_index]) < stats.ants.Fighter.SPEED * stats.ants.Fighter.LIFESPAN * 2 / 3 or random.random() > 9 / 10:
                    if ant_count_function("WorkerAnt") < ant_count_function() / 3 and ant_count_function() > 10:
                        spawn_shorthand("WorkerAnt", sorted_food[0])
                    if (ant_count_function("WorkerAnt") > 8 + (sum([distance[spawns[i]] for i in enemy_index]) / len(enemy_index) / 10) and ant_count_function("FighterAnt") < ant_count_function() * (1 / 2 - (sum([distance[spawns[i]] for i in enemy_index]) / len(enemy_index)) / 1000)): # hardcore ratio the fighters up
                        spawn_shorthand("FighterAnt")
                
            # if my_ant_under_attack:
            #     if random.random() < (ant_count_function("WorkerAnt") - 2) / 5 and random.random() > 1/2:
            #         spawn_shorthand("FighterAnt")

            if ant_count_function() >= stats.general.MAX_ANTS_PER_PLAYER * 5 / 6: # if too many ants on field (5/6 of limit) then make everyone else commit die
                spawn_shorthand("FighterAnt", spawns[random.choice(enemy_index)])

            if is_zone: #if zone (therefore we need settlers or fighters)
                if not distance[is_zone] >= stats.ants.Settler.LIFESPAN * stats.ants.Settler.SPEED:
                    if zone_time_left > distance[is_zone] / stats.ants.Settler.SPEED: # settler given conditions are good
                        if random.random() > (3/4 if can_reach_all_teams else 1/2):
                            spawn_shorthand("SettlerAnt", is_zone)
                if max(ant_count_function("All", "OtherList")) <= ant_count_function() * 2 / 3 and ant_count_function("WorkerAnt") > 5: # if none of the players have more than my ants * 2/3, and i have workers, make them commit die
                    spawn_shorthand("FighterAnt", is_zone)
                if max(ant_count_function("SettlerAnt", "OtherList")) >= ant_count_function("SettlerAnt") * 3 / 2: # if others have more settler than i fucking do * 3/2, make them commit die
                    spawn_shorthand("FighterAnt", is_zone)        

            if my_energy > min(stats.general.MAX_ENERGY_STORED - stats.ants.Fighter.COST, stats.general.MAX_ENERGY_STORED * 4 / 5):
                if ant_count_function("WorkerAnt") > 5:
                    spawn_shorthand("FighterAnt", spawns[random.choice(enemy_index)])
                else:
                    spawn_shorthand("WorkerAnt", sorted_food[0])

            if ant_count_function("WorkerAnt") > 5:
                for i in enemy_index:
                    if ant_count_function("WorkerAnt", i) > 20 and ant_count_function("FighterAnt", i) < 3 and random.random() > 3 / 20:
                        spawn_shorthand("FighterAnt", spawns[i])
                        break

            if ant_count_function("WorkerAnt") <= stats.general.MAX_ANTS_PER_PLAYER * 2 / 3 or random.random() > 0.8:
                for i in sorted_food:
                    if ant_count_function("WorkerAnt") > 5:
                        if ant_count_function("All", "Other") <= ant_count_function() * len(enemy_index) * 2 / 3 and ant_count_function("WorkerAnt") > 30:
                            spawn_shorthand("FighterAnt", spawns[random.choice(enemy_index)])
                            break
                        elif random.random() > 0.8 + (ant_count_function("WorkerAnt") * 0.005):
                            spawn_shorthand("FighterAnt", i)
                            break
                    if len(food_sites[i]["assigned_ally"]) <= ((distance[i] / stats.ants.Worker.SPEED) + (distance[i] / (stats.ants.Worker.ENCUMBERED_RATE * stats.ants.Worker.SPEED))) * stats.energy.PER_TICK / stats.energy.DELAY:
                        if food_sites_by_distance[-1] != i: #if not farthest
                            if random.random() > min(abs(distance[food_sites_by_distance[food_sites_by_distance.index(i) + 1]] - distance[i]) / 4, 3 / 4):
                                if len(food_sites[food_sites_by_distance[food_sites_by_distance.index(i) + 1]]["assigned_ally"]) <= ((distance[food_sites_by_distance[food_sites_by_distance.index(i) + 1]] / stats.ants.Worker.SPEED) + (distance[food_sites_by_distance[food_sites_by_distance.index(i) + 1]] / (stats.ants.Worker.ENCUMBERED_RATE * stats.ants.Worker.SPEED))) * stats.energy.PER_TICK / stats.energy.DELAY:
                                    spawn_shorthand("WorkerAnt", food_sites_by_distance[food_sites_by_distance.index(i) + 1])
                        spawn_shorthand("WorkerAnt", i)
                        break

            if ant_count_function("WorkerAnt") == 0:
                spawn_shorthand("WorkerAnt", sorted_food[0])

            if not spawned:
                break 





    else:


        # print('alternate mode')
        while can_spawn > 0:
            spawned = False
            if my_energy < min(stats.ants.Worker.COST, stats.ants.Settler.COST, stats.ants.Fighter.COST): # no energy then break
                break
            
            if my_queen_under_attack: # if under attack, (and with enough cost for at least one worker afterwards) fuck everything else and kill them
                if my_energy > stats.ants.Worker.COST + stats.ants.Fighter.COST or ant_count_function("WorkerAnt") > 3:
                    spawn_shorthand("FighterAnt", spawns[my_index])
            elif ant_count_function() == 0:
                spawn_shorthand("WorkerAnt", sorted_food[0])

            if (ant_count_function("WorkerAnt") > 8 + (sum([distance[spawns[i]] for i in enemy_index]) / len(enemy_index)) and ant_count_function("FighterAnt") < ant_count_function() * (3 / 10 - (sum([distance[spawns[i]] for i in enemy_index]) / len(enemy_index)) / 1000)): # hardcore ratio the fighters up AT LOWER RATE
                spawn_shorthand("FighterAnt")

            if is_zone: #if zone (therefore we need settlers or fighters)
                if not distance[is_zone] >= stats.ants.Settler.LIFESPAN * stats.ants.Settler.SPEED:
                    if zone_time_left > distance[is_zone] / stats.ants.Settler.SPEED: # settler given conditions are good
                        if random.random() > (3/4 if can_reach_all_teams else 1/4):
                            spawn_shorthand("SettlerAnt", is_zone)
                if max(ant_count_function("All", "OtherList")) <= ant_count_function() * 2 / 3 and ant_count_function("WorkerAnt") > 5: # if none of the players have more than my ants * 2/3, and i have workers, make them commit die
                    spawn_shorthand("FighterAnt", is_zone)
                if max(ant_count_function("SettlerAnt", "OtherList")) >= ant_count_function("SettlerAnt") * 3 / 2: # if others have more settler than i fucking do * 3/2, make them commit die
                    spawn_shorthand("FighterAnt", is_zone) 
            
            if ant_count_function() >= stats.general.MAX_ANTS_PER_PLAYER * 5 / 6:
                spawn_shorthand("FighterAnt", spawns[random.choice(enemy_index)])

            if my_energy > min(stats.general.MAX_ENERGY_STORED - stats.ants.Fighter.COST, stats.general.MAX_ENERGY_STORED * 4 / 5):
                if ant_count_function("WorkerAnt") > 5:
                    spawn_shorthand("FighterAnt", spawns[random.choice(enemy_index)])
                else:
                    spawn_shorthand("WorkerAnt", sorted_food[0])

            if ant_count_function("WorkerAnt") > 10:
                for i in enemy_index:
                    if ant_count_function("WorkerAnt", i) > 20 and ant_count_function("FighterAnt", i) < 3 and random.random() > 0.4:
                        spawn_shorthand("FighterAnt", spawns[i])

            if ant_count_function("WorkerAnt") <= stats.general.MAX_ANTS_PER_PLAYER * 2 / 3 or random.random() > 0.8:
                for i in (food_sites_by_distance if sum([distance[spawns[i]] for i in enemy_index])/len(enemy_index) > 40 else sorted_food):
                    if ant_count_function("WorkerAnt") > 5:
                        if ant_count_function("All", "Other") <= ant_count_function() * len(enemy_index) * 2 / 3 and ant_count_function("WorkerAnt") > 30:
                            spawn_shorthand("FighterAnt", spawns[random.choice(enemy_index)])
                        elif random.random() > 0.8 + (ant_count_function("WorkerAnt") * 0.005):
                            spawn_shorthand("FighterAnt", i)
                    if len(food_sites[i]["assigned_ally"]) <= ((distance[i] / stats.ants.Worker.SPEED) + (distance[i] / (stats.ants.Worker.ENCUMBERED_RATE * stats.ants.Worker.SPEED))) * stats.energy.PER_TICK / stats.energy.DELAY:
                        spawn_shorthand("WorkerAnt", i)

            if ant_count_function("WorkerAnt") == 0:
                spawn_shorthand("WorkerAnt", sorted_food[0])

            if not spawned:
                break 






        # MOVING FIGHTER ANTS AAAAA
    for i in all_ants_info[my_index]:
        if all_ants_info[my_index][i]["classname"] == "FighterAnt":
            new_goal = spawns[my_index]
            temp = create_map(all_ants_info[my_index][i]["info"]["position"])
            check = []
            for j in enemy_index:
                for k in all_ants_info[j]:
                    add = True                      
                    a = []
                    a.append((round(all_ants_info[j][k]["info"]["position"][1]), round(all_ants_info[j][k]["info"]["position"][0])))
                    if all_ants_info[j][k]["classname"] == "WorkerAnt":
                        a.append(1 + stats.ants.Worker.SPEED * (stats.ants.Worker.ENCUMBERED_RATE if all_ants_info[j][k]["info"]["encumbered_energy"] > 0 else 1))
                    elif all_ants_info[j][k]["classname"] == "SettlerAnt":
                        a.append(1 + stats.ants.Settler.SPEED + all_ants_info[j][k]["info"]["hp"] / (stats.ants.Fighter.ATTACK * stats.ants.Fighter.NUM_ATTACKS))
                    elif all_ants_info[j][k]["classname"] == "FighterAnt":
                        a.append(1 + stats.ants.Fighter.SPEED + all_ants_info[j][k]["info"]["hp"] / (stats.ants.Fighter.ATTACK * stats.ants.Fighter.NUM_ATTACKS))
                    if all_ants_info[j][k]["classname"] == "SettlerAnt" or all_ants_info[j][k]["classname"] == "FighterAnt":
                        if all_ants_info[j][k]["info"]["ticks_left"] < temp[a[0]] * a[1]:
                            add = False
                    if add:
                        check.append(a)
            for k in enemy_index:
                if not distance[spawns[k]] >= stats.ants.Fighter.LIFESPAN * stats.ants.Fighter.SPEED:
                    check.append([spawns[k], 1 if ant_count_function("All", k) > 0 else 3])
            check = list(sorted(check, key=lambda x: temp[x[0]] * x[1]))
            if len(check) > 0:
                new_goal = check[0][0]
            requests.append(GoalRequest(i, new_goal))

    # print([ant_count_function("All", i) for i in range(number_of_players)])
    # print([distance[spawns[i]] for i in enemy_index])
    if am_defeated:
        return []
    return requests
