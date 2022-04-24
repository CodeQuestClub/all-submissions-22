import codequest22.stats as stats
from codequest22.server.ant import AntTypes
import random
class DS_set:
    def __init__(self,N):
        self.Array_=[-1]*N
        
    def find(self,a):
        if self.Array_[a] < 0:
            return a
        self.Array_[a]=self.find(self.Array_[a])
        return self.Array_[a]
        
    def union(self,a,b):
        root_a=self.find(a)
        root_b=self.find(b)
        rank_a=-self.Array_[root_a]
        rank_b=-self.Array_[root_b]
        
        if rank_a>rank_b:
            self.Array_[root_b]=root_a
            self.Array_[root_a]=-(rank_a+rank_b)
        else:
            self.Array_[root_a]=root_b
            self.Array_[root_b]=-(rank_a+rank_b)
        
    def get_groups(self):
        groups={}
        for i in range(len(self.Array_)):
            if i<0:
                r=i
            else:
                r=self.find(i)
            if r in groups:
                groups[r].append(i)
            else:
                groups[r]=[i]
        return groups.values()

class Variables: 
    def __init__(self):
        #self.my_energy = stats.general.STARTING_ENERGY
        self.map_data = {}
        self.spawns = [None]*4
        self.food = []
        self.distance = []
        self.closest_site = None
        self.total_ants = 0
        self.my_index=None
        self.ticks=0
        self.hills=[]
        self.pass_threshold=None
        self.agra_threshold=None
        self.AH=None
        self.TE=stats.general.SIMULATION_TICKS
        self.min_TE=stats.general.SIMULATION_TICKS-stats.hill.MAX_ZONE_TIME-stats.hill.MIN_WAIT_TIME
        self.alpha=0.5 #portion of Energy used to spawn worker, 1-/alpha used to spawn settler
        self.beta=3 #min settler on active hill
        self.spawn_this_tick=0
        self.attacked_by=0
        self.attacksers={} #key: fighter id, value: 
        self.overcharge={} #dict key: loc value (tick,multi)
        self.overcharge={}
        self.food_site_infos_dic = {}
        self.settlers=[]
        self.fighters=[[],[]] #0:defence 1:attack
        '''
        self.spawn_info_dic = {}  # id: goals
        for id in list(range(5)):
            item_info_dic = {}
            item_info_dic["is_alive"] = False
            item_info_dic["goal"] = None
            self.spawn_info_dic[id] = item_info_dic
        '''

    def update_food_site_infos_dic_by_food_tile_action(self, pos, num_ticks, multiplier):

        if not pos in self.food_site_infos_dic.keys():
            return

        self.food_site_infos_dic[pos]["energy"] = self.food_site_infos_dic[pos]["base_energy"] * multiplier
        self.food_site_infos_dic[pos]["rate"] = self.food_site_infos_dic[pos]["energy"] / \
                                                self.food_site_infos_dic[pos]["distance"]


        # energy_distance_rate_dic = {}
        # for key, value in self.food_site_infos_dic.items():
        #     energy_distance_rate_dic[key] = value["rate"]
        #
        # energy_distance_rate_dic = list(sorted(energy_distance_rate_dic.items(), key=lambda item: item[1], reverse=True))
        #
        # self.food = []
        # for item in energy_distance_rate_dic:
        #     self.food.append(item[0])

        #print("pos, num_ticks, multiplier: ", pos, num_ticks, multiplier)
        #print("self.food_site_infos_dic: ", self.food_site_infos_dic)
        #print("energy_distance_rate_dic: ", energy_distance_rate_dic)
        #print("vars.food: ", vars.food)

    def update_food_site_infos_dic(self):
        for item_pos in self.food:
            share_food_num = self.share_food(item_pos) + 1
            self.food_site_infos_dic[item_pos]["shared_energy"] = self.food_site_infos_dic[item_pos]["energy"] / share_food_num
            self.food_site_infos_dic[item_pos]["rate"] = self.food_site_infos_dic[item_pos]["shared_energy"] / \
                                                    self.food_site_infos_dic[item_pos]["distance"]

        energy_distance_rate_dic = {}
        for key, value in self.food_site_infos_dic.items():
            energy_distance_rate_dic[key] = value["rate"]

        energy_distance_rate_dic = list(
            sorted(energy_distance_rate_dic.items(), key=lambda item: item[1], reverse=True))

        last_food_pos_list = self.food.copy()

        self.food = []
        for item in energy_distance_rate_dic:
            self.food.append(item[0])

        # for i in range(len(self.food)):
        for i in range(3):
            old_loc = last_food_pos_list[i]
            new_loc = self.food[i]
            self.update_worker(old_loc, new_loc)

        # print("self.food_site_infos_dic: ", self.food_site_infos_dic)
        # print("energy_distance_rate_dic: ", energy_distance_rate_dic)
        # print("#"*30)


    #def calc_agra_thre(self):
    #    if self.AH:
    #        self.beta+
    def calc_info(self):
        self.group_hills()
        self.calc_prepareTime()
        self.init_workers()
        #self.init_fighters()
        
    def init_fighters(self):
        self.fighter_goal=[]
        self.fighter_distribution=[]
        self.fighters=[]
        #defence at index=0
        self.fighter_distribution.append(0)
        self.workers.append([])
        self.workers.append(self.spawns[self.my_index])
        
    def get_target(self,ecos):
        coef=[]
        for i in range(vars.n_players):
            b=self.Q_HP[i]!=0
            ETA=(self.distance[self.my_index][self.spawns[i]]/stats.ants.Fighter.SPEED)
            c=stats.ants.Fighter.LIFESPAN-ETA>=3
            d=self.my_index!=i
            
            if b and c and d:
                coef.append(i)
                
        if coef==[]:
            return
            
        if len(coef)==1:
            return coef[0]
                
        ind=sorted(coef,key=lambda x: (self.hill_points[x]+0.5)*ecos[x]/self.Q_HP[x],reverse = True)[0]
        '''
        if self.hill_points[ind]==0:
            if self.energys[self.my_index]>0.9*stats.general.MAX_ENERGY_STORED:
                return ind
            else:
                return
        '''
        return ind   
        
    def check_worker(self):
        nextTo=lambda loc1,loc2,x: abs(loc1[0]-loc2[0])<=x and abs(loc1[1]-loc2[1])<=x
        coef=[]
        for loc in self.worker_goal:
            f_num=0
            w_num=0
            for i,a in enumerate(self.ants):
                if i==self.my_index:
                    continue
                for k,v in a.items():
                    if v["ant_type"] == AntTypes.FIGHTER and nextTo(v["pos"],loc,3):
                        f_num+=1
                    elif v["ant_type"] == AntTypes.WORKER and nextTo(v["pos"],loc,1):
                        w_num+=1
            if f_num>=2:
                return loc,2
            elif w_num>0 or f_num>0:
                coef.append(1)
            else:
                coef.append(0)
                
        for i,c in enumerate(coef):
            if c:
                return self.worker_goal[i],1
                        
    def init_workers(self):
        self.worker_distribution=[]
        self.workers=[]
        self.worker_goal=[]
        for i in range(3):
            Dis=self.distance[self.my_index][self.food[i]]
            Tgo=Dis/stats.ants.Worker.SPEED
            Tback=Dis/(stats.ants.Worker.SPEED*stats.ants.Worker.ENCUMBERED_RATE)
            self.worker_distribution.append((Tgo+Tback)//stats.energy.DELAY)
            self.workers.append([])
            self.worker_goal.append(self.food[i])
            
    def update_worker(self,old_loc,new_loc):
        #new_id=len(self.worker_distribution)
        if old_loc in self.worker_goal:
            ind=self.worker_goal.index(old_loc)
        else:
            # return None
            raise ValueError()
        Dis=self.distance[self.my_index][new_loc]
        Tgo=Dis/stats.ants.Worker.SPEED
        Tback=Dis/(stats.ants.Worker.SPEED*stats.ants.Worker.ENCUMBERED_RATE)
        self.worker_distribution[ind] = (Tgo+Tback)//stats.energy.DELAY
        #self.workers.append([])
        self.worker_goal[ind] = new_loc



        
    def pre_set(self):
        self.hill_points=[0 for _ in range(self.n_players)]
        self.distance=[{} for _ in range(self.n_players)]
        self.Q_HP=[stats.general.QUEEN_HEALTH for _ in range(self.n_players)]
        self.energys= [stats.general.STARTING_ENERGY for _ in range(self.n_players)]
        self.ants= [{} for _ in range(self.n_players)]
        self.no_response=[0 for _ in range(self.n_players)]
        
    def get_opt_worker(self):
        return self.food_goal

    def get_enemy_num(self,t,loc):
        num=0
        nextTo=lambda loc1,loc2 : abs(loc1[0]-loc2[0])<=3 and abs(loc1[1]-loc2[1])<=3
        for k,v in enumerate(self.ants):
            if k==self.my_index: continue
            for i,a in v.items():
                if a["ant_type"]==t:
                    trig=False
                    if a["pos"]:
                        trig=trig or nextTo(a["pos"],loc)
                    if a["goal"]:
                        trig=trig or nextTo(a["goal"],loc)
                    if trig:
                        num+=1
        return num
                    
    
    def group_hills(self):
        nextTo=lambda loc1,loc2 : abs(loc1[0]-loc2[0])<=1 and abs(loc1[1]-loc2[1])<=1
        groups=DS_set(len(self.hills))
        uni=[]
        for a,loca in enumerate(self.hills):
            for b,locb in enumerate(self.hills):
                if loca!=locb and nextTo(loca,locb) and {loca,locb} not in uni:
                    groups.union(a,b)
                    uni.append({loca,locb})
        groups=groups.get_groups()
        ind2loc=lambda l:list(map(lambda x: self.hills[x], l))
        self.groups=list(map(ind2loc,groups))
        #TODO: make first loc in each group is cloest to Spawn
        #self.settlers=[0 for _ in self.groups]
        self.remains=[stats.hill.NUM_ACTIVATIONS for _ in self.groups]
        
    def calc_prepareTime(self):
        g=None
        max_dis=999999999
        #max of all groups
        for gi,g in enumerate(self.groups):
            temp_dis=self.distance[self.my_index][g[0]]
            if max_dis<temp_dis:
                max_dis=temp_dis
                g=gi
                
        max_dis=min([self.distance[self.my_index][i] for i in self.groups[gi]]) #min in a group of hill
        self.prepare=stats.hill.GRACE_PERIOD-(max_dis//stats.ants.Settler.SPEED)
        
    def active_food(self,pos,tick,mult):
        self.overcharge[pos]=[tick,mult]
    
    def deactive_food(self,pos):
        self.overcharge.pop(pos)
        
    def score(self,player,amount):
        self.hill_points[player]+=amount
        
    def get_food(self,pos):
        return self.energy_info[pos]*(self.overcharge[pos][1] if pos in self.overcharge else 1)
    
    def active_hill(self,AH,ticks):
        for i,g in enumerate(self.groups):
            if AH[0] in g:
                self.AH=i
                break
        
        if self.ticks>=self.min_TE:
            self.TE=stats.general.SIMULATION_TICKS-min(map(lambda x: self.distance[self.my_index][x],AH))  
        
        self.AHticks=ticks
  
    def game_tick(self):
        self.update_food_site_infos_dic()

        self.spawned_this_tick=0
        self.ticks+=1
        self.attacked_by=1
        if self.AH:
            self.AHticks-=1
        for k,v in self.overcharge.items():
            self.overcharge[k][0]-=1
        
        self.food_goal=self.food[:]
        for k,v in self.ants[self.my_index].items():
            if v["ant_type"]==AntTypes.WORKER:
                if v["pos"] in self.food_goal:
                    self.food_goal.remove(v["pos"])
                elif v["goal"] in self.food_goal:
                    self.food_goal.remove(v["goal"])
        
        
        
    def deactive_hill(self):
        self.remains[self.AH]-=1
        if self.remains[self.AH]==0:
            self.remains.pop(self.AH)
            self.groups.pop(self.AH)
        self.AH=None
    
    def defeat(self, defeated_index,by_index,new_hill_score):
        self.hill_points[by_index]=new_hill_score
        #self.distance.pop(defeated_index)
        self.hill_points[defeated_index]=0
        self.Q_HP[defeated_index]=0
    
    def check_ending(self):
        return self.ticks>self.TE

    def check_pass(self):
        return self.ticks<self.prepare or self.energys[self.my_index]<3*stats.ants.Worker.COST or self.energys[self.my_index]< self.pass_threshold
        
    def check_agg(self):
        return (self.settlers[self.AH]>self.beta if self.AH else True) and (0 not in self.settlers)
    
    def get_eco_level(self):
        echo_level=self.energys[:]
        for i in range(self.n_players):
            for k,v in self.ants[i].items():
                echo_level[i]+=v["cost"]
                
        return echo_level

    def get_next_food(self):
        if self.food_goal:
            return self.food_goal.pop(0)
        else:
            # return self.energy_distance_rate_sort[0][0]
            return self.food[0]

    def share_food(self,loc):
        num=0
        for i,a in enumerate(self.ants):
            if i==self.my_index:
                continue
            for k,v in a.items():
                if v["ant_type"]==AntTypes.WORKER and v["pos"]==loc:
                    num+=1
                    break
        return num
        
vars = Variables()