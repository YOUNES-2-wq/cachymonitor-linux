"""CachyMonitor : module sampler (voir cachymonitor.py)."""

from PySide6.QtCore import QThread, Signal
from .config import DEFAULT_INTERVAL_MS
from .debug import debug_exc
from .controllers import read_controllers
from .game import MangoHudGameReader
from .sensors import make_cpu_reader, read_gpu, read_ram



# ----------------------------------------------------------------------------- #
#  Thread d'échantillonnage (évite de bloquer l'UI avec nvidia-smi)
# ----------------------------------------------------------------------------- #

class Sampler(QThread):
    sampled = Signal(dict)

    def __init__(self):
        super().__init__()
        self._running = True
        self.interval_ms = DEFAULT_INTERVAL_MS
        self._cpu = make_cpu_reader()
        self._game = MangoHudGameReader()

    def _collect(self):
        data = {}
        data.update(self._cpu.sample())
        data.update(read_ram())
        data.update(read_gpu())
        try:
            data["controllers"] = read_controllers()
        except Exception:
            debug_exc("manettes")
            data["controllers"] = []   # une manette exotique ne doit pas tout bloquer

        game = self._game.sample()
        if game is not None:
            # Quand le log MangoHud n'a pas les charges CPU/GPU, les mesures
            # système du tour en cours situent le goulot d'étranglement.
            if game.get("cpu_load") is None:
                game["cpu_load"] = data.get("cpu_pct")
            if game.get("gpu_load") is None:
                game["gpu_load"] = data.get("gpu_pct")
        data["game"] = game
        return data

    def run(self):
        self._game.start()
        while self._running:
            try:
                data = self._collect()
            except Exception:
                # Une lecture qui échoue (/proc illisible, ligne inattendue) ne doit
                # pas tuer le thread : l'affichage resterait figé sans explication.
                debug_exc("mesure")
                data = None
            if data is not None:
                self.sampled.emit(data)
            # sommeil découpé pour réagir vite à l'arrêt / changement d'intervalle
            slept = 0
            while self._running and slept < self.interval_ms:
                self.msleep(50)
                slept += 50

    def stop(self):
        self._running = False
        self._game.stop()
        self.wait(8000)   # une mesure en cours (nvidia-smi...) peut durer plusieurs secondes
