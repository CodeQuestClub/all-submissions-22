import random

from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import *
from codequest22.server.requests import GoalRequest, SpawnRequest


# flags to indicate our bot's status
under_attack = False
stalled = False

MAX_WORKERS = 70
MAX_FIGHTERS = 30
MAX_SETTLERS = 0
# energy thresholds for updating ant type count
MIN_THRESHOLD = 250
MAX_THRESHOLD = 750

def get_team_name():
	return f"Crombopulos"


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
# list of positions for the entryway to each spawn
corridors = []
total_ants = 0
worker = []
fighter = []
settler = []
hill = []
wall = []
zone = None

spawn_dict = {}
food_tile = []

closest_food_sites = []

# flags
zone_active = False
defend = False
siege = False
siege_position = None


def read_map(md, energy_info):
	global map_data, spawns, food, distance, closest_site, hill, wall, closest_food_sites
	map_data = md
	for y in range(len(map_data)):
		for x in range(len(map_data[0])):
			if map_data[y][x] == "F":
				food.append((x, y))
			if map_data[y][x] == "Z":
				hill.append((x, y))
			if map_data[y][x] == "W":
				wall.append((x, y))
			if map_data[y][x] in "RBYG":
				spawns["RBYG".index(map_data[y][x])] = (x, y)
	# Read map is called after read_index
	for spawn in spawns:
		startpoint = spawn
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
		# e_food_tile.append(food_sites[0])
		if spawn == spawns[my_index]:
			print(spawn)
			closest_site = food_sites[0]
			closest_food_sites = food_sites[:3]
			# e_food_tile[my_index] = None


def handle_failed_requests(requests):
	global my_energy
	for req in requests:
		if req.player_index == my_index:
			print(f"Request {req.__class__.__name__} failed. Reason: {req.reason}.")
			raise ValueError()


def handle_events(events):
	global my_energy, total_ants, worker, fighter, settler, zone, \
		MAX_FIGHTERS, MAX_SETTLERS, MAX_WORKERS, \
		MIN_THRESHOLD, MAX_THRESHOLD, zone_active, defend, siege, siege_position
	requests = []
	for ev in events:
		if isinstance(ev, SpawnEvent):
			if ev.player_index == my_index:
				if ev.ant_type == AntTypes.WORKER:
					worker.append(ev.ant_id)
				if ev.ant_type == AntTypes.FIGHTER:
					fighter.append(ev.ant_id)
				if ev.ant_type == AntTypes.SETTLER:
					settler.append(ev.ant_id)
		if isinstance(ev, ZoneActiveEvent):
			zone_active = True
			zone = ev.points
			if defend:
				if my_energy < 150:
					MAX_SETTLERS = 50
					MAX_FIGHTERS = 20
					MAX_WORKERS = 30
				else:
					MAX_WORKERS = 10
					MAX_FIGHTERS = 20
					MAX_SETTLERS = 70
			else:
				if my_energy < 150:
					MAX_WORKERS = 40
					MAX_FIGHTERS = 10
					MAX_SETTLERS = 50
				else:
					MAX_WORKERS = 10
					MAX_FIGHTERS = 5
					MAX_SETTLERS = 85
		elif isinstance(ev, ZoneDeactivateEvent):
			zone = None
			zone_active = False
			MAX_SETTLERS = 0
			if defend:
				if my_energy < 150:
					MAX_WORKERS = 60
					MAX_FIGHTERS = 40
				else:
					MAX_WORKERS = 40
					MAX_FIGHTERS = 60
			else:
				if my_energy < 150:
					MAX_WORKERS = 80
					MAX_FIGHTERS = 20
				else:
					MAX_WORKERS = 65
					MAX_FIGHTERS = 35
		# if isinstance(ev, MoveEvent):
		# 	pass
		if isinstance(ev, DepositEvent):
			if ev.player_index == my_index:
				if bool(random.getrandbits(1)):
					requests.append(GoalRequest(ev.ant_id, closest_site))
				else:
					requests.append(GoalRequest(ev.ant_id, random.choice(closest_food_sites)))
					my_energy = ev.cur_energy
		elif isinstance(ev, ProductionEvent):
			if ev.player_index == my_index:
				requests.append(GoalRequest(ev.ant_id, spawns[my_index]))
		if isinstance(ev, DieEvent):
			if ev.player_index == my_index:
				total_ants -= 1
				if ev.ant_id in worker:
					worker.remove(ev.ant_id)
				if ev.ant_id in fighter:
					fighter.remove(ev.ant_id)
				if ev.ant_id in settler:
					settler.remove(ev.ant_id)
		if isinstance(ev, FoodTileActiveEvent):
			if ev.pos in closest_food_sites:
				food_tile.append(ev.pos)
		elif isinstance(ev, FoodTileDeactivateEvent):
			if ev.pos in closest_food_sites:
				food_tile.remove(ev.pos)
		if isinstance(ev, QueenAttackEvent):
			if ev.queen_player_index == my_index:
				defend = True
			else:
				siege_position = ev.queen_player_index

	# Can I spawn ants?
	spawned_this_tick = 0
	while (
			total_ants < stats.general.MAX_ANTS_PER_PLAYER and
			spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
			my_energy >= stats.ants.Worker.COST
	):
		spawned_this_tick += 1
		total_ants += 1
		enemies = [x for x in spawns if x != spawns[my_index]]
		# if zone_active:
		# 	if my_energy > 100:
		# 		if len(settler) < MAX_SETTLERS:
		# 			requests.append(spawnAnt(AntTypes.SETTLER, random.choice(zone)))
		# 			my_energy -= stats.ants.Settler.COST
		# 		else:
		# 			requests.append(spawnAnt(AntTypes.FIGHTER, getCenterPoint(zone)))
		# 			my_energy -= stats.ants.Fighter.COST
		# 	else:
		# 		requests.append(spawnAnt(AntTypes.WORKER, closest_site))
		# 		my_energy -= stats.ants.Worker.COST
		# elif len(worker) < MAX_WORKERS:
		# 	if food_tile:
		# 		if random.randint(0, 2) == 1:
		# 			requests.append(spawnAnt(AntTypes.WORKER, random.choice(food_tile)))
		# 			my_energy -= stats.ants.Worker.COST
		# 		else:
		# 			requests.append(spawnAnt(AntTypes.WORKER, closest_site))
		# 			my_energy -= stats.ants.Worker.COST
		# 	else:
		# 		requests.append(spawnAnt(AntTypes.WORKER, closest_site))
		# 		my_energy -= stats.ants.Worker.COST
		# elif my_energy > 150 and len(fighter) < MAX_FIGHTERS:
		# 	enemies = [x for x in spawns if x != spawns[my_index]]
		# 	if defend:
		# 		requests.append(spawnAnt(AntTypes.FIGHTER, spawns[my_index]))
		# 		my_energy -= stats.ants.Fighter.COST
		# 	elif siege:
		# 		requests.append(spawnAnt(AntTypes.FIGHTER, spawns[siege_position]))
		# 		my_energy -= stats.ants.Fighter.COST
		# 	else:
		# 		if random.randint(0, 1) == 0:
		# 			requests.append(spawnAnt(AntTypes.FIGHTER, random.choice(enemies)))
		# 			my_energy -= stats.ants.Fighter.COST
		# elif total_ants == 0:
		# 	requests.append(spawnAnt(AntTypes.WORKER, closest_site))

		if my_energy < 60:
			requests.append(spawnAnt(AntTypes.WORKER, closest_site))
			my_energy -= stats.ants.Worker.COST
		elif zone_active:
			if defend:
				if my_energy < 150:
					if len(worker) < MAX_WORKERS:
						requests.append(spawnAnt(AntTypes.WORKER, closest_site))
						my_energy -= stats.ants.Worker.COST
					elif len(settler) < MAX_SETTLERS:
						requests.append(spawnAnt(AntTypes.SETTLER, random.choice(zone)))
						my_energy -= stats.ants.Settler.COST
					elif len(fighter) < MAX_FIGHTERS:
						requests.append(spawnAnt(AntTypes.FIGHTER, spawns[my_index]))
						my_energy -= stats.ants.Fighter.COST
				else:
					if len(settler) < MAX_SETTLERS:
						requests.append(spawnAnt(AntTypes.SETTLER, random.choice(zone)))
						my_energy -= stats.ants.Settler.COST
					elif len(worker) < MAX_WORKERS:
						requests.append(spawnAnt(AntTypes.WORKER, closest_site))
						my_energy -= stats.ants.Worker.COST
					elif len(fighter) < MAX_FIGHTERS:
						requests.append(spawnAnt(AntTypes.FIGHTER, spawns[my_index]))
						my_energy -= stats.ants.Fighter.COST
			else:
				if my_energy < 150:
					if len(worker) < MAX_WORKERS:
						requests.append(spawnAnt(AntTypes.WORKER, closest_site))
						my_energy -= stats.ants.Worker.COST
					elif len(settler) < MAX_SETTLERS:
						requests.append(spawnAnt(AntTypes.SETTLER, random.choice(zone)))
						my_energy -= stats.ants.Settler.COST
					elif len(fighter) < MAX_FIGHTERS:
						requests.append(spawnAnt(AntTypes.FIGHTER, random.choice(enemies)))
						my_energy -= stats.ants.Fighter.COST
				else:
					if len(settler) < MAX_SETTLERS:
						requests.append(spawnAnt(AntTypes.SETTLER, random.choice(zone)))
						my_energy -= stats.ants.Settler.COST
					elif len(fighter) < MAX_FIGHTERS:
						requests.append(spawnAnt(AntTypes.FIGHTER, random.choice(enemies)))
						my_energy -= stats.ants.Fighter.COST
					elif len(worker) < MAX_WORKERS:
						requests.append(spawnAnt(AntTypes.WORKER, closest_site))
						my_energy -= stats.ants.Worker.COST
		else:
			if defend:
				if my_energy < 150:
					if len(worker) < MAX_WORKERS:
						requests.append(spawnAnt(AntTypes.WORKER, closest_site))
						my_energy -= stats.ants.Worker.COST
					else:
						requests.append(spawnAnt(AntTypes.FIGHTER, spawns[my_index]))
						my_energy -= stats.ants.Fighter.COST
				else:
					if len(fighter) < MAX_FIGHTERS:
						requests.append(spawnAnt(AntTypes.FIGHTER, spawns[my_index]))
						my_energy -= stats.ants.Fighter.COST
					else:
						requests.append(spawnAnt(AntTypes.WORKER, random.choice(closest_food_sites)))
						my_energy -= stats.ants.Worker.COST
			else:
				if my_energy < 150:
					if len(worker) < MAX_WORKERS:
						requests.append(spawnAnt(AntTypes.WORKER, closest_site))
						my_energy -= stats.ants.Worker.COST
					else:
						requests.append(spawnAnt(AntTypes.FIGHTER, spawns[my_index]))
						my_energy -= stats.ants.Fighter.COST
				else:
					if len(fighter) < MAX_FIGHTERS:
						requests.append(spawnAnt(AntTypes.FIGHTER, random.choice(enemies)))
						my_energy -= stats.ants.Fighter.COST
					else:
						requests.append(spawnAnt(AntTypes.WORKER, random.choice(closest_food_sites)))
						my_energy -= stats.ants.Worker.COST


	return requests

# def calculateCorridor(point):
# 	for x, y in point:


def getCenterPoint(points):
	x = [x[0] for x in points]
	y = [y[1] for y in points]
	return sum(x) / len(x), sum(y) / len(y)

def spawnAnt(a_type, a_goal):
	request = SpawnRequest(a_type, id=None, color=None, goal=a_goal)
	return request

def updateStatuses(event):
	global MAX_WORKERS, MAX_FIGHTERS, MAX_SETTLERS, \
		MIN_THRESHOLD, MAX_THRESHOLD, zone_active, zone
	if event == ZoneActiveEvent:
		print("zone activated")
		if MIN_THRESHOLD < my_energy < MAX_THRESHOLD:
			MAX_SETTLERS = 60
			MAX_FIGHTERS = 30
			MAX_WORKERS = 10
		else:
			MAX_SETTLERS = 50
			MAX_FIGHTERS = 35
			MAX_WORKERS = 15
	elif event == ZoneDeactivateEvent:
		zone = None
		zone_active = False
		MAX_SETTLERS = 0
		if MIN_THRESHOLD < my_energy <= MAX_THRESHOLD:
			MAX_WORKERS = 10
			MAX_FIGHTERS = 80
		else:
			MAX_WORKERS = 50
			MAX_FIGHTERS = 50

