from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import DepositEvent, DieEvent, ProductionEvent, SpawnEvent, ZoneDeactivateEvent, ZoneActiveEvent, QueenAttackEvent
from codequest22.server.requests import GoalRequest, SpawnRequest


def get_team_name():
    return f"TacticalTable"

my_index = None
target_index = None
def read_index(player_index, n_players):
    global my_index, target_index
    my_index = player_index
    if my_index == 0:
        target_index = 2
    elif my_index == 1:
        target_index = 3
    elif my_index == 2:
        target_index = 0
    elif my_index == 3:
        target_index = 1


my_energy = stats.general.STARTING_ENERGY
map_data = {}
spawns = [None]*4
food = []
hills = []
distance = {}
closest_site = None
closest_hill_site = None
total_ants = 0
total_workers = 0
total_settlers = 0
total_fighters = 0
underattack = 0
current_tick = 0
todeploy = 0
sendEnd = 0
ant_types = {}
currentactivezone = False
active_hill_site = []

def read_map(md, energy_info):
    global map_data, spawns, food, distance, closest_site, hills, closest_hill_site, active_hill_site, startpoint, target_location
    map_data = md
    for y in range(len(map_data)):
        for x in range(len(map_data[0])):
            if map_data[y][x] == "F":
                food.append((x, y))
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
    hill_sites = list(sorted(hills, key=lambda prod: distance[prod]))
    closest_hill_site = hill_sites[0]
    target_location = spawns[target_index]

def handle_failed_requests(requests):
    global my_energy
    for req in requests:
        if req.player_index == my_index:
            print(f"Request {req.__class__.__name__} failed. Reason: {req.reason}.")
            raise ValueError()

def handle_events(events):
    global my_energy, total_ants, total_workers, total_fighters, total_settlers, currentactivezone, underattack, current_tick, active_hill_site, startpoint, target_location, todeploy, sendEnd
    requests = []

    settlers_this_tick = 0
    fighters_this_tick = 0
    current_tick += 1

    for ev in events:
        if isinstance(ev, DepositEvent):
            if ev.player_index == my_index:
                # One of my worker ants just made it back to the Queen! Let's send them back to the food site.
                requests.append(GoalRequest(ev.ant_id, closest_site))
                # Additionally, let's update how much energy I've got.
                my_energy = ev.cur_energy
        elif isinstance(ev, ProductionEvent):
            if ev.player_index == my_index:
                # One of my worker ants just made it to the food site! Let's send them back to the Queen.
                requests.append(GoalRequest(ev.ant_id, spawns[my_index]))
        elif isinstance(ev, DieEvent):
            if ev.player_index == my_index:
                # One of my workers just died :(
                antid = ev.ant_id
                anttype = ant_types[antid]
                if anttype == AntTypes.SETTLER:
                    total_settlers -= 1
                elif anttype == AntTypes.WORKER:
                    total_workers -= 1
                elif anttype == AntTypes.FIGHTER:
                    total_fighters -= 1
                ant_types.pop(antid)
                total_ants -= 1
        elif isinstance(ev, SpawnEvent):
            if ev.player_index == my_index:
                antid, anttype = ev.ant_id, ev.ant_type
                ant_types[antid] = anttype
        elif isinstance(ev, ZoneActiveEvent):
            currentactivezone = True
            active_hill_site = ev.points[0]
            activeFor = ev.num_ticks
            sendEnd = current_tick + (activeFor - 20)
        elif isinstance(ev, ZoneDeactivateEvent):
            currentactivezone = False
        elif isinstance(ev, QueenAttackEvent):
            if ev.queen_player_index == my_index:
                underattack = True
                todeploy = 25

    # Can I spawn ants?
    spawned_this_tick = 0
    if (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Fighter.COST and
            current_tick >= 1000
    ):
        spawned_this_tick += 1
        total_ants += 1
        total_fighters += 1
        requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=target_location)) #attack queen with most points
        my_energy -= stats.ants.Fighter.COST

    if (
        total_ants < stats.general.MAX_ANTS_PER_PLAYER and
        spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
        my_energy >= stats.ants.Fighter.COST and underattack == True and
        todeploy != 0
    ):
        spawned_this_tick += 1
        total_ants += 1
        total_fighters += 1
        todeploy -= 1
        requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=spawns[my_index])) #protect the queen
        my_energy -= stats.ants.Fighter.COST

    if (
        total_ants < stats.general.MAX_ANTS_PER_PLAYER and
        spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
        my_energy >= stats.ants.Worker.COST and total_workers <= 25
    ):
        spawned_this_tick += 1
        total_ants += 1
        total_workers += 1
        requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=closest_site))
        my_energy -= stats.ants.Worker.COST

    if (
        total_ants < stats.general.MAX_ANTS_PER_PLAYER and
        spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
        my_energy >= stats.ants.Settler.COST and currentactivezone == True and
        settlers_this_tick <= 3 and
        current_tick <= sendEnd
    ):
        spawned_this_tick += 1
        total_ants += 1
        total_settlers += 1
        requests.append(SpawnRequest(AntTypes.SETTLER, id=None, color=None, goal=active_hill_site)) #go to active hill
        my_energy -= stats.ants.Settler.COST
        settlers_this_tick += 1

    if (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Fighter.COST and currentactivezone == True and
            fighters_this_tick <= 2 and
            current_tick <= sendEnd
    ):
        spawned_this_tick += 1
        total_ants += 1
        total_settlers += 1
        requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=active_hill_site)) #deploy with settlers
        my_energy -= stats.ants.Fighter.COST
        fighters_this_tick += 1


    return requests
