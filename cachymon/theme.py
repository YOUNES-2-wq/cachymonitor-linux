"""CachyMonitor : module theme (voir cachymonitor.py)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from .i18n import DEFAULT_LANG, set_language



set_language(DEFAULT_LANG)


# ----------------------------------------------------------------------------- #
#  Thèmes
# ----------------------------------------------------------------------------- #
#
# Aucune couleur n'est écrite en dur dans le reste du fichier : le code désigne
# un « rôle » (cpu, texte, alerte…) et col() renvoie la teinte du thème actif.
# Changer de thème se résume donc à changer de dictionnaire puis à redessiner.
#
# Le thème clair ne se contente pas d'inverser le fond : les accents y sont
# assombris, sinon un jaune ou un vert pensés pour du noir deviennent illisibles
# sur du blanc.

THEMES = {
    "sombre": {
        "cpu": "#4ca3ff",
        "gpu": "#5ddc7f",
        "ram": "#b48cff",
        "vram": "#ff9d5c",
        "fps": "#ffd23f",
        "ft": "#ff6b8a",    # frametime (les pics = micro-saccades)
        "ok": "#5ddc7f",
        "warn": "#ffb347",
        "bad": "#ff5f56",
        "bg": "#13151b",
        "card": "#1c1f29",
        "text": "#e6e9f0",
        "muted": "#7d8499",
        "ring": "#272b36",   # anneau de fond des jauges
        "border": "#2a2e3a",
    },
    # Noir pur pour les écrans OLED : le fond éteint les pixels. Mêmes accents que le sombre.
    "noir": {
        "cpu": "#4ca3ff",
        "gpu": "#5ddc7f",
        "ram": "#b48cff",
        "vram": "#ff9d5c",
        "fps": "#ffd23f",
        "ft": "#ff6b8a",
        "ok": "#5ddc7f",
        "warn": "#ffb347",
        "bad": "#ff5f56",
        "bg": "#000000",
        "card": "#0b0c10",
        "text": "#e6e9f0",
        "muted": "#7d8499",
        "ring": "#171a21",
        "border": "#1a1d26",
    },
    "clair": {
        "cpu": "#1668d0",
        "gpu": "#12833f",
        "ram": "#7343c8",
        "vram": "#c25d0a",
        "fps": "#a6740a",
        "ft": "#cf2f56",
        "ok": "#12833f",
        "warn": "#b06a00",
        "bad": "#c9271c",
        "bg": "#eef1f6",
        "card": "#ffffff",
        "text": "#1b1f2a",
        "muted": "#66707f",
        "ring": "#dde2ec",
        "border": "#ccd3e0",
    },
    # Midnight
    "midnight": {
        "cpu": "#5aa9ff",
        "gpu": "#4ade80",
        "ram": "#a78bfa",
        "vram": "#fb923c",
        "fps": "#fbbf24",
        "ft": "#f472b6",
        "ok": "#4ade80",
        "warn": "#fbbf24",
        "bad": "#f87171",
        "bg": "#0b1020",
        "card": "#131a2e",
        "text": "#e4e9f7",
        "muted": "#7f8bab",
        "ring": "#1c2542",
        "border": "#222c4d",
    },
    # Graphite
    "graphite": {
        "cpu": "#6ea8fe",
        "gpu": "#6fcf97",
        "ram": "#b69cf0",
        "vram": "#f2994a",
        "fps": "#f2c94c",
        "ft": "#eb7a9c",
        "ok": "#6fcf97",
        "warn": "#f2994a",
        "bad": "#eb5757",
        "bg": "#17181a",
        "card": "#212326",
        "text": "#e3e5e8",
        "muted": "#8a8f98",
        "ring": "#2d3033",
        "border": "#33363a",
    },
    # Aurora
    "aurora": {
        "cpu": "#4fd1e8",
        "gpu": "#6ee7a8",
        "ram": "#b794f4",
        "vram": "#f6ad55",
        "fps": "#f6e05e",
        "ft": "#f687b3",
        "ok": "#6ee7a8",
        "warn": "#f6ad55",
        "bad": "#fc8181",
        "bg": "#0a1a1f",
        "card": "#11272e",
        "text": "#e2f3f1",
        "muted": "#7fa5a8",
        "ring": "#183640",
        "border": "#1d414b",
    },
    # Emerald
    "emerald": {
        "cpu": "#4ecdc4",
        "gpu": "#3ddc84",
        "ram": "#a78bfa",
        "vram": "#ffa94d",
        "fps": "#ffd166",
        "ft": "#ef7aa6",
        "ok": "#3ddc84",
        "warn": "#ffa94d",
        "bad": "#ff6b6b",
        "bg": "#0e1512",
        "card": "#16211c",
        "text": "#e1eee6",
        "muted": "#7f9a8a",
        "ring": "#20302a",
        "border": "#263a32",
    },
    # Nord
    "nord": {
        "cpu": "#88c0d0",
        "gpu": "#a3be8c",
        "ram": "#b48ead",
        "vram": "#d08770",
        "fps": "#ebcb8b",
        "ft": "#e08a9c",
        "ok": "#a3be8c",
        "warn": "#ebcb8b",
        "bad": "#d9777f",
        "bg": "#2e3440",
        "card": "#3b4252",
        "text": "#eceff4",
        "muted": "#97a3ba",
        "ring": "#4c566a",
        "border": "#4c566a",
    },
    # Dracula
    "dracula": {
        "cpu": "#8be9fd",
        "gpu": "#50fa7b",
        "ram": "#bd93f9",
        "vram": "#ffb86c",
        "fps": "#f1fa8c",
        "ft": "#ff79c6",
        "ok": "#50fa7b",
        "warn": "#ffb86c",
        "bad": "#ff5555",
        "bg": "#21222c",
        "card": "#282a36",
        "text": "#f8f8f2",
        "muted": "#8f9bc7",
        "ring": "#3a3d4e",
        "border": "#44475a",
    },
    # Catppuccin Mocha
    "mocha": {
        "cpu": "#89b4fa",
        "gpu": "#a6e3a1",
        "ram": "#cba6f7",
        "vram": "#fab387",
        "fps": "#f9e2af",
        "ft": "#f5c2e7",
        "ok": "#a6e3a1",
        "warn": "#fab387",
        "bad": "#f38ba8",
        "bg": "#11111b",
        "card": "#1e1e2e",
        "text": "#cdd6f4",
        "muted": "#8087a2",
        "ring": "#313244",
        "border": "#313244",
    },
    # Catppuccin Macchiato
    "macchiato": {
        "cpu": "#8aadf4",
        "gpu": "#a6da95",
        "ram": "#c6a0f6",
        "vram": "#f5a97f",
        "fps": "#eed49f",
        "ft": "#f5bde6",
        "ok": "#a6da95",
        "warn": "#f5a97f",
        "bad": "#ed8796",
        "bg": "#181926",
        "card": "#24273a",
        "text": "#cad3f5",
        "muted": "#8087a2",
        "ring": "#363a4f",
        "border": "#363a4f",
    },
    # Catppuccin Frappé
    "frappe": {
        "cpu": "#8caaee",
        "gpu": "#a6d189",
        "ram": "#ca9ee6",
        "vram": "#ef9f76",
        "fps": "#e5c890",
        "ft": "#f4b8e4",
        "ok": "#a6d189",
        "warn": "#ef9f76",
        "bad": "#e78284",
        "bg": "#232634",
        "card": "#303446",
        "text": "#c6d0f5",
        "muted": "#838ba7",
        "ring": "#414559",
        "border": "#414559",
    },
    # Tokyo Night
    "tokyo": {
        "cpu": "#7aa2f7",
        "gpu": "#9ece6a",
        "ram": "#bb9af7",
        "vram": "#ff9e64",
        "fps": "#e0af68",
        "ft": "#f7768e",
        "ok": "#9ece6a",
        "warn": "#e0af68",
        "bad": "#f7768e",
        "bg": "#16161e",
        "card": "#1a1b26",
        "text": "#c0caf5",
        "muted": "#7982a9",
        "ring": "#292e42",
        "border": "#2f334d",
    },
    # Gruvbox
    "gruvbox": {
        "cpu": "#83a598",
        "gpu": "#b8bb26",
        "ram": "#d3869b",
        "vram": "#fe8019",
        "fps": "#fabd2f",
        "ft": "#e86f8f",
        "ok": "#b8bb26",
        "warn": "#fabd2f",
        "bad": "#fb4934",
        "bg": "#1d2021",
        "card": "#282828",
        "text": "#ebdbb2",
        "muted": "#a89984",
        "ring": "#3c3836",
        "border": "#504945",
    },
    # Rosé Pine
    "rosepine": {
        "cpu": "#9ccfd8",
        "gpu": "#8fcfae",
        "ram": "#c4a7e7",
        "vram": "#ebbcba",
        "fps": "#f6c177",
        "ft": "#eb6f92",
        "ok": "#8fcfae",
        "warn": "#f6c177",
        "bad": "#eb6f92",
        "bg": "#191724",
        "card": "#1f1d2e",
        "text": "#e0def4",
        "muted": "#908caa",
        "ring": "#322e4a",
        "border": "#2a2740",
    },
    # One Dark
    "onedark": {
        "cpu": "#61afef",
        "gpu": "#98c379",
        "ram": "#c678dd",
        "vram": "#d19a66",
        "fps": "#e5c07b",
        "ft": "#ff8fa3",
        "ok": "#98c379",
        "warn": "#e5c07b",
        "bad": "#e06c75",
        "bg": "#21252b",
        "card": "#282c34",
        "text": "#abb2bf",
        "muted": "#7f848e",
        "ring": "#353b45",
        "border": "#3e4451",
    },
    # Solarized Dark
    "solarized": {
        "cpu": "#268bd2",
        "gpu": "#859900",
        "ram": "#8087e0",
        "vram": "#e0602a",
        "fps": "#b58900",
        "ft": "#e0509f",
        "ok": "#859900",
        "warn": "#b58900",
        "bad": "#f0504b",
        "bg": "#002b36",
        "card": "#073642",
        "text": "#93a1a1",
        "muted": "#7a9097",
        "ring": "#0f4552",
        "border": "#124a59",
    },
    # Catppuccin Latte
    "latte": {
        "cpu": "#1e66f5",
        "gpu": "#2f8a1f",
        "ram": "#8839ef",
        "vram": "#d9520a",
        "fps": "#b9770e",
        "ft": "#d6409f",
        "ok": "#2f8a1f",
        "warn": "#b9770e",
        "bad": "#d20f39",
        "bg": "#dce0e8",
        "card": "#eff1f5",
        "text": "#4c4f69",
        "muted": "#6c6f85",
        "ring": "#ccd0da",
        "border": "#bcc0cc",
    },
    # Nord Light
    "nordclair": {
        "cpu": "#5e81ac",
        "gpu": "#5f8445",
        "ram": "#8f6a8c",
        "vram": "#c0643f",
        "fps": "#a8801f",
        "ft": "#bf616a",
        "ok": "#5f8445",
        "warn": "#a8801f",
        "bad": "#bf616a",
        "bg": "#d8dee9",
        "card": "#eceff4",
        "text": "#2e3440",
        "muted": "#5e6b82",
        "ring": "#d8dee9",
        "border": "#c3cad8",
    },
    # Solarized Light
    "solarizedclair": {
        "cpu": "#268bd2",
        "gpu": "#738500",
        "ram": "#6c71c4",
        "vram": "#cb4b16",
        "fps": "#9a7400",
        "ft": "#d33682",
        "ok": "#738500",
        "warn": "#9a7400",
        "bad": "#dc322f",
        "bg": "#eee8d5",
        "card": "#fdf6e3",
        "text": "#586e75",
        "muted": "#6f8588",
        "ring": "#eee8d5",
        "border": "#d9d2bd",
    },
    # Claude : chaud et vitré. Corail Claude en accent, fond dégradé animé et cartes
    # en verre (voir MainWindow.paintEvent et build_style, qui le traitent à part).
    "claude": {
        "cpu": "#f09470",
        "gpu": "#6fd6b8",
        "ram": "#a99be8",
        "vram": "#e6b95a",
        "fps": "#f2a07e",
        "ft": "#e8799f",
        "ok": "#6fd6b8",
        "warn": "#e6b95a",
        "bad": "#ee6b6b",
        "bg": "#120e0d",
        "card": "#1d1613",
        "text": "#f4ece4",
        "muted": "#a69488",
        "ring": "#2a201b",
        "border": "#3a2c25",
    },
}

# Modes proposés à l'utilisateur. « système » suit le réglage du bureau.
THEME_MODES = ("systeme", "sombre", "noir", "midnight", "graphite", "aurora", "emerald", "nord", "dracula", "mocha", "macchiato", "frappe", "tokyo", "gruvbox", "rosepine", "onedark", "solarized", "claude", "clair", "latte", "nordclair", "solarizedclair")
THEME_LABELS = {
    "systeme": "System",
    "sombre": "Dark",
    "noir": "Black (OLED)",
    "midnight": "Midnight",
    "graphite": "Graphite",
    "aurora": "Aurora",
    "emerald": "Emerald",
    "nord": "Nord",
    "dracula": "Dracula",
    "mocha": "Catppuccin Mocha",
    "macchiato": "Catppuccin Macchiato",
    "frappe": "Catppuccin Frappé",
    "tokyo": "Tokyo Night",
    "gruvbox": "Gruvbox",
    "rosepine": "Rosé Pine",
    "onedark": "One Dark",
    "solarized": "Solarized Dark",
    "claude": "Claude",
    "clair": "Light",
    "latte": "Catppuccin Latte",
    "nordclair": "Nord Light",
    "solarizedclair": "Solarized Light",
}
DEFAULT_THEME = "systeme"

_palette = THEMES["sombre"]
_name = "sombre"


def col(role):
    """Couleur du rôle demandé dans le thème actif."""
    return _palette[role]


def set_palette(theme):
    """Active une palette ('sombre' ou 'clair')."""
    global _palette, _name
    _palette = THEMES[theme]
    _name = theme


# Réglages du thème Claude : intensité du verre (0 = discret, 1 = néon), couleur d'accent.
DEFAULT_GLASS_LEVEL = 0.30
_glass_level = DEFAULT_GLASS_LEVEL
# nom affiché, couleur principale, couleur des FPS, halo du fond (RGB)
CLAUDE_ACCENTS = {
    "coral":  ("Coral",  "#f09470", "#f2a07e", (217, 119, 87)),
    "cyan":   ("Cyan",   "#6cc8e8", "#86d4ee", (70, 170, 210)),
    "violet": ("Violet", "#b39cf0", "#c2b0f4", (140, 110, 230)),
    "green":  ("Green",  "#6fd6a0", "#86deb2", (70, 190, 140)),
    "amber":  ("Amber",  "#e8b45c", "#eec27a", (220, 160, 60)),
    "rose":   ("Rose",   "#e87fa8", "#ee98ba", (215, 100, 140)),
}
DEFAULT_ACCENT = "coral"
_claude_orb = CLAUDE_ACCENTS[DEFAULT_ACCENT][3]


def glass_level():
    return _glass_level


def set_glass_level(value):
    global _glass_level
    _glass_level = max(0.0, min(1.0, float(value)))


def set_claude_accent(key):
    """Change la couleur d'accent du thème Claude (couleur principale, FPS, halo)."""
    global _claude_orb
    if key not in CLAUDE_ACCENTS:
        key = DEFAULT_ACCENT
    _, main, fps, orb = CLAUDE_ACCENTS[key]
    THEMES["claude"]["cpu"] = main
    THEMES["claude"]["fps"] = fps
    _claude_orb = orb


def claude_orb():
    return _claude_orb


def is_glass():
    """True pour le thème Claude : fond dégradé animé, cartes en verre, jauges néon."""
    return _name == "claude"


def system_theme():
    """Thème du bureau, via Qt. Replié sur 'sombre' si le bureau ne dit rien.

    Qt 6.5+ rapporte le réglage du bureau.
    """
    scheme = QApplication.instance().styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Light:
        return "clair"
    if scheme == Qt.ColorScheme.Dark:
        return "sombre"
    return "sombre"


def resolve_theme(mode):
    """Traduit un mode ('systeme'/'sombre'/'clair') en palette réelle."""
    return system_theme() if mode == "systeme" else mode


def temp_role(t):
    """Rôle de couleur d'une température (None = inconnue)."""
    if t is None:
        return "muted"
    if t >= 85:
        return "bad"
    if t >= 70:
        return "warn"
    return "ok"
