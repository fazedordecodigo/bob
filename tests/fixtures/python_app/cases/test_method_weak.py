from app.gauge import Gauge


def test_classify() -> None:
    assert Gauge().classify(1) == "pos"
