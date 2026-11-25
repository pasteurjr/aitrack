"""Matemática determinística de corredor, histerese e parada."""
import math
from dataclasses import dataclass

def point_segment_distance_m(point,a,b):
    lat0=math.radians(point[1]);scale=6371008.8
    def xy(p):return (math.radians(p[0]-point[0])*math.cos(lat0)*scale,math.radians(p[1]-point[1])*scale)
    ax,ay=xy(a);bx,by=xy(b);dx=bx-ax;dy=by-ay
    if dx==dy==0:return math.hypot(ax,ay)
    t=max(0,min(1,-(ax*dx+ay*dy)/(dx*dx+dy*dy)));return math.hypot(ax+t*dx,ay+t*dy)

def distance_to_route_m(point,coordinates):
    if len(coordinates)<2:raise ValueError('Rota sem segmentos')
    return min(point_segment_distance_m(point,coordinates[i-1],coordinates[i]) for i in range(1,len(coordinates)))

@dataclass(frozen=True)
class RouteEvolution:
    stable_on_route:bool|None;pending_on_route:bool|None;pending_samples:int;transition:str|None

def evolve_route_state(stable,pending,samples,distance,corridor,accuracy=0,hysteresis=10,confirmations=2):
    effective=corridor+max(0,float(accuracy or 0));candidate=True if distance<=max(0,effective-hysteresis) else False if distance>effective+hysteresis else stable
    if candidate is None or candidate==stable:return RouteEvolution(stable,None,0,None)
    count=samples+1 if pending==candidate else 1
    if count>=confirmations:return RouteEvolution(candidate,None,0,'recovered' if candidate else 'deviation')
    return RouteEvolution(stable,candidate,count,None)

def is_planned_stop(point,stops):
    return any(point_segment_distance_m(point,[s['longitude'],s['latitude']],[s['longitude'],s['latitude']])<=float(s['radius_meters']) for s in stops)
