"""CachyMonitor : module sensors (voir cachymonitor.py)."""

import os
import re
import glob
import shutil
import subprocess

from .config import _num, _read_first
from .debug import debug_exc
from .i18n import tr



# ----------------------------------------------------------------------------- #
#  Lecture des capteurs
# ----------------------------------------------------------------------------- #

def _find_hwmon(name):
    """Renvoie le chemin d'un hwmon par son nom (ex: 'k10temp')."""
    for path in glob.glob("/sys/class/hwmon/hwmon*"):
        try:
            with open(os.path.join(path, "name")) as f:
                if f.read().strip() == name:
                    return path
        except OSError:
            continue
    return None


# Pilotes de température CPU, par ordre de préférence.
#   k10temp  : AMD (Zen / Ryzen / Threadripper)
#   zenpower : pilote AMD alternatif (paquet AUR)
#   coretemp : Intel
#   cpu_thermal / acpitz : repli générique (ARM, machines virtuelles, portables)
CPU_TEMP_DRIVERS = ("k10temp", "zenpower", "coretemp", "cpu_thermal", "acpitz")

# Libellés de capteurs correspondant à la température « globale » du CPU.
#   Tctl/Tdie  : AMD          Package id 0 : Intel
CPU_TEMP_LABELS = ("tctl", "tdie", "package id 0", "cpu")


def find_cpu_temp_file():
    """Trouve le fichier sysfs de la température CPU, quel que soit le matériel (Linux).

    On cherche un pilote connu (AMD, Intel, générique), puis dans ce pilote le
    capteur qui représente le processeur entier plutôt qu'un cœur isolé : son
    libellé (tempN_label) vaut Tctl/Tdie chez AMD, « Package id 0 » chez Intel.
    Sans libellé exploitable, on retombe sur temp1_input.
    """
    for driver in CPU_TEMP_DRIVERS:
        hw = _find_hwmon(driver)
        if not hw:
            continue
        # 1) On privilégie le capteur « paquet » via son libellé.
        for label_file in sorted(glob.glob(os.path.join(hw, "temp*_label"))):
            label = (_read_first(label_file) or "").lower()
            if any(k in label for k in CPU_TEMP_LABELS):
                cand = label_file.replace("_label", "_input")
                if os.path.exists(cand):
                    return cand
        # 2) Sinon, le premier capteur disponible.
        for cand in sorted(glob.glob(os.path.join(hw, "temp*_input"))):
            return cand
    return None


class LinuxCpuReader:
    """Usage CPU (total + par cœur), fréquence et température, via /proc et /sys."""

    def __init__(self):
        self._prev = self._read_stat()
        # Détection indépendante du constructeur (AMD, Intel, générique).
        self._temp_file = find_cpu_temp_file()

    @staticmethod
    def _read_stat():
        totals = {}
        with open("/proc/stat") as f:
            for line in f:
                if not line.startswith("cpu"):
                    break
                parts = line.split()
                key = parts[0]
                vals = list(map(int, parts[1:]))
                idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
                total = sum(vals)
                totals[key] = (idle, total)
        return totals

    def _usage(self):
        cur = self._read_stat()
        out = {}
        for key, (idle, total) in cur.items():
            pidle, ptotal = self._prev.get(key, (idle, total))
            dt = total - ptotal
            di = idle - pidle
            out[key] = max(0.0, min(100.0, 100.0 * (1 - di / dt))) if dt > 0 else 0.0
        self._prev = cur
        return out

    @staticmethod
    def _freq_mhz():
        files = glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq")
        vals = []
        for fp in files:
            try:
                with open(fp) as f:
                    vals.append(int(f.read()) / 1000.0)  # kHz -> MHz
            except (OSError, ValueError):
                pass
        return sum(vals) / len(vals) if vals else None

    def _temp(self):
        if not self._temp_file:
            return None
        try:
            with open(self._temp_file) as f:
                return int(f.read()) / 1000.0
        except (OSError, ValueError):
            return None

    def sample(self):
        usage = self._usage()
        cores = sorted(
            (k for k in usage if k != "cpu"),
            key=lambda k: int(k[3:]),
        )
        return {
            "cpu_pct": usage.get("cpu", 0.0),
            "cpu_cores": [usage[k] for k in cores],
            "cpu_freq": self._freq_mhz(),
            "cpu_temp": self._temp(),
            "cpu_power": None,
        }


def make_cpu_reader():
    return LinuxCpuReader()


def read_ram():
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, _, v = line.partition(":")
            info[k] = int(v.split()[0])  # kB
    total = info.get("MemTotal", 0) / 1024 / 1024          # GiB
    avail = info.get("MemAvailable", 0) / 1024 / 1024
    used = total - avail
    pct = (used / total * 100) if total else 0.0
    return {"ram_used": used, "ram_total": total, "ram_pct": pct}


# ----------------------------------------------------------------------------- #
#  Détection du nom du matériel (statique : lu une seule fois au démarrage)
# ----------------------------------------------------------------------------- #

def _clean_cpu(name):
    """Raccourcit le libellé CPU : 'AMD Ryzen 5 5600 6-Core Processor' -> 'AMD Ryzen 5 5600'."""
    name = re.sub(r"\(R\)|\(TM\)|\(tm\)", "", name)
    name = re.sub(r"\s*\d+-Core Processor", "", name)
    name = re.sub(r"@.*$", "", name)
    name = name.replace("Processor", "").replace("CPU", "")
    return " ".join(name.split()) or "CPU"


def read_cpu_name():
    """Nom du processeur (ex: 'AMD Ryzen 5 5600')."""
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return _clean_cpu(line.split(":", 1)[1].strip())
    except OSError:
        pass
    return "CPU"


def _ram_dmi():
    """Type + vitesse RAM via dmidecode, uniquement si accessible sans sudo (sinon None)."""
    try:
        out = subprocess.run(
            ["dmidecode", "-t", "memory"],
            capture_output=True, text=True, timeout=2,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    mtype = speed = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("Type:") and "DDR" in line:
            mtype = line.split(":", 1)[1].strip()
        elif line.startswith("Configured Memory Speed:") and "Unknown" not in line:
            speed = line.split(":", 1)[1].strip()
    parts = [p for p in (mtype, speed) if p]
    return " ".join(parts) or None


# dmidecode coûte cher : la RAM ne change pas en cours de session, on
# ne l'interroge donc qu'une fois (read_ram_name est rappelé à chaque
# changement de langue, pour traduire l'unité).
_RAM_EXTRA_UNREAD = object()
_ram_extra_cache = _RAM_EXTRA_UNREAD


def _ram_extra():
    global _ram_extra_cache
    if _ram_extra_cache is _RAM_EXTRA_UNREAD:
        try:
            _ram_extra_cache = _ram_dmi()
        except Exception:
            debug_exc("RAM (type, vitesse)")
            _ram_extra_cache = None
    return _ram_extra_cache


def read_ram_name():
    """Capacité physique (+ type/vitesse si lisibles), ex: '16 Gio · DDR4 3200 MT/s'."""
    kb = None
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    kb = int(line.split()[1])
                    break
    except OSError:
        pass
    if not kb:
        return "RAM"
    gib = kb / 1024 / 1024
    # La capacité « affichée » est < à la capacité physique (kernel, intégré) :
    # on arrondit au multiple de 4 Gio le plus proche pour retomber sur 8/16/32…
    phys = round(gib / 4) * 4 if gib > 6 else round(gib)
    cap = f"{phys} {tr('GiB')}"
    extra = _ram_extra()
    return f"{cap} · {extra}" if extra else cap


# Identifiants PCI des constructeurs de cartes graphiques (AMD et Intel ; NVIDIA passe par nvidia-smi).
PCI_VENDOR_AMD = "0x1002"
PCI_VENDOR_INTEL = "0x8086"


def _drm_cards():
    """Cartes graphiques vues par le noyau : [(chemin_device, id_constructeur)].

    Note : l'index n'est pas toujours 0 (sur la machine de dev c'est 'card1'),
    d'où le glob plutôt qu'un chemin en dur.
    """
    cards = []
    for dev in sorted(glob.glob("/sys/class/drm/card[0-9]*/device")):
        vendor = _read_first(os.path.join(dev, "vendor"))
        if vendor:
            cards.append((dev, vendor.lower()))
    return cards


def _gpu_name_lspci(dev_path, fallback):
    """Nom commercial du GPU via lspci (paquet pciutils, présent par défaut)."""
    slot = os.path.basename(os.path.realpath(dev_path))  # ex: 0000:08:00.0
    if slot.startswith("0000:"):
        slot = slot[5:]
    try:
        out = subprocess.run(["lspci", "-s", slot], capture_output=True,
                             text=True, timeout=3).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return fallback
    # "08:00.0 VGA compatible controller: NVIDIA Corporation GA106 [GeForce RTX 3060]"
    if ":" in out:
        name = out.split(":")[-1].strip()
        # L'ordre compte : on retire d'abord « (rev a1) », sinon l'ancrage de fin
        # de l'expression suivante ne trouve jamais les crochets.
        name = re.sub(r"\s*\(rev [^)]+\)", "", name)
        # lspci met le nom commercial entre crochets :
        #   « Navi 31 [Radeon RX 7900 XTX] » -> « Radeon RX 7900 XTX »
        m = re.search(r"\[([^\]]+)\]\s*$", name)
        if m:
            name = m.group(1)
        for noise in ("Corporation ", "Advanced Micro Devices, Inc. ",
                      "[AMD/ATI] ", "[AMD] ", "Intel Corporation "):
            name = name.replace(noise, "")
        if name:
            return name.strip()
    return fallback


def _hwmon_of(dev_path):
    """hwmon rattaché à une carte (température / conso / fréquence)."""
    for hw in glob.glob(os.path.join(dev_path, "hwmon", "hwmon*")):
        return hw
    return None


_smi_missing = None


def _nvidia_smi_missing():
    """Vrai si nvidia-smi est introuvable (Linux). Résolu une seule fois, comme le chemin."""
    global _smi_missing
    if _smi_missing is None:
        _smi_missing = shutil.which("nvidia-smi") is None
    return _smi_missing


_nvml_lib = None   # None = pas encore essayé, False = indisponible
_nvml_handle = None


def _nvml_paths():
    """Emplacements de la bibliothèque NVML, dans l'ordre d'essai."""
    return ["libnvidia-ml.so.1"]


def _nvml_open():
    """Charge NVML une seule fois.

    Elle sert quand nvidia-smi est absent alors que le pilote est installé.
    """
    global _nvml_lib, _nvml_handle
    if _nvml_lib is not None:
        return _nvml_lib or None
    _nvml_lib = False
    import ctypes
    for path in _nvml_paths():
        try:
            lib = ctypes.CDLL(path)
            break
        except OSError:
            continue
    else:
        return None
    try:
        if lib.nvmlInit_v2() != 0:
            return None
        handle = ctypes.c_void_p()
        if lib.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(handle)) != 0:
            return None
    except (OSError, AttributeError):
        return None
    _nvml_lib, _nvml_handle = lib, handle
    return lib


def _gpu_nvidia_nvml():
    """GPU NVIDIA via NVML, mêmes champs que _gpu_nvidia()."""
    lib = _nvml_open()
    if lib is None:
        return None
    import ctypes

    class Util(ctypes.Structure):
        _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]

    class Mem(ctypes.Structure):
        _fields_ = [("total", ctypes.c_ulonglong), ("free", ctypes.c_ulonglong),
                    ("used", ctypes.c_ulonglong)]

    class Mem2(ctypes.Structure):
        _fields_ = [("version", ctypes.c_uint), ("total", ctypes.c_ulonglong),
                    ("reserved", ctypes.c_ulonglong), ("free", ctypes.c_ulonglong),
                    ("used", ctypes.c_ulonglong)]

    h = _nvml_handle
    name = ctypes.create_string_buffer(96)
    util = Util()
    temp, clock, power = ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint()
    if lib.nvmlDeviceGetName(h, name, 96) != 0:
        return None
    ok_util = lib.nvmlDeviceGetUtilizationRates(h, ctypes.byref(util)) == 0
    # La version 2 retire de « used » la mémoire réservée par le pilote, comme
    # nvidia-smi (1604 Mio contre 1777 sur une RTX 3060). Les pilotes trop
    # anciens ne l'ont pas : on retombe alors sur la version 1.
    mem = Mem2()
    mem.version = ctypes.sizeof(Mem2) | (2 << 24)
    try:
        ok_mem = lib.nvmlDeviceGetMemoryInfo_v2(h, ctypes.byref(mem)) == 0
    except AttributeError:
        ok_mem = False
    if not ok_mem:
        mem = Mem()
        ok_mem = lib.nvmlDeviceGetMemoryInfo(h, ctypes.byref(mem)) == 0
    ok_temp = lib.nvmlDeviceGetTemperature(h, 0, ctypes.byref(temp)) == 0  # 0 = cœur GPU
    ok_clock = lib.nvmlDeviceGetClockInfo(h, 0, ctypes.byref(clock)) == 0  # 0 = graphique
    ok_power = lib.nvmlDeviceGetPowerUsage(h, ctypes.byref(power)) == 0    # milliwatts
    return {
        "gpu_name": name.value.decode(errors="replace"),
        "gpu_pct": float(util.gpu) if ok_util else 0.0,
        "gpu_temp": float(temp.value) if ok_temp else None,
        "vram_used": mem.used / 1048576 if ok_mem else 0.0,   # MiB
        "vram_total": mem.total / 1048576 if ok_mem else 0.0,
        "gpu_clock": float(clock.value) if ok_clock else None,
        "gpu_power": power.value / 1000 if ok_power else None,
    }


def _gpu_nvidia():
    """GPU NVIDIA (usage, temp, VRAM, clock, power).

    nvidia-smi, ou NVML quand il est absent.
    """
    if _nvidia_smi_missing():
        return _gpu_nvidia_nvml()
    query = "name,utilization.gpu,temperature.gpu,memory.used,memory.total,clocks.gr,power.draw"
    try:
        out = subprocess.run(
            ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=4,
        ).stdout.strip().splitlines()
    except (OSError, subprocess.SubprocessError):
        return None
    if not out:
        return None
    fields = [x.strip() for x in out[0].split(",")]
    if len(fields) < 7:
        return None
    return {
        "gpu_name": fields[0],
        "gpu_pct": _num(fields[1]) or 0.0,
        "gpu_temp": _num(fields[2]),
        "vram_used": _num(fields[3]) or 0.0,   # MiB
        "vram_total": _num(fields[4]) or 0.0,
        "gpu_clock": _num(fields[5]),
        "gpu_power": _num(fields[6]),
    }


def _gpu_amd():
    """GPU AMD via le pilote amdgpu, qui expose tout dans /sys (aucun outil externe).

    ⚠️ Écrit d'après la documentation du noyau, NON TESTÉ sur une vraie Radeon
    (machine de développement équipée en NVIDIA). Retours bienvenus.
    """
    for dev, vendor in _drm_cards():
        if vendor != PCI_VENDOR_AMD:
            continue
        busy = _num(_read_first(os.path.join(dev, "gpu_busy_percent")))
        vram_total = _num(_read_first(os.path.join(dev, "mem_info_vram_total")))
        vram_used = _num(_read_first(os.path.join(dev, "mem_info_vram_used")))
        # Une carte AMD sans ces fichiers = pilote trop ancien : on passe.
        if busy is None and vram_total is None:
            continue

        temp = power = clock = None
        hw = _hwmon_of(dev)
        if hw:
            t = _num(_read_first(os.path.join(hw, "temp1_input")))
            temp = t / 1000.0 if t is not None else None          # m°C -> °C
            p = _num(_read_first(os.path.join(hw, "power1_average")))
            if p is None:
                p = _num(_read_first(os.path.join(hw, "power1_input")))
            power = p / 1e6 if p is not None else None            # µW -> W
            f = _num(_read_first(os.path.join(hw, "freq1_input")))
            clock = f / 1e6 if f is not None else None            # Hz -> MHz

        return {
            "gpu_name": _gpu_name_lspci(dev, "AMD GPU"),
            "gpu_pct": busy or 0.0,
            "gpu_temp": temp,
            "vram_used": (vram_used / 1024 / 1024) if vram_used else 0.0,   # octets -> MiB
            "vram_total": (vram_total / 1024 / 1024) if vram_total else 0.0,
            "gpu_clock": clock,
            "gpu_power": power,
        }
    return None


def _gpu_intel():
    """GPU Intel (i915 / xe). Volontairement partiel.

    Le taux d'occupation d'un GPU Intel n'est pas exposé dans /sys : il faut
    intel_gpu_top, qui réclame les privilèges root. On se limite donc à ce qui
    est lisible sans droits particuliers (nom, température, fréquence).
    La VRAM est de la mémoire système partagée : pas de compteur dédié.

    ⚠️ NON TESTÉ sur du matériel Intel. Retours bienvenus.
    """
    for dev, vendor in _drm_cards():
        if vendor != PCI_VENDOR_INTEL:
            continue
        temp = clock = None
        hw = _hwmon_of(dev)
        if hw:
            t = _num(_read_first(os.path.join(hw, "temp1_input")))
            temp = t / 1000.0 if t is not None else None
        # i915 publie la fréquence dans le dossier de la carte (cardN), pas dans
        # « device » ; les pilotes récents (xe, i915 récent) la rangent sous gt/gt0.
        card = os.path.dirname(dev)
        f = None
        for cand in (os.path.join(card, "gt_cur_freq_mhz"),
                     os.path.join(card, "gt", "gt0", "rps_cur_freq_mhz"),
                     os.path.join(dev, "gt_cur_freq_mhz")):
            f = _num(_read_first(cand))
            if f is not None:
                break
        clock = f
        return {
            "gpu_name": _gpu_name_lspci(dev, "Intel GPU"),
            "gpu_pct": 0.0,          # indisponible sans root
            "gpu_temp": temp,
            "vram_used": 0.0,        # mémoire partagée avec la RAM
            "vram_total": 0.0,
            "gpu_clock": clock,
            "gpu_power": None,
        }
    return None


def read_gpu():
    """Lit le GPU, quel que soit le constructeur.

    On essaie NVIDIA (nvidia-smi), puis AMD et Intel (/sys). Le premier lecteur qui renvoie quelque chose
    gagne ; si aucun ne répond, l'interface affiche « GPU indisponible » au lieu
    de planter.
    """
    for reader in (_gpu_nvidia, _gpu_amd, _gpu_intel):
        try:
            data = reader()
        except Exception:
            debug_exc("GPU : " + reader.__name__)
            data = None          # un GPU exotique ne doit jamais faire tomber l'app
        if data:
            return data
    return _gpu_none()


def _gpu_none():
    return {
        "gpu_name": tr("GPU unavailable"), "gpu_pct": 0.0, "gpu_temp": None,
        "vram_used": 0.0, "vram_total": 0.0, "gpu_clock": None, "gpu_power": None,
    }
