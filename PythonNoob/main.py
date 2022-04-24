from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import DepositEvent, DieEvent, ProductionEvent, ZoneActiveEvent, SettlerScoreEvent, ZoneDeactivateEvent, FoodTileActiveEvent, FoodTileDeactivateEvent, TeamDefeatedEvent, AttackEvent
from codequest22.server.requests import GoalRequest, SpawnRequest

def get_team_name():
    return f"Final Bot"
n_player = 0
my_index = None
def read_index(player_index, n_players):
    global my_index
    my_index = player_index
    n_player = n_players

my_energy = stats.general.STARTING_ENERGY
map_data = {}
spawns = [None]*4
food = []
hill = []
closest_hill_site = None
distance = {}
closest_site = None
total_ants = 0
count = 0
group_list = []
num_hill = 0
sant_id = 0
zone_count = 0
act_zone = []
last = 0
act_food = ()
last_food = 0
multiplier = 0
food_count = 0
food_act_dict = {}
spawn_sites = []
spawn = []
work_dict = {}
score = {}
team = []
tick = 0
signal = False
second_goal = 0
goal_record = {"0": 0, "1": 0}

def read_map(md, energy_info):
    global map_data, spawns, food, distance, closest_site, hill, closest_hill_site, group_list, num_hill, spawn, spawn_sites, score, team
    map_data = md

    for y in range(len(map_data)):
        for x in range(len(map_data[0])):
            if map_data[y][x] == "F":
                food.append((x, y))
            elif map_data[y][x] == "Z":
                hill.append((x, y))
            if map_data[y][x] in "RBYG":
                spawns["RBYG".index(map_data[y][x])] = (x, y)
                spawn.append(spawns["RBYG".index(map_data[y][x])])
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
    closest_site = food_sites  #[0:len(food_sites)//3]
    hill_sites = list(sorted(hill, key=lambda prod: distance[prod]))
    spawn_sites = list(sorted(spawn, key=lambda prod: distance[prod]))

    for i in range(len(hill_sites)):
        if i == 0:
            group_list = [hill_sites[i]]
        else:
            flag = 0
            for g in group_list:
                if abs(sum(hill_sites[i])-sum(g)) > 2:
                    flag = 1
                else:
                    flag = 0
                    break
            if flag == 1:
                group_list.append(hill_sites[i])
    ## print the grouped hills
    closest_hill_site = group_list[0]
    num_hill = len(group_list)

def handle_failed_requests(requests):
    global my_energy
    for req in requests:
        if req.player_index == my_index:
            print(f"Request {req.__class__.__name__} failed. Reason: {req.reason}.")
            raise ValueError()

def handle_events(events):
    global my_energy, total_ants, count, zone_count, act_zone, last, act_food, last_food, multiplier, food_count, food_act_dict, work_dict, tick, signal, second_goal
    global goal_record
    # global team, score
    requests = []

    for ev in events:
        if isinstance(ev, DepositEvent):
            if str(ev.player_index) not in team and ev.player_index != my_index:
                team.append(str(ev.player_index))
            if str(ev.player_index) not in score:
                score[str(ev.player_index)] = [str(ev.player_index), 0]
            if ev.ant_id not in work_dict and ev.player_index == my_index:
                work_dict[ev.ant_id] = 1
            elif ev.player_index == my_index:
                work_dict[ev.ant_id] += 1

            if ev.player_index == my_index:
                if tick > 100:
                    goal = count % 3
                    requests.append(GoalRequest(ev.ant_id, closest_site[goal]))
                    my_energy = ev.cur_energy
                elif len(food_act_dict) == 0 and work_dict[ev.ant_id] == 1: #
                # One of my worker ants just made it back to the Queen! Let's send them back to the food site.
                    goal = len(closest_site) - 1
                    requests.append(GoalRequest(ev.ant_id, closest_site[goal]))
                    my_energy = ev.cur_energy
                elif len(food_act_dict) == 0 and work_dict[ev.ant_id] == 2: #
                    goal = len(closest_site) - 1
                    # goal = int(ev.ant_id) % int(len(closest_site)*0.8 - 1) + 1
                    requests.append(GoalRequest(ev.ant_id, closest_site[goal]))
                    my_energy = ev.cur_energy
                elif len(food_act_dict) != 0:
                    food_pos_list = []
                    for i in food_act_dict.keys():
                        food_pos_list.append(food_act_dict[i][0])
                    food_act_sites = list(sorted(food_pos_list, key=lambda prod: distance[prod]))
                    if len(food_act_sites) == 1:
                        goal = 0
                    elif len(food_act_sites) == 2:
                        goal = 1
                    elif len(food_act_sites) == 3:
                        goal = 2
                    elif len(food_act_sites) == 4:
                        goal = 3
                    else:
                        goal = len(food_act_sites) - 1
                    # print(f"len(food_act_sites):{len(food_act_sites)}, goal:{goal}")
                    requests.append(GoalRequest(ev.ant_id, food_act_sites[goal]))
                    my_energy = ev.cur_energy
        elif isinstance(ev, ProductionEvent):
            if ev.player_index == my_index:
                # One of my worker ants just made it to the food site! Let's send them back to the Queen.
                # if ev.energy_amount != 30:
                #     print(ev.energy_amount)
                requests.append(GoalRequest(str(ev.ant_id), spawns[my_index]))
        elif isinstance(ev, DieEvent):
            if ev.player_index == my_index:
                # One of my workers just died :(
                total_ants -= 1

        elif isinstance(ev, ZoneActiveEvent):
            act_zone = ev.points
            last = ev.num_ticks
            zone_count = 0
            # print(act_zone, last)
        elif isinstance(ev, ZoneDeactivateEvent):
            act_zone = []
            last = 0
        elif isinstance(ev, FoodTileActiveEvent):
            food_act_dict[str(ev.pos)] = [ev.pos, ev.num_ticks, ev.multiplier]
            # print(f"FoodTileActiveEvent:{ev.multiplier}")
        elif isinstance(ev, FoodTileDeactivateEvent):
            del food_act_dict[str(ev.pos)]
        elif isinstance(ev, SettlerScoreEvent):
            signal = True
            if ev.player_index != my_index:
                score[str(ev.player_index)][1] += 1
        elif isinstance(ev, TeamDefeatedEvent):
            if str(ev.defeated_index) in score:
                del score[str(ev.defeated_index)]
            if ev.defeated_index != my_index and str(ev.defeated_index) in team:
                team.remove(str(ev.defeated_index))
            if spawns[ev.defeated_index] in spawn_sites:
                # print(spawns[ev.defeated_index], spawn_sites)
                spawn_sites.remove(spawns[ev.defeated_index])

    if len(act_zone) != 0:
        zone_count += 1



    tick += 1
    # print(team)
    # print(score)
    # print(total_ants)
    spawned_this_tick = 0
    while (
        total_ants < stats.general.MAX_ANTS_PER_PLAYER and
        spawned_this_tick < 2 and  # stats.general.MAX_SPAWNS_PER_TICK
        my_energy >= stats.ants.Worker.COST
    ):
        spawned_this_tick += 1
        count += 1
        total_ants += 1

        # Spawn an ant, give it some id, no color, and send it to the closest site.
        # I will pay the base cost for this ant, so cost=None.
        if tick < 100:
            if (my_energy > 160 and total_ants > 70 and my_energy > stats.ants.Fighter.COST) or (spawned_this_tick == 2 and my_energy > 40 and tick > 50):
                if signal:
                    if len(team) == 1:
                        second_goal = int(team[0])
                    elif len(team) == 2:
                        if score[team[0]][1] >= score[team[1]][1]:
                            second_goal = int(team[1])
                    else:  # len(team) == 3
                        if score[team[0]][1] >= score[team[1]][1]:
                            if score[team[1]][1] >= score[team[2]][1]:
                                second_goal = int(team[1])
                        elif score[team[0]][1] >= score[team[2]][1]:
                            second_goal = int(team[0])
                        else:
                            second_goal = int(team[2])
                    requests.append(SpawnRequest(AntTypes.FIGHTER, id=str(count), color=None, goal=spawns[second_goal]))
                    my_energy -= stats.ants.Fighter.COST
                else:
                    temp = int(count % 5)
                    if temp == 1 or temp == 2:  # attack
                        goal = 1
                        temp_l = []
                        for i in team:
                            temp_l.append(spawns[int(i)])
                        for i in spawn_sites:
                            if i in temp_l:
                                site = i
                        requests.append(SpawnRequest(AntTypes.FIGHTER, id=str(count), color=None, goal=site))
                    else:
                        goal = 0
                        requests.append(SpawnRequest(AntTypes.FIGHTER, id=str(count), color=None, goal=spawn_sites[goal]))

                    my_energy -= stats.ants.Fighter.COST

            else:  # len(food_act_dict) == 0
                requests.append(SpawnRequest(AntTypes.WORKER, id=str(count), color=None, goal=closest_site[0]))
                my_energy -= stats.ants.Worker.COST

        else:
            if (my_energy > 160 and total_ants > 70 and my_energy > stats.ants.Fighter.COST) or (spawned_this_tick == 2 and my_energy > 40):
                temp = count % 5
                if temp == 1 or temp == 2:  # attack
                    goal = 1
                    temp_l = []
                    for i in team:
                        temp_l.append(spawns[int(i)])
                    for i in spawn_sites:
                        if i in temp_l:
                            site = i
                            break
                    requests.append(SpawnRequest(AntTypes.FIGHTER, id=str(count), color=None, goal=site))
                else:
                    goal = 0
                    requests.append(SpawnRequest(AntTypes.FIGHTER, id=str(count), color=None, goal=spawn_sites[goal]))
                my_energy -= stats.ants.Fighter.COST
            elif len(act_zone) != 0:
                for e in act_zone:
                    if e in group_list:
                        goal = e
                        break
                if my_energy >= stats.ants.Settler.COST and tick > 900:
                    requests.append(SpawnRequest(AntTypes.SETTLER, id=None, color=None, goal=goal))
                    my_energy -= stats.ants.Settler.COST
                else:
                    requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=closest_site[0]))
                    my_energy -= stats.ants.Worker.COST
            else:
                requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=closest_site[0]))
                my_energy -= stats.ants.Worker.COST

    return requests
