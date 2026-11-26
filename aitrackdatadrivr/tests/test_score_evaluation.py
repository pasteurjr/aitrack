from server.score_evaluation import evaluate_score_dataset, score_band, wilson_interval


def test_score_bands_match_interface_ranges():
    assert score_band(75) == 'safe'
    assert score_band(74.9) == 'attention'
    assert score_band(50) == 'attention'
    assert score_band(49.9) == 'critical'


def test_versioned_dataset_proves_formula_and_documents_false_negatives():
    report = evaluate_score_dataset()
    assert report['case_count'] == 17
    assert report['metrics']['max_absolute_score_error'] == 0
    assert report['confusion'] == {'tp': 3, 'fp': 0, 'fn': 7, 'tn': 7}
    assert report['metrics']['false_positive_rate'] == 0
    assert report['metrics']['false_negative_rate'] == 0.7
    assert report['metrics']['positive_cases'] == 10
    assert report['metrics']['negative_cases'] == 7
    assert report['metrics']['false_negative_rate_ci95'] == [0.3968, 0.8922]
    assert set(report['group_metrics']) == {'tracker', 'dirijabem'}
    assert report['group_metrics']['tracker']['false_negative_rate'] == 0.75
    assert report['group_metrics']['tracker']['positive_cases'] == 4
    assert report['group_metrics']['dirijabem']['false_negative_rate'] == 2 / 3
    assert report['dataset_kind'] == 'synthetic_golden_cases_not_real_world_performance_evidence'
    assert report['schema_version'] == 'behavior-score-evaluation.v2'
    assert report['blocked_autonomy_classes'] == ['harsh_brake', 'mixed', 'speeding']
    assert report['passed'] is False
    assert report['operational_recommendation'] == 'do_not_use_score_as_sole_trigger'


def test_evaluation_reports_class_severity_context_and_wilson_intervals():
    report = evaluate_score_dataset()
    assert {'source', 'event_class', 'severity', 'context'} == set(report['stratified_metrics'])
    assert {'harsh_brake', 'speeding', 'mixed', 'no_event'} <= set(report['stratified_metrics']['event_class'])
    assert {'high', 'critical', 'none'} <= set(report['stratified_metrics']['severity'])
    assert {'urban', 'highway', 'mixed', 'unknown'} <= set(report['stratified_metrics']['context'])
    for dimension in report['stratified_metrics'].values():
        for metrics in dimension.values():
            if metrics['positive_cases']:
                assert metrics['false_negative_rate_ci95'] is not None
            if metrics['negative_cases']:
                assert metrics['false_positive_rate_ci95'] is not None
    assert wilson_interval(0, 0) is None


def test_duplicate_episode_and_window_boundaries_are_explicit():
    report = evaluate_score_dataset()
    by_id = {result['id']: result for result in report['results']}
    assert by_id['S11']['actual_score'] == 95.5
    assert by_id['S16']['actual_score'] == 95.5
    assert by_id['S17']['actual_score'] == 100.0
