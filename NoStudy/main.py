from codequest22.server.ant import AntTypes
import codequest22.stats as stats

from codequest22.server.requests import GoalRequest, SpawnRequest
from Variables import vars
import modes

def get_team_name():
    return f"own_bot"

def read_index(player_index, n_players):
    vars.my_index = player_index
    vars.n_players = n_players
    vars.pre_set()
    
def read_map(md, energy_info):
    vars.energy_info=energy_info
    vars.map_data = md
    for y in range(len(vars.map_data)):
        for x in range(len(vars.map_data[0])):
            if vars.map_data[y][x] == "F":
                vars.food.append((x, y))
            if vars.map_data[y][x] in "RBYG":
                vars.spawns["RBYG".index(vars.map_data[y][x])] = (x, y)
            if vars.map_data[y][x] =="Z":
                vars.hills.append((x,y))
    # Read map is called after read_index
    
    startpoint = vars.spawns[vars.my_index]
    adj = {}
    h, w = len(vars.map_data), len(vars.map_data[0])
    points = []
    idx = {}
    counter = 0
    for y in range(h):
        for x in range(w):
            adj[(x, y)] = []
            if vars.map_data[y][x] == "W": continue
            points.append((x, y))
            idx[(x, y)] = counter
            counter += 1
    for x, y in points:
        for a, b in [(y+1, x), (y-1, x), (y, x+1), (y, x-1)]:
            if 0 <= a < h and 0 <= b < w and vars.map_data[a][b] != "W":
                adj[(x, y)].append((b, a, 1))
    import heapq
    for i in range(vars.n_players):
        expanded = [False] * len(points)
        queue = []
        heapq.heappush(queue, (0, startpoint))
        while queue:
            d, (a, b) = heapq.heappop(queue)
            if expanded[idx[(a, b)]]: continue
            expanded[idx[(a, b)]] = True
            vars.distance[i][(a, b)] = d
            for j, k, d2 in adj[(a, b)]:
                if not expanded[idx[(j, k)]]:
                    heapq.heappush(queue, (d + d2,(j, k) ) )
    # Now I can calculate the closest food site.
    vars.food = list(sorted(vars.food, key=lambda prod: vars.distance[vars.my_index][prod]))
    if len(vars.food) > 5:
        vars.food = vars.food[:5]

    #print([(i,vars.distance[vars.my_index][i]) for i in vars.food])
    # vars.closest_site = vars.food[0]
    # vars.calc_info()

    #print("food_sites: ", vars.food)
    #print("vars.food: ", vars.food)
    #print(vars.distance[vars.my_index][vars.food[0]])
    #print("vars.n_players: ", vars.n_players)

    # record food_site_infos and sort
    vars.food_site_infos_dic = {}
    for food_pos in vars.food:
        vars.food_site_infos_dic[food_pos] = {}
        vars.food_site_infos_dic[food_pos]["base_energy"] = vars.energy_info[food_pos]
        vars.food_site_infos_dic[food_pos]["distance"] = vars.distance[vars.my_index][food_pos]
        vars.food_site_infos_dic[food_pos]["energy"] = vars.energy_info[food_pos]
        vars.food_site_infos_dic[food_pos]["shared_energy"] = vars.energy_info[food_pos]
        vars.food_site_infos_dic[food_pos]["num_ticks"] = 9999
        vars.food_site_infos_dic[food_pos]["multiplier"] = 1
        vars.food_site_infos_dic[food_pos]["rate"] = vars.energy_info[food_pos] / vars.distance[0][food_pos]
    '''
    energy_distance_rate_dic = {}
    for key, value in vars.food_site_infos_dic.items():
        energy_distance_rate_dic[key] = value["rate"]

    energy_distance_rate_dic = list(sorted(energy_distance_rate_dic.items(), key=lambda item: item[1], reverse=True))

    vars.food = []
    for item in energy_distance_rate_dic:
        vars.food.append(item[0])

    vars.closest_site = vars.food[0]
    vars.calc_info()
    '''
    energy_distance_rate_dic = {}
    for key, value in vars.food_site_infos_dic.items():
        energy_distance_rate_dic[key] = value["distance"]

    energy_distance_rate_dic = list(sorted(energy_distance_rate_dic.items(), key=lambda item: item[1]))

    vars.food = []
    for item in energy_distance_rate_dic:
        vars.food.append(item[0])
    
    #vars.food=vars.food[0:min(5,len(vars.food)-1)]
    vars.calc_info()
    #print("vars.food_site_infos_dic: ", vars.food_site_infos_dic)
    #print("energy_distance_rate_dic: ", energy_distance_rate_dic)
    #print("vars.food: ", vars.food)






def handle_failed_requests(requests):
    for req in requests:
        #if req.player_index == vars.my_index:
        print(f"Request {req.__class__.__name__} failed. Reason: {req.reason}.")
        #raise ValueError()

def handle_events(events):
    requests = []
    vars.game_tick()
    
    #set thresold for passive mode
    if vars.ticks==vars.prepare:
        vars.pass_threshold=vars.energys[vars.my_index]
    
    requests+=modes.response(events)
    temp=modes.defence()
    #print(temp)
    requests+=temp
    #print(vars.ants[vars.my_index])
    if vars.check_ending():
        requests+=modes.ending()
    else:
        if vars.energys[vars.my_index]<0.9*stats.general.MAX_ENERGY_STORED:
            requests+=modes.get_workers()
        #print(vars.my_index,"-->",vars.workers,"-->",vars.worker_distribution,"t{},s{},l{}".format(vars.total_ants,vars.spawn_this_tick,len(vars.ants[vars.my_index]))," E:",vars.energys[vars.my_index])
        requests+=modes.aggrassive()
    
    #[print(i) for i in requests]
    #print("*"*10)
    return requests
    ''' 
    #find mode
    if vars.check_pass():
        requests+=modes.passive()
        
    #elif vars.check_agg():
        #requests+=modes.aggrassive()
    #    requests+=modes.mid()
    #    if vars.attacked_by > 0 :
    #        requests+=modes.defence()
    elif vars.check_ending():
        requests+=modes.ending()
    else:
        requests+=modes.aggrassive()
        if vars.attacked_by > 0 :
            requests+=modes.defence()
    # [print(r) for r in requests]
    '''

