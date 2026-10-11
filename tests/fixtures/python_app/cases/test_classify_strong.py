from app.weak import classify


def test_classify_positive() -> None:
    assert classify(1) == "pos"


def test_classify_zero() -> None:
    assert classify(0) == "nonpos"


def test_classify_negative() -> None:
    assert classify(-1) == "nonpos"
