from codequest22.server.ant import AntTypes
from codequest22 import stats
# from codequest22.server.events import DepositEvent, DieEvent, ProductionEvent, SpawnEvent
from codequest22.server.events import *
from codequest22.server.requests import GoalRequest, SpawnRequest
import numpy as np
import json

djikstra_initialised = False
adj = {}
points = []
idx = {}

def get_distances(map_data, startpoint):
	global adj, points, idx, djikstra_initialised, all_distances
	
	if startpoint in all_distances:
		return all_distances[startpoint]
	
	if not djikstra_initialised:
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
	distance = {}
	heapq.heappush(queue, (0, startpoint))
	while queue:
		d, (a, b) = heapq.heappop(queue)
		# print((a,b))
		# print(idx[(a,b)])
		# print(expanded[idx[(a,b)]])
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
	
	all_distances[startpoint] = distance
	djikstra_initialised = True
	return distance

def get_team_name():
	return f"Maxwell Bot"

my_index = None
def read_index(player_index, n_players):
	global my_index
	my_index = player_index

defined_keys = [
	"color",
	"player_index",
	"id",
	"position",
	"hp",
	"cost",
]

energies = {0:stats.general.STARTING_ENERGY, 1:stats.general.STARTING_ENERGY, 2:stats.general.STARTING_ENERGY, 3:stats.general.STARTING_ENERGY}
map_data = {}
energy_info = None
spawns = [None]*4
all_players = [0,1,2,3]
alive_players = all_players.copy()
all_spawn_dists = {}
all_distances = {}
food = []
food_sites = {}
zones = {}
distance = {}
closest_site = None
spawn_dists = None
total_ants = 0
ants = {0:{}, 1:{}, 2:{}, 3:{}}
armies = []
tick = 0
ENERGY_OVERLOAD_MULT = 2
max_workers = 70

wait_for_juggernaut = False

disrupt_proportion = 0.6 # spend 30% of all energy on energy disruption
energy_spent_on_disruption = 0
energy_spent_on_workers = 0
total_energy_spent = 0

energy_spent_on_settlers=0
settler_proportion=0.4

min_efficiency = None
efficiency_threshold = 0.5

# worker_value = None # coded as min_efficiency
fighter_value = None
settler_value = None

spawned_this_tick = 0
requests = []

def profit_per_time(spawn_pos, food_pos, food_val, wait_time=0, dists=None):
	if dists is None:
		global map_data
		dists = get_distances(map_data, spawn_pos)
	dist = dists[food_pos]

	cost = stats.ants.Worker.COST/stats.ants.Worker.TRIPS
	# dist = 23
	encumber_rate = stats.ants.Worker.ENCUMBERED_RATE
	base_speed = stats.ants.Worker.SPEED
	time = dist/base_speed + dist/(base_speed*encumber_rate) + wait_time
	energy_return = food_val
	energy_per_time = energy_return/time
	energy_profit = energy_return - cost
	energy_profit_per_time = energy_profit/time
	# print(energy_profit, energy_per_time, energy_profit_per_time)
	return energy_profit_per_time

def compute_profit_rates(food=None, energy_info=None, wait_times={}, copy=False):
	food_sites = {}
	# print("")
	# global spawn_dists
	
	spawn_dists = get_distances(map_data, spawns[my_index])
	for food_pos in food:
		if not food_pos in food_sites:
			food_sites[food_pos] = {}
		food_sites[food_pos]["dist"] = spawn_dists[food_pos]
		food_sites[food_pos]["queue"] = 0
		if not energy_info is None:
			food_sites[food_pos]["food_val"] = energy_info[food_pos]
		food_val = food_sites[food_pos]["food_val"]
		if food_pos in wait_times:
			wait_time = wait_times[food_pos]
		else:
			wait_time = 0
		food_sites[food_pos]["profit_rate"] = profit_per_time(spawns[my_index], food_pos, food_val, dists=spawn_dists, wait_time=wait_time)
		# print(f"DELAY:{wait_time}")
		# print(food_pos, food_sites[food_pos]["profit_rate"])
	return food_sites

def read_map(md, energy_data):
	global map_data, spawns, food, distance, closest_site, spawn_dists, energy_info, food_sites, my_index
	energy_info = energy_data
	# print(energy_info)
	map_data = md
	for y in range(len(map_data)):
		for x in range(len(map_data[0])):
			if map_data[y][x] == "F":
				food.append((x, y))
			if map_data[y][x] in "RBYG":
				spawns["RBYG".index(map_data[y][x])] = (x, y)
	# Read map is called after read_index
	distance = get_distances(map_data, spawns[my_index])
	# Now I can calculate the closest food site.
	food_sites_list = list(sorted(food, key=lambda prod: distance[prod]))
	closest_site = food_sites_list[0]
	# print(map_data)
	# print("")
	# print(closest_site)
	# print(type(closest_site))
	# raise ValueError()
	
	food_sites = compute_profit_rates(food=food, energy_info=energy_info)
	
	# global all_distances
	# for y in range(len(map_data)):
		# for x in range(len(map_data[0])):
			# if map_data[y][x] != "W":
				# pos = (x,y)
				# all_distances[pos] = get_distances(map_data, pos)
	
	global all_spawn_dists
	for player_index in range(4):
		all_spawn_dists[player_index] = get_distances(map_data, spawns[player_index])
	
	spawn_dists = get_distances(map_data, spawns[my_index])
	# for spawn in alive_players:
		# print(f"dist from my spawn to enemy: {spawn_dists[spawns[spawn]]}")
		

def handle_failed_requests(requests):
	# pass
	for req in requests:
		if req.player_index == my_index:
			print(f"Request {req.__class__.__name__} failed. Reason: {req.reason}.")

def send_worker(pos, spawned_this_tick, requests):
	global energies
	conditions_met = len(ants[my_index]) < stats.general.MAX_ANTS_PER_PLAYER and spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and energies[my_index] >= stats.ants.Worker.COST
	if conditions_met:
		requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=pos))
		energies[my_index] -= stats.ants.Worker.COST
		spawned_this_tick += 1
	return conditions_met, spawned_this_tick

def find_target():
	
	# for k, v in sorted_food_sites.items():
		# print(k, v)
	# sorted_food_sites = dict(sorted(food_sites, key=lambda prod: food_sites[prod]["profit_rate"]))
	wait_times = {}
	for site_pos, data in food_sites.items():
		arrival_tick = tick+data["dist"]+1 # 1 for spawn delay
		if data["queue"] > 0: # if the spot is taken
			wait_times[site_pos] = data["queue"]
		else:
			wait_times[site_pos] = 0
	rates = compute_profit_rates(food=food, energy_info=energy_info, wait_times=wait_times, copy=True)
	
	sorted_rates = dict(sorted(rates.items(), key=lambda item: item[1]["profit_rate"], reverse=True))
	
	global min_efficiency
	if min_efficiency is None:
		min_efficiency = sorted_rates[list(sorted_rates.keys())[0]]["profit_rate"]
		# print(f"max_efficiency: {min_efficiency}")
	else:
		min_efficiency = min(sorted_rates[list(sorted_rates.keys())[0]]["profit_rate"], min_efficiency)
	
	optimal_target = list(sorted_rates.keys())[0]
	# if optimal_target == (5,1): print(wait_times[(5,1)])
	return optimal_target

def book_target(pos):
	# for t in range(arrival_tick, arrival_tick+stats.energy.DELAY + np.random.randint(1)):
	food_sites[pos]["queue"] += stats.energy.DELAY
	# print(f"{pos} booked for tick {t}")

def send_optimal_worker():
	global spawned_this_tick, requests, max_workers
	if len([1 for k, v in ants[my_index].items() if v["classname"]=="WorkerAnt"]) < max_workers:
		optimal_target = find_target()
		if not optimal_target is None:
			success, spawned_this_tick = send_worker(optimal_target, spawned_this_tick, requests)
			# print(f"sent worker to {optimal_target}")
			if success: book_target(optimal_target)

class army:
	def __init__(self):
		leader = None
		self.fighters = []
		self.workers = []
		self.settlers = []
		self.units = {}
	
	def add_unit(self, ant_obj):
		if self.leader is None:
			self.leader = ant_obj
		if ant_obj["classname"] == "WorkerAnt":
			self.workers.append(ant_obj)
		elif ant_obj["classname"] == "FighterAnt":
			self.fighters.append(ant_obj)
			if self.leader["classname"] == "WorkerAnt" or self.leader["classname"] == "SettlerAnt":
				self.leader = ant_obj
		elif ant_obj["classname"] == "SettlerAnt":
			self.settlers.append(ant_obj)
			if self.leader["classname"] == "WorkerAnt":
				self.leader = ant_obj
		else:
			print("unknown ant class " + ant_obj["classname"])
			
	def move(self, pos):
		global requests
		requests.append(GoalRequest(self.leader["info"]["id"], pos))
		for ant_obj in self.fighters:
			requests.append(GoalRequest(ant_obj["info"]["id"], pos))
		for ant_obj in self.settlers:
			requests.append(GoalRequest(ant_obj["info"]["id"], pos))
		for ant_obj in self.workers: # workers follow the leader cos they'd be faster otherwise, slower is better
			requests.append(GoalRequest(ant_obj["info"]["id"], self.leader["info"]["position"]))
			
def handle_events(events):
	global tick, energies, spawned_this_tick, requests, efficiency_threshold, energy_spent_on_workers, energy_spent_on_disruption, disrupt_proportion, total_energy_spent, energy_spent_on_settlers, settler_proportion, zones
	# print("handling events")
	# print(f"{tick}: {energies[my_index]} at start of turn")
	
	# 1. Deal with incoming player requests (and reject any bad requests)
	# 2. Move all ants, with goals not equal to their current position
	# 3. Handle all fighter ant attacks
	# 4. Handle all ant deaths
	# 5. For any remaining ants, calculate:
		# i. Queen Depositing
		# ii. Food Tile Production
		# iii. Settler Scoring
	# 6. Zone / Food - Activation / Deactivation
	
	requests = []
	
	spawned_this_tick = 0
	
	for e in events:
		if isinstance(e, SpawnEvent):
			ants[e.player_index][e.ant_id] = e.ant_str
			
			ants[e.player_index][e.ant_id]["mission"] = ""
			if e.player_index == my_index:
				total_energy_spent += e.cost
				if e.ant_str["info"]["color"] == (1,0,1,0):
					ants[e.player_index][e.ant_id]["mission"] = "offensive_supply_chain_raid"
					energy_spent_on_disruption += e.cost
				elif e.ant_str["info"]["color"] == (1,1,1,0):
					ants[e.player_index][e.ant_id]["mission"] = "juggernaut"
				elif e.ant_str["classname"] == "WorkerAnt":
					energy_spent_on_workers += e.cost
				elif e.ant_str["classname"] == "SettlerAnt":
					energy_spent_on_settlers += e.cost
			
			if e.ant_str["classname"] == "WorkerAnt":
				ants[e.player_index][e.ant_id]["ticks_remaining"] = 1200
			elif e.ant_str["classname"] == "FighterAnt":
				ants[e.player_index][e.ant_id]["ticks_remaining"] = stats.ants.Fighter.LIFESPAN
			elif e.ant_str["classname"] == "SettlerAnt":
				ants[e.player_index][e.ant_id]["ticks_remaining"] = stats.ants.Settler.LIFESPAN
			
			if e.ant_str["classname"] == "WorkerAnt":
				ants[e.player_index][e.ant_id]["info"]["deposits_remaining"] = stats.ants.Worker.TRIPS
				ants[e.player_index][e.ant_id]["info"]["energy"] = 0
			# print(ants[e.player_index][e.ant_id])
			
			# if e.player_index == my_index:
				# print(f"ant {e.ant_id} of player {e.player_index} was spawned")
			
			# print(e.ant_type)
			if e.player_index != my_index:
				if e.ant_type == AntTypes.WORKER:
					energies[e.player_index] -= stats.ants.Worker.COST
				elif e.ant_type == AntTypes.SETTLER:
					energies[e.player_index] -= stats.ants.Settler.COST
				elif e.ant_type == AntTypes.FIGHTER:
					energies[e.player_index] -= stats.ants.Fighter.COST
		
		# 2. Move all ants, with goals not equal to their current position
		elif isinstance(e, MoveEvent):
			# print(e)
			# if e.ant_str["classname"] == "WorkerAnt":
				# deposits_remaining = ants[e.player_index][e.ant_id]["info"]["deposits_remaining"]
			if e.ant_id in ants[e.player_index]:
				for k in defined_keys:
					ants[e.player_index][e.ant_id]["info"][k] = e.ant_str["info"][k]
			else:
				ants[e.player_index][e.ant_id] = e.ant_str # somehow slipped through
				# ants[e.player_index][e.ant_id] = e.ant_str
				# ants[e.player_index][e.ant_id]["info"]["deposits_remaining"] = deposits_remaining
			# else:
				# ants[e.player_index][e.ant_id] = e.ant_str
			# ants[e.player_index][e.ant_id] = e.ant_str
		# 3. Handle all fighter ant attacks
		# 3.5 Handle all queen deaths
		elif isinstance(e, TeamDefeatedEvent):
			alive_players.remove(e.defeated_index)
		# 4. Handle all ant deaths
		elif isinstance(e, DieEvent):
			ants[e.player_index].pop(e.ant_id)
			# print(f"ant {e.ant_id} of player {e.player_index} died")
			
			# if e.player_index == my_index and e.ant_str["classname"] == "WorkerAnt":
				# print(e.ant_id, "died")
				# send_optimal_worker()
					# print(f"purchased worker: now {energies[my_index]}")
		# 5. For any remaining ants, calculate:
		# i. Queen Depositing
		# ii. Food Tile Production
		# iii. Settler Scoring
		# 6. Zone / Food - Activation / Deactivation
		elif isinstance(e, ZoneActiveEvent):
			zones[e.zone_index] =  {}
			zones[e.zone_index]["active"], zones[e.zone_index]["points"], zones[e.zone_index]["num_ticks"], zones[e.zone_index]["end_tick"] = True, e.points, e.num_ticks, tick+e.num_ticks
		elif isinstance(e, ZoneDeactivateEvent):
			zones[e.zone_index]["active"] = False
		elif isinstance(e, FoodTileActiveEvent):
			compute_profit_rates([e.pos], {e.pos:food_sites[e.pos]["food_val"]*ENERGY_OVERLOAD_MULT})
			# for k, v in food_sites.items():
				# print(k, v)
		elif isinstance(e, FoodTileDeactivateEvent):
			compute_profit_rates([e.pos], {e.pos:food_sites[e.pos]["food_val"]/ENERGY_OVERLOAD_MULT})
			# for k, v in food_sites.items():
				# print(k, v)
		elif isinstance(e, ProductionEvent):
			pos = (int(round(e.ant_str["info"]["position"][1])), int(round(e.ant_str["info"]["position"][0])))
			food_sites[pos]["queue"] -= stats.energy.DELAY
			ants[e.player_index][e.ant_id]["info"]["energy"] = e.energy_amount
			if e.player_index == my_index:
				requests.append(GoalRequest(e.ant_id, spawns[my_index]))
				# print(e.ant_id, "harvested")
		elif isinstance(e, DepositEvent):
			# energies[e.player_index] += e.energy_amount
			energies[e.player_index] = e.total_energy
			# print(ants[e.player_index][e.ant_id])
			ants[e.player_index][e.ant_id]["info"]["deposits_remaining"] -= 1
			ants[e.player_index][e.ant_id]["info"]["energy"] = 0
			if e.player_index == my_index:
				# print(f"{e.ant_id} deposited {e.energy_amount}: now {e.total_energy}")
				# print(f"my_energy now {energies[my_index]}")
				
				# if e.ant_id in ants[e.player_index]:
				if ants[e.player_index][e.ant_id]["info"]["deposits_remaining"] > 0:
					target = find_target()
					# print(f"{e.ant_id} booking {target} on return trip")
					book_target(target)
					
					requests.append(GoalRequest(e.ant_id, target))
					# requests.append(GoalRequest(e.ant_id, (5,1)))
		
	# if len(ants) != 0:
		# print(ants[list(ants.keys())[0]])
		# if isinstance(e, DepositEvent):
			# if e.total_energy == stats.general.MAX_ENERGY_STORED:
				# requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=(5,5)))
			# print(e.total_energy, stats.general.MAX_ENERGY_STORED, e.total_energy==stats.general.MAX_ENERGY_STORED)
	# print()
	# print(ants)
	
	# if tick == 0:
		# if len(ants[my_index]) < stats.general.MAX_ANTS_PER_PLAYER and spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and energies[my_index] >= stats.ants.Worker.COST:
			# requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=closest_site))
			# energies[my_index] -= stats.ants.Worker.COST
			# spawned_this_tick += 1
			# print(f"purchased worker: now {energies[my_index]}")
	
	# if len(ants[my_index]) < 30 and len(ants[my_index]) < stats.general.MAX_ANTS_PER_PLAYER and spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and energies[my_index] >= stats.ants.Worker.COST:
		# requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=food[np.random.choice(range(len(food)))]))
		# energies[my_index] -= stats.ants.Worker.COST
		# spawned_this_tick += 1
		# print(f"purchased worker: now {energies[my_index]}")
		
	# elif len(ants[my_index]) < stats.general.MAX_ANTS_PER_PLAYER and spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and energies[my_index] >= stats.ants.Fighter.COST:
		# requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=spawns[np.random.choice([0,1,2,3])]))
		# energies[my_index] -= stats.ants.Fighter.COST
		# spawned_this_tick += 1
		# print(f"purchased fighter: now {energies[my_index]}")
	
	# print(f"{tick}: {energies[my_index]} at end of turn")
	global all_distances
	
	if energies[my_index] > 100:
		juggernaut_radius = 15
		juggernaut_threshold = 1
		fighters_within_radius = 0
		for player_index in alive_players:
			if player_index != my_index:
				for enemy_ant_id, enemy_ant in ants[player_index].items():
					if enemy_ant["classname"] == "FighterAnt":
						enemy_pos = (int(round(enemy_ant["info"]["position"][1])), int(round(enemy_ant["info"]["position"][0])))
						distance_from_spawn = get_distances(map_data, spawns[my_index])[enemy_pos]
						if distance_from_spawn < juggernaut_radius:
							fighters_within_radius += 1
		if fighters_within_radius >= juggernaut_threshold:
			requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=(1,1,1,0), goal=spawns[my_index]))
	
	rates = {}
	ant_dists = {}
	for my_ant_id, my_ant in ants[my_index].items():
		# print("is_fighter", my_ant["classname"] == "FighterAnt", "mission", my_ant["mission"])
		if my_ant["classname"] == "FighterAnt" and my_ant["mission"] == "offensive_supply_chain_raid":
			# print("finding raid target")
			rates[my_ant_id] = {}
			rates[my_ant_id]["best_value"] = 0
			for player_index in alive_players:
			# print(my_ant)
			# ant_ratings = {}
				if player_index != my_index:
					for ant_id, ant in ants[player_index].items():
						if ant["classname"] == "WorkerAnt":
							if ant["info"]["energy"] > 0:
								# assuming encumbered
								pos = (int(round(ant["info"]["position"][1])), int(round(ant["info"]["position"][0])))
								ant_value = stats.ants.Worker.COST * ant["info"]["deposits_remaining"]/stats.ants.Worker.TRIPS + ant["info"]["energy"]
								distance_from_spawn = all_spawn_dists[player_index][pos]
								encumbered_worker_speed = stats.ants.Worker.SPEED*stats.ants.Worker.ENCUMBERED_RATE
								time_to_spawn = distance_from_spawn*encumbered_worker_speed
								my_pos = (int(round(my_ant["info"]["position"][1])), int(round(my_ant["info"]["position"][0])))
								# dist_to_enemy = all_distances[my_pos][pos]
								dist_to_enemy = get_distances(map_data, my_pos)[pos]
								if dist_to_enemy == 0:
									dist_to_enemy = 1
								warrior_speed = stats.ants.Fighter.SPEED
								time_to_enemy = dist_to_enemy/(warrior_speed-encumbered_worker_speed)
								# rate = ant_value/time_to_enemy
								rate = ant_value/dist_to_enemy
								# print(f"time_to_spawn:{time_to_spawn}; time_to_enemy:{time_to_enemy}")
								# print(f"ant {my_ant_id}: {ant_id} of player {player_index} returns {rate}", rates[my_ant_id]["best_value"])
								if time_to_spawn > time_to_enemy or True:
									if rate > rates[my_ant_id]["best_value"]:
										rates[my_ant_id]["best_value"] = rate
										rates[my_ant_id]["best_value_ant_id"] = ant_id
										rates[my_ant_id]["best_value_player_index"] = player_index
										# print(f"found new best value for ant {my_ant_id}: {ant_id} of player {player_index} returns {rate}")
									# ant_ratings[ant["info"]["id"]] = rate
									# print("item added to ant_ratings")
								# else:
		elif my_ant["mission"] == "juggernaut":
			for player_index in alive_players:
				ant_dists[my_ant_id] = {}
				if player_index != my_index:
					for ant_id, ant in ants[player_index].items():
						if ant["classname"] == "FighterAnt":
							pos = (int(round(ant["info"]["position"][1])), int(round(ant["info"]["position"][0])))
							my_pos = (int(round(my_ant["info"]["position"][1])), int(round(my_ant["info"]["position"][0])))
							dist_to_enemy = get_distances(map_data, my_pos)[pos]
							if dist_to_enemy == 0:
								dist_to_enemy = 1	
							if not (my_ant_id in ant_dists and "dist" in ant_dists[my_ant_id] and "target_id" in ant_dists[my_ant_id] and "target_player_id" in ant_dists[my_ant_id]) or dist_to_enemy < ant_dists[my_ant_id]["dist"]:
								ant_dists[my_ant_id] = {}
								ant_dists[my_ant_id]["dist"] = dist_to_enemy
								ant_dists[my_ant_id]["target_id"] = ant_id
								ant_dists[my_ant_id]["target_player_id"] = player_index
	# for ant_id, ant in ant_dists.items():
		# enemies = alive_players.copy()
		# enemies.remove(my_index)
		# target_pos = spawns[np.random.choice(enemies)]
		# target_ant = ant
		# if "target_player_id" in ant:
			# target_player_id = ant["target_player_id"]
			# target_pos = ants[target_player_id][ant["target_id"]]["info".pos]
		# requests.append(GoalRequest(ant_id, target_pos))
	for ant_id in rates.keys():
		if "best_value_ant_id" in rates[ant_id]:
			rates_obj = rates[ant_id]
			target_ant_id = rates_obj["best_value_ant_id"]
			target_player_index = rates_obj["best_value_player_index"]
			target_pos = (int(round(ants[target_player_index][target_ant_id]["info"]["position"][1])), int(round(ants[target_player_index][target_ant_id]["info"]["position"][0])))
			requests.append(GoalRequest(ant_id, target_pos))
		
	global min_efficiency, wait_for_juggernaut
	find_target()
	for i in range(3):
		# if energies[my_index] < 200:
		if energies[my_index] < 100:
			send_optimal_worker()
		elif energy_spent_on_disruption < total_energy_spent * disrupt_proportion or energies[my_index] > stats.general.MAX_ENERGY_STORED - 100:
			# enemy_spawns = [0,1,2,3]
			enemy_spawns = alive_players.copy()
			enemy_spawns.remove(my_index)
			chosen_loc = spawns[np.random.choice(enemy_spawns)]
			requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=(1,0,1,0), goal=chosen_loc))
			# if min_efficiency > efficiency_threshold:
		elif energy_spent_on_settlers < total_energy_spent * settler_proportion and sum([zone["active"] for zone_index, zone in zones.items()])>0:
			active_zone = 0
			for zone_index, zone in zones.items():
				if zone["active"]:
					active_zone = zone_index
					break
			zone_point = zones[active_zone]["points"][0] # an arbitrary point in the zone
			requests.append(SpawnRequest(AntTypes.SETTLER, id=None, color=None, goal=zone_point))
			# send settler if worth it
		else:
			send_optimal_worker()
		
		# juggernaut_created = True
			
	# print(food_sites[(5,1)]["schedule"])
	
	# print(f"min_efficiency: {min_efficiency}")
	min_efficiency = None
	
	# print(food_sites[(5,1)]["schedule"])
	
	tick += 1
	for player in all_players:
		for ant_id, ant in ants[player].items():
			ant["ticks_remaining"] -= 1
	# if tick % 10 == 0: print(f"{len(ants[my_index])} ants")
	return requests