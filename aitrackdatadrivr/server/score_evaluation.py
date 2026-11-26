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


def wilson_interval(successes, total, z=1.959963984540054):
    """Intervalo de Wilson de 95%; retorna None quando não há observações."""
    if total == 0:
        return None
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * ((proportion * (1 - proportion) / total + z * z / (4 * total * total)) ** 0.5) / denominator
    return [round(max(0.0, center - margin), 4), round(min(1.0, center + margin), 4)]


def _group_key(case, dimension):
    if dimension == 'source':
        return case['source']
    return case['labels'][dimension]


def _metrics(counts):
    positives = counts['tp'] + counts['fn']
    negatives = counts['fp'] + counts['tn']
    false_negatives = counts['fn']
    false_positives = counts['fp']
    return {
        **counts,
        'positive_cases': positives,
        'negative_cases': negatives,
        'false_negative_rate': false_negatives / positives if positives else None,
        'false_negative_rate_ci95': wilson_interval(false_negatives, positives),
        'false_positive_rate': false_positives / negatives if negatives else None,
        'false_positive_rate_ci95': wilson_interval(false_positives, negatives),
    }


def evaluate_score_dataset(dataset_path=DATASET):
    dataset = json.loads(Path(dataset_path).read_text(encoding='utf-8'))
    reference = datetime.fromisoformat(dataset['reference_time'])
    threshold = float(dataset['intervention_threshold'])
    results = []
    confusion = {'tp': 0, 'fp': 0, 'fn': 0, 'tn': 0}
    absolute_errors = []
    group_counts = {dimension: {} for dimension in ('source', 'event_class', 'severity', 'context')}
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
        for dimension, groups in group_counts.items():
            group = groups.setdefault(_group_key(case, dimension), {'tp': 0, 'fp': 0, 'fn': 0, 'tn': 0})
            group[key] += 1
        results.append({
            'id': case['id'], 'source': case['source'], 'profile': case['profile'],
            'expected_score': expected, 'actual_score': actual, 'score_error': error,
            'band': score_band(actual), 'requires_intervention': expected_intervention,
            'predicted_intervention': predicted, 'outcome': key,
        })

    metrics = {
        'mean_absolute_score_error': sum(absolute_errors) / len(absolute_errors),
        'max_absolute_score_error': max(absolute_errors),
        **{key: value for key, value in _metrics(confusion).items() if key not in confusion},
    }
    stratified_metrics = {
        dimension: {label: _metrics(counts) for label, counts in groups.items()}
        for dimension, groups in group_counts.items()
    }
    # Preserve the existing source-keyed API field for current clients.
    group_metrics = stratified_metrics['source']
    blocked_autonomy_classes = sorted({
        case['labels']['event_class']
        for case, result in zip(dataset['cases'], results)
        if case['labels']['severity'] in {'high', 'critical'}
        and result['requires_intervention']
        and not result['predicted_intervention']
    })
    passed = metrics['max_absolute_score_error'] == 0 and metrics['false_negative_rate'] <= 0.10 and metrics['false_positive_rate'] <= 0.10
    return {
        'schema_version': 'behavior-score-evaluation.v2',
        'dataset_version': dataset['schema_version'],
        'dataset_kind': dataset.get('dataset_kind', 'unspecified'),
        'limitations': dataset.get('limitations', []),
        'case_count': len(results),
        'intervention_threshold': threshold,
        'confusion': confusion,
        'metrics': metrics,
        'group_metrics': group_metrics,
        'stratified_metrics': stratified_metrics,
        'blocked_autonomy_classes': blocked_autonomy_classes,
        'passed': passed,
        'operational_recommendation': 'eligible_as_sole_trigger' if passed else 'do_not_use_score_as_sole_trigger',
        'results': results,
    }
