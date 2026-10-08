from issuebot.constants import Status
from issuebot.services.rules import capabilities, except_actor, note_recipients


def test_open_issue_assignee_can_resolve_but_not_confirm():
    caps = capabilities(
        status=Status.OPEN,
        is_owner=False,
        is_reporter=False,
        is_assignee=True,
        is_member=True,
        has_post=True,
    )
    assert caps.resolve
    assert not caps.confirm
    assert caps.note
    assert caps.reassign


def test_reporter_confirms_only_after_resolve():
    waiting = capabilities(
        status=Status.RESOLVED,
        is_owner=False,
        is_reporter=True,
        is_assignee=False,
        is_member=True,
        has_post=True,
    )
    assert waiting.confirm
    assert waiting.reopen
    assert not waiting.resolve


def test_owner_can_resolve_unassigned_open_issue():
    caps = capabilities(
        status=Status.OPEN,
        is_owner=True,
        is_reporter=False,
        is_assignee=False,
        is_member=True,
        has_post=False,
    )
    assert caps.resolve
    assert caps.publish


def test_outsider_can_do_nothing():
    caps = capabilities(
        status=Status.OPEN,
        is_owner=False,
        is_reporter=False,
        is_assignee=False,
        is_member=False,
        has_post=False,
    )
    assert caps == type(caps)()


def test_notifications_skip_the_actor():
    assert except_actor([1, 2, 2, 3], 2) == [1, 3]
    assert note_recipients(reporter_id=1, assignee_ids=[2, 3], actor_id=1) == [2, 3]
