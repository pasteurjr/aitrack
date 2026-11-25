"""Validação canônica de LineString e comprimento geodésico de rota."""

import hashlib,json,math

MAX_POINTS=2000

def _point(value,index):
    if not isinstance(value,(list,tuple)) or len(value)!=2:raise ValueError(f'Ponto {index} deve ser [longitude, latitude]')
    lon,lat=value
    if isinstance(lon,bool) or isinstance(lat,bool) or not isinstance(lon,(int,float)) or not isinstance(lat,(int,float)):raise ValueError(f'Ponto {index} inválido')
    lon=float(lon);lat=float(lat)
    if not math.isfinite(lon) or not math.isfinite(lat) or not -180<=lon<=180 or not -90<=lat<=90:raise ValueError(f'Ponto {index} fora dos limites')
    return [lon,lat]

def _distance(a,b):
    radius=6371008.8;p1=math.radians(a[1]);p2=math.radians(b[1]);dp=p2-p1;dl=math.radians(b[0]-a[0])
    h=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*radius*math.asin(min(1,math.sqrt(h)))

def normalize_route_geometry(geometry,corridor_meters):
    if not isinstance(geometry,dict) or geometry.get('type')!='LineString':raise ValueError('geometry.type deve ser LineString')
    raw=geometry.get('coordinates')
    if not isinstance(raw,list) or not 2<=len(raw)<=MAX_POINTS:raise ValueError(f'LineString deve ter entre 2 e {MAX_POINTS} pontos')
    points=[_point(value,index) for index,value in enumerate(raw)]
    if any(points[i]==points[i-1] for i in range(1,len(points))):raise ValueError('Rota não aceita pontos consecutivos iguais')
    if isinstance(corridor_meters,bool) or not isinstance(corridor_meters,(int,float)) or not 5<=float(corridor_meters)<=5000:raise ValueError('corridor_meters deve estar entre 5 e 5000')
    length=sum(_distance(points[i-1],points[i]) for i in range(1,len(points)))
    if length<=1 or length>20_000_000:raise ValueError('Comprimento da rota fora dos limites')
    canonical={'type':'LineString','coordinates':points};raw_json=json.dumps(canonical,separators=(',',':'),sort_keys=True)
    return {'geometry':canonical,'geometry_json':raw_json,'geometry_sha256':hashlib.sha256(raw_json.encode()).hexdigest(),'corridor_meters':float(corridor_meters),'length_meters':round(length,2)}
