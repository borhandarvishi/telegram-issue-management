def test_bot_modules_import():
    import issuebot.app  # noqa: F401
    import issuebot.handlers.channel  # noqa: F401
    import issuebot.handlers.private  # noqa: F401
    import issuebot.handlers.screens  # noqa: F401
