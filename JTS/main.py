from PIL.ImageQt import rgb
from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import DepositEvent, DieEvent, ProductionEvent, ZoneActiveEvent, ZoneDeactivateEvent, \
    QueenAttackEvent, SettlerScoreEvent, TeamDefeatedEvent
from codequest22.server.requests import GoalRequest, SpawnRequest


def get_team_name():
    return "JTS"


my_index = None


def read_index(player_index, n_players):
    global my_index
    my_index = player_index


my_energy = stats.general.STARTING_ENERGY
MAX_SPAWNS_PER_TICK = stats.general.MAX_SPAWNS_PER_TICK
MAX_ANTS_PER_PLAYER = stats.general.MAX_ANTS_PER_PLAYER

map_data = {}
spawns = [None] * 4
enemy_spawns = [None] * 4
food = []
distance = {}
closest_site = None
active_zone = None
total_ants = 0
zone_is_active = False
total_zone_activations = 0

MY_HP = stats.general.QUEEN_HEALTH

count_ants = {
    "workers": 0,
    "settlers": 0,
    "fighters": 0
}


def read_map(md, energy_info):
    global map_data, spawns, food, distance, closest_site
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


def handle_failed_requests(requests):
    global my_energy
    for req in requests:
        if req.player_index == my_index:
            print(f"Request {req.__class__.__name__} failed. Reason: {req.reason}.")
            raise ValueError()
    # pass


# # Enemy spawn stuff
# is_defeated = [False] * 4
# is_defeated[my_index] = True
# # enemy_spawns = [item for i, item in enumerate(spawns) if i != my_index]
# enemy_spawns = tuple(zip(enemy_spawns, is_defeated))

is_defeated = [False] * 4


def handle_events(events):
    global my_energy, total_ants, active_zone, zone_is_active, total_zone_activations, MY_HP, is_defeated
    requests = []
    is_defeated[my_index] = True
    enemy = spawns[is_defeated.index(False)]
    for ev in events:
        if isinstance(ev, DepositEvent):
            if ev.player_index == my_index:
                requests.append(GoalRequest(ev.ant_id, closest_site))
                my_energy = ev.cur_energy

        if isinstance(ev, ProductionEvent):
            if ev.player_index == my_index:
                # One of my worker ants just made it to the food site! Let's send them back to the Queen.
                requests.append(GoalRequest(ev.ant_id, spawns[my_index]))
        if isinstance(ev, DieEvent):
            if ev.player_index == my_index:
                # One of my workers just died :(
                total_ants -= 1
                if ev.ant_str["classname"] == "SettlerAnt":
                    count_ants["settlers"] -= 1

                if ev.ant_str["classname"] == "WorkerAnt":
                    count_ants["workers"] -= 1
        if isinstance(ev, ZoneActiveEvent):
            active_zone = ev.points[0]
            zone_is_active = True

        if isinstance(ev, ZoneDeactivateEvent):
            zone_is_active = False
            active_zone = None
            total_zone_activations += 1

        if isinstance(ev, QueenAttackEvent):
            # print(ev.queen_hp)
            if ev.queen_player_index == my_index:
                MY_HP = ev.queen_hp

        if isinstance(ev, TeamDefeatedEvent):
            is_defeated[ev.defeated_index] = True

        if isinstance(ev, SettlerScoreEvent):
            if ev.player_index == my_index:
                # print(ev.score_amount)
                pass
    spawned_this_tick = 0

    workers = 0
    settlers = 0
    fighters = 0

    # if total_zone_activations >= 2:
    #     workers = MAX_SPAWNS_PER_TICK - 1 if not zone_is_active else 1
    #     settlers = 0 if not zone_is_active else MAX_SPAWNS_PER_TICK - 3
    #     fighters = 1 if not zone_is_active else 5
    #
    # else:
    #     workers = MAX_SPAWNS_PER_TICK if not zone_is_active else 1
    #     settlers = 0 if not zone_is_active else MAX_SPAWNS_PER_TICK - 1

    # if MY_HP >= (stats.general.QUEEN_HEALTH / 2):
    #     if zone_is_active:
    #         if count_ants["workers"] >= MAX_ANTS_PER_PLAYER / 2:
    #             settlers = 5
    #         else:
    #             workers = 2
    #             settlers = 3
    #     else:
    #         if count_ants["workers"] >= MAX_ANTS_PER_PLAYER / 2:
    #             fighters = 5
    #         else:
    #             workers = 3
    #             fighters = 2
    # else:
    #     if zone_is_active:
    #         if count_ants["workers"] >= MAX_ANTS_PER_PLAYER / 2:
    #             settlers = 3
    #             fighters = 2
    #         else:
    #             workers = 1
    #             settlers = 2
    #             fighters = 2
    #     else:
    #         if count_ants["workers"] >= MAX_ANTS_PER_PLAYER / 3 or stats.ants.Fighter.COST * 5 >= my_energy:
    #             fighters = 5
    #         else:
    #             workers = 2
    #             fighters = 3

    if zone_is_active:
        if count_ants["workers"] > MAX_ANTS_PER_PLAYER / 2:
            settlers = 5
        else:
            workers = 2
            settlers = 3
    else:
        if count_ants["workers"] > MAX_ANTS_PER_PLAYER / 2:
            fighters = 5
        else:
            workers = 3
            fighters = 2

    # if (stats.ants.Worker.COST * workers) + (stats.ants.Settler.COST * settlers) + (
    #         stats.ants.Fighter.COST * fighters) > my_energy:
    #     workers = int((my_energy / stats.ants.Worker.COST) - 0.5)
    #     fighters = 0
    #     settlers = 0

    print(total_ants, workers, settlers, fighters)

    for _ in range(workers):
        if total_ants + 1 <= MAX_ANTS_PER_PLAYER and my_energy >= stats.ants.Worker.COST:
            requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=closest_site))
            spawned_this_tick += 1
            total_ants += 1
            count_ants["workers"] += 1
            my_energy -= stats.ants.Worker.COST
        else:
            break

    for _ in range(settlers):
        if total_ants + 1 <= stats.general.MAX_ANTS_PER_PLAYER and my_energy >= stats.ants.Settler.COST:
            requests.append(SpawnRequest(AntTypes.SETTLER, id=None, color=None, goal=active_zone))
            spawned_this_tick += 1
            total_ants += 1
            count_ants["settlers"] += 1
            my_energy -= stats.ants.Settler.COST
        else:
            break

    for _ in range(fighters):
        if total_ants + 1 <= MAX_ANTS_PER_PLAYER and my_energy >= stats.ants.Fighter.COST:
            requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=enemy))
            spawned_this_tick += 1
            total_ants += 1
            count_ants["settlers"] += 1
            my_energy -= stats.ants.Settler.COST
        else:
            break

    return requests

