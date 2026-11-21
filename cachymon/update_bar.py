"""CachyMonitor : barre de mise à jour (voir cachymonitor.py).

Cachée tant qu'il n'y a rien de neuf. Quand une version existe : un texte et un bouton
(« Mettre à jour » pour le paquet AUR, « Voir les nouveautés » depuis les sources).
Pendant l'installation, une barre « en cours » (sans pourcentage : il n'existe pas).
Rien ne s'installe sans clic.
"""

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton,
                               QVBoxLayout)

from cachymon.i18n import tr
from cachymon.updater import KIND_PAGE, NO_HELPER, OK, RELEASE_PAGE, Updater


class UpdateBar(QFrame):
    def __init__(self, current_version):
        super().__init__()
        self.setObjectName("updateBar")
        self.setVisible(False)
        self.info = None
        self._state = "idle"     # idle, available, working, installed, error
        self._error = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(6)
        top = QHBoxLayout()
        self.label = QLabel()
        self.label.setObjectName("updateLabel")
        self.label.setWordWrap(True)
        self.button = QPushButton()
        self.button.setObjectName("updateButton")
        self.button.setCursor(Qt.PointingHandCursor)
        self.button.clicked.connect(self._clicked)
        top.addWidget(self.label, 1)
        top.addWidget(self.button)
        lay.addLayout(top)
        self.bar = QProgressBar()
        self.bar.setObjectName("updateProgress")
        self.bar.setRange(0, 0)          # « en cours », sans pourcentage
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        lay.addWidget(self.bar)

        self.updater = Updater(current_version)
        self.updater.found.connect(self._found)
        self.updater.done.connect(self._done)
        self._render()

    # -- appelé par la fenêtre ------------------------------------------------ #
    def check(self):
        """Lance une vérification (ignorée pendant une installation ou une erreur)."""
        if not self.updater.busy and self._state in ("idle", "available"):
            self.updater.check()

    def retext(self):
        self._render()

    # -- signaux de l'Updater ------------------------------------------------- #
    def _found(self, info):
        if info is None:                      # la version a été installée à la main entre-temps
            if self._state == "available":
                self.info, self._state = None, "idle"
                self._render()
            return
        if self._state in ("working", "installed", "error"):
            return
        self.info = info
        self._state = "available"
        self._render()

    def _done(self, result):
        self.updater.busy = False
        if result == OK:
            self._state = "installed"
        else:
            self._state = "error"
            self._error = result
        self._render()

    # -- interface ------------------------------------------------------------ #
    def _clicked(self):
        if self.info and self.info["kind"] == KIND_PAGE:
            QDesktopServices.openUrl(QUrl(RELEASE_PAGE))
        else:                       # « Mettre à jour » ou « Réessayer »
            self._state = "working"
            self._render()
            self.updater.install(self.info)

    def _render(self):
        if self.info is None:
            self.setVisible(False)
            return
        self.setVisible(True)
        version = self.info["version"]
        st = self._state
        self.bar.setVisible(st == "working")
        self.button.setVisible(st in ("available", "error"))
        if st == "available":
            self.label.setText(tr("Version {version} is available").format(version=version))
            self.button.setText(tr("See what's new") if self.info["kind"] == KIND_PAGE
                                else tr("Update"))
        elif st == "working":
            self.label.setText(tr("Updating to {version}…").format(version=version))
        elif st == "installed":
            self.label.setText(tr("Version {version} installed: restart CachyMonitor to use it")
                               .format(version=version))
        elif st == "error":
            text = ("Install yay or paru to update from here." if self._error == NO_HELPER
                    else "The update failed.")
            self.label.setText(tr(text))
            self.button.setText(tr("Try again"))
