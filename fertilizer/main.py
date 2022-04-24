import math

import arcade
from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import DepositEvent, DieEvent, ProductionEvent, ZoneActiveEvent, SpawnEvent, MoveEvent, \
    AttackEvent, ZoneDeactivateEvent, FoodTileActiveEvent, FoodTileDeactivateEvent, SettlerScoreEvent, QueenAttackEvent, \
    TeamDefeatedEvent
from codequest22.server.requests import GoalRequest, SpawnRequest

import random


def get_team_name():
    return f"Samsan Tech"


my_index = None


def read_index(player_index, n_players):
    global my_index
    my_index = player_index


# Game wide related
my_energy = stats.general.STARTING_ENERGY
tick = 0
map_data = []
spawns = [None] * 4
queen_healths = [stats.general.QUEEN_HEALTH] * 4
distances = {}
max_distance = 0

# Food related
foods = []
closest_food = None
food_sites = []
food_base_energy_dict = {}
food_site_charged_dict = {}

# Hills related
hills = []
closest_hill = None
hill_sites = []
is_hill_activated = False

# My ants related
total_ants = 0

active_hill = None
enemies_in_safe_zone = {0: [], 1: [], 2: [], 3: []}

# All ants related
players_ants = {0: {AntTypes.WORKER: [], AntTypes.FIGHTER: [], AntTypes.SETTLER: []},
                1: {AntTypes.WORKER: [], AntTypes.FIGHTER: [], AntTypes.SETTLER: []},
                2: {AntTypes.WORKER: [], AntTypes.FIGHTER: [], AntTypes.SETTLER: []},
                3: {AntTypes.WORKER: [], AntTypes.FIGHTER: [], AntTypes.SETTLER: []}}
ants_id_to_type_dict = {0: {}, 1: {}, 2: {}, 3: {}}

# Parameters
WORKER_ANTS_THRESHOLD = 0.05 * stats.general.MAX_ANTS_PER_PLAYER
SETTLER_ANTS_THRESHOLD = 0.05 * stats.general.MAX_ANTS_PER_PLAYER


def read_map(md, energy_info):
    global map_data, spawns, foods, hills, distances, closest_food, closest_hill, food_sites, hill_sites, \
        food_base_energy_dict, food_site_charged_dict, max_distance
    map_data = md
    food_base_energy_dict = energy_info

    for y in range(len(map_data)):
        for x in range(len(map_data[0])):
            if map_data[y][x] == "F":
                foods.append((x, y))
            if map_data[y][x] == "Z":
                hills.append((x, y))
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
            if map_data[y][x] == "W":
                continue
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
        if expanded[idx[(a, b)]]:
            continue
        # If we haven't already looked at this point, put it in expanded and update the distance.
        expanded[idx[(a, b)]] = True
        distances[(a, b)] = d
        # Look at all neighbours
        for j, k, d2 in adj[(a, b)]:
            if not expanded[idx[(j, k)]]:
                heapq.heappush(queue, (
                    d + d2,
                    (j, k)
                ))
    # Now I can calculate the closest food site.
    food_sites = list(sorted(foods, key=lambda prod: distances[prod]))
    hill_sites = list(sorted(hills, key=lambda prod: distances[prod]))
    closest_food = food_sites[0]
    closest_hill = hill_sites[0]

    food_site_charged_dict = {k: 1 for k in food_sites}
    max_distance = distances[max(distances, key=distances.get)]


def handle_failed_requests(requests):
    global my_energy
    for req in requests:
        if req.player_index == my_index:
            print(f"Request {req.__class__.__name__} failed. Reason: {req.reason}.")


def handle_events(events):
    global my_energy, total_ants, active_hill, tick, is_hill_activated, WORKER_ANTS_THRESHOLD, max_distance, SETTLER_ANTS_THRESHOLD
    tick += 1

    # Increase the worker ants threshold up to half of our total ants allowed
    worker_threshold_increase_tick_interval = 40
    max_workers_cap = 0.4 * stats.general.MAX_ANTS_PER_PLAYER
    worker_ants_threshold_increment = 4
    if tick % worker_threshold_increase_tick_interval == 0 and WORKER_ANTS_THRESHOLD < max_workers_cap:
        WORKER_ANTS_THRESHOLD += worker_ants_threshold_increment

    # If the game extends for too long, start spawning for settler ants
    if tick > (0.5 * stats.general.SIMULATION_TICKS):
        SETTLER_ANTS_THRESHOLD = 0.1 * stats.general.MAX_ANTS_PER_PLAYER

    requests = []

    # We're dead
    if queen_healths[my_index] <= 0:
        pass

    # Process the W/F goals now so we don't have to do it repeatedly
    w_goal = evaluate_workers_goal()
    f_goal = evaluate_fighters_goal()

    for ev in events:
        if isinstance(ev, DepositEvent):
            if ev.player_index == my_index:
                # One of my worker ants just made it back to the Queen! Let's send them back to the food site.
                requests.append(GoalRequest(ev.ant_id, w_goal))
                # Additionally, let's update how much energy I've got.
                my_energy = ev.total_energy
        elif isinstance(ev, ProductionEvent):
            if ev.player_index == my_index:
                # One of my worker ants just made it to the food site! Let's send them back to the Queen.
                requests.append(GoalRequest(ev.ant_id, spawns[my_index]))
        elif isinstance(ev, MoveEvent):
            # Update position of ant
            ants_id_to_type_dict[ev.player_index][ev.ant_id].position = ev.position

            ant_type = ants_id_to_type_dict[ev.player_index][ev.ant_id].ant_type

            for i, ant in enumerate(players_ants[ev.player_index][ant_type]):
                if ant.ant_id == ev.ant_id:
                    players_ants[ev.player_index][ant_type][i].position = ev.position
                    break

            # Check if any of the enemy ants are in our safe zone
            if ev.player_index != my_index:
                ev_x, ev_y = ev.position
                ev_x = int(ev_x)
                ev_y = int(ev_y)

                # safe zone will be 20% of max distance
                safe_zone_percentage = 0.2
                SAFE_ZONE = safe_zone_percentage * max_distance

                # If is to prevent from checking walls
                if (ev_x, ev_y) in distances:
                    if distances[ev_x, ev_y] < SAFE_ZONE and ev.ant_id not in enemies_in_safe_zone[ev.player_index]:
                        enemies_in_safe_zone[ev.player_index].append(ev.ant_id)
                elif (ev_x + 1, ev_y + 1) in distances:
                    if distances[ev_x + 1, ev_y + 1] < SAFE_ZONE and ev.ant_id not in enemies_in_safe_zone[
                        ev.player_index]:
                        enemies_in_safe_zone[ev.player_index].append(ev.ant_id)

        elif isinstance(ev, SpawnEvent):
            # Someone just spawned an ant
            players_ants[ev.player_index][ev.ant_type].append(ev)
            ants_id_to_type_dict[ev.player_index][ev.ant_id] = ev
        elif isinstance(ev, DieEvent):
            # An ant has just died
            # Remove enemy ant that was in our safe zone
            if ev.player_index != my_index and ev.ant_id in enemies_in_safe_zone[ev.player_index]:
                enemies_in_safe_zone[ev.player_index].remove(ev.ant_id)

            # Remove ant from dictionaries
            ant_type = ants_id_to_type_dict[ev.player_index][ev.ant_id].ant_type

            for i, ant in enumerate(players_ants[ev.player_index][ant_type]):
                if ant.ant_id == ev.ant_id:
                    players_ants[ev.player_index][ant_type].pop(i)
                    break

            if ev.player_index == my_index:
                # One of my ants just died :(
                total_ants -= 1

            del ants_id_to_type_dict[ev.player_index][ev.ant_id]

        elif isinstance(ev, AttackEvent):
            pass

        elif isinstance(ev, ZoneActiveEvent):
            is_hill_activated = True
            active_hill = random.choice(ev.points)

            # Send all of our settlers to the active hill
            for ant in players_ants[my_index][AntTypes.SETTLER]:
                requests.append(GoalRequest(ant.ant_id, active_hill))

        elif isinstance(ev, ZoneDeactivateEvent):
            pass
        elif isinstance(ev, FoodTileActiveEvent):
            food_site_charged_dict[ev.pos] = ev.multiplier
        elif isinstance(ev, FoodTileDeactivateEvent):
            food_site_charged_dict[ev.pos] = 1
        elif isinstance(ev, SettlerScoreEvent):
            pass
        elif isinstance(ev, QueenAttackEvent):
            # Update queen hp after being attacked
            queen_healths[ev.queen_player_index] = ev.queen_hp
        elif isinstance(ev, TeamDefeatedEvent):
            spawns[ev.defeated_index] = None

    # Can I spawn ants?
    spawned_this_tick = 0
    defensive_fighter_spawned_this_tick = 0
    ant_spawned = True  # Flag used to stop while loop
    while (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK
    ):
        # Spawn an ant, give it some id, no color, and send it to its goal.
        # I will pay the base cost for this ant, so cost=None.
        # requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=closest_site))
        if not ant_spawned:
            break

        requests, spawned_this_tick, defensive_fighter_spawned_this_tick, ant_spawned = spawn_ant(requests,
                                                                                                  spawned_this_tick,
                                                                                                  defensive_fighter_spawned_this_tick,
                                                                                                  f_goal, w_goal)

    return requests


def flatten_list(alist):
    return [i for sublist in alist for i in sublist]


def euclidean_distance(point_a, point_b):
    x_a, y_a = point_a
    x_b, y_b = point_b

    return math.sqrt((x_a - x_b) ** 2 + (y_a - y_b) ** 2)


def normalize(_min, _max, x):
    return (x - _min) / (_max - _min + 10 ** -100)


def find_ant_in_player_ants(ant_id, player_index):
    owned_ants = players_ants[player_index]
    ant = ants_id_to_type_dict[player_index][ant_id]
    ant_found = False
    idx = 0
    key = None
    for k, v in owned_ants.items():
        if ant_found:
            break
        for i, ant in enumerate(v):
            if ant.ant_id == ant_id:
                ant_found = True
                key = k
                idx = i
                break

    return key, idx


def evaluate_workers_goal():
    global max_distance

    # Spawned worker ants go for the food based on this heuristics
    # Heuristics are - Distance from spawn, number of waiting ants, base energy of food, whether food is overcharged or not
    max_score = None
    workers_waiting_score = -5
    enemy_fighters_waiting_score = -4
    distance_score = -2
    base_energy_score = 3
    charged_food_site_score = 1

    # Gather all worker ants
    all_worker_ants = []

    # Gather all figher ants
    all_fighter_ants = []

    for k, v in players_ants.items():
        for ant_type in v:
            if ant_type == AntTypes.WORKER:
                all_worker_ants += v[ant_type]
            if ant_type == AntTypes.FIGHTER:
                all_fighter_ants += v[ant_type]

    # The farther this distance, the more likely a food tile will be considered as "occupied"
    worker_waiting_distance_threshold = 1
    fighter_waiting_distance_threshold = 3

    for i, site in enumerate(food_sites):
        workers_waiting = sum(
            euclidean_distance(ant.position, site) < worker_waiting_distance_threshold for ant in all_worker_ants)

        enemy_fighters_waiting = sum(
            euclidean_distance(ant.position, site) < fighter_waiting_distance_threshold
            for ant in all_fighter_ants if ant.player_index != my_index
        )

        dist = distances[site]

        # Normalize values here
        workers_waiting = normalize(0, len(all_worker_ants), workers_waiting)
        enemy_fighters_waiting = normalize(0, len(all_fighter_ants), enemy_fighters_waiting)
        dist = normalize(0, max_distance, dist)
        food_base_energy = normalize(food_base_energy_dict[min(food_base_energy_dict, key=food_base_energy_dict.get)],
                                     food_base_energy_dict[max(food_base_energy_dict, key=food_base_energy_dict.get)],
                                     food_base_energy_dict[site])
        charged_food = normalize(food_site_charged_dict[min(food_site_charged_dict, key=food_site_charged_dict.get)],
                                 food_site_charged_dict[max(food_site_charged_dict, key=food_site_charged_dict.get)],
                                 food_site_charged_dict[site])

        score = (
            (workers_waiting_score * workers_waiting + 1) + (
                    enemy_fighters_waiting_score * enemy_fighters_waiting + 1) + (
                    distance_score * dist + 1) + (
                    base_energy_score * food_base_energy + 1) + (
                    charged_food_site_score * charged_food + 1), site)

        if max_score is None:
            max_score = score
        else:
            max_score = max(max_score, score, key=lambda x: x[0])

    return max_score[1]


def evaluate_fighters_goal():
    # Spawned fighter ants go for the enemy ants based on this heuristics
    # 1. Defensive first strategy, eliminate enemy fighters within safe zone
    # 2. Choose target based on their unit distribution
    # 3. Attack high traffic areas of workers + settlers, avoid fighters
    threats = [(k, v) for k, v in enemies_in_safe_zone.items()]

    threats = [(p_idx, t) for p_idx, t in threats if len(t) > 0]
    if threats:
        threat = threats[0]
        return ants_id_to_type_dict[threat[0]][threat[1][0]].position

    max_score = None

    player_targets_dict = {k: v for k, v in players_ants.items() if k != my_index}

    workers_score = 5
    settlers_score = 2
    fighters_score = 2
    distance_score = -2  # Less likely to attack further targets

    for k, v in player_targets_dict.items():
        score = 0
        for k1, v1 in v.items():
            # Order of priority will be workers > settlers > fighters
            if k1 == AntTypes.WORKER:
                score += len(v1) * workers_score
            elif k1 == AntTypes.SETTLER:
                score += len(v1) * settlers_score
            else:
                score += len(v1) * fighters_score

        score += distance_score * normalize(0, max_distance, distances[spawns[k]])
        max_score = (score, k) if max_score is None else (max((score, k), max_score, key=lambda x: x[0]))

    targets = player_targets_dict[max_score[1]]

    # Find high traffic areas for worker ants, then settler ants, and finally fighter ants
    enemy_pos_dict = {}

    # Frequency of enemy worker positions
    for worker in targets[AntTypes.WORKER]:
        if worker.position not in enemy_pos_dict:
            enemy_pos_dict[worker.position] = 1
        else:
            enemy_pos_dict[worker.position] += 1

    # Frequency of enemy settler positions
    for settler in targets[AntTypes.SETTLER]:
        if settler.position not in enemy_pos_dict:
            enemy_pos_dict[settler.position] = 1
        else:
            enemy_pos_dict[settler.position] += 1

    # Set the highest frequency position as the goal
    if enemy_pos_dict:
        return max(enemy_pos_dict, key=enemy_pos_dict.get)

    # Attack the enemy Queen Ant
    spawn_idx_to_atk = random.choice(
        [i for i, spawn in enumerate(spawns) if spawn is not None and spawn != spawns[my_index]])
    return spawns[spawn_idx_to_atk]


def spawn_ant(requests, spawned_this_tick, defensive_fighter_spawned_this_tick, f_goal, w_goal):
    global my_energy, map_data, closest_food, closest_hill, is_hill_activated, total_ants, SETTLER_ANTS_THRESHOLD
    ant_spawned = False

    ant_stats_mapping = {AntTypes.WORKER: stats.ants.Worker,
                         AntTypes.FIGHTER: stats.ants.Fighter,
                         AntTypes.SETTLER: stats.ants.Settler, }

    ant_types = [AntTypes.WORKER, AntTypes.FIGHTER, AntTypes.SETTLER]
    num_threats = sum(len(v) for v in enemies_in_safe_zone.values())
    num_threats_threshold = 3

    # Try to spawn fighter ants; this way we pool resources
    defensive_fighter_limit = 2
    offensive_fighter_limit = 2
    if defensive_fighter_spawned_this_tick < defensive_fighter_limit and num_threats > num_threats_threshold:
        ant_to_spawn = AntTypes.FIGHTER
        ant_cost = ant_stats_mapping[ant_to_spawn].COST

        if my_energy >= ant_cost:
            spawn_request = SpawnRequest(ant_to_spawn, id=None, color=arcade.color.CORN,
                                         goal=f_goal)

            spawned_this_tick += 1
            defensive_fighter_spawned_this_tick += 1
            total_ants += 1
            my_energy -= ant_cost

            requests.append(spawn_request)
            ant_spawned = True

    # Spawn worker ant if it is less than the threshold defined
    elif len(players_ants[my_index][AntTypes.WORKER]) < WORKER_ANTS_THRESHOLD:
        ant_cost = ant_stats_mapping[AntTypes.WORKER].COST
        if my_energy >= ant_cost:
            spawn_request = SpawnRequest(AntTypes.WORKER, id=None, color=arcade.color.ALABAMA_CRIMSON,
                                         goal=w_goal)

            spawned_this_tick += 1
            total_ants += 1
            my_energy -= ant_cost

            requests.append(spawn_request)
            ant_spawned = True
    else:
        # Pool resources in the mid game
        lower_energy_reserve = 0.3 * stats.general.MAX_ENERGY_STORED
        upper_energy_reserve = 0.6 * stats.general.MAX_ENERGY_STORED
        mid_game_tick = 0.2 * stats.general.SIMULATION_TICKS
        if tick > mid_game_tick and lower_energy_reserve <= my_energy < upper_energy_reserve:
            return requests, spawned_this_tick, defensive_fighter_spawned_this_tick, ant_spawned

        ant_choices = [AntTypes.FIGHTER, AntTypes.FIGHTER, AntTypes.SETTLER]

        # Within grace period of inactive hills, just spawn fighters
        if not is_hill_activated:
            ant_to_spawn = AntTypes.FIGHTER
        else:
            if len(players_ants[my_index][AntTypes.SETTLER]) < SETTLER_ANTS_THRESHOLD:
                ant_to_spawn = random.choice(ant_choices)
            else:
                ant_to_spawn = AntTypes.FIGHTER

        ant_cost = ant_stats_mapping[ant_to_spawn].COST

        # Pool resources in the early game to defend against sudden rushes
        energy_threshold = stats.ants.Fighter.COST * 2  # Reserve enough to burst out 2 fighter ants
        if my_energy <= energy_threshold:
            return requests, spawned_this_tick, defensive_fighter_spawned_this_tick, ant_spawned

        if my_energy >= ant_cost:
            if ant_to_spawn == AntTypes.WORKER:
                spawn_request = SpawnRequest(ant_to_spawn, id=None, color=arcade.color.ALABAMA_CRIMSON,
                                             goal=w_goal)
            elif ant_to_spawn == AntTypes.SETTLER:
                # Spawned settler ants go for active hills or nearest hills
                goal = closest_hill if active_hill is None else active_hill
                spawn_request = SpawnRequest(ant_to_spawn, id=None, color=arcade.color.AIR_FORCE_BLUE,
                                             goal=goal)
            else:
                spawn_request = SpawnRequest(ant_to_spawn, id=None, color=arcade.color.CORN,
                                             goal=f_goal)

            spawned_this_tick += 1
            total_ants += 1
            my_energy -= ant_cost

            requests.append(spawn_request)
            ant_spawned = True

    return requests, spawned_this_tick, defensive_fighter_spawned_this_tick, ant_spawned
