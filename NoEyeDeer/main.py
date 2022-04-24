from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import DepositEvent, DieEvent, ProductionEvent
from codequest22.server.requests import GoalRequest, SpawnRequest


def get_team_name():
    return f"Sample Bot"


my_index = None


def read_index(player_index, n_players):
    global my_index
    my_index = player_index


my_energy = stats.general.STARTING_ENERGY
map_data = {}
spawns = [None] * 4
food = []
distance = {}
closest_site = None
total_ants = 0
enemy_site = None
hill = []
closest_hill_site = None


def read_map(md, energy_info):
    global map_data, spawns, food, distance, closest_site, enemy_site, hill, closest_hill_site
    map_data = md
    for y in range(len(map_data)):
        for x in range(len(map_data[0])):
            if map_data[y][x] == "F":
                food.append((x, y))
            if map_data[y][x] in "RBYG":
                spawns["RBYG".index(map_data[y][x])] = (x, y)
            if map_data[y][x] == 'Z':
                hill.append((x, y))
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
    player_site = list(sorted(spawns, key=lambda prod: distance[prod]))
    enemy_site = player_site[3]
    hill_sites = list(sorted(hill, key=lambda prod: distance[prod]))
    closest_hill_site = hill_sites[0]


def handle_failed_requests(requests):
    global my_energy
    for req in requests:
        if req.player_index == my_index:
            print(
                f"Request {req.__class__.__name__} failed. Reason: {req.reason}.")
            raise ValueError()


def handle_events(events):
    global my_energy, total_ants, fighters_size, workers_size, settlers_size
    requests = []

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
                total_ants -= 1

    # Can I spawn ants?
    spawned_this_tick = 0
    fighters_size = 0
    workers_size = 0
    settlers_size = 0
    while (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and
            spawned_this_tick <= stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Worker.COST * 2 + stats.ants.Fighter.COST
            + stats.ants.Worker.COST
    ):
        if total_ants <= stats.general.MAX_ANTS_PER_PLAYER - 4 and \
                spawned_this_tick <= stats.general.MAX_SPAWNS_PER_TICK - 4:
            total_ants += 4
            spawned_this_tick += 4
            # Spawn an ant, give it some id, no color, and send it to the closest site.
            # I will pay the base cost for this ant, so cost=None.
            requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None,
                                         goal=enemy_site))
            requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None,
                                         goal=closest_site))
            requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None,
                                         goal=closest_hill_site))
            requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None,
                                         goal=closest_site))
            # requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None,
            #                              goal=closest_site))
            # my_energy -= stats.ants.Fighter.COST
            my_energy -= stats.ants.Worker.COST * 3 + stats.ants.Fighter.COST
        else:
            break

    return requests
