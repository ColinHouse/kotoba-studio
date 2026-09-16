import sys

from kotoba import spa


def test_default_dist_uses_meipass_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert spa.default_dist() == tmp_path / "frontend" / "dist"


def test_default_dist_points_at_the_repository_build(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert spa.default_dist().parts[-2:] == ("frontend", "dist")
