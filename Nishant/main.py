from dis import dis
from tkinter.messagebox import NO
from urllib import request
from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import DepositEvent, DieEvent, ProductionEvent, ZoneActiveEvent, ZoneDeactivateEvent, TeamDefeatedEvent, QueenAttackEvent, SettlerScoreEvent
from codequest22.server.requests import GoalRequest, SpawnRequest
from numpy import isin
from dijkstrasAlgorithm import dijkstrasAlgorithm

def get_team_name():
    return f"Nishant's Bot 2"

bot_index = None
number_of_players = None
weakest_enemy = 0
strongest_enemy = 0
def read_index(player_index, n_players):
    global bot_index, number_of_players, weakest_enemy, strongest_enemy
    bot_index = player_index
    number_of_players = n_players
    if weakest_enemy == bot_index:
        if weakest_enemy + 1 <= number_of_players - 1:
            weakest_enemy += 1
        elif weakest_enemy - 1 > 0:
            weakest_enemy -= 1
    if strongest_enemy == bot_index:
        if strongest_enemy + 1 <= number_of_players - 1:
            strongest_enemy += 1
        elif strongest_enemy - 1 > 0:
            strongest_enemy -= 1


my_energy = stats.general.STARTING_ENERGY
id = 0
map_data = {}
spawns = [None]*4
food = []
food_energy = {}
hills = []
distance = {}
total_ants = 0
food_sorted = []
worker_ants = {}
teams_defeated = []
waiting_worker_ants = []
worker_dispatch_timer = 0
phase = None
zone_active = False
zone_active_points = []
zone_active_ticks = 0
defence = 0
ticks = 0
hill_scores = [0]*4
current_goal = 0
queen_attack = False
queen_health = [stats.general.QUEEN_HEALTH]*4

def read_map(md, energy_info):
    global map_data, spawns, food, food_sorted, distance, enemy_start_point, all_energy, enemy_choke_points, enemy_start_points
    
    all_energy = [stats.general.STARTING_ENERGY]*(number_of_players)
    
    map_data = md
    for y in range(len(map_data)):
        for x in range(len(map_data[0])):
            if map_data[y][x] == "F":
                food.append((x, y))
                food_energy[(x, y)] = energy_info[(x, y)]
            elif map_data[y][x] in "RBYG":
                spawns["RBYG".index(map_data[y][x])] = (x, y)
            elif map_data[y][x] == "Z":
                hills.append((x, y))

    bot_start_point = spawns[bot_index]
    enemy_start_points = list(filter(lambda point: (point != None and point != spawns[bot_index]), spawns))
    
    distance = dijkstrasAlgorithm(map_data=map_data, start_point=bot_start_point)
    
    food_sorted = list(sorted(food, key=lambda prod: distance[prod]))
    
    enemy_choke_points = []
    for point in enemy_start_points:
        enemy_distance = dijkstrasAlgorithm(map_data=map_data, start_point=point)
        
        enemy_choke_points.append(list(sorted(food, key=lambda prod: enemy_distance[prod])))
    
def handle_failed_requests(requests):
    # # Debugging
    # global my_energy
    # for req in requests:
    #     if req.player_index == bot_index:
    #         print(f"{bot_index} : Request {req.__class__.__name__} failed. Reason: {req.reason}.")
    #         raise ValueError()
    pass

def handle_events(events):
    global bot_index, my_energy, total_ants, worker_ants, id, all_energy, weakest_enemy, teams_defeated, figther_protection_group, worker_dispatch_timer, waiting_worker_ants
    global phase, enemy_choke_points, zone_active, zone_active_points, distance, zone_active_ticks, defence, ticks, strongest_enemy, enemy_start_points, hill_scores, number_of_players
    global current_goal, queen_attack, queen_health
    requests = []
    spawned_this_tick = 0
    
    for ev in events:
        if isinstance(ev, DieEvent):
            if ev.player_index == bot_index:
                total_ants -= 1
                
                if ev.ant_id in worker_ants:
                    del worker_ants[str(ev.ant_id)]
        elif isinstance(ev, DepositEvent):
            if ev.player_index == bot_index:
                requests.append(GoalRequest(ev.ant_id, food_sorted[worker_ants[ev.ant_id]]))
                my_energy = ev.total_energy
        elif isinstance(ev, ProductionEvent):
            if ev.player_index == bot_index:
                requests.append(GoalRequest(ev.ant_id, spawns[bot_index]))
        elif isinstance(ev, TeamDefeatedEvent):
            if ev.defeated_index != bot_index:
                teams_defeated.append(ev.defeated_index)
                print(teams_defeated)
                
                enemy_hill_scores = []
                enemy_hill_scores_index = []
                
                for player in range(4):
                    if player not in teams_defeated and player != bot_index:
                        enemy_hill_scores.append(hill_scores[player])
                        enemy_hill_scores_index.append(player)
                        
                strongest_enemy = enemy_hill_scores_index[enemy_hill_scores.index(max(enemy_hill_scores))]
                weakest_enemy = hill_scores.index(min(hill_scores))
                
                if len(teams_defeated) == number_of_players - 1:
                    phase = 4
                
                if strongest_enemy in teams_defeated and queen_attack == True:
                    queen_attack = False
        elif isinstance(ev, ZoneActiveEvent):
            zone_active = True
            zone_active_points = list(sorted(ev.points, key=lambda prod: distance[prod]))
            zone_active_ticks = ev.num_ticks - distance[zone_active_points[0]]/stats.ants.Settler.SPEED
        elif isinstance(ev, ZoneDeactivateEvent):
            zone_active = False
        elif isinstance(ev, SettlerScoreEvent):
            if queen_attack == False:
                hill_scores[ev.player_index] = hill_scores[ev.player_index] + ev.score_amount
                enemy_hill_scores = []
                enemy_hill_scores_index = []
                for player in range(4):
                    if player not in teams_defeated and player != bot_index:
                        enemy_hill_scores.append(hill_scores[player])
                        enemy_hill_scores_index.append(player)

                strongest_enemy = enemy_hill_scores_index[enemy_hill_scores.index(max(enemy_hill_scores))]
                weakest_enemy = hill_scores.index(min(hill_scores))
        elif isinstance(ev, QueenAttackEvent):
            if ev.queen_player_index == bot_index:
                queen_attack = True
                phase = 3
                strongest_enemy = ev.ant_player_index
            
            
    if ticks < 25: 
        phase = 1
        
    elif phase == 1: 
        phase = 2 
            
    elif ticks > 100 and phase == 2: 
        phase = 3
    
    
    if phase == 1:
        if (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Worker.COST
        ):
            spawned_this_tick += 1
            total_ants += 1
            
            requests.append(SpawnRequest(AntTypes.WORKER, id=str(id), color=None, goal=food_sorted[0]))
            worker_ants[str(id)] = 0
            id += 1
            
            my_energy -= stats.ants.Worker.COST
                
    if phase == 2:
        while (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Worker.COST
        ):
            spawned_this_tick += 1
            total_ants += 1
            
            requests.append(SpawnRequest(AntTypes.WORKER, id=str(id), color=None, goal=food_sorted[current_goal]))
            if current_goal < len(food_sorted) - 1:
                current_goal += 1
            else: 
                current_goal = 0
            worker_ants[str(id)] = current_goal
            id += 1
            
            my_energy -= stats.ants.Worker.COST
    
    if phase == 3:
        if (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Worker.COST and
            len(worker_ants) < stats.general.MAX_ANTS_PER_PLAYER*0.75
        ):
            spawned_this_tick += 1
            total_ants += 1
            
            requests.append(SpawnRequest(AntTypes.WORKER, id=str(id), color=None, goal=food_sorted[current_goal]))
            if current_goal < len(food_sorted) - 1:
                current_goal += 1
            else: 
                current_goal = 0
            worker_ants[str(id)] = current_goal
            id += 1
            
            my_energy -= stats.ants.Worker.COST

        while (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Fighter.COST + stats.ants.Worker.COST + 1
        ):
            spawned_this_tick += 1
            total_ants += 1
            
            requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=spawns[strongest_enemy]))
            print(strongest_enemy)
            
            my_energy -= stats.ants.Fighter.COST
        
    if phase == 4:
        if (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Worker.COST and
            len(worker_ants) < stats.general.MAX_ANTS_PER_PLAYER*0.75
        ):
            spawned_this_tick += 1
            total_ants += 1
            
            requests.append(SpawnRequest(AntTypes.WORKER, id=str(id), color=None, goal=food_sorted[current_goal]))
            if current_goal < len(food_sorted) - 1:
                current_goal += 1
            else: 
                current_goal = 0
            worker_ants[str(id)] = current_goal
            id += 1
            
            my_energy -= stats.ants.Worker.COST 
        if zone_active == True:
            while (
                total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
                spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
                my_energy >= stats.ants.Settler.COST + stats.ants.Worker.COST and 
                zone_active_ticks > 0
            ):
                spawned_this_tick += 1
                total_ants += 1
                
                requests.append(SpawnRequest(AntTypes.SETTLER, id=None, color=None, goal=zone_active_points[0]))
                
                my_energy -= stats.ants.Settler.COST
                
                zone_active_ticks -= 1   
        
            

    ticks += 1
    return requests