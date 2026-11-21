"""Tests des calculs purs : ils ne demandent ni materiel ni ecran.

Ce sont eux qui protegent le plus contre une regression discrete (une jauge qui
ment, un 1% low faux) quand on retouche le code sans le materiel d'origine.
"""
import pytest

from cachymon.config import _as_bool
from cachymon.controllers import _clean_controller_name
from cachymon.game import _percentile, game_stats, bottleneck, MangoHudGameReader
from cachymon.theme import temp_role
from cachymon.widgets import battery_role


@pytest.mark.parametrize("valeur,attendu", [
    (True, True), (False, False), ("true", True), ("false", False),
    ("1", True), ("0", False), (None, False),
])
def test_as_bool(valeur, attendu):
    assert _as_bool(valeur) == attendu


# -- percentiles et statistiques de jeu ------------------------------------ #
def test_percentile_vide_et_bornes():
    assert _percentile([], 0.5) is None
    vals = [10.0, 20.0, 30.0, 40.0]
    assert _percentile(vals, 0.0) == 10.0
    assert _percentile(vals, 1.0) == 40.0


def _session(fps_list, pas=0.1, debut=10.0):
    return [(debut + i * pas, f, 1000.0 / f) for i, f in enumerate(fps_list)]


def test_game_stats_vide():
    assert game_stats([], True, "x") is None


def test_game_stats_valeurs_simples():
    st = game_stats(_session([100.0] * 50), True, "Jeu")
    assert st["avg"] == pytest.approx(100.0)
    assert st["min"] == st["max"] == 100.0
    assert st["fps"] == 100.0 and st["name"] == "Jeu"
    assert st["samples"] == 50


def test_game_stats_low_voit_les_saccades():
    fps = [100.0] * 98 + [20.0, 20.0]
    st = game_stats(_session(fps), True, "Jeu")
    assert st["low1"] < 50          # le 1% low doit refleter les chutes
    assert st["avg"] > 90           # la moyenne, peu


def test_game_stats_hors_ligne_masque_le_fps_courant():
    st = game_stats(_session([60.0] * 10), False, "Jeu")
    assert st["fps"] is None and st["frametime"] is None


def test_game_stats_fenetre_glissante():
    # Un trou de chargement tres ancien (hors fenetre de 60 s) ne doit plus peser.
    ancien = [(0.0 + i * 0.1, 5.0, 200.0) for i in range(20)]
    recent = [(200.0 + i * 0.1, 100.0, 10.0) for i in range(100)]
    st = game_stats(ancien + recent, True, "Jeu")
    assert st["low01"] == pytest.approx(100.0)
    assert st["min"] == 5.0         # mais le minimum de session, lui, le garde


def test_game_stats_extra():
    st = game_stats(_session([60.0] * 5), True, "Jeu", extra={"source": "X"})
    assert st["source"] == "X"


# -- goulot d'etranglement ------------------------------------------------- #
def test_bottleneck_inconnu():
    assert bottleneck(None, 50) == (None, None)
    assert bottleneck(50, None) == (None, None)


@pytest.mark.parametrize("cpu,gpu,role", [
    (40, 99, "gpu"), (90, 60, "cpu"), (30, 30, "muted"), (82, 88, "muted"),
])
def test_bottleneck_roles(cpu, gpu, role):
    assert bottleneck(cpu, gpu)[1] == role


# -- couleurs -------------------------------------------------------------- #
@pytest.mark.parametrize("t,role", [
    (None, "muted"), (40, "ok"), (69.9, "ok"), (70, "warn"), (84.9, "warn"), (85, "bad"),
])
def test_temp_role(t, role):
    assert temp_role(t) == role


@pytest.mark.parametrize("pct,role", [
    (None, "muted"), (100, "ok"), (51, "ok"), (50, "warn"), (21, "warn"), (20, "bad"), (0, "bad"),
])
def test_battery_role(pct, role):
    assert battery_role(pct) == role


def test_nom_de_manette_sans_prefixe_constructeur():
    assert _clean_controller_name("Sony Interactive Entertainment DualSense Wireless Controller") \
        == "DualSense Wireless Controller"


# -- lecture d'un log MangoHud -------------------------------------------- #
def _csv(tmp_path, lignes):
    p = tmp_path / "monjeu_2026-01-02_03-04-05.csv"
    p.write_text("fps,frametime,cpu_load,gpu_load,gpu_vram_used,elapsed\n"
                 + "\n".join(lignes) + "\n")
    return p


def test_mangohud_nom_du_jeu():
    assert MangoHudGameReader._game_name("/x/urban_terror_2026-07-20_12-40-15.csv") == "Urban Terror"


def test_mangohud_ignore_chargement_et_images_nulles(tmp_path):
    ns = 1_000_000_000
    lignes = [f"0,0,10,10,100,{0}",              # image a 0 fps au lancement
              f"90,11,10,10,100,{1 * ns}",       # dans les 5 s de chauffe
              f"100,10,20,70,2048,{6 * ns}",
              f"120,8.3,30,80,2048,{7 * ns}"]
    r = MangoHudGameReader()
    r._reset_for(str(_csv(tmp_path, lignes)))
    r._consume(r._path)
    assert [s[1] for s in r._samples] == [100.0, 120.0]
    assert r._last["gpu_load"] == 80.0


def test_mangohud_lecture_incrementale(tmp_path):
    ns = 1_000_000_000
    # 1re ligne a 0 fps : elle fixe l'origine du temps, puis la chauffe de 5 s passe.
    p = _csv(tmp_path, ["0,0,0,0,0,0", f"100,10,20,70,2048,{6 * ns}"])
    r = MangoHudGameReader()
    r._reset_for(str(p))
    r._consume(r._path)
    assert len(r._samples) == 1
    with open(p, "a") as f:
        f.write(f"110,9,20,70,2048,{7 * ns}\n")
    r._consume(r._path)
    assert len(r._samples) == 2             # pas de doublon a la 2e lecture


def test_mangohud_en_tete_sans_fps(tmp_path):
    r = MangoHudGameReader()
    assert r._parse_header("a,b,c") is None


def test_mangohud_ligne_coupee_attend_la_suite(tmp_path):
    ns = 1_000_000_000
    p = _csv(tmp_path, ["0,0,0,0,0,0", f"100,10,20,70,2048,{6 * ns}"])
    r = MangoHudGameReader()
    r._reset_for(str(p))
    r._consume(r._path)
    assert len(r._samples) == 1
    # MangoHud n'a écrit que le début de la ligne suivante : rien ne doit être pris.
    with open(p, "a") as f:
        f.write("14")
    r._consume(r._path)
    assert len(r._samples) == 1
    # La ligne est complétée : elle est lue entière, avec la bonne valeur.
    with open(p, "a") as f:
        f.write(f"4,9,20,70,2048,{7 * ns}\n")
    r._consume(r._path)
    assert [s[1] for s in r._samples] == [100.0, 144.0]


def test_mangohud_ignore_le_fichier_resume(tmp_path, monkeypatch):
    from cachymon import game
    (tmp_path / "jeu_summary.csv").write_text("a,b\n1,2\n")
    (tmp_path / "jeu_2026-01-02_03-04-05.csv").write_text("fps\n60\n")
    # Le résumé est plus récent que le log : il ne doit pas être choisi.
    import os
    old = (tmp_path / "jeu_2026-01-02_03-04-05.csv")
    os.utime(old, (1_000_000, 1_000_000))
    monkeypatch.setattr(game, "FPS_LOG_DIRS", [str(tmp_path)])
    path, _ = MangoHudGameReader._newest_log()
    assert path.endswith("jeu_2026-01-02_03-04-05.csv")


def test_config_mangohud_sauvegarde_d_origine_gardee(tmp_path, monkeypatch):
    from cachymon import mangohud_conf as mc
    conf = tmp_path / "MangoHud.conf"
    conf.write_text("fps_limit=60\n")
    monkeypatch.setenv("MANGOHUD_CONFIGFILE", str(conf))
    monkeypatch.setattr(mc, "MANGOHUD_LOG_DIR", str(tmp_path / "logs"))
    mc.enable_mangohud_logging()
    mc.set_mangohud_hud_hidden(True)
    bak = (tmp_path / "MangoHud.conf.cachymonitor.bak").read_text()
    assert bak == "fps_limit=60\n"      # l'original, pas la version modifiée
