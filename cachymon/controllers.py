"""CachyMonitor : module controllers (voir cachymonitor.py)."""

import os
import glob

from .config import _num, _read_first



# ----------------------------------------------------------------------------- #
#  Manettes
# ----------------------------------------------------------------------------- #
#
# Linux : chaque manette reconnue par le noyau a un nœud /sys/class/input/jsN.
# Son périphérique d'entrée donne le nom et le bus (USB ou Bluetooth) ; la
# batterie, quand le pilote la publie, est un « power_supply » rangé sous le même
# périphérique HID (hid-playstation, hid-sony, hid-nintendo, xpadneo…) ou un
# peu plus haut dans l'arbre pour les récepteurs sans fil USB (xpad).

# Type de connexion, d'après /sys/.../id/bustype (valeurs de linux/input.h).
# Un dongle sans fil USB (Xbox, 8BitDo) apparaît comme une connexion USB.
BUS_TYPES = {0x03: "usb", 0x05: "bluetooth"}

# Certains pilotes (xpad) ne donnent qu'un niveau, pas un pourcentage.
# On le traduit en valeur approchée pour pouvoir dessiner la jauge.
BATTERY_LEVELS = {"full": 100, "high": 75, "normal": 50, "low": 20, "critical": 5}

# Préfixes de fabricant retirés du nom affiché, déjà assez long comme ça.
CONTROLLER_NAME_PREFIXES = ("Sony Interactive Entertainment ", "Sony Computer Entertainment ",
                            "Microsoft ", "Nintendo ")


def _clean_controller_name(name):
    for prefix in CONTROLLER_NAME_PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def _controller_battery(dev_path):
    """Batterie d'une manette : (pourcentage, état) ou (None, None).

    On cherche sur le périphérique HID, puis deux niveaux au-dessus (interface
    et appareil USB) : la batterie d'un récepteur sans fil USB est publiée là,
    pas sur la manette. Monter plus haut, ce serait risquer de tomber sur la
    batterie d'un autre appareil branché sur le même concentrateur.
    """
    path = dev_path
    for _ in range(3):
        for supply in sorted(glob.glob(os.path.join(path, "power_supply", "*"))):
            if _read_first(os.path.join(supply, "scope"), "").lower() != "device":
                continue
            pct = _num(_read_first(os.path.join(supply, "capacity")))
            if pct is None:
                level = _read_first(os.path.join(supply, "capacity_level"), "").lower()
                pct = BATTERY_LEVELS.get(level)
            status = _read_first(os.path.join(supply, "status"), "").lower() or None
            return (int(pct) if pct is not None else None), status
        path = os.path.dirname(path)
    return None, None


def read_controllers():
    """Liste des manettes connectées : nom, connexion, batterie.

    Une manette peut exposer plusieurs nœuds jsN (rare), et la DualSense crée
    aussi des périphériques pour son pavé tactile et ses capteurs de mouvement :
    on dédoublonne par périphérique HID, qui est unique par manette.
    """
    found, seen = [], set()
    for js in sorted(glob.glob("/sys/class/input/js*")):
        input_dev = os.path.realpath(os.path.join(js, "device"))
        hid_dev = os.path.realpath(os.path.join(input_dev, "device"))
        if hid_dev in seen:
            continue
        seen.add(hid_dev)

        name = _read_first(os.path.join(input_dev, "name"), "") or "?"
        try:
            bus = int(_read_first(os.path.join(input_dev, "id", "bustype"), ""), 16)
        except ValueError:
            bus = None
        battery, status = _controller_battery(hid_dev)
        found.append({
            "name": _clean_controller_name(name),
            "bus": BUS_TYPES.get(bus),
            "battery": battery,
            "status": status,     # "charging", "discharging", "full"… ou None
        })
    return found
