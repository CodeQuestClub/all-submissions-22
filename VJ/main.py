from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import DepositEvent, ProductionEvent, DieEvent, ZoneActiveEvent, ZoneDeactivateEvent, QueenAttackEvent, SettlerScoreEvent, FoodTileActiveEvent, TeamDefeatedEvent
from codequest22.server.requests import SpawnRequest, GoalRequest
from enum import Enum


class Ant(Enum):
    WORKER = 0
    SETTLER = 1
    FIGHTER = 2


food = []  # to store all food positions

my_energy = stats.general.STARTING_ENERGY
spawns = [None] * 4
food = []  # stores positions of all foods
distance = {}
closest_food_sites = [None] * 4
total_ants = [0] * len(Ant)
zone_ticks = 0
active_zone = any
food_site_counter = 0
attack_records = [0] * 4
queen_cur_hp = stats.general.QUEEN_HEALTH

counter = 0


def get_team_name():
    return "vj"


def read_index(player_index, n_players):
    global my_index
    my_index = player_index


def read_map(md, energy_info):
    global map_data, spawns, food, distance, max_health_food_sites
    map_data = md

    max_health = -1
    max_health_food_sites = []

    # find food sites with max energy
    for item in energy_info.items():
        if item[1] > max_health:
            max_health = item[1]
    for item in energy_info.items():
        if item[1] == max_health:
            max_health_food_sites.append(item[0])

    for y in range(len(map_data)):
        for x in range(len(map_data[0])):
            if map_data[y][x] == "F":
                food.append((x, y))
            if map_data[y][x] in "RBYG":
                spawns["RBYG".index(map_data[y][x])] = (x, y)

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
        for a, b in [(y+1, x), (y-1, x), (y, x+1), (y, x-1)]:
            if 0 <= a < h and 0 <= b < w and map_data[a][b] != "W":
                adj[(x, y)].append((b, a, 1))
    # Step 2: Run Dijkstra's for each player
    import heapq
    for i in range(len(closest_food_sites)):
        start = spawns[i]
        ex = [False] * len(points)
        # What nodes are we currently looking at?
        queue = []
        # What is the distance to the startpoint from every other point?
        heapq.heappush(queue, (0, start))
        while queue:
            d, (a, b) = heapq.heappop(queue)
            if ex[idx[(a, b)]]:
                continue
            # If we haven't already looked at this point, put it in expanded and update the distance.
            ex[idx[(a, b)]] = True
            distance[(a, b)] = d
            # Look at all neighbours
            for j, k, d2 in adj[(a, b)]:
                if not ex[idx[(j, k)]]:
                    heapq.heappush(queue, (
                        d + d2,
                        (j, k)
                    ))
        # Now I can calculate the closest food site.
        food_sites = list(sorted(food, key=lambda prod: distance[prod]))
        closest_food_sites[i] = food_sites[0]


def handle_failed_requests(requests):
    pass


def handle_events(events):
    global my_energy, zone_ticks, active_zone, food_site_counter, attack_records, counter
    requests = []
    ants_spawned = 0
    zone_activated = False

    if zone_ticks > 0:
        zone_ticks -= 1
        zone_activated = True
    else:
        active_zone = any

    if my_energy == 20:
        if (sum(total_ants) < stats.general.MAX_ANTS_PER_PLAYER and
            ants_spawned < stats.general.MAX_SPAWNS_PER_TICK and
                my_energy >= stats.ants.Worker.COST):
            requests.append(SpawnRequest(AntTypes.WORKER, id=None,
                            color=None, goal=closest_food_sites[my_index]))
            ants_spawned += 1
            total_ants[Ant.WORKER.value] += 1
            my_energy -= stats.ants.Worker.COST

    for e in events:
        # remove the dead ones from the map
        if isinstance(e, TeamDefeatedEvent):
            spawns[e.defeated_index] = None

        if isinstance(e, QueenAttackEvent):
            if e.queen_player_index == my_index:
                attack_records[e.ant_player_index] += queen_cur_hp - e.queen_hp
                max_damage = -1
                max_damage_player_index = -1
                for i in range(len(attack_records)):
                    if attack_records[i] > max_damage and attack_records[i] != 0:
                        max_damage = attack_records[i]
                        max_damage_player_index = i
                if spawns[max_damage_player_index] is not None:
                    while (
                        sum(total_ants) < stats.general.MAX_ANTS_PER_PLAYER - 50 and
                        ants_spawned < stats.general.MAX_SPAWNS_PER_TICK - 3 and
                        my_energy >= stats.ants.Fighter.COST
                    ):
                        requests.append(SpawnRequest(
                            AntTypes.FIGHTER, id=None, color=None, goal=spawns[max_damage_player_index]))
                        ants_spawned += 1
                        total_ants[Ant.FIGHTER.value] += 1
                        my_energy -= stats.ants.Fighter.COST

        if isinstance(e, DepositEvent):
            # if i am depositing
            if e.player_index == my_index:
                requests.append(GoalRequest(
                    e.ant_id, closest_food_sites[my_index]))
                my_energy = e.cur_energy
            # if opponent is depositing, attack them
            else:
                if my_energy > 210 and e.cur_energy < 200:
                    for _ in range(4):
                        requests.append(SpawnRequest(
                            AntTypes.FIGHTER, id=None, color=None, goal=spawns[e.player_index]))
                        ants_spawned += 1
                        total_ants[Ant.FIGHTER.value] += 1
                        my_energy -= stats.ants.Fighter.COST

        if isinstance(e, FoodTileActiveEvent):
            if my_energy < 190:
                for _ in range(stats.general.MAX_SPAWNS_PER_TICK):
                    if my_energy > stats.ants.Worker.COST:
                        requests.append(SpawnRequest(
                            AntTypes.WORKER, id=None, color=None, goal=e.pos))
                        ants_spawned += 1
                        total_ants[Ant.WORKER.value] += 1
                        my_energy -= stats.ants.Worker.COST

        if isinstance(e, ProductionEvent):
            if e.player_index == my_index:
                requests.append(GoalRequest(e.ant_id, spawns[my_index]))
            else:
                if my_energy > 130 and spawns[e.player_index] is not None and counter % 2 == 0:
                    requests.append(SpawnRequest(
                        AntTypes.FIGHTER, id=None, color=None, goal=closest_food_sites[e.player_index]))
                    total_ants[Ant.FIGHTER.value] += 1
                    ants_spawned += 1
                    my_energy -= stats.ants.Fighter.COST
                    counter += 1

        if isinstance(e, DieEvent):
            if e.player_index == my_index:
                if e.ant_str['classname'] == 'WorkerAnt':
                    total_ants[Ant.WORKER.value] -= 1

                    for i in range(len(spawns)):
                        if i != my_index and i is not None:
                            if my_energy > 250:
                                while (
                                    sum(total_ants) < stats.general.MAX_ANTS_PER_PLAYER and
                                    ants_spawned < stats.general.MAX_SPAWNS_PER_TICK and
                                    my_energy >= stats.ants.Fighter.COST
                                ):
                                    requests.append(SpawnRequest(
                                        AntTypes.FIGHTER, id=None, color=None, goal=spawns[i]))
                                    ants_spawned += 1
                                    total_ants[Ant.FIGHTER.value] += 1
                                    my_energy -= stats.ants.Fighter.COST

                elif e.ant_str['classname'] == 'SettlerAnt':
                    total_ants[Ant.SETTLER.value] -= 1
                    # when a settler dies, spawn more if the zone is active
                    if zone_activated:
                        while (
                            sum(total_ants) < stats.general.MAX_ANTS_PER_PLAYER and
                            ants_spawned < stats.general.MAX_SPAWNS_PER_TICK and
                            my_energy >= stats.ants.Settler.COST
                        ):
                            requests.append(SpawnRequest(
                                AntTypes.SETTLER, id=None, color=None, goal=active_zone))
                            ants_spawned += 1
                            total_ants[Ant.SETTLER.value] += 1
                            my_energy -= stats.ants.Settler.COST
                else:
                    total_ants[Ant.FIGHTER.value] -= 1

        if isinstance(e, ZoneActiveEvent):
            zone_activated = True
            zone_ticks = e.num_ticks
            active_zone = e.points[0]
            # spawn settlers when zone is activated
            while (
                sum(total_ants) < stats.general.MAX_ANTS_PER_PLAYER and
                ants_spawned < stats.general.MAX_SPAWNS_PER_TICK and
                my_energy >= stats.ants.Settler.COST
            ):
                requests.append(SpawnRequest(AntTypes.SETTLER,
                                id=None, color=None, goal=e.points[0]))
                total_ants[Ant.SETTLER.value] += 1
                my_energy -= stats.ants.Settler.COST
                ants_spawned += 1

        if isinstance(e, ZoneDeactivateEvent):
            zone_activated = False

        if isinstance(e, SettlerScoreEvent):
            if e.player_index != my_index:
                for _ in range(6):
                    if (sum(total_ants) < stats.general.MAX_ANTS_PER_PLAYER and
                        ants_spawned < stats.general.MAX_SPAWNS_PER_TICK and
                            my_energy >= stats.ants.Fighter.COST):
                        requests.append(SpawnRequest(
                            AntTypes.FIGHTER, id=None, color=None, goal=spawns[e.player_index]))
                        total_ants[Ant.FIGHTER.value] += 1
                        my_energy -= stats.ants.Fighter.COST

    if not zone_activated and my_energy < 180:
        for _ in range(len(max_health_food_sites)):
            while (
                    sum(total_ants) < stats.general.MAX_ANTS_PER_PLAYER - 25 and
                    ants_spawned < stats.general.MAX_SPAWNS_PER_TICK and
                    my_energy >= stats.ants.Worker.COST):
                requests.append(SpawnRequest(
                    AntTypes.WORKER, id=None, color=None, goal=max_health_food_sites[(food_site_counter) % len(max_health_food_sites)]))
                ants_spawned += 1
                total_ants[Ant.WORKER.value] += 1
                my_energy -= stats.ants.Worker.COST
                food_site_counter += 1
    elif not zone_activated:
        while (
            sum(total_ants) < stats.general.MAX_ANTS_PER_PLAYER - 25 and
            ants_spawned < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Worker.COST
        ):
            requests.append(SpawnRequest(AntTypes.WORKER,
                            id=None, color=None, goal=closest_food_sites[my_index]))
            ants_spawned += 1
            total_ants[Ant.WORKER.value] += 1
            my_energy -= stats.ants.Worker.COST
    else:
        for _ in range(len(max_health_food_sites)):
            while (
                    sum(total_ants) < stats.general.MAX_ANTS_PER_PLAYER - 50 and
                    ants_spawned < stats.general.MAX_SPAWNS_PER_TICK and
                    my_energy >= stats.ants.Worker.COST):
                requests.append(SpawnRequest(
                    AntTypes.WORKER, id=None, color=None, goal=max_health_food_sites[(food_site_counter) % len(max_health_food_sites)]))
                ants_spawned += 1
                total_ants[Ant.WORKER.value] += 1
                my_energy -= stats.ants.Worker.COST
                food_site_counter += 1

    return requests
