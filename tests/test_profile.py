from issuebot.profile import PHOTO_NAME, profile_photo_path


def test_default_photo_is_present() -> None:
    path = profile_photo_path()
    assert path is not None
    assert path.name == PHOTO_NAME
    assert path.is_file()
