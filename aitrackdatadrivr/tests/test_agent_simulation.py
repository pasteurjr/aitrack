from pathlib import Path
from server.agent_autonomy import AutonomyPolicy,evaluate_autonomy

MIGRATION=Path(__file__).resolve().parents[1]/'migrations'/'041_create_agent_simulation_mode.sql'

def valid_decision():
    return {'schema_version':'vehicle-monitoring-decision.v1','classification':'attention','confidence':.8,'summary':'Incidente requer acompanhamento operacional.','risk':{'level':'high','score':80,'rationale':'Evidência persistida requer confirmação.'},'evidence':[{'source':'tracker','type':'position','ref':'position:1','summary':'Posição persistida.'}],'proposed_actions':[{'type':'contact_owner','priority':'normal','rationale':'Confirmar deslocamento com responsável.','requires_approval':False}],'human_review':{'required':True,'reason':'Risco alto exige revisão humana.','deadline_seconds':300}}

def test_simulation_records_would_do_disposition_without_execution_eligibility():
    value=valid_decision();value['risk'].update(level='low',score=10);value['human_review'].update(required=False,reason='Risco baixo sem revisão exigida.')
    result=evaluate_autonomy(AutonomyPolicy(1,2,'execute','low',('contact_owner',),'simulation'),value)
    assert result['execution_mode']=='simulation' and result['actions'][0]['disposition']=='simulated'

def test_migration_persists_only_immutable_simulated_receipts():
    sql=MIGRATION.read_text().lower()
    for token in ('execution_mode','agent_simulated_actions','authorization_json','trg_agent_simulated_action_immutable_update','trg_agent_simulated_action_immutable_delete'):assert token in sql
    assert 'drop table' not in sql and 'delete from' not in sql
