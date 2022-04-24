from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.requests import GoalRequest, SpawnRequest
from Variables import vars


class WorkersActor(object):
    
    def __init__(self,def_goal=None):
        if def_goal is None:
            def_goal=vars.closest_site
        self.default_goal=def_goal
    '''
    def add_actor(self, spawn_num):
        self.actors_wait_for_spawn += spawn_num
    '''
    def spawn_actor(self,spawn_num,goals=None):
        requests = []
        assert goals is None,"goal to workers" 
        i=vars.worker_goal.index(self.default_goal)
        new_id=max(vars.workers[i])+1 if vars.workers[i] else 0
        while (vars.total_ants < stats.general.MAX_ANTS_PER_PLAYER and
               vars.spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
               vars.energys[vars.my_index] >= stats.ants.Worker.COST+2*stats.ants.Fighter.COST and
               spawn_num>0
        ):
            goal= goals.pop() if goals else self.default_goal
            
            vars.spawned_this_tick += 1
            # Spawn an ant, give it some id, no color, and send it to the closest site.
            # I will pay the base cost for this ant, so cost=None.
            requests.append(SpawnRequest(AntTypes.WORKER, id='{}-{}-{}'.format(0,i,new_id), color=None, goal=goal))
            vars.energys[vars.my_index] -= stats.ants.Worker.COST
            vars.workers[i].append(new_id)
            vars.total_ants += 1
            # self.actors_wait_for_spawn -= 1
            spawn_num -= 1
            new_id+=1

        return requests


class SettlerActor(object):
    
    def __init__(self,def_goal=None):
        if def_goal is None:
            if vars.AH:
                def_goal=vars.groups[vars.AH][0]
            elif 0 in vars.settlers:
                def_goal=vars.groups[vars.settlers.index(0)][0]
            else:
                assert False,"useless settler"
        self.default_goal=def_goal
    '''
    def add_actor(self, spawn_num):
        self.actors_wait_for_spawn += spawn_num
    '''
    def spawn_actor(self,spawn_num,goals=None):
        requests = []
        new_id=max(vars.settlers)+1 if vars.settlers else 0
        while (vars.total_ants < stats.general.MAX_ANTS_PER_PLAYER and
               vars.spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
               vars.energys[vars.my_index] >= stats.ants.Settler.COST+2*stats.ants.Fighter.COST and
               spawn_num>0
        ):
            vars.spawned_this_tick += 1
            vars.total_ants += 1
            #self.actors_wait_for_spawn -= 1
            spawn_num -= 1
            
            # Spawn an ant, give it some id, no color, and send it to the closest site.
            # I will pay the base cost for this ant, so cost=None.
            goal= goals.pop() if goals else self.default_goal
            requests.append(SpawnRequest(AntTypes.SETTLER, id='{}-{}-{}'.format(1,0,new_id), color=None, goal=goal))
            vars.energys[vars.my_index] -= stats.ants.Settler.COST
            vars.settlers.append(new_id)
            new_id+=1
        return requests


class FighterActor(object):
    
    def __init__(self,def_goal=None):
        self.default_goal=def_goal
    '''
    def add_actor(self, spawn_num):
        self.actors_wait_for_spawn += spawn_num
    '''
    def spawn_actor(self,spawn_num,goals=None):
        requests = []
        #new_id=max(vars.fighters)+1 if vars.fighters else 0
        while (vars.total_ants < stats.general.MAX_ANTS_PER_PLAYER and
               vars.spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
               vars.energys[vars.my_index] >= stats.ants.Fighter.COST and
               spawn_num>0
        ):
            vars.spawned_this_tick += 1
            vars.total_ants += 1
            #self.actors_wait_for_spawn -= 1
            spawn_num -= 1
            # Spawn an ant, give it some id, no color, and send it to the closest site.
            # I will pay the base cost for this ant, so cost=None.
            goal= goals.pop() if goals else self.default_goal
            if goal==None:
                code=0
            else:
                code=1
            new_id=max(vars.fighters[code])+1 if vars.fighters[code] else 0
            requests.append(SpawnRequest(AntTypes.FIGHTER, id='{}-{}-{}'.format(2,code,new_id), color=None, goal=goal))
            vars.energys[vars.my_index] -= stats.ants.Fighter.COST
            vars.fighters[code].append(new_id)
        return requests


##class DefenceActor(object):
##      '''
##    def __init__(self):
##        self.actors_wait_for_spawn = 0
##
##    def add_actor(self, spawn_num):
##        self.actors_wait_for_spawn += spawn_num
##      '''
##    def spawn_actor(self,spawn_num):
##        requests = []
##
##        vars.spawned_this_tick = 0
##        while (vars.total_ants < stats.general.MAX_ANTS_PER_PLAYER and
##               vars.spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
##               vars.energys[vars.my_index] >= stats.ants.Fighter.COST and
##               spawn_num>0
##        ):
##            vars.spawned_this_tick += 1
##            vars.total_ants += 1
##            #self.actors_wait_for_spawn -= 1
##            spawn_num -= 1
##            # Spawn an ant, give it some id, no color, and send it to the closest site.
##            # I will pay the base cost for this ant, so cost=None.
##            requests.append(SpawnRequest(AntTypes.Fighter, id=None, color=None, goal=None))
##            vars.energys[vars.my_index] -= stats.ants.Fighter.COST
##
##        return requests
