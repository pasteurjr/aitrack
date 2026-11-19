#!/usr/bin/env python3
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from server.agent_evaluation import decision_from_candidate,evaluate_cases
dataset=json.loads((root/'evaluation'/'agent_cases_v1.json').read_text(encoding='utf-8'))
report=evaluate_cases(dataset['cases'],decision_from_candidate,3)
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['passed'] else 1)
