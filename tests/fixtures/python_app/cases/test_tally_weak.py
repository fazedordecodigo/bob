from app.tally import tally


def test_tally() -> None:
    assert tally(-1, 3) == 2
