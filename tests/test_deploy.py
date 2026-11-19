"""Das Hilfsskript, das den Blueprint zum Ausprobieren in Home Assistant spielt."""

from __future__ import annotations

import importlib.util

import pytest

from conftest import REPO

_spec = importlib.util.spec_from_file_location("ha_deploy", REPO / "scripts" / "ha_deploy.py")
ha_deploy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ha_deploy)


@pytest.mark.parametrize(
    "ziel,scp",
    [
        ("root@homeassistant.local:/config/blueprints/automation/wled_matrix/", True),
        ("root@192.168.1.10:/homeassistant/blueprints/", True),
        (r"\\homeassistant.local\config\blueprints\automation\wled_matrix", False),
        (r"C:\Users\ich\ha-config\blueprints", False),
        ("/Volumes/config/blueprints/automation/wled_matrix", False),
    ],
)
def test_scp_ziel_wird_erkannt(ziel, scp):
    """Ein Windows-Laufwerk wie C:\\ darf nicht für ein scp-Ziel gehalten werden."""
    assert ha_deploy.ist_scp_ziel(ziel) is scp


def test_env_datei(tmp_path):
    datei = tmp_path / ".ha.env"
    datei.write_text(
        '# Kommentar\n\nHA_URL="http://ha:8123"\nHA_TOKEN = abc\nkaputt\n', encoding="utf-8"
    )
    assert ha_deploy.lies_env_datei(datei) == {"HA_URL": "http://ha:8123", "HA_TOKEN": "abc"}


def test_umgebung_hat_vorrang(tmp_path, monkeypatch):
    datei = tmp_path / ".ha.env"
    datei.write_text("HA_URL=http://alt\nHA_TOKEN=aus-datei\n", encoding="utf-8")
    monkeypatch.setattr(ha_deploy, "ENV_DATEI", datei)
    cfg = ha_deploy.einstellungen({"HA_URL": "http://neu"})
    assert cfg == {"HA_URL": "http://neu", "HA_TOKEN": "aus-datei"}


def test_trocken_kopiert_nichts(tmp_path, capsys):
    ha_deploy.kopieren(str(tmp_path), trocken=True)
    assert not list(tmp_path.iterdir())
    assert "copy ->" in capsys.readouterr().out


def test_kopiert_den_blueprint(tmp_path):
    ha_deploy.kopieren(str(tmp_path), trocken=False)
    kopie = tmp_path / ha_deploy.BLUEPRINT.name
    assert kopie.read_bytes() == ha_deploy.BLUEPRINT.read_bytes()


def test_env_datei_ist_ignoriert():
    """Die Datei enthält den Zugriffstoken und darf nie eingecheckt werden."""
    assert ".ha.env" in (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
