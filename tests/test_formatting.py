from datetime import UTC, datetime

from issuebot.constants import BUTTON_LIMIT, Status
from issuebot.formatting import (
    IssueCard,
    NoteLine,
    channel_card,
    channel_delivery,
    detail_card,
    format_person,
    issue_button,
    link,
    linkify,
    unique_labels,
)


def _card(**overrides) -> IssueCard:
    base = dict(
        number=12,
        project="Shop",
        title="Login fails",
        description="After the password, the page stays blank.\nhttps://example.com/login",
        status=Status.OPEN,
        reporter="@sara (Sara Ahmadi)",
        assignees=("@ali (Ali Rezaei)",),
        notes=(),
        timeline=("Filed by @sara (Sara Ahmadi)",),
        created_at=datetime(2026, 10, 8, 19, 11, tzinfo=UTC),
        photo_count=0,
    )
    base.update(overrides)
    return IssueCard(**base)


def test_person_with_username():
    assert format_person("ali", "Ali", "Rezaei") == "@ali (Ali Rezaei)"


def test_person_without_username_hides_numeric_id():
    assert format_person(None, "Sara", "Ahmadi") == "Sara Ahmadi"
    assert "123" not in format_person(None, "Sara", None)


def test_person_strips_duplicate_at():
    assert format_person("@ali", "Ali", None) == "@ali (Ali)"


def test_channel_card_puts_number_at_the_end_and_names_people():
    text = channel_card(_card())
    assert text.startswith("🔴 <b>ISSUE #12</b>")
    assert text.strip().endswith("#12")
    assert "<b>Reporter</b>" in text
    assert "@sara (Sara Ahmadi)" in text
    assert "<b>Assignees</b>" in text
    assert "@ali (Ali Rezaei)" in text
    assert "<blockquote>" in text
    assert "────────────\n<b>Login fails</b>" in text
    assert "────────────\n<b>Reporter</b>" in text
    assert "────────────\n<b>Assignees</b>" in text
    assert "────────────\n#12" in text
    assert "8 Oct 2026" in text
    assert "19:11" not in text
    assert "UTC" not in text
    assert "https://example.com/login" in text


def test_resolved_and_confirmed_status_lines():
    resolved = channel_card(_card(status=Status.RESOLVED, solver="@ali (Ali Rezaei)"))
    assert "Resolved by @ali (Ali Rezaei)" in resolved
    assert resolved.strip().endswith("#12")
    confirmed = channel_card(_card(status=Status.CONFIRMED, confirmer="@sara (Sara Ahmadi)"))
    assert "Confirmed by @sara (Sara Ahmadi)" in confirmed
    assert confirmed.strip().endswith("#12")


def test_user_html_is_escaped():
    text = channel_card(_card(title="<b>x</b>"))
    assert "<b>x</b>" not in text
    assert "&lt;b&gt;x&lt;/b&gt;" in text


def test_detail_includes_timeline_and_notes():
    text = detail_card(
        _card(notes=(NoteLine("@ali (Ali Rezaei)", "Cleared the cache"),), photo_count=2)
    )
    assert "Notes" in text
    assert "Cleared the cache" in text
    assert "History" in text
    assert "<b>Photos</b>" in text
    assert "2 photos" in text


def test_delivery_keeps_photos_and_text_in_one_post():
    assert channel_delivery("hello", 0) == "text"
    assert channel_delivery("hello", 1) == "photo"
    assert channel_delivery("x" * 2000, 1) == "photo"
    assert channel_delivery("hello", 3) == "album"


def test_urls_in_the_card_are_clickable():
    text = channel_card(_card(description="See https://example.com/report."))
    assert '<a href="https://example.com/report">https://example.com/report</a>' in text
    assert link("https://t.me/+abc") == '<a href="https://t.me/+abc">https://t.me/+abc</a>'
    assert "<a" not in linkify("not a link")
    assert "<a" not in link("javascript:alert(1)")


def test_status_colors():
    assert channel_card(_card()).startswith("🔴")
    assert channel_card(_card(urgent=True)).startswith("🔴⚠️")
    assert channel_card(_card(reopened=True)).startswith("🟡")
    resolved = channel_card(_card(status=Status.RESOLVED, solver="@ali (Ali)"))
    assert resolved.startswith("🟤")
    confirmed = channel_card(_card(status=Status.CONFIRMED, confirmer="@sara (Sara)"))
    assert confirmed.startswith("🟢")
    card = channel_card(_card())
    assert "👤 @ali (Ali Rezaei)" in card
    assert "👤 @sara (Sara Ahmadi)" in card


def test_buttons_stay_within_telegram_limit():
    label = issue_button(12, "A very long title " * 20, "A long project name")
    assert len(label) <= BUTTON_LIMIT
    assert label.startswith("ISSUE #12")
    labels = unique_labels([("ISSUE #1", 1), ("ISSUE #1", 2)])
    assert len(labels) == 2
    assert all(len(item) <= BUTTON_LIMIT for item in labels)
