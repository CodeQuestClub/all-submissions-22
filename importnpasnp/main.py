import json
import math
import operator

from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import DepositEvent, DieEvent, ProductionEvent, ZoneActiveEvent, ZoneDeactivateEvent, \
    SpawnEvent, MoveEvent, FoodTileActiveEvent, FoodTileDeactivateEvent, QueenAttackEvent, TeamDefeatedEvent
from codequest22.server.requests import GoalRequest, SpawnRequest
import random
from collections import defaultdict


def get_team_name():
    return f"Import numpy as No Problem"


def ant_class_to_type(name):
    if name == "WorkerAnt":
        return AntTypes.WORKER
    elif name == "FighterAnt":
        return AntTypes.FIGHTER
    elif name == "SettlerAnt":
        return AntTypes.SETTLER
    else:
        raise ValueError(f"Unknown ant classname: {name}")


def ant_key(player_index, ant_id):
    return player_index, ant_id


my_index = None
num_players = None
alive_enemy_indexes = set()
enemy_energies = {}
enemy_energy_deposits = defaultdict(dict)  # enemy_index : tick : int


def read_index(player_index, n_players):
    global my_index, num_players, alive_enemy_indexes, enemy_energies
    num_players = n_players
    my_index = player_index
    alive_enemy_indexes.update(list(range(n_players)))
    alive_enemy_indexes.remove(player_index)
    for ind in list(alive_enemy_indexes):
        enemy_energies[ind] = stats.general.STARTING_ENERGY


my_energy = stats.general.STARTING_ENERGY
map_data = {}
spawns = [None] * 4
current_ants = [defaultdict(int) for _ in range(4)]
food_sites = {}
food = []
hills = []
distance = {}
closest_site = None
total_ants = 0
active_zone = None
last_zone_activation_tick = None
energy_data = None
ant_locations = {}
ant_types = {}
tick = 0
ant_goals = {}
ants_that_need_rerouting = set()
walls = set()
spawn_voronoi = defaultdict(set)
dijkstras_distances = {}
ant_has_energy = defaultdict(set)
defending_fighters = set()
worker_pipelines = defaultdict(set)


def read_map(md, energy_info):
    global map_data, spawns, food, distance, closest_site, hills, energy_data, food_sites, spawn_voronoi, \
        dijkstras_distances
    energy_data = energy_info
    map_data = md
    for y in range(len(map_data)):
        for x in range(len(map_data[0])):
            if map_data[y][x] == "F":
                food.append((x, y))
            elif map_data[y][x] == "Z":
                hills.append((x, y))
            elif map_data[y][x] == "W":
                walls.add((x, y))
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
        for a, b in [(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)]:
            if 0 <= a < h and 0 <= b < w and map_data[a][b] != "W":
                adj[(x, y)].append((b, a, 1))
    # Step 2: Run Dijkstra's
    import heapq
    for p_index in range(num_players):
        # What nodes have we already looked at?
        expanded = [False] * len(points)
        # What nodes are we currently looking at?
        queue = []
        # What is the distance to the startpoint from every other point?
        heapq.heappush(queue, (0, spawns[p_index]))
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

        dijkstras_distances[p_index] = distance.copy()

        if p_index == my_index:
            food_sites = {}
            for loc in food:
                food_sites[loc] = {
                    "distance": distance[loc],
                    "energy": energy_info[loc]
                }

    # for p in dijkstras_distances:
    #     print(p)
    #     print(dijkstras_distances[p])
    for map_y in range(len(map_data)):
        for map_x in range(len(map_data[0])):
            if (map_x, map_y) in walls: continue
            values = [(dijkstras_distances[p][(map_x, map_y)], p) for p in dijkstras_distances]
            value = min(values, key=operator.itemgetter(0))
            index = value[1]
            spawn_voronoi[index].add((map_x, map_y))


def handle_failed_requests(requests):
    global my_energy
    for req in requests:
        if req.player_index == my_index:
            print(f"energy: {my_energy}")
            print(f"Request {req.__class__.__name__} failed. Reason: {req.reason}.")
            raise ValueError()


_current_ant_id = 0


def create_ant(goal):
    global ant_goals, _current_ant_id
    ID = f"ant-{_current_ant_id}"
    ant_goals[ID] = goal
    _current_ant_id += 1
    return ID


def get_expected_energy_gain(index, num_ticks):
    global enemy_energy_deposits, tick
    enemy_deposits = enemy_energy_deposits[index]
    count = 0
    for t in range(round(tick - num_ticks), tick):
        if t in enemy_deposits:
            count += enemy_deposits[t]
    return count


def handle_events(events):
    global my_energy, total_ants, active_zone, current_ants, tick, last_zone_activation_tick, enemy_energies, \
        enemy_energy_deposits
    tick += 1
    requests = []
    am_being_attacked = False

    # evaluate all possible worker ant options (based on food goal)
    results = []
    for loc, data in food_sites.items():
        num_ticks_to_food = data["distance"] / stats.ants.Worker.SPEED
        num_ticks_back = data["distance"] / (stats.ants.Worker.SPEED * stats.ants.Worker.ENCUMBERED_RATE)
        # assume no ants will be at the site?
        expected_wait_time = stats.energy.DELAY
        energy_return = data["energy"] / (num_ticks_to_food + num_ticks_back + expected_wait_time)
        maximum_ants_in_pipeline = (num_ticks_to_food + num_ticks_back + expected_wait_time) / stats.energy.DELAY
        results.append((loc, energy_return, maximum_ants_in_pipeline))

    results.sort(reverse=True, key=operator.itemgetter(1))
    # print([round(e[1], 4) for e in results])

    # record enemy fighter_previous_locations
    enemy_fighter_previous_locations = {}
    for (player_id, ant_id), type_of_ant in ant_types.items():
        if player_id != my_index and type_of_ant == AntTypes.FIGHTER:
            enemy_fighter_previous_locations[(player_id, ant_id)] = ant_locations[(player_id, ant_id)]

    enemy_spawn_distances = [(dijkstras_distances[my_index][spawns[i]], spawns[i]) for i in list(alive_enemy_indexes)]
    closest_enemy_spawn = None
    if not enemy_spawn_distances:
        closest_enemy_spawn = None
    else:
        closest_enemy_spawn = min(enemy_spawn_distances, key=operator.itemgetter(0))[1]

    for ev in events:
        if isinstance(ev, DepositEvent):
            if tick in enemy_energy_deposits[ev.player_index]:
                enemy_energy_deposits[ev.player_index][tick] += ev.energy_amount
            else:
                enemy_energy_deposits[ev.player_index][tick] = ev.energy_amount
            if ev.player_index == my_index:
                # One of my worker ants just made it back to the Queen! Let's send them back to the food site.
                for (loc, energy_return, maximum_ants_in_pipeline) in results:
                    if len(worker_pipelines[loc]) < maximum_ants_in_pipeline:
                        goal = loc
                        for _p in worker_pipelines.keys():
                            if ev.ant_id in worker_pipelines[_p]:
                                worker_pipelines[_p].remove(ev.ant_id)
                        worker_pipelines[loc].add(ev.ant_id)
                        requests.append(GoalRequest(ev.ant_id, goal))
                        ant_goals[ev.ant_id] = goal
                        # Additionally, let's update how much energy I've got.
                        my_energy = ev.total_energy
                        break
            else:
                enemy_energies[ev.player_index] = ev.total_energy
            ant_has_energy[ev.player_index].remove(ev.ant_id)
        elif isinstance(ev, ProductionEvent):
            if ev.player_index == my_index:
                # One of my worker ants just made it to the food site! Let's send them back to the Queen.
                requests.append(GoalRequest(ev.ant_id, spawns[my_index]))
                ant_goals[ev.ant_id] = spawns[my_index]
            ant_has_energy[ev.player_index].add(ev.ant_id)
        elif isinstance(ev, SpawnEvent):
            key = ant_key(ev.player_index, ev.ant_id)
            ant_locations[key] = ev.position
            ant_types[key] = ev.ant_type
            if ev.player_index == my_index:
                continue
            current_ants[ev.player_index][ev.ant_type] += 1
        elif isinstance(ev, DieEvent):
            ant = ev.ant_str
            a_type = ant_class_to_type(ant["classname"])
            current_ants[ev.player_index][a_type] -= 1
            if ev.player_index == my_index:
                del ant_goals[ev.ant_id]
                total_ants -= 1
                if ev.ant_id in defending_fighters:
                    defending_fighters.remove(ev.ant_id)
                for _p in worker_pipelines.keys():
                    if ev.ant_id in worker_pipelines[_p]:
                        worker_pipelines[_p].remove(ev.ant_id)
            key = ant_key(ev.player_index, ev.ant_id)
            del ant_locations[key]
            del ant_types[key]
            if ev.ant_id in ant_has_energy[ev.player_index]:
                ant_has_energy[ev.player_index].remove(ev.ant_id)
        elif isinstance(ev, ZoneActiveEvent):
            active_zone = ev.points
            last_zone_activation_tick = tick
        elif isinstance(ev, ZoneDeactivateEvent):
            active_zone = None
            last_zone_activation_tick = None
        elif isinstance(ev, MoveEvent):
            key = ant_key(ev.player_index, ev.ant_id)
            ant_locations[key] = ev.position
        elif isinstance(ev, FoodTileActiveEvent):
            food_sites[ev.pos]["energy"] *= 2
        elif isinstance(ev, FoodTileDeactivateEvent):
            food_sites[ev.pos]["energy"] /= 2
        elif isinstance(ev, QueenAttackEvent):
            if ev.queen_player_index == my_index:
                am_being_attacked = True
            else:
                if ev.queen_hp <= 0:
                    if ev.queen_player_index in alive_enemy_indexes:
                        alive_enemy_indexes.remove(ev.queen_player_index)
        elif isinstance(ev, TeamDefeatedEvent):
            if ev.defeated_index != my_index:
                if ev.defeated_index in alive_enemy_indexes:
                    alive_enemy_indexes.remove(ev.defeated_index)

    # check if I need to move any of my ants away from enemy fighter ants
    enemy_fighter_locations = []
    # for (player_id, ant_id), type_of_ant in ant_types.items():
    #     if player_id != my_index and type_of_ant == AntTypes.FIGHTER:
    #         enemy_fighter_locations.append(ant_locations[(player_id, ant_id)])
    current_enemy_fighter_locations = {}
    for (player_id, ant_id), type_of_ant in ant_types.items():
        if player_id != my_index and type_of_ant == AntTypes.FIGHTER:
            current_enemy_fighter_locations[(player_id, ant_id)] = ant_locations[(player_id, ant_id)]

    # find expected future positions of the enemy fighter ants
    for (player_id, ant_id), loc in current_enemy_fighter_locations.items():
        if (player_id, ant_id) not in enemy_fighter_previous_locations:
            enemy_fighter_locations.append(loc)
            continue
        previous_loc = enemy_fighter_previous_locations[(player_id, ant_id)]
        x_diff = loc[0] - previous_loc[0]
        y_diff = loc[1] - previous_loc[1]
        lookahead_factor = stats.ants.Fighter.SPEED + stats.ants.Fighter.RANGE
        new_x = loc[0] + lookahead_factor * x_diff
        new_y = loc[1] + lookahead_factor * y_diff
        enemy_fighter_locations.append((new_x, new_y))

    if len(enemy_fighter_locations) > 0:
        my_non_fighter_ants = []
        for (player_id, ant_id), type_of_ant in ant_types.items():
            if player_id == my_index and type_of_ant != AntTypes.FIGHTER:
                if type_of_ant == AntTypes.SETTLER:
                    if active_zone:
                        if math.dist(ant_locations[(player_id, ant_id)], active_zone[0]) < 3:
                            continue
                my_non_fighter_ants.append((ant_id, ant_locations[(player_id, ant_id)]))

        enemy_voronoi = [[math.inf for _ in range(len(map_data[0]))] for _ in range(len(map_data))]
        for y in range(len(map_data)):
            for x in range(len(map_data[0])):
                enemy_voronoi[y][x] = min([math.dist(enemy, [x, y]) for enemy in enemy_fighter_locations] + [math.inf])

        for ant_id, loc in my_non_fighter_ants:
            x, y = loc
            x = math.floor(x)
            y = math.floor(y)
            if False and enemy_voronoi[y][x] <= 3:
                if ant_id in ant_has_energy[my_index] and math.dist((x, y), spawns[my_index]) < 6: continue
                # re-route the worker/settler ant
                best_value = -100
                best_square = (0, 0)
                for map_y in range(len(enemy_voronoi)):
                    for map_x in range(len(enemy_voronoi[0])):
                        if (map_x, map_y) in walls:
                            continue
                        if not 6 <= math.dist(loc, (map_x, map_y)) <= 9:
                            continue
                        value = enemy_voronoi[y][x]
                        if value >= best_value:
                            best_value = value
                            best_square = (map_x, map_y)

                if best_square == (0, 0):
                    continue

                requests.append(GoalRequest(ant_id, best_square))
                ants_that_need_rerouting.add(ant_id)
            else:
                if ant_id in ants_that_need_rerouting:
                    requests.append(GoalRequest(ant_id, ant_goals[ant_id]))
                    ants_that_need_rerouting.remove(ant_id)

    # check the number and position of enemy fighter ants
    enemy_fighters = 0
    for p_index in range(num_players):
        if p_index != my_index:
            enemy_fighters += current_ants[p_index][AntTypes.FIGHTER]

    enemy_fighters_in_my_area = 0
    if enemy_fighters > 0:
        for (player_id, ant_id), type_of_ant in ant_types.items():
            if type_of_ant == AntTypes.FIGHTER and player_id != my_index:
                if ant_locations[(player_id, ant_id)] in spawn_voronoi[my_index]:
                    enemy_fighters_in_my_area += 1

    enemy_fighter_distances = [(1000, None)]
    # for loc in enemy_fighter_locations:
    #     new_loc = math.floor(loc[0]), math.floor(loc[1])
    #     if new_loc in dijkstras_distances[my_index]:
    #         enemy_fighter_distances.append((dijkstras_distances[my_index][new_loc], new_loc))
    #     else:
    #         enemy_fighter_distances.append((math.dist(new_loc, spawns[my_index]), new_loc))
    for loc in current_enemy_fighter_locations.values():
        new_loc = round(loc[0]), round(loc[1])
        enemy_fighter_distances.append((dijkstras_distances[my_index][new_loc], loc))
    closest_enemy_fighter = min(enemy_fighter_distances, key=operator.itemgetter(0))[1]

    for ant_id in list(defending_fighters):
        if closest_enemy_fighter is None or ((enemy_fighters_in_my_area == 0 and current_ants[my_index][AntTypes.WORKER]
                                              >= 0.5 * stats.general.MAX_ANTS_PER_PLAYER) and closest_enemy_spawn):
            requests.append(GoalRequest(ant_id, closest_enemy_spawn))
            defending_fighters.remove(ant_id)
        else:
            requests.append(GoalRequest(ant_id, closest_enemy_fighter))

    # Can I spawn ants?
    spawned_this_tick = 0
    while (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Worker.COST
    ):
        avg_enemy_ants = (enemy_fighters + enemy_fighters_in_my_area) // 2
        num_fighter_to_save_up_for = min(int(tick > 50) + 0.5 * avg_enemy_ants, 5)
        amount_to_save = stats.ants.Fighter.COST * num_fighter_to_save_up_for
        can_spawn_worker = (my_energy - amount_to_save) >= stats.ants.Worker.COST
        can_spawn_fighter = (my_energy - amount_to_save) >= stats.ants.Fighter.COST
        can_spawn_settler = (my_energy - amount_to_save) >= stats.ants.Settler.COST

        if am_being_attacked or len(defending_fighters) < enemy_fighters_in_my_area:
            if my_energy >= stats.ants.Fighter.COST:
                goal = closest_enemy_fighter
                if goal is None:
                    print("goal is none")
                    break
                this_ant_id = create_ant(goal)
                defending_fighters.add(this_ant_id)
                requests.append(SpawnRequest(AntTypes.FIGHTER, id=this_ant_id, color=None, goal=goal))
                current_ants[my_index][AntTypes.FIGHTER] += 1
                my_energy -= stats.ants.Fighter.COST
                spawned_this_tick += 1
                total_ants += 1
                continue
            else:
                break
        elif can_spawn_worker and can_spawn_fighter and can_spawn_settler or (can_spawn_worker and tick < 20):

            # decide if an attack is viable
            options = []
            my_ants = current_ants[my_index][AntTypes.WORKER] + current_ants[my_index][AntTypes.SETTLER] + \
                      current_ants[my_index][AntTypes.FIGHTER]
            for enemy_index in list(alive_enemy_indexes):
                enemy_energy = enemy_energies[enemy_index]
                dist_to_enemy_spawn = dijkstras_distances[my_index][spawns[enemy_index]]
                enemy_num_worker_ants = current_ants[enemy_index][AntTypes.WORKER]
                time_to_get_there = dist_to_enemy_spawn / stats.ants.Fighter.SPEED
                num_spawnable_fighters = min(my_energy / stats.ants.Fighter.COST, stats.general.MAX_SPAWNS_PER_TICK -
                                             spawned_this_tick, stats.general.MAX_ANTS_PER_PLAYER - my_ants)
                estimated_dmg = num_spawnable_fighters * (
                            stats.ants.Fighter.LIFESPAN - time_to_get_there) * stats.ants.Fighter.ATTACK * \
                                stats.ants.Fighter.NUM_ATTACKS
                enemy_total_ants = current_ants[enemy_index][AntTypes.WORKER] + current_ants[enemy_index][
                    AntTypes.SETTLER] \
                                   + current_ants[enemy_index][AntTypes.FIGHTER]
                future_enemy_energy_gain = get_expected_energy_gain(enemy_index, time_to_get_there)
                enemy_spawnable_fighters = min((enemy_energy + future_enemy_energy_gain) / stats.ants.Fighter.COST, stats.general.MAX_SPAWNS_PER_TICK, stats.general.MAX_ANTS_PER_PLAYER - enemy_total_ants)
                enemy_defendable_dmg = enemy_spawnable_fighters * stats.ants.Fighter.ATTACK * stats.ants.Fighter.NUM_ATTACKS * stats.ants.Fighter.LIFESPAN
                if current_ants[my_index][AntTypes.WORKER] >= 0.6 * stats.general.MAX_ANTS_PER_PLAYER:
                    value = estimated_dmg - enemy_defendable_dmg
                    if value > 0 or (my_energy >= 0.8 * stats.general.MAX_ENERGY_STORED):
                        options.append((estimated_dmg, enemy_index))

            if options:
                best_enemy_to_attack = max(options, key=operator.itemgetter(0))[1]
                while (my_energy >= stats.ants.Fighter.COST and my_ants < stats.general.MAX_ANTS_PER_PLAYER and
                       spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK):
                    print("Spawning attack fighter!!!!")
                    goal = spawns[best_enemy_to_attack]
                    this_ant_id = create_ant(goal)
                    # print(my_energy)
                    requests.append(SpawnRequest(AntTypes.FIGHTER, id=this_ant_id, color=None, goal=goal))
                    current_ants[my_index][AntTypes.FIGHTER] += 1
                    my_energy -= stats.ants.Fighter.COST
                    spawned_this_tick += 1
                    total_ants += 1
                    my_ants += 1
                break

            # choose which is more helpful
            if tick > 0.5 * stats.hill.GRACE_PERIOD and total_ants > 0.7 * stats.general.MAX_ANTS_PER_PLAYER and \
                    current_ants[my_index][AntTypes.SETTLER] <= 0.2 * stats.general.MAX_ANTS_PER_PLAYER and active_zone \
                    and tick - last_zone_activation_tick + dijkstras_distances[my_index][active_zone[0]] / \
                    stats.ants.Settler.SPEED < stats.hill.MAX_ZONE_TIME * 0.7:
                goal = random.choice(active_zone)
                requests.append(SpawnRequest(AntTypes.SETTLER, id=create_ant(goal), color=None, goal=goal))
                current_ants[my_index][AntTypes.SETTLER] += 1
                my_energy -= stats.ants.Settler.COST
                spawned_this_tick += 1
                total_ants += 1
            else:
                if total_ants > 0.8 * stats.general.MAX_ANTS_PER_PLAYER and not enemy_fighters:
                    break
                # spawn a worker ant
                if results:
                    for (loc, energy_return, maximum_ants_in_pipeline) in results:
                        if len(worker_pipelines[loc]) < maximum_ants_in_pipeline:
                            goal = loc
                            ant_id = create_ant(goal)
                            worker_pipelines[loc].add(ant_id)
                            requests.append(SpawnRequest(AntTypes.WORKER, id=ant_id, color=None, goal=goal))
                            current_ants[my_index][AntTypes.WORKER] += 1
                            # Additionally, let's update how much energy I've got.
                            my_energy -= stats.ants.Worker.COST
                            spawned_this_tick += 1
                            total_ants += 1
                            break
                else:
                    break

        else:
            break

    # print(f"my ants: {current_ants[my_index]}")
    # print(current_ants)

    # print(f"energy at the end of func: {my_energy}")
    return requests
