"""Deriva proveniência verificável dos campos estruturados da decisão."""

import hashlib
import json
from typing import Dict

from .agent_decision_schema import validate_decision


def canonical_json(value) -> str:
    return json.dumps(value,ensure_ascii=False,separators=(',',':'),sort_keys=True)


def sha256_json(value) -> str:
    return hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()


def build_provenance(decision: Dict, context: Dict) -> Dict:
    decision=validate_decision(decision)
    if not isinstance(context,dict):raise ValueError('context deve ser objeto JSON')
    evidence=[]
    for ordinal,item in enumerate(decision['evidence']):
        evidence.append({
            'ordinal':ordinal,'source_code':item['source'],
            'evidence_type':item['type'],'evidence_ref':item['ref'],
            'summary':item['summary'],'observed_at':item.get('observed_at'),
            'content_sha256':sha256_json(item),
        })
    manifest_hash=sha256_json([item['content_sha256'] for item in evidence])
    return {
        'classification':decision['classification'],'confidence':decision['confidence'],
        'risk_level':decision['risk']['level'],'risk_score':decision['risk']['score'],
        'context_sha256':sha256_json(context),
        'evidence_manifest_sha256':manifest_hash,'evidence_count':len(evidence),
        'evidence':evidence,
    }
