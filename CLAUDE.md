# CachyMonitor Linux — notes pour Claude

Moniteur système gaming (Python + PySide6) pour **Linux uniquement**. Dépôt issu de la
séparation (21/11/2026) du projet CachyMonitor : la version Windows vit dans
https://github.com/YOUNES-2-wq/cachymonitor (dépôt séparé, aucun code Windows ici, et
aucun code Linux là-bas). Ce dépôt ne mentionne Windows que par un lien dans le README.
`APP_VERSION` (dans `cachymonitor.py`) est la seule source du numéro de version.

## Organisation du code
`cachymonitor.py` ne garde que le point d'entrée : `APP_VERSION`, `MainWindow`, `main()`.
Le reste vit dans `cachymon/` : `config` (constantes, `APP_ROOT`), `i18n` (TRANSLATIONS,
`tr`), `theme`, `sensors` (CPU, RAM, GPU), `controllers` (manettes via /sys), `game`
(statistiques + lecteur MangoHud), `mangohud_conf`, `sampler`, `widgets`, `debug`.
Piège : une globale réécrite (`global X`) doit rester dans le module qui la définit.

## Contrôles avant une release
- `ruff check .` (réglages dans `pyproject.toml`) et `python -m pytest -q` : doivent passer.
  La CI GitHub (`.github/workflows/tests.yml`) les lance.
- `tests/conftest.py` isole le journal de débogage : aucun test n'écrit dans le vrai
  `~/.cache/cachymonitor/debug.log`.
- Option `--debug` (ou `CACHYMONITOR_DEBUG=1`) : écrit les erreurs normalement avalées dans
  `~/.cache/cachymonitor/debug.log`. À demander aux testeurs Radeon/Intel avec la sortie
  de `scripts/hw-report.sh`.

## Avec qui on travaille
Younes (GitHub `YOUNES-2-wq`, AUR `younes-2`) : gamer, **pas développeur**. Toujours répondre
**en français**, expliquer simplement, demander avant les actions publiques.

## Distribution
- **AUR** `cachymonitor` (dépôt séparé `ssh://aur@aur.archlinux.org/cachymonitor.git`,
  PKGBUILD qui télécharge l'archive du tag GitHub). **Après la séparation, le PKGBUILD doit
  pointer vers ce dépôt** (`cachymonitor-linux`), pas vers l'ancien ; dernière version AUR : 1.5.2.
- Flathub : voir plus bas.

## Matériel de test (le seul vérifié)
Ryzen 5 5600 + RTX 3060 ; CachyOS KDE Wayland. Manette : **DualSense (PS5)**, appairée en
Bluetooth. Le reste (Radeon, Intel, autres manettes) est écrit d'après la documentation du
noyau, jamais testé : le README le dit, ne jamais le présenter comme testé.

## Version Flathub (en cours, 04/10/2026)
**Règle de Flathub sur l'IA** (docs.flathub.org, "Generative AI policy", lue le 04/10/2026) :
le manifeste ne doit contenir **aucun contenu écrit ou assisté par IA** (la divulgation
n'y change rien) ; une IA ne doit ni ouvrir la PR de soumission ni écrire ses commits,
descriptions ou réponses de revue ; le code de l'appli généré par IA doit être déclaré,
avec son ampleur, et un relecteur peut refuser sans examen. **Claude n'écrit donc jamais
le manifeste, le `metainfo.xml` ni la PR** : Younes les écrit, Claude explique les champs
et relit ou débogue. Claude peut modifier le code de l'appli (à déclarer comme tel).

**Acquis** : identifiant `io.github.YOUNES_2_wq.CachyMonitor` (confirmé : `_` devient `-`
dans l'URL GitHub). Un Flatpak jetable (jamais à soumettre) a été construit avec le runtime
`org.kde.Platform` 6.11 et la base `io.qt.PySide.BaseApp` 6.11 ; construction par
`flatpak run org.flatpak.Builder --user --install --state-dir=...` (flatpak-builder n'est
pas installé en paquet, `--state-dir` doit être sur le même disque que le dossier de build).

**Résultats dans le sandbox**, vérifiés sur la RTX 3060 :
- GPU NVIDIA : `nvidia-smi` est absent, mais l'extension NVIDIA fournit `libnvidia-ml`.
  Corrigé en 04/10/2026 par une lecture NVML (ctypes) dans `cachymonitor.py`. OK.
- CPU, températures, manette (DualSense), `lspci` : OK. FPS : OK avec SuperTuxKart.
- `dmidecode` absent : la RAM (type, vitesse) restera à `—`, accepté.
- Logs MangoHud : le Goverlay de Younes écrit dans `~/.local/share/goverlay` ; le prototype
  a eu besoin de `--filesystem=xdg-data/goverlay:ro` (et `xdg-data/MangoHud:ro`).
  Le bouton "Activer le logging" écrit dans `~/.config/MangoHud` : bloqué par le sandbox,
  non testé. Un jeu Steam en Flatpak écrit ses logs dans `~/.var/app/com.valvesoftware.Steam/`.

**Reste à décider/faire** (par Younes) : quelles permissions demander (Flathub veut le
minimum et préfère les portails), écrire le manifeste, le `metainfo.xml` (captures dans
`docs/`, `content_rating` OARS, licence MIT, liste des versions), le `.desktop` et l'icône
renommés selon l'identifiant, tester avec `flatpak-builder-lint`, puis la PR sur
`github.com/flathub/flathub` (branche `new-pr`) ; revue humaine de quelques jours à
plusieurs semaines. Risque : refus à cause de la part d'IA. Prototype à désinstaller après :
`flatpak uninstall --user io.github.YOUNES_2_wq.CachyMonitor`.

## Plan de promotion (en pause, décidé le 04/10/2026)
Faites le 04/10/2026 : description GitHub anglaise + mots-clés ; README principal en
anglais (`README.fr.md` pour le français) ; toutes les releases passées en anglais seul
(Younes ne veut **qu'une langue** par release : l'anglais).
Reste, à reprendre après Flathub :
1. Post r/linux_gaming : appel aux testeurs Radeon/Intel, écrit en français pour sa
   relecture puis traduit. Dire ouvertement que l'appli est faite avec l'aide d'une IA.
2. r/cachyos + forum/Discord CachyOS, GamingOnLinux, fiche
   AlternativeTo (alternative à MangoHud).
3. GIF ou vidéo de 30 s (jeu + CachyMonitor en double écran, batterie DualSense) en haut
   du README et dans les posts.
Point de départ chiffré (03/10/2026, avant séparation) : 3 étoiles, 12 visiteurs
uniques sur 14 jours, 0 vote AUR, aucune issue.

Pas d'emojis dans les textes rédigés pour Younes ou en son nom.
