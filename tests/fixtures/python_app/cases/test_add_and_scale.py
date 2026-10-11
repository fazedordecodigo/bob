from app.safe import add, scale


def test_add() -> None:
    assert add(1, 2) == 3


def test_scale() -> None:
    assert scale(3) == 6
