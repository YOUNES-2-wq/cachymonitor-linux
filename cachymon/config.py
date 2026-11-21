"""CachyMonitor : module config (voir cachymonitor.py)."""

import os



# Dossier qui contient cachymonitor.py (et les icônes) : un cran au-dessus de ce paquet.
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ----------------------------------------------------------------------------- #
#  Configuration
# ----------------------------------------------------------------------------- #

HISTORY = 120          # nombre d'échantillons gardés pour les graphes
GAME_HISTORY = 6000    # échantillons de jeu gardés (100 ms => ~10 min de jeu)
LOG_INTERVAL_MS = 100  # log_interval de MangoHud (repli si 'elapsed' absent du CSV)
GAME_WARMUP_S = 5.0    # début de session ignoré (lancement + 1er chargement)
GAME_WINDOW_S = 60.0   # fenêtre glissante sur laquelle les « lows » sont calculés
# Une image qui dure plus d'une seconde n'est pas une saccade de jeu : c'est le
# jeu suspendu (alt-tab, pause, chargement). On l'écarte des statistiques, sinon
# elle écrase à elle seule le 0.1% low. Seuil volontairement très conservateur :
# une vraie saccade ressentie reste bien au-dessus de 1 fps.
FREEZE_IGNORE_MS = 1000.0
DEFAULT_INTERVAL_MS = 1000
DEFAULT_FPS_TARGET = 165   # sert d'échelle aux jauges FPS (= fps_limit MangoHud)

# Dossiers où chercher les logs CSV de MangoHud (le plus récent est utilisé).
FPS_LOG_DIRS = [
    os.path.expanduser("~/.local/share/MangoHud/logs"),
    os.path.expanduser("~/mangohud"),
    os.path.expanduser("~/.local/share/MangoHud"),
    os.path.expanduser("~/.local/share/goverlay"),  # output_folder par défaut de Goverlay
    os.path.expanduser("~/.local/share/goverlay/logs"),
]
FPS_STALE_SECONDS = 5  # au-delà, on considère qu'aucun jeu ne tourne

def asset_dir():
    """Dossier des ressources (icônes) : celui de cachymonitor.py."""
    return APP_ROOT


def _num(x):
    """Conversion en float d'une valeur venue de l'extérieur, ou None."""
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def app_settings():
    """Réglages mémorisés de l'appli . Un seul endroit
    pour le couple organisation/appli : le changer ici le change partout."""
    from PySide6.QtCore import QSettings   # import local : config reste sans Qt
    return QSettings("CachyMonitor", "CachyMonitor")


def _as_bool(v):
    """QSettings rend les booléens en texte selon le backend."""
    if isinstance(v, str):
        return v.lower() in ("true", "1", "yes")
    return bool(v)


def _read_first(path, default=None):
    """Lit un fichier sysfs et renvoie son contenu nettoyé (ou default)."""
    try:
        with open(path) as f:
            return f.read().strip()
    except (OSError, ValueError):
        return default
