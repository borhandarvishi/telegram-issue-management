from issuebot.services.linking import parse_channel_ref


def test_public_channel_refs():
    assert parse_channel_ref("@shop") == "@shop"
    assert parse_channel_ref("https://t.me/shop") == "@shop"
    assert parse_channel_ref("t.me/shop/12") == "@shop"


def test_private_invite_links_are_not_readable():
    assert parse_channel_ref("https://t.me/+AbCdEf") == "private"
    assert parse_channel_ref("https://t.me/joinchat/AbCdEf") == "private"


def test_plain_text_is_not_a_channel():
    assert parse_channel_ref("Shop") is None
