from server.action_queue_db import _action_summary


def test_action_timeline_summaries_cover_operational_flow_in_portuguese():
    assert _action_summary('action','claim','approved','claimed') == 'Execução iniciada (approved → claimed)'
    assert _action_summary('provider','delivered') == 'Provedor confirmou entrega'
    assert _action_summary('provider','read') == 'Mensagem lida'
    assert _action_summary('provider','responded') == 'Destinatário respondeu'
    assert _action_summary('approval','approval_requested') == 'Aprovação humana solicitada'


def test_unknown_action_event_remains_visible_instead_of_being_dropped():
    assert _action_summary('provider','future_status') == 'Future status'
