"""Avaliação reproduzível da fórmula de score comportamental."""

from datetime import datetime, timedelta
import json
from pathlib import Path

from .behavioral_engine import calculate_score_from_events


DATASET = Path(__file__).resolve().parents[1] / 'evaluation' / 'score_cases_v1.json'


def score_band(score):
    if score >= 75:
        return 'safe'
    if score >= 50:
        return 'attention'
    return 'critical'


def evaluate_score_dataset(dataset_path=DATASET):
    dataset = json.loads(Path(dataset_path).read_text(encoding='utf-8'))
    reference = datetime.fromisoformat(dataset['reference_time'])
    threshold = float(dataset['intervention_threshold'])
    results = []
    confusion = {'tp': 0, 'fp': 0, 'fn': 0, 'tn': 0}
    absolute_errors = []
    group_counts = {}
    for case in dataset['cases']:
        events = []
        for index, raw in enumerate(case['events']):
            event = dict(raw)
            event['timestamp'] = (reference - timedelta(seconds=raw['age_seconds'])).isoformat()
            event.setdefault('episode_id', f"{case['id']}:{index}")
            events.append(event)
        actual = calculate_score_from_events(events, now=reference)
        expected = float(case['expected_score'])
        error = round(actual - expected, 4)
        absolute_errors.append(abs(error))
        predicted = actual < threshold
        expected_intervention = bool(case['requires_intervention'])
        key = 'tp' if predicted and expected_intervention else 'fp' if predicted else 'fn' if expected_intervention else 'tn'
        confusion[key] += 1
        group = group_counts.setdefault(case['source'], {'tp': 0, 'fp': 0, 'fn': 0, 'tn': 0})
        group[key] += 1
        results.append({
            'id': case['id'], 'source': case['source'], 'profile': case['profile'],
            'expected_score': expected, 'actual_score': actual, 'score_error': error,
            'band': score_band(actual), 'requires_intervention': expected_intervention,
            'predicted_intervention': predicted, 'outcome': key,
        })

    def rates(values):
        positive = values['tp'] + values['fn']
        negative = values['fp'] + values['tn']
        return {
            'false_negative_rate': values['fn'] / positive if positive else 0.0,
            'false_positive_rate': values['fp'] / negative if negative else 0.0,
        }

    metrics = {
        'mean_absolute_score_error': sum(absolute_errors) / len(absolute_errors),
        'max_absolute_score_error': max(absolute_errors),
        **rates(confusion),
    }
    group_metrics = {source: {**counts, **rates(counts)} for source, counts in group_counts.items()}
    passed = metrics['max_absolute_score_error'] == 0 and metrics['false_negative_rate'] <= 0.10 and metrics['false_positive_rate'] <= 0.10
    return {
        'schema_version': 'behavior-score-evaluation.v1',
        'dataset_version': dataset['schema_version'],
        'case_count': len(results),
        'intervention_threshold': threshold,
        'confusion': confusion,
        'metrics': metrics,
        'group_metrics': group_metrics,
        'passed': passed,
        'operational_recommendation': 'eligible_as_sole_trigger' if passed else 'do_not_use_score_as_sole_trigger',
        'results': results,
    }
