from spawns import *
import codequest22.stats as stats
from Variables import vars
from codequest22.server.events import *
from codequest22.server.ant import AntTypes
import math

# def passive():
#     spawn_workers=WorkersActor()
#     return spawn_workers.spawn_actor(stats.general.MAX_SPAWNS_PER_TICK)

def get_workers():
    #print("my=",vars.energys[my_index])
    #print("max="stats.general.MAX_ENERGY_STORED*0.7)
    '''
    if vars.energys[vars.my_index]>=stats.general.MAX_ENERGY_STORED*0.6:
        worker_num=0
        for k,v in vars.ants[vars.my_index].items():
            if v["ant_type"]==AntTypes.WORKER:
                worker_num+=1
        if worker_num>=stats.general.MAX_ANTS_PER_PLAYER*0.5:
            return[]
    goals=vars.get_opt_worker()
    spawn_workers=WorkersActor()
    req=spawn_workers.spawn_actor(len(goals),goals)
    '''
    
    req=[]
    if vars.ticks<=35:
        end=1
    elif vars.ticks<=45:
        end=2
    else:
        end=3
    for i,v in enumerate(vars.worker_distribution):
        spawn_workers=WorkersActor(vars.worker_goal[i])
        if len(vars.workers[i])<v:
            temp=spawn_workers.spawn_actor(v-len(vars.workers[i]))
            if temp==[]:
                break
            else:
                req+=temp
    return req

def passive():
    spawn_workers=WorkersActor()

    count = 0
    for value in vars.worker_info_dic.values():
        if value["is_alive"] is False:
            count += 1

    if count >= stats.general.MAX_SPAWNS_PER_TICK:
        return spawn_workers.spawn_actor(stats.general.MAX_SPAWNS_PER_TICK)
    else:
        return spawn_workers.spawn_actor(count)


def aggrassive():
    requests=[]
    ecos=vars.get_eco_level()
    
    if (vars.AH is not None) and ((vars.AHticks > vars.distance[vars.my_index][vars.groups[vars.AH][0]]/stats.ants.Settler.SPEED)): #check the ETA to AH
        #print(vars.AHticks,"->",vars.distance[vars.my_index][vars.groups[vars.AH][0]]/stats.ants.Settler.SPEED)
        #if (vars.AHticks > vars.distance[vars.my_index][vars.groups[vars.AH][0]]/stats.ants.Settler.SPEED):
        spawn_fighter=FighterActor(vars.groups[vars.AH][0])
        spawn_settlers=SettlerActor(vars.groups[vars.AH][0])   
        if ecos[vars.my_index]==max(ecos):
            fighter_num=vars.get_enemy_num(AntTypes.FIGHTER,vars.groups[vars.AH][0])
            if fighter_num and (vars.spawned_this_tick>=(stats.general.MAX_SPAWNS_PER_TICK-1-2) or vars.energys[vars.my_index]<stats.ants.Fighter.COST+stats.ants.Settler.COST):
                return []
            fighter_num+=(vars.get_enemy_num(AntTypes.SETTLER,vars.groups[vars.AH][0])//2)
        else:
            fighter_num=vars.get_enemy_num(AntTypes.FIGHTER,vars.groups[vars.AH][0])
            if fighter_num and (vars.spawned_this_tick>=(stats.general.MAX_SPAWNS_PER_TICK-1-2) or vars.energys[vars.my_index]<stats.ants.Fighter.COST+stats.ants.Settler.COST):
                return []
            fighter_num+=vars.get_enemy_num(AntTypes.SETTLER,vars.groups[vars.AH][0])
            fighter_num//=2
        
        if fighter_num:
            requests+=spawn_fighter.spawn_actor(fighter_num)
            
        if vars.attacked_by==0 and len(vars.fighters[0])>0:
            for i in vars.fighters[0]:
                requests.append(GoalRequest("{}-{}-{}".format(2,0,i), vars.groups[vars.AH][0]))
        requests+=spawn_settlers.spawn_actor(stats.general.MAX_SPAWNS_PER_TICK)
        
    else:
        info=vars.check_worker()
        if info:
            loc,num=info
            for k,v in vars.ants[vars.my_index].items():
                if v["ant_type"]==AntTypes.FIGHTER and v["pos"]==loc:
                    num-=1
                    if num<=0:
                        break
            else:
                spawn_fighter=FighterActor(loc)
                requests+=spawn_fighter.spawn_actor(num)
            
        #if  vars.spawned_this_tick>=(stats.general.MAX_SPAWNS_PER_TICK-1-2) or vars.energys[vars.my_index]<=90:
        
        if vars.spawned_this_tick>=(stats.general.MAX_SPAWNS_PER_TICK-1-2) or vars.energys[vars.my_index]<0.8*stats.general.MAX_ENERGY_STORED:
                return []
                
        ind=vars.get_target(ecos)
        if ind is None:
            return []
        else:
            spawn_fighter=FighterActor(vars.spawns[ind])
        
        if vars.attacked_by==0 and len(vars.fighters[0])>0:
            for i in vars.fighters[0]:
                requests.append(GoalRequest("{}-{}-{}".format(2,0,i), vars.spawns[ind]))
        requests+=spawn_fighter.spawn_actor(stats.general.MAX_SPAWNS_PER_TICK)
        
    return requests
    '''
    #spawn settlers
    spawn_num=0
    for i,h in enumerate(vars.settlers):
        num_required=1
        if i==vars.AH:
            num_required=vars.beta
        spawn_num+=(num_required-h)
    spawn_settlers=SettlerActor()
    requests+=spawn_settlers.spawn_actor(spawn_num)
    #spawn the rest as worker
    spawn_workers=WorkersActor()
    requests+=spawn_workers.spawn_actor(stats.general.MAX_SPAWNS_PER_TICK)
    '''
    
    
def ending(): 
    coef=[]
    for i in range(vars.n_players):
        b=vars.Q_HP[i]!=0
        ETA=(vars.distance[vars.my_index][vars.spawns[i]]/stats.ants.Fighter.SPEED)
        c=stats.ants.Fighter.LIFESPAN-ETA>=3
        d=vars.my_index!=i
        if b and c and d:
            coef.append(i)
            
    if coef==[]:
        spawn_fighter=FighterActor()
    elif len(coef)==1:
        ind=coef[0]
        spawn_fighter=FighterActor(vars.spawns[ind])
    else:
        ind=sorted(coef,key=lambda x: vars.distance[vars.my_index][vars.spawns[x]])[0]
        spawn_fighter=FighterActor(vars.spawns[ind])
    
    return spawn_fighter.spawn_actor(stats.general.MAX_SPAWNS_PER_TICK)
    
def defence(): 
    nextTo=lambda loc1,loc2 : abs(loc1[0]-loc2[0])<=4 and abs(loc1[1]-loc2[1])<=4
    vars.attacked_by=0
    spawn_fighter=FighterActor()
    for i,a in enumerate(vars.ants):
        if i==vars.my_index:
            continue
        for k,v in a.items():
            if v["ant_type"]==AntTypes.FIGHTER and nextTo(v["pos"],vars.spawns[vars.my_index]):
                vars.attacked_by+=1
                
    #vars.fighter_distribution[0]=math.ceil(vars.attacked_by/2)
    #def_num=math.ceil(vars.attacked_by/2)
    def_num=vars.attacked_by
    if vars.attacked_by==0:
        return []
    if len(vars.fighters[0])<def_num:
        return spawn_fighter.spawn_actor(def_num-len(vars.fighters[0]))  
    else:
        return []
    
    
def response(events):
    requests=[]
    check=[0]*vars.n_players
    
    for ev in events: 
        if isinstance(ev, DepositEvent):
            if ev.player_index == vars.my_index:
                i=ev.ant_id.split('-')[1]
                new_goal=vars.worker_goal[int(i)]
                requests.append(GoalRequest(ev.ant_id, new_goal))
                vars.ants[vars.my_index][ev.ant_id]["goals"]=new_goal
            vars.energys[ev.player_index]=ev.cur_energy
            
        elif isinstance(ev, ProductionEvent):
            if ev.player_index == vars.my_index:
                requests.append(GoalRequest(ev.ant_id, vars.spawns[vars.my_index]))
                vars.ants[vars.my_index][ev.ant_id]["goals"]=vars.spawns[vars.my_index]
            
        elif isinstance(ev, DieEvent):
            #print(ev.ant_id)
            #print(vars.ants[ev.player_index])
            #print(ev)
            if ev.ant_id in vars.ants[ev.player_index]:
                vars.ants[ev.player_index].pop(ev.ant_id)
                if ev.player_index==vars.my_index:
                    vars.total_ants =len(vars.ants[vars.my_index])

            if ev.player_index==vars.my_index:
                
                #print(vars.my_index,": die before:",vars.total_ants)
                #vars.total_ants -= 1
                #print(vars.my_index,": die after:",vars.total_ants)
                ant_info=list(map(int,ev.ant_id.split('-')))

                if ant_info[0]==0:
                    i=ant_info[1]
                    vars.workers[i].remove(ant_info[2])
                elif ant_info[0]==2:
                    i=ant_info[1]
                    vars.fighters[i].remove(ant_info[2])

        elif isinstance(ev, SpawnEvent):
            if hasattr(ev, "ticks_left"):
                life = ev.ticks_left
            if hasattr(ev, "remaining_trips"):
                life = ev.remaining_trips
            vars.ants[ev.player_index][ev.ant_id]={"ant_type":ev.ant_type,"goal":ev.goal,"life":life,"pos":ev.position,"cost":ev.cost}
            
            if ev.player_index!=vars.my_index:
                vars.energys[ev.player_index]-=ev.cost
                
            check[ev.player_index]=1
            
        elif isinstance(ev, MoveEvent):
            vars.ants[ev.player_index][ev.ant_id]["pos"]=ev.position
            
        elif isinstance(ev, AttackEvent):
            attack_response(ev)
            
        elif isinstance(ev, ZoneActiveEvent):
            vars.active_hill(ev.points,ev.num_ticks)
            
        elif isinstance(ev, ZoneDeactivateEvent):
            vars.deactive_hill()
            
        elif isinstance(ev, FoodTileActiveEvent):
            vars.active_food(ev.pos, ev.num_ticks, ev.multiplier)

            vars.update_food_site_infos_dic_by_food_tile_action(ev.pos, ev.num_ticks, ev.multiplier)

        elif isinstance(ev, FoodTileDeactivateEvent):
            vars.deactive_food(ev.pos)
            
        elif isinstance(ev, SettlerScoreEvent):
            vars.score(ev.player_index,ev.score_amount)
            
        elif isinstance(ev, QueenAttackEvent):
            #if ev.ant_player_index!=vars.my_index:
            #    return []
            #if ev.queen_player_index==vars.my_index:
            #    self.attacked_by+=1
            #requests+=queen_attack_response(ev)
            pass
        elif isinstance(ev, TeamDefeatedEvent):
            vars.defeat(ev.defeated_index,ev.by_index,ev.new_hill_score)
    
    for i,v in enumerate(check):
        if v:
            vars.no_response+=1
        else:
            vars.no_response=0
            
    return requests
    
def queen_attack_response(ev):
    if ev.ant_player_index==vars.my_index:
        return []
    if ev.queen_player_index==vars.my_index:
        return defence()
    return []
    
def attack_response(ev):
    if ev.attacker_index==vars.my_index:
        return