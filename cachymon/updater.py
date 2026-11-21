"""CachyMonitor : mises à jour (voir cachymonitor.py).

Deux cas :
  - paquet AUR : la version du paquet AUR est comparée à la version en cours ;
    l'installation passe par l'assistant AUR (yay ou paru), avec pkexec pour le mot
    de passe.
  - lancé depuis les sources : on prévient seulement qu'une version existe et on
    ouvre la page de la release.

Rien ici ne touche à l'interface : l'objet Updater émet des signaux, la barre
(update_bar.py) les affiche.
"""

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import urllib.request

from PySide6.QtCore import QObject, Signal

from cachymon.debug import debug_exc, debug_msg


REPO = "YOUNES-2-wq/cachymonitor-linux"
GITHUB_API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASE_PAGE = f"https://github.com/{REPO}/releases/latest"
AUR_API = "https://aur.archlinux.org/rpc/v5/info?arg[]=cachymonitor"
AUR_PACKAGE = "cachymonitor"
# Nom générique : aucune information sur l'utilisateur n'est envoyée.
USER_AGENT = "CachyMonitor-updater"
NET_TIMEOUT = 10
INSTALL_TIMEOUT = 20 * 60   # secondes : au-delà, l'installation est abandonnée

# Genres de mise à jour (champ « kind » de ce que renvoie check_update).
KIND_AUR = "aur"           # paquet AUR installé par un assistant
KIND_PAGE = "page"         # rien d'automatique : ouvrir la page de la release

# Résultats d'une installation (second argument du signal « done »).
OK, FAILED, NO_HELPER = "ok", "failed", "no-helper"


# ----------------------------------------------------------------------------- #
#  Logique pure (testée dans tests/test_updater.py)
# ----------------------------------------------------------------------------- #

def parse_version(text):
    """'v1.5.2' ou '1.5.2-1' (version AUR, éventuellement '1:1.5.2-1') -> (1, 5, 2) ;
    () si illisible. Un suffixe comme 'rc1' est ignoré."""
    base = str(text).strip().split("-")[0].split(":")[-1]
    m = re.match(r"v?(\d+(?:\.\d+)*)", base)
    return tuple(int(n) for n in m.group(1).split(".")) if m else ()


def is_newer(candidate, current):
    """Vrai si « candidate » est strictement plus récente que « current »."""
    a, b = parse_version(candidate), parse_version(current)
    if not a or not b:
        return False
    size = max(len(a), len(b))      # (1, 8) et (1, 8, 0) sont la même version
    a += (0,) * (size - len(a))
    b += (0,) * (size - len(b))
    return a > b


def display_version(text):
    """'1:1.5.4-1' (version AUR avec epoch et pkgrel) -> '1.5.4' pour l'affichage."""
    return str(text).strip().split("-")[0].split(":")[-1]


def aur_helper():
    """Premier assistant AUR disponible (yay ou paru), ou None."""
    for name in ("yay", "paru"):
        if shutil.which(name):
            return name
    return None


def installed_from_package():
    """Vrai si l'application qui tourne vient du paquet pacman (et non des sources)."""
    if not shutil.which("pacman"):
        return False
    try:
        # -q : n'affiche que le nom du paquet propriétaire (pas le chemin).
        r = subprocess.run(["pacman", "-Qoq", os.path.abspath(sys.argv[0])],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0 and r.stdout.strip() == AUR_PACKAGE


def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=NET_TIMEOUT) as r:
        return json.load(r)


def check_update(current):
    """Dictionnaire décrivant la mise à jour disponible, ou None s'il n'y en a pas.
    Lève une exception si le réseau est indisponible (l'appelant l'ignore)."""
    if installed_from_package():
        # La référence est le paquet AUR, pas GitHub : une release GitHub n'est
        # installable qu'une fois le paquet AUR mis à jour.
        results = _get_json(AUR_API).get("results") or []
        version = str(results[0].get("Version", "")) if results else ""
        if is_newer(version, current):
            return {"kind": KIND_AUR, "version": display_version(version)}
        return None
    rel = _get_json(GITHUB_API)
    version = str(rel.get("tag_name", ""))
    if is_newer(version, current):
        return {"kind": KIND_PAGE, "version": version.lstrip("v")}
    return None


# ----------------------------------------------------------------------------- #
#  Installation (dans un fil à part, jamais dans l'interface)
# ----------------------------------------------------------------------------- #

def _installed_aur_version():
    try:
        out = subprocess.run(["pacman", "-Q", AUR_PACKAGE], capture_output=True,
                             text=True, timeout=5).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return ""
    return out[1] if len(out) > 1 else ""


def _kill_group(proc, wait=True):
    """Arrête l'assistant et tout ce qu'il a lancé (makepkg, pkexec, pacman)."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        if not wait:
            return           # fermeture de la fenêtre : on ne bloque pas l'interface
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        proc.wait()
    except (ProcessLookupError, PermissionError):
        proc.kill()
        proc.wait()


def _run_aur(info, helper, on_start=None):
    cmd = [helper, "-S", "--noconfirm", "--sudo", "pkexec", AUR_PACKAGE]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, text=True, errors="replace",
                            env={**os.environ, "LC_ALL": "C"},
                            start_new_session=True)   # groupe à part : on peut tout arrêter
    if on_start:
        on_start(proc)
    tail = []        # les 8 dernières lignes de sortie, pour le journal --debug

    def read():
        for line in proc.stdout:
            tail.append(line.rstrip())
            del tail[:-8]

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    try:
        proc.wait(timeout=INSTALL_TIMEOUT)
    except subprocess.TimeoutExpired:
        # Par exemple pkexec sans fenêtre de mot de passe : on abandonne.
        _kill_group(proc)
        reader.join(timeout=2)
        debug_msg("mise à jour AUR : délai dépassé", "\n".join(tail))
        return FAILED
    reader.join(timeout=2)
    if proc.returncode != 0:
        debug_msg(f"mise à jour AUR : code {proc.returncode}", "\n".join(tail))
        return FAILED
    # « Rien à faire » renvoie aussi 0 : on vérifie que la version a bien changé.
    installed = _installed_aur_version()
    if not parse_version(installed) or is_newer(info["version"], installed):
        debug_msg("mise à jour AUR : version non changée", f"installée : {installed!r}")
        return FAILED
    return OK


class Updater(QObject):
    """Vérifie et installe. Les signaux partent de fils à part : Qt les remet
    dans le fil de l'interface."""

    found = Signal(object)       # dict de check_update, ou None s'il n'y a rien de neuf
    done = Signal(str)           # OK, FAILED ou NO_HELPER

    def __init__(self, current_version):
        super().__init__()
        self.current = current_version
        self.busy = False
        self._proc = None
        self._cancelled = False

    def check(self):
        """Vérification en arrière-plan ; silencieuse si le réseau manque."""
        def work():
            try:
                info = check_update(self.current)
            except Exception:
                debug_exc("vérification de mise à jour")
                return
            self.found.emit(info)      # None : rien de neuf (efface une barre devenue périmée)
        threading.Thread(target=work, daemon=True).start()

    def _set_proc(self, proc):
        self._proc = proc
        if self._cancelled:          # fermeture pendant le lancement : on arrête tout de suite
            _kill_group(proc, wait=False)

    def cancel(self):
        """Arrête l'installation en cours (appelé à la fermeture de la fenêtre)."""
        self._cancelled = True       # une installation qui n'a pas encore démarré ne démarrera pas
        proc = self._proc
        if proc is not None and proc.poll() is None:
            _kill_group(proc, wait=False)

    def install(self, info):
        if self.busy:
            return
        self.busy = True
        threading.Thread(target=self._install, args=(info,), daemon=True).start()

    def _install(self, info):
        result = FAILED
        try:
            if info["kind"] == KIND_AUR:
                helper = aur_helper()
                if helper is None:
                    result = NO_HELPER
                elif not self._cancelled:
                    result = _run_aur(info, helper, on_start=self._set_proc)
        except Exception:
            debug_exc("installation de la mise à jour")
            result = FAILED
        # « busy » est remis à False par la barre, dans le fil de l'interface, une
        # fois le résultat traité (voir UpdateBar._done).
        self.done.emit(result)
