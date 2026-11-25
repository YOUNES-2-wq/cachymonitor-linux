#!/usr/bin/env python3
"""
CachyMonitor — moniteur système gaming (CPU / GPU / RAM / températures / FPS).

Application Linux : /proc, /sys (hwmon, manettes), nvidia-smi / NVML et logs CSV
MangoHud. Ce fichier est le point d'entrée ; le code vit dans le dossier
cachymon/ (config, sensors, controllers, game, widgets...) et doit toujours être
installé à côté de lui.

Dépendance : PySide6. Aucune autre librairie : les graphes sont dessinés au QPainter.

--------------------------------------------------------------------------
MATÉRIEL — ce qui est réellement testé
--------------------------------------------------------------------------
Le code vise tous les matériels, mais il n'a été VÉRIFIÉ que sur :

    CPU AMD Ryzen 5 5600 (k10temp) + GPU NVIDIA RTX 3060 (nvidia-smi)
      · CachyOS / KDE Plasma / Wayland

Écrit d'après la documentation mais JAMAIS EXÉCUTÉ sur le matériel
correspondant :

  * température CPU Intel      -> capteur « coretemp »
  * GPU AMD (Radeon)           -> pilote amdgpu via /sys
  * GPU Intel (i915 / xe)      -> partiel, /sys

Si vous testez sur l'une de ces configurations, les retours sont les
bienvenus : ouvrez une « issue » avec la sortie de `scripts/hw-report.sh`
(ou simplement une capture de l'application).
https://github.com/YOUNES-2-wq/cachymonitor-linux/issues
--------------------------------------------------------------------------
"""


import math
import os
import random
import sys
import time
# Le dossier de ce fichier d'abord : le paquet cachymon/ y est installe a cote, y compris
# quand Python est lance en mode isole (-I) ou via un lien symbolique.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QBrush, QColor, QIcon, QImage, QLinearGradient, QPainter, QPalette, QPen, QPixmap, QRadialGradient  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QCheckBox, QSpinBox, QComboBox, QToolButton, QListView, QMessageBox, QSlider  # noqa: E402
from cachymon.config import DEFAULT_FPS_TARGET, DEFAULT_INTERVAL_MS, _as_bool, app_settings, asset_dir  # noqa: E402
from cachymon.i18n import DEFAULT_LANG, LANG_LABELS, LANG_MODES, set_language, tr  # noqa: E402
from cachymon.sampler import Sampler  # noqa: E402
from cachymon.update_bar import UpdateBar  # noqa: E402
from cachymon.sensors import read_cpu_name, read_ram_name  # noqa: E402
from cachymon.theme import (CLAUDE_ACCENTS, DEFAULT_ACCENT, DEFAULT_GLASS_LEVEL, DEFAULT_THEME, THEME_LABELS,  # noqa: E402
                            THEME_MODES, claude_orb, col, glass_level, is_glass, resolve_theme,
                            set_claude_accent, set_glass_level, set_palette, temp_role)
from cachymon.widgets import ControllerPanel, GamePanel, GaugeCard  # noqa: E402


APP_VERSION = "1.6.1"
APP_AUTHOR = "YOUNES-2-wq"
APP_URL = "https://github.com/YOUNES-2-wq/cachymonitor-linux"


# ----------------------------------------------------------------------------- #
#  Menu déroulant
# ----------------------------------------------------------------------------- #

class DropDownComboBox(QComboBox):
    """Liste déroulante qui s'ouvre TOUJOURS sous le champ, sur un fond opaque.

    Laissés au style du bureau, Breeze et Adwaita affichent la liste comme un
    menu centré sur l'entrée courante : choisie la dernière entrée, la liste
    s'ouvre vers le haut — déroutant — et son fond translucide laisse voir le
    bureau à travers. La règle QSS « combobox-popup: 0 » impose la liste
    déroulante classique ; les deux réglages ci-dessous rendent son conteneur
    opaque. Ils sont reposés à chaque ouverture car le style du bureau les
    réapplique après coup (et seule une fenêtre encore invisible peut changer
    de transparence).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setView(QListView())

    def showPopup(self):
        popup = self.view().window()
        popup.setAttribute(Qt.WA_TranslucentBackground, False)
        popup.setAutoFillBackground(True)
        super().showPopup()


# ----------------------------------------------------------------------------- #
#  Fenêtre principale
# ----------------------------------------------------------------------------- #

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CachyMonitor")
        self.resize(560, 720)
        self.theme_mode = DEFAULT_THEME
        self.lang_mode = DEFAULT_LANG
        self._translucent = False          # fenêtre réellement transparente (thème Claude)
        self._bg_timer = QTimer(self)      # fait dériver les halos du fond (thème Claude)
        self._bg_timer.setInterval(100)    # 10 images/s : la dérive est très lente
        self._bg_timer.timeout.connect(self.update)
        # Le fond réagit à la machine : chaleur (0..1), charge GPU (0..1), jeu en cours.
        self._heat = 0.0
        self._gpu_load = 0.0
        self._in_game = False
        self._bg_phase = 0.0               # position de la dérive des halos
        self._bg_last = None
        self._grain = None                 # texture de grain, créée à la demande
        self._overlay = None               # grain + quadrillage déjà dessinés (cache)
        self._overlay_key = None
        # Les changements de style (curseur d'intensité) sont regroupés : reconstruire
        # la feuille de style à chaque cran serait lourd.
        self._restyle_timer = QTimer(self)
        self._restyle_timer.setSingleShot(True)
        self._restyle_timer.setInterval(150)
        self._restyle_timer.timeout.connect(self.apply_theme)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        # En-tête : titre + bouton qui déplie les réglages
        header = QHBoxLayout()
        title = QLabel("CachyMonitor")
        title.setObjectName("appTitle")
        header.addWidget(title)
        header.addStretch()

        self.opt_button = QToolButton()
        self.opt_button.setObjectName("optButton")
        self.opt_button.setText("⚙  Options")
        self.opt_button.setCheckable(True)
        self.opt_button.setCursor(Qt.PointingHandCursor)
        header.addWidget(self.opt_button)
        root.addLayout(header)

        # Le panneau existe avant qu'on branche le signal : _toggle_options
        # planterait s'il se déclenchait sur un self.options pas encore créé.
        self._build_options()
        root.addWidget(self.options)
        self.opt_button.toggled.connect(self._toggle_options)

        # Barre de mise à jour : cachée tant qu'il n'y a rien de neuf.
        self.update_bar = UpdateBar(APP_VERSION)
        root.addWidget(self.update_bar)

        # Cartes
        grid = QGridLayout()
        grid.setSpacing(14)
        self.cards_grid = grid

        self.cpu = GaugeCard("CPU", "cpu")
        self.gpu = GaugeCard("GPU", "gpu")
        self.ram = GaugeCard("RAM", "ram")
        self.vram = GaugeCard("VRAM", "vram")
        self.game = GamePanel()
        self.controllers = ControllerPanel()

        # Les cartes sont placées par _apply_layout (choix des cartes, mode compact).
        root.addLayout(grid, 1)

        # Noms matériel statiques (lus une seule fois)
        self.cpu.hw.setText(read_cpu_name())
        self.ram.hw.setText(read_ram_name())

        self.status = QLabel(tr("Starting…"))
        self.started = False   # passe à True au 1er échantillon (statut réel)

        self.status.setObjectName("status")
        root.addWidget(self.status)

        # Réglages mémorisés (intervalle, cible FPS, thème, langue, "au-dessus",
        # géométrie). Les textes sont posés avec la langue par défaut pendant la
        # construction : retext() les repose dans celle qui a été mémorisée.
        self._load_settings()
        self.retext()
        self.apply_theme()

        # Suivi du thème du bureau quand le mode « Système » est choisi.
        QApplication.instance().styleHints().colorSchemeChanged.connect(
            self._on_system_theme_changed
        )

        # Sampler
        self.sampler = Sampler()
        self.sampler.interval_ms = self.interval.value()
        self.sampler.sampled.connect(self.on_sample)
        self.sampler.start()
        self._start_update_checks()

    # -- panneau Options ---------------------------------------------------- #
    def _build_options(self):
        """Zone de réglages dépliable. Repliée par défaut : l'écran reste dédié
        aux mesures, qui sont la raison d'être de l'application."""
        self.options = QFrame()
        self.options.setObjectName("options")
        self.options.setVisible(False)

        grid = QGridLayout(self.options)
        grid.setContentsMargins(14, 12, 14, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        self.interval = QSpinBox()
        self.interval.setRange(200, 5000)
        self.interval.setSingleStep(100)
        self.interval.setValue(DEFAULT_INTERVAL_MS)
        self.interval.setSuffix(" ms")
        self.interval.setToolTip(tr("Measurement refresh rate"))
        self.interval.valueChanged.connect(self._set_interval)

        self.fps_target = QSpinBox()
        self.fps_target.setRange(30, 500)
        self.fps_target.setSingleStep(5)
        self.fps_target.setValue(DEFAULT_FPS_TARGET)
        self.fps_target.setToolTip(
            tr("Scales the FPS colours and marks the frametime graph")
        )

        self.theme = DropDownComboBox()
        for mode in THEME_MODES:
            self.theme.addItem(tr(THEME_LABELS[mode]), mode)
        self.theme.setToolTip(tr("« System » follows the desktop light/dark setting"))
        self.theme.currentIndexChanged.connect(self._set_theme)

        self.lang = DropDownComboBox()
        for mode in LANG_MODES:
            self.lang.addItem(tr(LANG_LABELS[mode]), mode)
        self.lang.setToolTip(tr("« System » follows the desktop language"))
        self.lang.currentIndexChanged.connect(self._set_language)

        self.ontop = QCheckBox(tr("Always on top"))
        self.ontop.toggled.connect(self._toggle_ontop)

        self.compact = QCheckBox(tr("Compact mode"))
        self.compact.toggled.connect(self._on_layout_option)
        self.transparent = QCheckBox(tr("Transparent window (Claude theme)"))
        self.transparent.setChecked(False)      # lisibilité d'abord : opaque par défaut
        self.transparent.toggled.connect(self._on_glass_option)
        self.bg_anim = QCheckBox(tr("Animated background (Claude theme)"))
        self.bg_anim.setChecked(True)
        self.bg_anim.toggled.connect(self._on_glass_option)
        self.calm = QCheckBox(tr("Calm background while gaming"))
        self.calm.setChecked(True)
        self.calm.toggled.connect(self._on_glass_option)
        self.l_intensity = QLabel(tr("Glass intensity"))
        self.intensity = QSlider(Qt.Horizontal)
        self.intensity.setRange(0, 100)
        self.intensity.setValue(int(DEFAULT_GLASS_LEVEL * 100))
        self.intensity.valueChanged.connect(self._on_intensity)
        self.l_accent = QLabel(tr("Accent colour"))
        self.accent = DropDownComboBox()
        for key, (name, _main, _fps, _orb) in CLAUDE_ACCENTS.items():
            self.accent.addItem(tr(name), key)
        self.accent.currentIndexChanged.connect(self._on_accent)
        self.l_cards = QLabel(tr("Cards"))
        self.card_boxes = {}
        cards_row = QHBoxLayout()
        for key, label in (("cpu", "CPU"), ("gpu", "GPU"), ("ram", "RAM"), ("vram", "VRAM"),
                           ("controllers", "Controllers"), ("game", "Game")):
            box = QCheckBox(tr(label) if key in ("controllers", "game") else label)
            box.setChecked(True)
            box.toggled.connect(self._on_layout_option)
            self.card_boxes[key] = box
            cards_row.addWidget(box)
        cards_row.addStretch()

        self.l_interval = QLabel(tr("Interval"))
        self.l_fps = QLabel(tr("FPS target"))
        self.l_theme = QLabel(tr("Theme"))
        self.l_lang = QLabel(tr("Language"))

        self.about_button = QToolButton()
        self.about_button.setObjectName("aboutButton")
        self.about_button.setCursor(Qt.PointingHandCursor)
        self.about_button.setText(tr("About"))
        self.about_button.clicked.connect(self._show_about)

        grid.addWidget(self.l_interval, 0, 0)
        grid.addWidget(self.interval, 0, 1)
        grid.addWidget(self.l_fps, 0, 2)
        grid.addWidget(self.fps_target, 0, 3)
        grid.addWidget(self.l_theme, 1, 0)
        grid.addWidget(self.theme, 1, 1)
        grid.addWidget(self.l_lang, 1, 2)
        grid.addWidget(self.lang, 1, 3)
        grid.addWidget(self.ontop, 2, 0, 1, 3)
        grid.addWidget(self.about_button, 2, 3)
        grid.addWidget(self.compact, 5, 0, 1, 4)
        grid.addWidget(self.transparent, 6, 0, 1, 4)
        grid.addWidget(self.bg_anim, 7, 0, 1, 4)
        grid.addWidget(self.calm, 8, 0, 1, 4)
        grid.addWidget(self.l_intensity, 9, 0)
        grid.addWidget(self.intensity, 9, 1, 1, 3)
        grid.addWidget(self.l_accent, 10, 0)
        grid.addWidget(self.accent, 10, 1)
        grid.addWidget(self.l_cards, 11, 0)
        grid.addLayout(cards_row, 11, 1, 1, 3)
        grid.setColumnStretch(4, 1)

    # -- disposition des cartes ---------------------------------------------- #
    def _on_layout_option(self, _checked=False):
        """Mode compact ou choix des cartes modifié : on replace tout."""
        was_compact = getattr(self, "_was_compact", False)
        self._apply_layout()
        compact = self.compact.isChecked()
        if compact == was_compact:
            return
        self._was_compact = compact
        if self.isMaximized() or self.isFullScreen():
            return
        if compact:
            self._normal_size = self.size()      # pour la retrouver en quittant le compact
            QTimer.singleShot(0, lambda: self.resize(440, self.minimumSizeHint().height()))
        else:
            size = getattr(self, "_normal_size", None)
            QTimer.singleShot(0, lambda: self.resize(size or QSize(560, 720)))

    def _apply_layout(self):
        """Place les cartes cochées (jauges sur deux colonnes, puis manettes et
        jeu pleine largeur). Le mode compact retire aussi les courbes, le graphe
        de frametime et les manettes : il ne reste que les chiffres."""
        compact = self.compact.isChecked()
        g = self.cards_grid
        everyone = (self.cpu, self.gpu, self.ram, self.vram, self.controllers, self.game)
        for w in everyone:
            g.removeWidget(w)
            w.hide()
        for r in range(8):
            g.setRowStretch(r, 0)

        gauges = [w for key, w in (("cpu", self.cpu), ("gpu", self.gpu),
                                   ("ram", self.ram), ("vram", self.vram))
                  if self.card_boxes[key].isChecked()]
        for i, w in enumerate(gauges):
            alone = (i == len(gauges) - 1 and len(gauges) % 2 == 1)
            g.addWidget(w, i // 2, i % 2, 1, 2 if alone else 1)
            w.set_compact(compact)
            w.show()
        row = (len(gauges) + 1) // 2
        if self.card_boxes["controllers"].isChecked() and not compact:
            g.addWidget(self.controllers, row, 0, 1, 2)
            self.controllers.show()
            row += 1
        if self.card_boxes["game"].isChecked():
            g.addWidget(self.game, row, 0, 1, 2)
            self.game.set_compact(compact)
            self.game.show()
            g.setRowStretch(row, 1)
        elif gauges:
            g.setRowStretch(row - 1, 1)

    def _toggle_options(self, shown):
        self.options.setVisible(shown)

    def _show_about(self):
        """Fenêtre « À propos » : version, description, lien du projet, et de quoi
        identifier l'installation quand quelqu'un signale un bug."""
        import platform
        from PySide6 import __version__ as pyside_version

        system = "%s %s" % (platform.system(), platform.release())
        lines = [
            "<h3>CachyMonitor</h3>",
            "<p><b>%s</b></p>" % tr("Version {version}").format(version=APP_VERSION),
            "<p>%s</p>" % tr("Lightweight gaming system monitor for Linux: "
                             "CPU, GPU, RAM, VRAM, temperatures, FPS and controller battery."),
            "<p>%s</p>" % tr("Made by {author}, free and open source (MIT license).")
            .format(author=APP_AUTHOR),
            "<p>%s<br>" % tr("Source code, updates and bug reports:"),
        ]
        lines.append('<a href="%s">%s</a>' % (APP_URL, APP_URL))
        lines.append("</p><p style='color:%s; font-size:11px;'>%s<br>Python %s · Qt %s"
                     % (col("muted"), tr("System: {value}").format(value=system),
                        platform.python_version(), pyside_version))
        lines.append("</p>")

        box = QMessageBox(self)
        box.setWindowTitle(tr("About CachyMonitor"))
        box.setTextFormat(Qt.RichText)
        box.setText("".join(lines))
        box.setTextInteractionFlags(Qt.TextBrowserInteraction)
        icon = self.windowIcon()
        if not icon.isNull():
            box.setIconPixmap(icon.pixmap(64, 64))
        box.setStandardButtons(QMessageBox.Ok)
        box.exec()

    # -- langue ------------------------------------------------------------- #
    def _set_language(self, _index):
        self.lang_mode = self.lang.currentData()
        set_language(self.lang_mode)
        self.retext()

    def retext(self):
        """Repose tous les textes fixes de l'interface dans la langue active.

        Les textes qui dépendent des mesures (statut, goulot, unités des jauges)
        ne sont pas touchés ici : ils sont réécrits au prochain échantillon, donc
        au plus tard après un intervalle de rafraîchissement.
        """
        self.interval.setToolTip(tr("Measurement refresh rate"))
        self.fps_target.setToolTip(
            tr("Scales the FPS colours and marks the frametime graph")
        )
        self.l_interval.setText(tr("Interval"))
        self.l_fps.setText(tr("FPS target"))
        self.l_theme.setText(tr("Theme"))
        self.l_lang.setText(tr("Language"))
        self.ontop.setText(tr("Always on top"))
        self.compact.setText(tr("Compact mode"))
        self.transparent.setText(tr("Transparent window (Claude theme)"))
        self.bg_anim.setText(tr("Animated background (Claude theme)"))
        self.calm.setText(tr("Calm background while gaming"))
        self.l_intensity.setText(tr("Glass intensity"))
        self.l_accent.setText(tr("Accent colour"))
        for i in range(self.accent.count()):
            self.accent.setItemText(i, tr(CLAUDE_ACCENTS[self.accent.itemData(i)][0]))
        self.l_cards.setText(tr("Cards"))
        self.card_boxes["controllers"].setText(tr("Controllers"))
        self.card_boxes["game"].setText(tr("Game"))
        self.about_button.setText(tr("About"))
        self.update_bar.retext()
        self.theme.setToolTip(tr("« System » follows the desktop light/dark setting"))
        self.lang.setToolTip(tr("« System » follows the desktop language"))

        # Les entrées des listes : on réécrit le libellé sans toucher au choix.
        for combo, labels in ((self.theme, THEME_LABELS), (self.lang, LANG_LABELS)):
            for i in range(combo.count()):
                combo.setItemText(i, tr(labels[combo.itemData(i)]))

        self.game.retext()
        self.controllers.retext()
        # Capacité RAM : lue une seule fois au démarrage, son unité est traduite.
        self.ram.hw.setText(read_ram_name())
        if not self.started:
            self.status.setText(tr("Starting…"))

    # -- thème -------------------------------------------------------------- #
    def _set_theme(self, _index):
        self.theme_mode = self.theme.currentData()
        self.apply_theme()

    def _on_system_theme_changed(self, _scheme):
        """Le bureau est passé du clair au sombre (ou l'inverse)."""
        if self.theme_mode == "systeme":
            self.apply_theme()

    def apply_theme(self):
        """Bascule la palette et redessine tout, sans redémarrer l'application :
        l'historique des courbes et la session de jeu en cours sont conservés."""
        set_palette(resolve_theme(self.theme_mode))
        app = QApplication.instance()
        app.setPalette(build_palette())
        app.setStyleSheet(build_style())
        # Thème Claude : le fond de la fenêtre est peint par paintEvent, donc le « fond »
        # de la palette est rendu transparent POUR CETTE FENÊTRE SEULEMENT. Posé sur
        # l'appli entière, il viderait aussi le fond des boîtes de dialogue.
        window_palette = QPalette(app.palette())
        if is_glass():
            window_palette.setColor(QPalette.Window, QColor(0, 0, 0, 0))
        self.setPalette(window_palette)
        self._apply_glass_window()
        # Le QSS ne couvre pas les couleurs posées en ligne ni le QPainter.
        for card in (self.cpu, self.gpu, self.ram, self.vram, self.game,
                     self.controllers):
            card.retheme()
        self.update()

    # -- thème Claude : fenêtre en verre ------------------------------------- #
    def _glass_controls(self):
        return (self.transparent, self.bg_anim, self.calm, self.l_intensity,
                self.intensity, self.l_accent, self.accent)

    def _on_glass_option(self, _checked=False):
        self._apply_glass_window()
        self.update()

    def _on_intensity(self, value):
        """Curseur d'intensité : le dessin suit tout de suite ; la feuille de style
        (fond des cartes) est reconstruite une fois le curseur posé."""
        set_glass_level(value / 100.0)
        self.update()
        for card in (self.cpu, self.gpu, self.ram, self.vram, self.game, self.controllers):
            card.update()
        self._restyle_timer.start()

    def _on_accent(self, _index):
        set_claude_accent(self.accent.currentData())
        self.apply_theme()

    def _bg_is_still(self):
        """Fond figé : animation coupée, ou jeu en cours avec le mode calme."""
        return (not self.bg_anim.isChecked()
                or (self._in_game and self.calm.isChecked()))

    def _sync_bg_timer(self):
        if is_glass() and not self._bg_is_still():
            if not self._bg_timer.isActive():
                self._bg_last = None
                self._bg_timer.start()
        else:
            self._bg_timer.stop()

    def _apply_glass_window(self):
        """Transparence réelle de la fenêtre et animation du fond, seulement avec le
        thème Claude. Le bureau (KWin « Better Blur », par exemple) peut alors flouter
        ce qui se trouve derrière. Changer la transparence recrée la fenêtre : on le
        fait seulement quand l'état change, et sans toucher au contenu."""
        glass = is_glass()
        for w in self._glass_controls():
            w.setEnabled(glass)
        want = glass and self.transparent.isChecked()
        if want != self._translucent:
            self._translucent = want
            self.setAttribute(Qt.WA_TranslucentBackground, want)
            if not want:
                # Qt pose aussi WA_NoSystemBackground avec la transparence et ne le retire
                # pas en la retirant : la fenêtre resterait sans fond (on verrait le bureau
                # derrière, même avec un thème normal).
                self.setAttribute(Qt.WA_NoSystemBackground, False)
            if self.isVisible():
                # Recréer la fenêtre native : on garde sa place et on la ré-active.
                geometry = self.geometry()
                self.hide()
                self.show()
                self.setGeometry(geometry)
                self.activateWindow()
        self._sync_bg_timer()

    def _react_background(self, d, game):
        """Le fond suit la machine : il rougit quand ça chauffe, ses halos se
        renforcent avec la charge GPU. En jeu avec le mode calme, il se fige (donc
        ne coûte plus de processeur) et n'est redessiné qu'à chaque mesure."""
        temps = [t for t in (d.get("cpu_temp"), d.get("gpu_temp")) if t is not None]
        hot = max(temps) if temps else 0.0
        self._heat = max(0.0, min(1.0, (hot - 70.0) / 20.0))     # 70 °C : 0, 90 °C : 1
        self._gpu_load = max(0.0, min(1.0, (d.get("gpu_pct") or 0.0) / 100.0))
        was = self._in_game
        self._in_game = bool(game and game.get("live"))
        if is_glass():
            if was != self._in_game:
                self._sync_bg_timer()
            if self._bg_is_still():
                self.update()

    def paintEvent(self, event):
        if is_glass():
            self._paint_glass_background()
            return
        # Autres thèmes : fond plein, peint explicitement (ne dépend d'aucun attribut de fenêtre).
        p = QPainter(self)
        p.fillRect(self.rect(), self.palette().window())
        p.end()
        super().paintEvent(event)

    def _grain_brush(self):
        """Grain très fin, calculé une fois : donne de la matière au fond."""
        if self._grain is None:
            rng = random.Random(7)
            img = QImage(96, 96, QImage.Format_ARGB32)
            for y in range(96):
                for x in range(96):
                    v = rng.randint(0, 255)
                    img.setPixelColor(x, y, QColor(v, v, v, rng.randint(0, 14)))
            self._grain = QBrush(img)
        return self._grain

    def _overlay_tile(self, lvl):
        """Une tuile de 96 px (grain + quadrillage de 32 px) répétée sur la fenêtre :
        minuscule à refaire quand l'intensité change, et à la résolution de l'écran
        (écrans HiDPI) pour que les traits restent nets."""
        dpr = self.devicePixelRatioF()
        key = (int(lvl * 100), dpr)
        if self._overlay_key != key:
            side = 96
            pix = QPixmap(int(side * dpr), int(side * dpr))
            pix.setDevicePixelRatio(dpr)
            pix.fill(Qt.transparent)
            q = QPainter(pix)
            q.fillRect(QRectF(0, 0, side, side), self._grain_brush())
            q.setPen(QPen(QColor(255, 255, 255, int(2 + 14 * lvl)), 1))
            for k in range(0, side, 32):
                q.drawLine(k, 0, k, side)
                q.drawLine(0, k, side, k)
            q.end()
            self._overlay, self._overlay_key = pix, key
        return self._overlay

    def _paint_glass_background(self):
        """Fond du thème Claude : dégradé chaud, trois halos qui dérivent lentement,
        grain et quadrillage. Un peu transparent quand la fenêtre l'est, pour laisser
        voir (et flouter) le bureau. Réagit à la machine (voir _react_background).

        Le dégradé et les halos sont flous par nature : on les calcule en petit
        (un quart de la taille) puis on agrandit, ce qui coûte bien moins cher."""
        w, h = self.width(), self.height()
        lvl = glass_level()
        base = 200 if self._translucent else 255
        heat = self._heat
        top = (24 + int(30 * heat), 17, 14)
        bot = (13 + int(18 * heat), 10, 12)

        # Dérive : suit l'horloge, plus vive pendant un jeu (sauf mode calme : figé).
        now = time.monotonic()
        if not self._bg_is_still():
            if self._bg_last is not None:
                speed = 1.6 if self._in_game else 1.0
                self._bg_phase += min(0.3, now - self._bg_last) * speed * 0.7
            self._bg_last = now
        else:
            self._bg_last = None
        t = self._bg_phase

        # Force des halos : curseur d'intensité, charge GPU, et calme pendant un jeu.
        scale = 0.2 + 1.4 * lvl
        scale *= 0.85 + 0.35 * self._gpu_load
        if self._in_game and self.calm.isChecked():
            scale *= 0.65
        accent = claude_orb()
        warm = (255, 80, 60)       # les halos virent à cette couleur quand ça chauffe

        def tint(c, amount=0.85):
            k = heat * amount
            return tuple(int(c[i] * (1 - k) + warm[i] * k) for i in range(3))

        orbs = (
            (0.18 + 0.16 * math.sin(t * 0.23), 0.12 + 0.10 * math.cos(t * 0.19), 0.70, tint(accent), 120),
            (0.86 + 0.10 * math.cos(t * 0.17), 0.50 + 0.14 * math.sin(t * 0.21), 0.75, tint((140, 100, 255), 0.6), 72),
            (0.30 + 0.18 * math.sin(t * 0.15 + 2), 0.96 + 0.05 * math.cos(t * 0.27), 0.70, tint((60, 220, 190), 0.6), 58),
        )

        sw, sh = max(1, w // 4), max(1, h // 4)
        small = QImage(sw, sh, QImage.Format_ARGB32_Premultiplied)
        small.fill(Qt.transparent)
        q = QPainter(small)
        sky = QLinearGradient(0, 0, 0, sh)
        sky.setColorAt(0.0, QColor(*top, base))
        sky.setColorAt(1.0, QColor(*bot, base))
        q.setCompositionMode(QPainter.CompositionMode_Source)
        q.fillRect(small.rect(), sky)
        q.setCompositionMode(QPainter.CompositionMode_SourceOver)
        size = max(sw, sh)
        for fx, fy, fr, (r, g, b), a in orbs:
            glow = QRadialGradient(QPointF(fx * sw, fy * sh), fr * size)
            glow.setColorAt(0.0, QColor(r, g, b, min(255, int(a * scale))))
            glow.setColorAt(1.0, QColor(r, g, b, 0))
            q.fillRect(small.rect(), QBrush(glow))
        q.end()

        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setCompositionMode(QPainter.CompositionMode_Source)    # remplace, ne mélange pas
        p.drawImage(self.rect(), small)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.drawTiledPixmap(self.rect(), self._overlay_tile(lvl))
        p.end()

    # -- handlers ----------------------------------------------------------- #
    def _start_update_checks(self):
        """Une vérification peu après le démarrage, puis une toutes les 6 h.
        Elle ne fait que prévenir : rien ne s'installe sans clic."""
        QTimer.singleShot(5000, self.update_bar.check)
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self.update_bar.check)
        self._update_timer.start(6 * 3600 * 1000)

    def _set_interval(self, v):
        self.sampler.interval_ms = v

    def _toggle_ontop(self, on):
        flag = Qt.WindowStaysOnTopHint
        self.setWindowFlag(flag, on)
        self.show()

    def on_sample(self, d):
        # CPU
        t = d["cpu_temp"]
        freq = f"{d['cpu_freq']/1000:.2f} GHz" if d["cpu_freq"] else "—"
        ttxt = f"{t:.0f}°C" if t is not None else "—"
        power = d.get("cpu_power")
        line = f"{freq} · {power:.0f} W" if power else freq
        self.cpu.update_value(d["cpu_pct"], f"{d['cpu_pct']:.0f}%",
                              f"{line}\n{ttxt}", temp_role(t))

        # GPU
        gpu_name = d["gpu_name"].replace("NVIDIA ", "")
        if self.gpu.hw.text() != gpu_name:
            self.gpu.hw.setText(gpu_name)
            self.vram.hw.setText(gpu_name)
        gt = d["gpu_temp"]
        gttxt = f"{gt:.0f}°C" if gt is not None else "—"
        pw = f"{d['gpu_power']:.0f} W" if d["gpu_power"] else "—"
        self.gpu.update_value(d["gpu_pct"], f"{d['gpu_pct']:.0f}%",
                              f"{pw}\n{gttxt}", temp_role(gt))

        # RAM
        self.ram.update_value(d["ram_pct"], f"{d['ram_pct']:.0f}%",
                              f"{d['ram_used']:.1f} / {d['ram_total']:.1f} {tr('GiB')}")

        # VRAM
        vt, vu = d["vram_total"], d["vram_used"]
        vpct = (vu / vt * 100) if vt else 0
        self.vram.update_value(vpct, f"{vpct:.0f}%",
                               f"{vu/1024:.1f} / {vt/1024:.1f} {tr('GiB')}")

        # Manettes
        self.controllers.update_controllers(d.get("controllers", []))

        # Session de jeu (MangoHud)
        g = d.get("game")
        if g is None:
            self.game.clear()
        else:
            self.game.update_game(g, self.fps_target.value())

        self._react_background(d, g)

        self.started = True
        self.status.setText(
            tr("Updated every {ms} ms").format(ms=self.sampler.interval_ms)
            + f" · {time.strftime('%H:%M:%S')}"
        )

    # -- persistance des réglages ------------------------------------------- #
    def _load_settings(self):
        """Restaure les réglages. Appelé AVANT la création du sampler : on coupe
        les signaux pendant la restauration, sinon _set_interval s'exécuterait
        alors que self.sampler n'existe pas encore."""
        s = app_settings()

        for widget, key, default in (
            (self.interval, "interval_ms", DEFAULT_INTERVAL_MS),
            (self.fps_target, "fps_target", DEFAULT_FPS_TARGET),
        ):
            try:
                value = int(s.value(key, default))
            except (TypeError, ValueError):
                value = default
            widget.blockSignals(True)
            widget.setValue(value)
            widget.blockSignals(False)

        # Thème : le mode est appliqué juste après, par apply_theme().
        mode = s.value("theme", DEFAULT_THEME)
        if mode not in THEME_MODES:
            mode = DEFAULT_THEME
        self.theme_mode = mode
        self.theme.blockSignals(True)
        self.theme.setCurrentIndex(THEME_MODES.index(mode))
        self.theme.blockSignals(False)

        # Langue : les textes sont reposés juste après, par retext().
        lang = s.value("language", DEFAULT_LANG)
        if lang not in LANG_MODES:
            lang = DEFAULT_LANG
        self.lang_mode = lang
        set_language(lang)
        self.lang.blockSignals(True)
        self.lang.setCurrentIndex(LANG_MODES.index(lang))
        self.lang.blockSignals(False)

        # QSettings renvoie les booléens en texte selon le backend.
        if _as_bool(s.value("options_open", False)):
            self.opt_button.setChecked(True)

        ontop = _as_bool(s.value("ontop", False))
        if ontop:
            self.ontop.blockSignals(True)
            self.ontop.setChecked(True)
            self.ontop.blockSignals(False)
            # On applique le drapeau sans appeler show() (la fenêtre n'est pas
            # encore affichée à ce stade).
            self.setWindowFlag(Qt.WindowStaysOnTopHint, True)

        compact = _as_bool(s.value("compact", False))
        self.compact.blockSignals(True)
        self.compact.setChecked(compact)
        self.compact.blockSignals(False)
        self._was_compact = compact
        for box, key, default in ((self.transparent, "transparent_window", False),
                                  (self.bg_anim, "bg_anim", True),
                                  (self.calm, "calm_game", True)):
            box.blockSignals(True)
            box.setChecked(_as_bool(s.value(key, default)))
            box.blockSignals(False)
        try:
            level = max(0, min(100, int(s.value("glass_level", int(DEFAULT_GLASS_LEVEL * 100)))))
        except (TypeError, ValueError):
            level = int(DEFAULT_GLASS_LEVEL * 100)
        self.intensity.blockSignals(True)
        self.intensity.setValue(level)
        self.intensity.blockSignals(False)
        set_glass_level(level / 100.0)
        accent = s.value("claude_accent", DEFAULT_ACCENT)
        if accent not in CLAUDE_ACCENTS:
            accent = DEFAULT_ACCENT
        self.accent.blockSignals(True)
        self.accent.setCurrentIndex(list(CLAUDE_ACCENTS).index(accent))
        self.accent.blockSignals(False)
        set_claude_accent(accent)
        for key, box in self.card_boxes.items():
            box.blockSignals(True)
            box.setChecked(_as_bool(s.value("show_" + key, True)))
            box.blockSignals(False)
        self._apply_layout()

        geo = s.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)

    def _save_settings(self):
        s = app_settings()
        s.setValue("interval_ms", self.interval.value())
        s.setValue("fps_target", self.fps_target.value())
        s.setValue("theme", self.theme_mode)
        s.setValue("language", self.lang_mode)
        s.setValue("options_open", self.opt_button.isChecked())
        s.setValue("ontop", self.ontop.isChecked())
        s.setValue("compact", self.compact.isChecked())
        s.setValue("transparent_window", self.transparent.isChecked())
        s.setValue("bg_anim", self.bg_anim.isChecked())
        s.setValue("calm_game", self.calm.isChecked())
        s.setValue("glass_level", self.intensity.value())
        s.setValue("claude_accent", self.accent.currentData())
        for key, box in self.card_boxes.items():
            s.setValue("show_" + key, box.isChecked())
        s.setValue("geometry", self.saveGeometry())

    def closeEvent(self, e):
        self.update_bar.updater.cancel()     # pas d'installation orpheline
        self._save_settings()
        self.sampler.stop()
        super().closeEvent(e)


def build_palette():
    """Palette Qt du thème actif.

    Indispensable : les éléments dessinés par le style du bureau (flèches des
    compteurs, coche des cases, flèche du menu déroulant) ignorent la feuille de
    style et suivent la palette. Sans ça, un bureau en thème sombre les dessine
    en clair — donc invisibles — dès qu'on passe CachyMonitor en thème clair.
    """
    pal = QPalette()
    bg, card = QColor(col("bg")), QColor(col("card"))
    text, muted = QColor(col("text")), QColor(col("muted"))
    for role, c in (
        (QPalette.Window, bg),
        (QPalette.WindowText, text),
        (QPalette.Base, card),
        (QPalette.AlternateBase, bg),
        (QPalette.Text, text),
        (QPalette.Button, card),
        (QPalette.ButtonText, text),
        (QPalette.ToolTipBase, card),
        (QPalette.ToolTipText, text),
        (QPalette.PlaceholderText, muted),
        (QPalette.Highlight, QColor(col("cpu"))),
        (QPalette.HighlightedText, card),
    ):
        pal.setColor(role, c)
    pal.setColor(QPalette.Disabled, QPalette.Text, muted)
    pal.setColor(QPalette.Disabled, QPalette.WindowText, muted)
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, muted)
    return pal


def build_style():
    """Feuille de style du thème actif (regénérée à chaque changement)."""
    return f"""
QWidget {{ background: {col('bg')}; color: {col('text')}; font-family: 'Inter','Noto Sans',sans-serif; font-size: 13px; }}
/* Sans fond transparent, chaque libellé peint un rectangle de la couleur du
   fond général, visible comme une bande sur les cartes. */
QLabel, QCheckBox {{ background: transparent; }}
#appTitle {{ font-size: 20px; font-weight: 700; }}
#card {{ background: {col('card')}; border-radius: 14px; }}
#cardTitle {{ color: {col('muted')}; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }}
#cardHw {{ font-size: 11px; font-weight: 600; }}
#cardValue {{ font-size: 26px; font-weight: 700; }}
#cardSub {{ color: {col('muted')}; font-size: 12px; }}
#status {{ color: {col('muted')}; font-size: 11px; }}
#options {{ background: {col('card')}; border-radius: 12px; }}
#optButton {{ background: {col('card')}; color: {col('muted')}; border: 1px solid {col('border')}; border-radius: 8px; padding: 5px 12px; font-weight: 600; }}
#optButton:hover {{ color: {col('text')}; }}
#optButton:checked {{ color: {col('cpu')}; border-color: {col('cpu')}; }}
#aboutButton {{ background: {col('bg')}; color: {col('muted')}; border: 1px solid {col('border')}; border-radius: 6px; padding: 3px 10px; }}
#aboutButton:hover {{ color: {col('cpu')}; border-color: {col('cpu')}; }}
#updateBar {{ background: {col('card')}; border: 1px solid {col('cpu')}; border-radius: 10px; }}
#updateLabel {{ color: {col('text')}; font-weight: 600; }}
#updateButton {{ background: {col('cpu')}; color: {col('card')}; border: none; border-radius: 6px; padding: 4px 12px; font-weight: 700; }}
QProgressBar#updateProgress {{ background: {col('bg')}; border: none; border-radius: 4px; }}
QProgressBar#updateProgress::chunk {{ background: {col('cpu')}; border-radius: 4px; }}
QSpinBox, QComboBox {{ background: {col('card')}; color: {col('text')}; border: 1px solid {col('border')}; border-radius: 6px; padding: 2px 6px; }}
/* combobox-popup: 0 => vraie liste déroulante sous le champ, au lieu du menu
   centré sur l'entrée courante que dessinent Breeze et Adwaita. */
QComboBox {{ combobox-popup: 0; }}
QComboBox QAbstractItemView {{ background-color: {col('card')}; color: {col('text')}; border: 1px solid {col('border')}; outline: 0; selection-background-color: {col('cpu')}; selection-color: {col('card')}; }}
/* Le conteneur du menu déroulant est translucide chez certains styles : on lui
   redonne un fond plein, sinon le bureau se voit à travers la liste. */
QComboBox QAbstractItemView::item {{ padding: 3px 6px; }}
QComboBox QListView {{ background-color: {col('card')}; }}
QCheckBox {{ color: {col('muted')}; spacing: 8px; }}
/* L'indicateur est dessiné ici plutôt que laissé au style natif, pour qu'il suive
   le thème de l'application. Le remplissage plein signale l'état coché. */
QCheckBox::indicator {{ width: 15px; height: 15px; border: 1px solid {col('border')}; border-radius: 4px; background: {col('bg')}; }}
QCheckBox::indicator:hover {{ border-color: {col('cpu')}; }}
QCheckBox::indicator:checked {{ background: {col('cpu')}; border-color: {col('cpu')}; }}
QSlider::groove:horizontal {{ height: 4px; background: {col('border')}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {col('cpu')}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {col('cpu')}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}
QSlider:disabled::sub-page:horizontal, QSlider::sub-page:horizontal:disabled {{ background: {col('muted')}; }}
""" + (_GLASS_STYLE.format(accent=col('cpu'), text=col('text'), muted=col('muted'), card=col('card'), border=col('border'),
                          top=int(12 + 40 * glass_level()), bot=int(5 + 16 * glass_level()),
                          edge=int(14 + 40 * glass_level())) if is_glass() else "")


# Thème Claude : surfaces en verre dépoli (blanc très léger, bord fin). Ajouté APRÈS
# la feuille normale pour la surcharger ; les listes déroulantes restent opaques.
_GLASS_STYLE = """
QWidget {{ background: transparent; }}
/* Les fenêtres qui ne sont pas la nôtre gardent un fond plein (la règle ci-dessus
   les viderait) ; placées après elle, ces règles de même poids l'emportent. */
QDialog, QMenu {{ background: {card}; }}
QToolTip {{ background: {card}; color: {text}; border: 1px solid {border}; }}
#card {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255,255,255,{top}), stop:1 rgba(255,255,255,{bot}));
        border: 1px solid rgba(255,255,255,{edge}); border-radius: 18px; }}
#options {{ background: rgba(255,255,255,14); border: 1px solid rgba(255,255,255,26); border-radius: 14px; }}
#optButton {{ background: rgba(255,255,255,16); border: 1px solid rgba(255,255,255,40); border-radius: 10px; }}
#optButton:checked {{ background: rgba(255,138,92,40); }}
#aboutButton {{ background: rgba(255,255,255,12); border: 1px solid rgba(255,255,255,36); }}
#updateBar {{ background: rgba(255,255,255,16); }}
QSpinBox, QComboBox {{ background: rgba(255,255,255,18); border: 1px solid rgba(255,255,255,38); }}
QCheckBox::indicator {{ background: rgba(255,255,255,14); border: 1px solid rgba(255,255,255,50); }}
QSlider::groove:horizontal {{ background: rgba(255,255,255,40); }}
#appTitle {{ font-size: 22px; font-weight: 800; letter-spacing: 1px; color: {text}; }}
#cardTitle {{ letter-spacing: 2px; }}
"""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CachyMonitor")
    # Sans cela, Wayland/KDE voit un programme « python » : l'épingle du
    # panneau n'a plus d'icône et ne relance rien.
    app.setDesktopFileName("cachymonitor")
    here = asset_dir()
    icon_path = os.path.join(here, "cachymonitor.svg")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        app.setWindowIcon(QIcon.fromTheme("utilities-system-monitor"))
    # La palette de départ est posée par MainWindow (apply_theme), qui connaît
    # le mode mémorisé.
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
