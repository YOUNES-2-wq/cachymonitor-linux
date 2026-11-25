# CachyMonitor Linux — notes pour Claude

Moniteur système gaming (Python + PySide6) pour **Linux uniquement**.
`APP_VERSION` (dans `cachymonitor.py`) est la seule source du numéro de version.

## Organisation du code
`cachymonitor.py` ne garde que le point d'entrée : `APP_VERSION`, `MainWindow`, `main()`.
Le reste vit dans `cachymon/` : `config` (constantes, `APP_ROOT`), `i18n` (TRANSLATIONS,
`tr`), `theme`, `sensors` (CPU, RAM, GPU), `controllers` (manettes via /sys), `game`
(statistiques + lecteur MangoHud), `mangohud_conf`, `sampler`, `widgets`, `debug`,
`updater` (mises à jour : logique + installation AUR), `update_bar` (barre d'interface).
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
  pointer vers ce dépôt** (`cachymonitor-linux`), pas vers l'ancien ; dernière version AUR : 1.6.1.

## Mises à jour intégrées (version 1.5.4, portées le 2026-11-21)
`cachymon/updater.py` (logique + fil réseau) et `cachymon/update_bar.py` (barre sous l'en-tête).
**Volontairement minimal** (décision de Younes le 2026-11-21, après 7 revues de code qui
trouvaient chacune de nouveaux cas limites) : une vérification 5 s après le démarrage puis
toutes les 6 h, une barre, un bouton. Rien ne s'installe sans clic : pas de mode
automatique, pas de bouton Redémarrer, pas de nouvelles tentatives, pas de pourcentage.
Ne pas rajouter ces fonctions sans demande explicite de Younes. Paquet AUR : compare la
version AUR (pas GitHub), installe par `yay`/`paru --sudo pkexec` (20 min au plus, arrêt à la
fermeture de la fenêtre). Sources : lien vers la release seulement. **Non testé** :
installation réelle via l'AUR. Tests : `tests/test_updater.py`.

## Thèmes et apparence (version 1.6.0, 2026-11-24)
`cachymon/theme.py` : 21 palettes (`THEMES`), chaque rôle de couleur doit exister dans toutes
(`tests/test_themes.py` vérifie rôles, hexadécimal, libellés traduits et contraste texte/carte).
Le thème **Claude** est « en verre » (`is_glass()`) : `MainWindow.paintEvent` peint un fond
dégradé avec trois halos qui dérivent (calculé en petit puis agrandi, grain et quadrillage en
cache : ~8 % d'un cœur animé, ~0 % figé, mesuré hors écran), les cartes (`HudFrame`) ont
bordure en dégradé et repères d'angle, les jauges des graduations et un dégradé conique.
Réglages propres à Claude (Options, grisés hors Claude) : intensité du verre (défaut 30 %),
couleur d'accent, fond animé, fond calme pendant un jeu (figé), fenêtre transparente
(décochée par défaut : Younes l'a trouvée illisible ; clé `transparent_window`). Le fond
réagit à la machine (rougit entre 70 et 90 °C, halos selon la charge GPU).
Autres nouveautés : jauges animées avec anneau orange/rouge en alerte (température, RAM/VRAM
>= 85/95 %), FPS en grand, bandes de couleur du frametime, mode compact, choix des cartes.
**Piège de test** : fermer une `MainWindow` écrit dans les VRAIS réglages
(`~/.config/CachyMonitor`) ; lancer tout script de test avec `XDG_CONFIG_HOME` isolé.
Le flou du bureau derrière une fenêtre transparente dépend du compositeur (KWin Better Blur
chez Younes), pas de l'appli.

## Matériel de test (le seul vérifié)
Ryzen 5 5600 + RTX 3060 ; CachyOS KDE Wayland. Manette : **DualSense (PS5)**, appairée en
Bluetooth. Le reste (Radeon, Intel, autres manettes) est écrit d'après la documentation du
noyau, jamais testé : le README le dit, ne jamais le présenter comme testé.

## Plan de promotion (en pause, décidé le 04/10/2026)
Faites le 04/10/2026 : description GitHub anglaise + mots-clés ; README principal en
anglais (`README.fr.md` pour le français) ; toutes les releases passées en anglais seul
(Younes ne veut **qu'une langue** par release : l'anglais).
Reste à faire :
1. Post r/linux_gaming : appel aux testeurs Radeon/Intel, écrit en français pour sa
   relecture puis traduit. Dire ouvertement que l'appli est faite avec l'aide d'une IA.
2. r/cachyos + forum/Discord CachyOS, GamingOnLinux, fiche
   AlternativeTo (alternative à MangoHud).
3. GIF ou vidéo de 30 s (jeu + CachyMonitor en double écran, batterie DualSense) en haut
   du README et dans les posts.
Point de départ chiffré (03/10/2026, avant séparation) : 3 étoiles, 12 visiteurs
uniques sur 14 jours, 0 vote AUR, aucune issue.

Pas d'emojis dans les textes rédigés pour Younes ou en son nom.

## Publier une version
1. `ruff check .` et `python -m pytest -q` doivent passer ; lancer l'appli (`python3 cachymonitor.py`).
2. Changer `APP_VERSION`, commit, `git push origin main` (deux commandes séparées), tag `vX.Y.Z`, release GitHub.
3. AUR : `packaging/aur/PKGBUILD` et `.SRCINFO` (fichier caché) sont à jour pour la 1.5.4 (empreinte du tag vérifiée, `makepkg` OK, optdepends `yay`/`polkit` inclus). Pour une nouvelle version : changer `pkgver`, recalculer l'empreinte de l'archive du tag, régénérer `.SRCINFO` (`makepkg --printsrcinfo`). Younes les pousse lui-meme :
`git clone ssh://aur@aur.archlinux.org/cachymonitor.git`, copier les deux fichiers, `git add`,
`git commit`, `git push`. A tester avant avec `makepkg -f`.
