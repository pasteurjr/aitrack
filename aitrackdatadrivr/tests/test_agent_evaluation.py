import copy,json
from pathlib import Path
from server.agent_evaluation import decision_from_candidate,evaluate_cases

DATASET=Path(__file__).resolve().parents[1]/'evaluation'/'agent_cases_v1.json'
def cases():return json.loads(DATASET.read_text())['cases']

def test_versioned_dataset_covers_normal_risk_false_positive_and_false_negative_inputs():
    values=cases();assert len(values)>=10
    assert {c['expected']['incident'] for c in values}=={True,False}
    assert {'low','medium','high','critical'}<=set(c['expected']['risk'] for c in values)
    assert {'gps_drift','duplicate_signal','telemetry_gap_moving','suspected_theft'}<=set(c['id'] for c in values)

def test_golden_baseline_meets_accuracy_safety_and_consistency_gate():
    report=evaluate_cases(cases(),decision_from_candidate,3)
    assert report['passed'] and report['metrics']=={'exact_accuracy':1.0,'incident_precision':1.0,'incident_recall':1.0,'false_positive_rate':0.0,'false_negative_rate':0.0,'safety_violations':0,'invalid_cases':0,'consistency_rate':1.0}

def test_evaluator_detects_false_negative_invalid_safety_and_inconsistency():
    values=copy.deepcopy(cases());target=next(c for c in values if c['id']=='suspected_theft');target['candidate'].update(classification='normal',risk='low',score=5,human=False)
    calls={}
    def varying(case):
        result=decision_from_candidate(case);calls[case['id']]=calls.get(case['id'],0)+1
        if case['id']=='normal_parked' and calls[case['id']]==2:result['confidence']=.5
        return result
    report=evaluate_cases(values,varying,3)
    assert not report['passed'] and report['confusion']['fn']>=1 and report['metrics']['consistency_rate']<1
