# CachyMonitor

**English** | [Français](README.fr.md)

A lightweight gaming system monitor for a second screen: **CPU, GPU, RAM, VRAM,
temperatures and FPS** with real-time graphs, session statistics (1% low, 0.1% low,
frametime, CPU/GPU bottleneck) and your **controller's battery level**. One Python
application for **Linux**, with a single dependency (PySide6).

```sh
paru -S cachymonitor                 # Arch, CachyOS, Manjaro...
```

Other Linux distributions: see [manual install](#manual-install-any-distribution).

> Independent community project, made by a CachyOS user. **Not affiliated with the
> official CachyOS team**; the name is just a nod to the distribution.

![CachyMonitor, dark theme](docs/screenshot.png)

*CPU / GPU / RAM / VRAM gauges with temperatures and trend graphs. At the bottom, the
session statistics: FPS, 1% low, 0.1% low, frametime and CPU/GPU bottleneck.*

![CachyMonitor, light theme with the Options panel open](docs/screenshot-clair.png)

*Light theme with the Options panel open: refresh interval, FPS target, theme (light /
dark / system), language and always-on-top.*

![CachyMonitor on a second screen during a game](docs/double-ecran.jpg)

**The perfect app for my second screen.**

> **Language**: the interface follows the system language by default (`LANG`/`LC_ALL`): **French** if your desktop is in French,
> **English** everywhere else. You can also switch it live in **Options > Language**
> (System / English / Français); the choice is remembered. Adding a language means
> adding an entry to the `TRANSLATIONS` dictionary at the top of `cachymonitor.py`.
> Contributions are welcome.

## Why CachyMonitor?

I'm a gamer and I play a lot of games on CachyOS. I wanted an app that could monitor my
hardware and tell me as much as possible about how my components behave while I play,
but I couldn't find a system monitor designed specifically for gaming. So I decided to
make my own.

**I'm not a developer.** I built CachyMonitor with a lot of help from an AI assistant,
Claude. I'm saying this upfront because I think you should know. The result surprised me
so much that I wanted to share it with anyone who'd like to try it. The whole program is
a single readable Python file, so anyone can check what it does.

## What it does

CachyMonitor builds on **[MangoHud](https://github.com/flightlessmango/MangoHud)**,
the reference tool for recording in-game performance. But where MangoHud shows an
**overlay on top of the game**, CachyMonitor **turns its logs into real session
statistics** in a separate window.

It is a companion window, separate from the game, that brings together in one interface:

- **computed session statistics**: 1% low, 0.1% low, average, frametime spikes
  (micro-stutters) and a **CPU vs GPU bottleneck** indicator;
- **live component gauges**: CPU, GPU, RAM, VRAM, clock speeds, power draw and
  temperatures, with trend graphs;
- **no overlay** drawn on top of the game, in a light app (one Python file, one
  dependency);
- your **controller**: model, wired or Bluetooth connection and battery level, so it
  doesn't die on you mid-game;
- **21 themes** (light, dark, OLED black, Nord, Dracula, Catppuccin, Tokyo Night, Gruvbox... and a
  frosted-glass "Claude" theme), chosen by you or following your desktop automatically;
- a **compact mode** and a choice of which cards to show.

The building blocks already existed (MangoHud, GOverlay...), but as far as I
know nobody had put them together into a **companion dashboard built for gaming**. That's
the whole idea: not reinventing the measurements, but making them **readable and easy to
analyse**. Many thanks to the MangoHud team, without whom none of this would be possible.

## Install on Linux

> **CachyMonitor works on any Linux distribution** (Arch, CachyOS, Fedora, Ubuntu,
> Debian, openSUSE, Pop!\_OS...). It only reads standard kernel sources (`/proc`,
> `/sys`, `hwmon`), `nvidia-smi` and MangoHud logs: nothing is distribution-specific.
> The only difference between distros is how you install the dependency (**PySide6**).
>
> - **Arch-based distros** (CachyOS, Manjaro, EndeavourOS...): one-command install from
>   the **AUR** (below).
> - **All other distros**: manual install from Git (further down).
>
> **X11 and Wayland**: no data goes through the display server, and Qt6 handles both.
> Tested on both. One thing to know: the "always on top" option is always honoured on
> X11, while many Wayland compositors ignore that request from an application. That's
> not a CachyMonitor bug.

### From the AUR (recommended on Arch-based distros)

[![AUR version](https://img.shields.io/aur/version/cachymonitor?label=AUR&color=1793d1&cacheSeconds=600)](https://aur.archlinux.org/packages/cachymonitor)

With an AUR helper, for example `paru`:

```sh
paru -S cachymonitor
```

or `yay`:

```sh
yay -S cachymonitor
```

Then launch **CachyMonitor** from your application menu, or run `cachymonitor`.

**Updates.** The app checks for a new version shortly after it starts, then every 6 hours (AUR for the package, GitHub releases otherwise): one request to `aur.archlinux.org` or `api.github.com`, with nothing about you in it. A bar tells you when one exists; nothing is installed without your click. For the AUR package, the button runs `yay`/`paru` (with `pkexec` for the password).

### Manual install (any distribution)

Works everywhere: all you need is **Python 3** (already present on every distro) and
**PySide6**.

**1. Install PySide6** with your distro's package manager:

```sh
# Arch / CachyOS / Manjaro
sudo pacman -S pyside6

# Fedora
sudo dnf install python3-pyside6

# Ubuntu / Debian / Pop!_OS / Mint
# Debian splits PySide6 into one package per Qt module: there is no global
# "python3-pyside6" package. CachyMonitor only needs these three.
sudo apt install python3-pyside6.qtcore python3-pyside6.qtgui python3-pyside6.qtwidgets

# openSUSE
sudo zypper install python3-PySide6
```

> If PySide6 isn't packaged on your distro, you can still install it with pip
> (ideally in a virtual environment): `pip install PySide6`.

**2. Clone the repository:**

```sh
git clone https://github.com/YOUNES-2-wq/cachymonitor-linux.git
```

**3. Run the app:**

```sh
python3 cachymonitor-linux/cachymonitor.py
```

**4. (Optional) Add CachyMonitor to your application menu**, from the folder where you
cloned the repository. The bundled launcher targets a system-wide (AUR) install; this
command makes a copy that points to your clone.

```sh
mkdir -p ~/.local/share/applications && sed -e "s|^Exec=.*|Exec=python3 $PWD/cachymonitor-linux/cachymonitor.py|" -e "s|^Icon=.*|Icon=$PWD/cachymonitor-linux/cachymonitor.svg|" cachymonitor-linux/cachymonitor.desktop > ~/.local/share/applications/cachymonitor.desktop
```

> Optional, depending on your hardware: `mangohud` (in-game statistics), `nvidia-utils`
> (NVIDIA GPU), `pciutils` (GPU name), `dmidecode` (RAM type/speed). Each one installs
> the same way on your distro (`dnf`, `apt`, `zypper`...).

## Data sources

| Metric          | Source                                   |
|-----------------|------------------------------------------|
| CPU usage/core  | `/proc/stat`                             |
| CPU clock       | `scaling_cur_freq`                       |
| CPU temperature | hwmon `k10temp` / `coretemp`             |
| RAM             | `/proc/meminfo` + `dmidecode`            |
| GPU / VRAM      | `nvidia-smi` (or NVML), `amdgpu`, `i915` |
| FPS / session   | **MangoHud** CSV logs                    |
| Controllers     | `/sys/class/input` + `power_supply`      |

## Enable FPS (MangoHud)

FPS comes from MangoHud's **CSV logs**, not from the on-screen overlay: having the
MangoHud HUD visible in game **is not enough**, MangoHud must also *record* a log (which
it doesn't do by default).

**The easy way**: if CachyMonitor finds no log, it shows a message and an **"Enable
MangoHud logging"** button. One click (after confirmation) adds the right lines to your
config, with a backup (`MangoHud.conf.cachymonitor.bak`). Then restart the game.

**By hand**: add this to `~/.config/MangoHud/MangoHud.conf`:

```ini
output_folder=~/.local/share/MangoHud/logs
autostart_log=1
log_interval=100
log_duration=86400
```

> `log_duration`: without it, recording stops after 30 seconds and the FPS disappears.
> You can also start recording on the fly with the `toggle_logging` key (Left Shift + F2
> by default with GOverlay).

Then launch a game with MangoHud:

- **Steam**: game properties > launch options: `mangohud %command%`
- **Directly**: `mangohud <game>`

As soon as a game is running and writing a log, CachyMonitor shows the FPS automatically
(and goes back to `—` a few seconds after the game closes).

> The folders it searches can be changed at the top of the script (`FPS_LOG_DIRS`).

## Hardware compatibility

CachyMonitor aims to support **any hardware**, but not everything has been verified.

| | CPU | GPU |
|---|---|---|
| **AMD** | Tested (`k10temp`) | Written, untested (`amdgpu` via `/sys`) |
| **Intel** | Written, untested (`coretemp`) | Partial, untested (`i915`/`xe`) |
| **NVIDIA** | — | Tested (`nvidia-smi`) |

**Controllers**: tested with a **DualSense (PS5) over Bluetooth**. Xbox
controllers (`xpad` / `xpadneo` drivers), Switch Pro and DualShock 4 use the same kernel
files and should work, but haven't been tried. A controller whose driver doesn't publish
its battery still shows up, with `—` instead of a percentage.

**Actually verified setup**: AMD Ryzen 5 5600 + NVIDIA RTX 3060, on
CachyOS / KDE Plasma / Wayland.

Everything else is written from the kernel documentation, without hardware at hand to
run it. The app won't crash if a sensor is missing: that value just shows `—`.

Note for Intel GPUs: utilisation isn't exposed in `/sys` and requires `intel_gpu_top`
with root rights. So only the name, temperature and clock speed are read. VRAM is shared
memory, with no dedicated counter.

### I need your help

I made CachyMonitor on my own, and I have **only one machine** to test it on (AMD
Ryzen 5 5600 + NVIDIA RTX 3060). In other words: **I have no idea how the app behaves
on any hardware other than mine.**

A Radeon, an Intel CPU, an integrated GPU... every setup is different, and without you
those cases stay blind spots. Your feedback is the only way for me to know how
the app reacts on your hardware, and so to improve it for everyone.

You don't need to be a developer or run anything. A simple message such as "everything
works for me" or "the GPU temperature shows `—`" already helps a lot. Tell me your setup
and what you see. It really matters to me.

**[Leave a comment (Discussions)](https://github.com/YOUNES-2-wq/cachymonitor-linux/discussions)**

<details>
<summary>Optional: attach a detailed hardware report</summary>

If you'd like to help further, a small script generates a report of your sensors. It is
**read-only**, **never** asks for root rights and shows **no** personal data. You can
open and read it before running it:

```bash
cat scripts/hw-report.sh   # inspect it first
./scripts/hw-report.sh     # then run it if you want
```

Paste its output in a comment or an
[issue](https://github.com/YOUNES-2-wq/cachymonitor-linux/issues).
</details>

## License

[MIT](LICENSE): you can use, modify and redistribute this code freely, as long as you
keep the copyright notice.
