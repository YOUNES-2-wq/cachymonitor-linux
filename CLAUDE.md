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
  pointer vers ce dépôt** (`cachymonitor-linux`), pas vers l'ancien ; dernière version AUR : 1.5.2.

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
3. AUR : `packaging/aur/PKGBUILD` et `.SRCINFO` sont prets pour la 1.5.3 (source = archive du tag GitHub ; recalculer l'empreinte après chaque tag). **A la release 1.5.4** : passer `pkgver`, et ajouter les optdepends `yay` (ou paru) et `polkit` (mises à jour intégrées). Younes les pousse lui-meme :
`git clone ssh://aur@aur.archlinux.org/cachymonitor.git`, copier les deux fichiers, `git add`,
`git commit`, `git push`. A tester avant avec `makepkg -f`.
