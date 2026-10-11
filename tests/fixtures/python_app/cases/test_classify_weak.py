from app.weak import classify


def test_classify() -> None:
    assert classify(1) == "pos"
