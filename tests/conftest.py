import os
import sys

# Les tests tournent sans ecran : Qt n'est de toute facon pas necessaire ici.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import pytest  # noqa: E402

from cachymon import debug  # noqa: E402


@pytest.fixture(autouse=True)
def journal_isole(tmp_path, monkeypatch):
    # Aucun test n'écrit dans le vrai journal de l'utilisateur
    # (~/.cache/cachymonitor/debug.log) : un test qui simule --debug
    # laissait le mode débogage actif (cache de enabled()) pour les suivants.
    # Chaque test repart d'un état neuf ; ceux qui en ont besoin le changent.
    monkeypatch.setattr(debug, "_enabled", False)
    monkeypatch.setattr(debug, "_seen", set())
    monkeypatch.setattr(debug, "_started", [])
    chemin = str(tmp_path / "debug.log")
    monkeypatch.setattr(debug, "_log_path_once", lambda: chemin)
