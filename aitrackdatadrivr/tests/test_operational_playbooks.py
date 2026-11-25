from scripts.validate_operational_playbooks import run_scenarios


def test_all_deterministic_operational_playbooks_pass_without_external_side_effects():
    result = run_scenarios()
    assert result['passed'] is True
    assert len(result['scenarios']) == 8
    assert all(item['passed'] for item in result['scenarios'])
    assert result['side_effects'] == {
        'external_message_deliveries': 0,
        'voice_calls': 0,
        'physical_commands': 0,
    }
