from server.score_evaluation import evaluate_score_dataset, score_band


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
    assert set(report['group_metrics']) == {'tracker', 'dirijabem'}
    assert report['passed'] is False
    assert report['operational_recommendation'] == 'do_not_use_score_as_sole_trigger'


def test_duplicate_episode_and_window_boundaries_are_explicit():
    report = evaluate_score_dataset()
    by_id = {result['id']: result for result in report['results']}
    assert by_id['S11']['actual_score'] == 95.5
    assert by_id['S16']['actual_score'] == 95.5
    assert by_id['S17']['actual_score'] == 100.0
