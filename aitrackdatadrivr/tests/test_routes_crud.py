from pathlib import Path
import pytest
from flask import Flask
from server.route_geometry import normalize_route_geometry
from server import route_api

MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'054_create_versioned_routes.sql'

def test_linestring_is_canonical_hashed_and_measured():
    value=normalize_route_geometry({'type':'LineString','coordinates':[[-46.63,-23.55],[-46.62,-23.54]]},100)
    assert value['geometry']['type']=='LineString' and value['length_meters']>1000 and len(value['geometry_sha256'])==64
    assert value['geometry_sha256']==normalize_route_geometry(value['geometry'],100)['geometry_sha256']

@pytest.mark.parametrize('geometry,corridor',[({'type':'Polygon','coordinates':[]},100),({'type':'LineString','coordinates':[[0,0]]},100),({'type':'LineString','coordinates':[[0,0],[0,0]]},100),({'type':'LineString','coordinates':[[0,0],[1,1]]},1)])
def test_invalid_geometry_or_corridor_is_rejected(geometry,corridor):
    with pytest.raises(ValueError):normalize_route_geometry(geometry,corridor)

def test_route_api_contract(monkeypatch):
    app=Flask(__name__);app.register_blueprint(route_api.route_bp);client=app.test_client()
    monkeypatch.setattr(route_api.route_db,'list_routes',lambda archived,limit:[{'public_id':'r1','status':'active'}])
    response=client.get('/api/routes');assert response.status_code==200 and response.get_json()['schema_version']=='routes.v1'
    monkeypatch.setattr(route_api.route_db,'create_route',lambda payload:{'public_id':'r2','version':1})
    assert client.post('/api/routes',json={'name':'Rota'}).status_code==201

def test_migration_versions_geometry_and_audit_are_immutable():
    sql=MIGRATION.read_text().lower()
    for token in ('monitoramento.routes','route_versions','geometry_sha256','corridor_meters','length_meters','route_audit_log'):assert token in sql
    assert 'route versions are immutable' in sql and 'route versions cannot be deleted' in sql
