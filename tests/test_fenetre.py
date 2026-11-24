"""Fenêtre principale hors écran : le fond reste plein quand on quitte la transparence."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CACHYMONITOR_NO_ELEVATE", "1")


@pytest.fixture(scope="module")
def fenetre():
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QStandardPaths
    from PySide6.QtWidgets import QApplication
    # Mode test de Qt : les réglages vont dans un dossier à part, jamais dans les vrais.
    QStandardPaths.setTestModeEnabled(True)
    app = QApplication.instance() or QApplication([])
    import cachymonitor as cm
    win = cm.MainWindow()
    win.sampler.stop()
    win.sampler.sampled.disconnect()
    win.update_bar.check = lambda *a, **k: None
    win.show()
    yield cm, win
    win.sampler.stop()
    win.hide()
    del app


def _pixel_du_coin(win):
    return win.grab().toImage().pixelColor(2, 2)


def test_fond_plein_apres_transparence(fenetre):
    # Défaut corrigé en 1.6.0 : activer puis retirer la transparence laissait la
    # fenêtre sans fond, y compris avec un thème normal (le bureau se voyait derrière).
    cm, win = fenetre
    win.theme.setCurrentIndex(cm.THEME_MODES.index("claude"))
    win.transparent.setChecked(True)
    win.transparent.setChecked(False)
    win.theme.setCurrentIndex(cm.THEME_MODES.index("gruvbox"))
    assert _pixel_du_coin(win).alpha() == 255


def test_fond_plein_pour_chaque_theme(fenetre):
    cm, win = fenetre
    for mode in cm.THEME_MODES[1:]:
        win.theme.setCurrentIndex(cm.THEME_MODES.index(mode))
        assert _pixel_du_coin(win).alpha() == 255, mode


def test_dialogues_opaques_avec_le_theme_claude(fenetre):
    # Le fond transparent du thème Claude ne doit pas vider les boîtes de dialogue.
    cm, win = fenetre
    from PySide6.QtWidgets import QMessageBox
    win.theme.setCurrentIndex(cm.THEME_MODES.index("claude"))
    box = QMessageBox(win)
    box.setText("test")
    box.show()
    assert box.grab().toImage().pixelColor(6, 6).alpha() == 255
    box.close()
