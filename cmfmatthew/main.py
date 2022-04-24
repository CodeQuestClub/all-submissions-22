from timeit import repeat
from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import DepositEvent, DieEvent, ProductionEvent
from codequest22.server.requests import GoalRequest, SpawnRequest


def get_team_name():
    return f"magimidori"


my_index = None
my_energy = stats.general.STARTING_ENERGY
map_data = {}
spawns = [None]*4
food = []
food_sites = []
hill = []
hill_sites = []
distance = {}
closest_food = closest_food2 = None
closest_hill = closest_hill2 = None
total_ants = 0
spawned_this_tick = 0
sid = 0
wid = 0
fid = 0

fflag = 0
hflag = 0


def read_index(player_index, n_players):
    global my_index
    my_index = player_index


def read_map(md, energy_info):
    global map_data, spawns, food, hill, distance, closest_food, closest_food2, closest_hill, closest_hill2
    map_data = md
    for y in range(len(map_data)):
        for x in range(len(map_data[0])):
            if map_data[y][x] == "Z":
                hill.append((x, y))
            elif map_data[y][x] == "F":
                food.append((x, y))
            elif map_data[y][x] in "RBYG":
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
        if expanded[idx[(a, b)]]:
            continue
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
    food_sites = list(sorted(food, key=lambda prod: distance[prod]),)
    closest_food = food_sites[0]
    closest_food2 = food_sites[1]
    hill_sites = list(sorted(hill, key=lambda prod: distance[prod]),)
    closest_hill = hill_sites[0]
    closest_hill2 = hill_sites[6]


def handle_failed_requests(requests):
    global my_energy
    for req in requests:
        if req.player_index == my_index:
            print(
                f"Request {req.__class__.__name__} failed. Reason: {req.reason}.")
            raise ValueError()


def spawn_wants(requests):
    global total_ants, spawned_this_tick, my_energy, wid
    # Spawn worker ant
    if (total_ants < stats.general.MAX_ANTS_PER_PLAYER and
        spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Worker.COST):
        spawned_this_tick += 1
        total_ants += 1
        requests.append(SpawnRequest(
            AntTypes.WORKER,
            id=int(str(3) + str(wid)),
            color=None,
            goal=closest_food,))
        wid += 1
        my_energy -= stats.ants.Worker.COST
    return requests


def spawn_wants2(requests):
    global total_ants, spawned_this_tick, my_energy,  wid
    # Spawn worker ant
    if (total_ants < stats.general.MAX_ANTS_PER_PLAYER and
        spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Worker.COST):
        spawned_this_tick += 1
        total_ants += 1
        requests.append(SpawnRequest(
            AntTypes.WORKER,
            id=int(str(3) + str(wid)),
            color=None,
            goal=closest_food2,))
        wid += 1
        my_energy -= stats.ants.Worker.COST
    return requests


def spawn_sants(requests):
    global total_ants, spawned_this_tick, my_energy,  sid
    # Spawn settlers
    if (total_ants < stats.general.MAX_ANTS_PER_PLAYER and
        spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Settler.COST):
        spawned_this_tick += 1
        total_ants += 1
        requests.append(SpawnRequest(
            AntTypes.SETTLER,
            id=int(str(5) + str(sid)),
            color=None,
            goal=closest_hill,))
        sid += 1
        my_energy -= stats.ants.Settler.COST
    return requests


def spawn_sants2(requests):
    global total_ants, spawned_this_tick, my_energy,  sid
    # Spawn settlers
    if (total_ants < stats.general.MAX_ANTS_PER_PLAYER and
        spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Settler.COST):
        spawned_this_tick += 1
        total_ants += 1
        requests.append(SpawnRequest(
            AntTypes.SETTLER,
            id=int(str(5) + str(sid)),
            color=None,
            goal=closest_hill2,))
        sid += 1
        my_energy -= stats.ants.Settler.COST
    return requests


def spawn_fants(requests):
    global total_ants, spawned_this_tick, my_energy, fid
    # Spawn fighters
    if (total_ants < stats.general.MAX_ANTS_PER_PLAYER and
        spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Settler.COST):
        spawned_this_tick += 1
        total_ants += 1
        requests.append(SpawnRequest(
            AntTypes.FIGHTER,
            id=int(str(7) + str(fid)),
            color=None,
            goal=closest_hill,))
        fid += 1
        my_energy -= stats.ants.Fighter.COST
    return requests


def spawn_fants2(requests):
    global total_ants, spawned_this_tick, my_energy, fid
    # Spawn fighters
    if (total_ants < stats.general.MAX_ANTS_PER_PLAYER and
        spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Settler.COST):
        spawned_this_tick += 1
        total_ants += 1
        requests.append(SpawnRequest(
            AntTypes.FIGHTER,
            id=int(str(7) + str(fid)),
            color=None,
            goal=closest_hill2,))
        fid += 1
        my_energy -= stats.ants.Fighter.COST
    return requests


def handle_events(events):
    global my_energy, total_ants, want, sant, fant, spawned_this_tick, fflag, hflag
    requests = []
    spawned_this_tick = 0

    for ev in events:
        if isinstance(ev, DepositEvent):
            if ev.player_index == my_index:
                # send them back to the food site.
                requests.append(GoalRequest(ev.ant_id, closest_food))
                # Additionally, let's update how much energy I've got.
                my_energy = ev.cur_energy
        elif isinstance(ev, ProductionEvent):
            if ev.player_index == my_index:
                # send them back to the Queen.
                requests.append(GoalRequest(ev.ant_id, spawns[my_index]))
        elif isinstance(ev, DieEvent):
            if ev.player_index == my_index:
                # One of my ants just died :(
                total_ants -= 1

    if(total_ants < 10) or (my_energy < 100):
        if (fflag == 0) or (fflag == 1):
            spawn_wants(requests)
            fflag += 1
        else:
            spawn_wants2(requests)
            fflag = 0
    elif(total_ants > 7):
        if (hflag == 0):
            spawn_sants(requests)
            spawn_fants(requests)
            hflag += 1
        else:
            spawn_sants2(requests)
            spawn_fants2(requests)
            hflag = 0
    return requests
