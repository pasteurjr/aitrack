import copy
from pathlib import Path

from server.agent_evidence import build_provenance


MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'039_persist_agent_decision_evidence.sql'


def decision():
    return {'schema_version':'vehicle-monitoring-decision.v1','classification':'attention','confidence':.8,
            'summary':'Incidente requer acompanhamento do operador.','risk':{'level':'medium','score':50,'rationale':'Evidência demanda confirmação.'},
            'evidence':[{'source':'tracker','type':'position','ref':'position:9','summary':'Posição persistida.','observed_at':'2026-11-19T15:00:00-03:00'},
                        {'source':'system','type':'incident','ref':'incident:9','summary':'Incidente operacional aberto.'}],
            'proposed_actions':[],'human_review':{'required':False,'reason':'Risco moderado sem ação externa.','deadline_seconds':300}}


def test_provenance_hashes_context_manifest_and_each_ordered_evidence():
    first=build_provenance(decision(),{'vehicle_id':9,'tools':{'position.latest':{'id':1}}})
    second=build_provenance(copy.deepcopy(decision()),{'tools':{'position.latest':{'id':1}},'vehicle_id':9})
    assert first==second and first['evidence_count']==2
    assert len(first['context_sha256'])==64 and len(first['evidence_manifest_sha256'])==64
    assert [item['ordinal'] for item in first['evidence']]==[0,1]
    assert all(len(item['content_sha256'])==64 for item in first['evidence'])


def test_any_evidence_change_changes_manifest_without_changing_context_hash():
    original=build_provenance(decision(),{'vehicle_id':9})
    changed=decision();changed['evidence'][0]['summary']='Posição persistida foi confirmada.'
    updated=build_provenance(changed,{'vehicle_id':9})
    assert original['context_sha256']==updated['context_sha256']
    assert original['evidence_manifest_sha256']!=updated['evidence_manifest_sha256']


def test_migration_normalizes_immutable_evidence_and_decision_metrics():
    sql=MIGRATION.read_text(encoding='utf-8').lower()
    for token in ('agent_decision_evidence','classification','confidence','risk_level','risk_score','context_sha256','evidence_manifest_sha256','trg_agent_evidence_immutable_update','trg_agent_evidence_immutable_delete'):
        assert token in sql
    assert 'drop table' not in sql and 'delete from' not in sql
