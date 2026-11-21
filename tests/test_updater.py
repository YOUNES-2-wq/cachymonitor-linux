"""Mises à jour : comparaison de versions, détection du paquet, installation AUR."""
import time

from cachymon import updater


def test_versions():
    assert updater.parse_version("v1.5.2") == (1, 5, 2)
    assert updater.parse_version("1.5.2-1") == (1, 5, 2)
    assert updater.is_newer("1.10.0", "1.9.9")
    assert not updater.is_newer("1.5.2", "1.5.2")
    assert not updater.is_newer("", "1.5.2")


def test_versions_de_longueurs_differentes():
    assert not updater.is_newer("1.5", "1.5.0")
    assert not updater.is_newer("1.5.0", "1.5")
    assert updater.is_newer("1.5.1", "1.5")


def test_suffixe_et_epoch_ignores():
    assert updater.parse_version("1.5.4rc1") == (1, 5, 4)
    assert updater.parse_version("1:1.5.2-1") == (1, 5, 2)
    assert updater.display_version("1:1.5.4-1") == "1.5.4"


def test_depot_de_la_version_linux():
    assert updater.REPO == "YOUNES-2-wq/cachymonitor-linux"


def test_paquet_homonyme_non_reconnu(monkeypatch):
    class R:
        returncode = 0
        stdout = "cachymonitor-git\n"
    monkeypatch.setattr(updater.shutil, "which", lambda n: "/usr/bin/pacman")
    monkeypatch.setattr(updater.subprocess, "run", lambda *a, **k: R())
    assert not updater.installed_from_package()
    R.stdout = "cachymonitor\n"
    assert updater.installed_from_package()


def _fake_helper(monkeypatch, script):
    real_popen = updater.subprocess.Popen
    monkeypatch.setattr(updater.subprocess, "Popen",
                        lambda cmd, **kw: real_popen(["sh", "-c", script], **kw))


def test_installation_reussie(monkeypatch):
    _fake_helper(monkeypatch, "echo installing; exit 0")
    monkeypatch.setattr(updater, "_installed_aur_version", lambda: "1.5.4-1")
    assert updater._run_aur({"version": "1.5.4"}, "yay") == updater.OK


def test_installation_version_inchangee(monkeypatch):
    """Code 0 mais rien d'installé (« rien à faire ») : c'est un échec."""
    _fake_helper(monkeypatch, "exit 0")
    monkeypatch.setattr(updater, "_installed_aur_version", lambda: "1.5.3-1")
    assert updater._run_aur({"version": "1.5.4"}, "yay") == updater.FAILED
    monkeypatch.setattr(updater, "_installed_aur_version", lambda: "")
    assert updater._run_aur({"version": "1.5.4"}, "yay") == updater.FAILED


def test_installation_version_equivalente(monkeypatch):
    _fake_helper(monkeypatch, "exit 0")
    monkeypatch.setattr(updater, "_installed_aur_version", lambda: "1.5-1")
    assert updater._run_aur({"version": "1.5.0"}, "yay") == updater.OK


def test_installation_code_erreur(monkeypatch):
    _fake_helper(monkeypatch, "echo boom; exit 3")
    assert updater._run_aur({"version": "1.5.4"}, "yay") == updater.FAILED


def test_installation_abandonnee_apres_delai(monkeypatch):
    """Un assistant qui ne finit jamais est arrêté."""
    monkeypatch.setattr(updater, "INSTALL_TIMEOUT", 0.5)
    _fake_helper(monkeypatch, "sleep 30")
    assert updater._run_aur({"version": "9.9.9"}, "yay") == updater.FAILED


def test_annulation_a_la_fermeture(monkeypatch):
    import threading
    _fake_helper(monkeypatch, "sleep 30")
    holder = []
    t = threading.Thread(target=updater._run_aur,
                         args=({"version": "9.9.9"}, "yay", holder.append))
    t.start()
    deadline = time.monotonic() + 5
    while not holder and time.monotonic() < deadline:
        time.sleep(0.01)
    assert holder, "le processus n'a pas démarré"
    up = updater.Updater("1.0.0")
    up._set_proc(holder[0])
    up.cancel()
    t.join(timeout=5)
    assert not t.is_alive()
    assert holder[0].poll() is not None


def test_la_barre_ne_verifie_pas_pendant_une_installation(monkeypatch):
    from PySide6.QtWidgets import QApplication
    from cachymon import update_bar
    QApplication.instance() or QApplication([])
    bar = update_bar.UpdateBar("1.0.0")
    calls = []
    monkeypatch.setattr(bar.updater, "check", lambda: calls.append(1))
    bar.check()
    assert calls == [1]
    bar._state = "working"
    bar.check()
    bar._state = "error"
    bar.check()
    assert calls == [1]


def test_installation_non_lancee_si_fermeture_avant_le_depart(monkeypatch):
    called = []
    monkeypatch.setattr(updater, "aur_helper", lambda: "yay")
    monkeypatch.setattr(updater, "_run_aur", lambda *a, **k: called.append(1) or updater.OK)
    up = updater.Updater("1.0.0")
    results = []
    up.done.connect(results.append)
    up.cancel()                                    # la fenêtre se ferme tout de suite
    up._install({"kind": updater.KIND_AUR, "version": "9.9.9"})
    assert not called and results == [updater.FAILED]


def test_barre_effacee_quand_plus_rien_de_neuf():
    from PySide6.QtWidgets import QApplication
    from cachymon import update_bar
    QApplication.instance() or QApplication([])
    bar = update_bar.UpdateBar("1.0.0")
    bar._found({"kind": updater.KIND_AUR, "version": "2.0.0"})
    assert not bar.isHidden()
    bar._found(None)
    assert bar.isHidden()
    bar._state, bar.info = "error", {"kind": updater.KIND_AUR, "version": "2.0.0"}
    bar._found({"kind": updater.KIND_AUR, "version": "3.0.0"})
    assert bar._state == "error"                   # un résultat tardif n'efface pas l'erreur
