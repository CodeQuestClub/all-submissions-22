from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import DepositEvent, DieEvent, ProductionEvent, MoveEvent, SpawnEvent, ZoneActiveEvent
from codequest22.server.requests import GoalRequest, SpawnRequest


def get_team_name():
    return f"Lindsay and associates"

my_index = None
def read_index(player_index, n_players):
    global my_index
    my_index = player_index

my_energy = stats.general.STARTING_ENERGY
map_data = {}
spawns = [None]*4
food = []
hills = []
distance = {}
closest_site = None
my_total_ants = 0

def read_map(md, energy_info):
    global map_data, spawns, food, distance, closest_site
    map_data = md
    for y in range(len(map_data)):
        for x in range(len(map_data[0])):
            if map_data[y][x] == "F":
                food.append((x, y))
            if map_data[y][x] in "RBYG":
                spawns["RBYG".index(map_data[y][x])] = (x, y)
            if map_data[y][x] in "Z":
                hills.append((x, y))
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


def handle_failed_requests(requests):
    # global my_energy
    # for req in requests:
    #     if req.player_index == my_index:
    #         print(f"Request {req.__class__.__name__} failed. Reason: {req.reason}.")
    #         raise ValueError()

    pass









def handle_events(events):
    global my_energy, my_total_ants
    """
    @NOTE The program runs at about 10 tps.
    @NOTE if you get an error like `local variable 'total_ants' referenced before assignment`, read this: https://www.programiz.com/python-programming/global-keyword
    @NOTE im pretty sure everything has to be done in response to an event. Its incredibly hard to move individual ants just because how tf do you even code that.
    @NOTE anything in codequest22.server.events HAS to be run under the `for ev in events` loop
    """
    def try_spawn_ants(request: dict):
        global my_total_ants, my_energy
        """
        @NOTE we reach max ants in around 150 ticks. 
        @NOTE request schema: {'worker': 0, 'fighter': 0, 'settler': 0}
        """
        
        spawn_workers,spawn_fighters,spawn_settlers = None,None,None

        try:
            spawn_workers = request['worker']
        except Exception as e:
            spawn_workers = 0
        try:
            spawn_fighters = request['fighter']
        except Exception as e:
            spawn_fighters = 0
        try:
            spawn_settlers = request['settler']
        except Exception as e:
            spawn_settlers = 0

        #@DEV This try and except is set up so we can request say only workers: e.g {'worker': 3}, and not have to write out the rest of the request.



        # Can I spawn ants?
        spawned_this_tick = 0
        while (
            my_total_ants < stats.general.MAX_ANTS_PER_PLAYER - 6 and # minus 6 here so we dont encounter any overflow issues. why 6? 5 is how many we can spawn, so 5 + 1 gives us safety. 
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Worker.COST
        ):
            
            if spawn_workers != 0:
                requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=closest_site))
                
                my_energy -= stats.ants.Worker.COST
                spawned_this_tick += 1
                my_total_ants += 1

                spawn_workers -= 1

            if spawn_fighters != 0:
                requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=closest_site))
                
                my_energy -= stats.ants.Fighter.COST
                spawned_this_tick += 1
                my_total_ants += 1

                spawn_fighters -= 1
            
            if spawn_settlers != 0:
                requests.append(SpawnRequest(AntTypes.SETTLER, id=None, color=None, goal=closest_site))
                
                my_energy -= stats.ants.Settler.COST
                spawned_this_tick += 1
                my_total_ants += 1

                spawn_settlers -= 1

            print(f"Total ants: {my_total_ants}") # @DEBUG



    # ============= HANDLE EVENTS =============
    requests = []
    for ev in events:
        # @DEV HELP? WTF WHY DOES `ev` look like this?? 
        # {"DieEvent": [{'classname': 'WorkerAnt', 'info': {'color': (0, 0, 0, 0), 'player_index': 0, 'id': 'ant-2',
        #  'position': (3.997260559313607, 2.0017029646892777), 'hp': 10, 'cost': 20, 'encumbered_energy': 0}}]
        # }
        # yet I can still access player_index like ev.player_index and also, why tf can I access ev.ant_id when that literally doesnt even exist.??
        # I raised the issue on discord. Read the comments there for clarification.



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
                print(f"One of my workers just died {ev.ant_id},{ev.old_age}")
                # print(ev)
                my_total_ants -= 1
        elif isinstance(ev, SpawnEvent):
            if ev.player_index == my_index:
                if ev.ant_type == AntTypes.WORKER:
                    # One of my workers just spawned!
                    # Lets make them go to the food site.
                    requests.append(GoalRequest(ev.ant_id, closest_site))
                    my_total_ants += 1

                if ev.ant_type == AntTypes.FIGHTER:
                    # One of my fighters just spawned!
                    
                    # # Lets make them go to the food site to protect the ants
                    # requests.append(GoalRequest(ev.ant_id, closest_site))
                    
                    # Lets make them go to the enemies' site to attack
                    print("myindex:", my_index)
                    try:
                        requests.append(GoalRequest(ev.ant_id, spawns[my_index + 1])) #@DEV spawns[my_index + 1] is temporary. need to do it properly.
                    except Exception as e:
                        requests.append(GoalRequest(ev.ant_id, spawns[0]))
                        # my_index = [0,1,2,3]
                    
                    my_total_ants += 1
                
                if ev.ant_type == AntTypes.SETTLER:
                    # One of my settlers just spawned!
                    requests.append(GoalRequest(ev.ant_id, hills[0])) #@DEV spawns[my_index + 1] is temporary. need to do it properly.
                    # Lets make them go to the hill  #ZoneActiveEvent
                    my_total_ants += 1
            elif isinstance(ev, ZoneActiveEvent):
                if ev.player_index == my_index:
                    pass
                    # One of my workers just spawned!
                    # Lets make them go to the food site.
                    # requests.append(GoalRequest(ev, closest_site))
                    
# [.,.,.,.,.,H,H,H,.,.,.,.,.,]
# [.,.,.,.,.,H,H,H,.,.,.,.,.,]
# [.,.,.,.,.,.,.,.,.,.,.,W,.,]
# [.,.,.,.,.,.,.,.,.,F,.,.,.,]
# [.,.,.,.,.,.,.,.,.,.,.,.,.,]

    # ============= HANDLE EVENTS END =============
    
    # ============= HANDLE NON EVENTS =============


    ### @DEV i don't know if this is a crap way to manage ant behaviour. lmk if you have a better idea.
    if my_total_ants > 80:
        # If we are almost maxed out on ants, we should do one of the following: [expand, attack, settle]
        print(f"We are almost maxed out on ants! We have {my_total_ants} ants.")
        try_spawn_ants({'worker': 3, 'fighter': 1, 'settler': 1})
        
        pass

    if my_total_ants < 80:
        # If we do not have ants for whatever reason, we need to act differently: [defend, spawn-ants] 
        print(f"We are not maxed out on ants! {my_total_ants}")
        if True:
            try_spawn_ants({'worker': 5})


    
    # ============= HANDLE NON EVENTS END =============
    
    return requests







# LOGIC PLANNING
# GAME BEGINNING - max out workers to max out ants.
# It is paramount that we are one of the last ant colonies to attack.
# I spent a good while working this out. I can explain in a vc if you want.
# I could be wrong though so lmk if you think I'm wrong.

# While we are increasing our ant colony size, we may be attacked. If we are attacked, 
# we will need to defend ourselves by spawning fighter ants.


# EARLY GAME
# After this we can do one of the following:
# 1. siege an enemy ant colony
# 2. capture a hill
# 3. protect ourself from enemy invasions

# ffs this is a feels like a mess of logic.
