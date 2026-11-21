"""CachyMonitor : journal de debogage (voir cachymonitor.py).

Beaucoup de lecteurs de capteurs avalent leurs erreurs a dessein : un capteur
exotique ne doit jamais faire tomber l'application. Revers de la medaille, quand
quelque chose ne s'affiche pas sur une machine qu'on ne possede pas, rien ne dit
pourquoi. Avec l'option --debug (ou la variable CACHYMONITOR_DEBUG=1), chaque
erreur avalee est ecrite, une seule fois, dans un fichier a joindre a une issue.

Sans l'option, ce module ne fait strictement rien.
"""

import os
import sys
import threading
import time
import traceback

_enabled = None
_seen = set()
_started = []
# Le thread de mesure et la fenêtre écrivent tous deux : une seule écriture à
# la fois, sinon deux « premières » écritures videraient le fichier tour à tour.
_write_lock = threading.Lock()


def log_path():
    """Fichier du journal, dans le dossier de cache de l'utilisateur."""
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, "cachymonitor", "debug.log")


_log_path_cell = []


def _log_path_once():
    """log_path() calculé une seule fois : il ne change pas pendant la vie du process."""
    if not _log_path_cell:
        _log_path_cell.append(log_path())
    return _log_path_cell[0]


def enabled():
    global _enabled
    if _enabled is None:
        _enabled = ("--debug" in sys.argv
                    or os.environ.get("CACHYMONITOR_DEBUG", "") not in ("", "0"))
    return _enabled


def debug_exc(context):
    """A appeler dans un `except` : note l'erreur en cours (une fois par cause)."""
    if not enabled():
        return
    # Sans le texte du message : il varie (chemins, adresses) et ferait
    # grossir le journal sans fin sur une erreur qui se repete 10 fois par seconde.
    # La trace n'est mise en forme qu'apres ce tri (fonction passee a _write).
    _write((context, sys.exc_info()[0]), context, traceback.format_exc)


def debug_msg(context, text):
    """Note un message sans exception en cours (une fois par texte)."""
    if enabled():
        _write((context, text), context, lambda: text + "\n")


def _write(key, context, make_body):
    with _write_lock:
        _write_locked(key, context, make_body)


def _write_locked(key, context, make_body):
    try:
        if key in _seen:
            return
        _seen.add(key)
        entry = "[%s] %s\n%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), context, make_body())
        path = _log_path_once()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Premiere ecriture de cette session : on repart d'un fichier neuf, pour que
        # le journal joint a une issue ne melange pas plusieurs lancements.
        mode = "a" if _started else "w"
        _started.append(True)
        with open(path, mode, encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass            # le journal ne doit jamais, lui non plus, faire tomber l'appli
