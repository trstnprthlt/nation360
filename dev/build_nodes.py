#!/usr/bin/env python3
"""
Convertit data/photos.csv en data/nodes.json (liens entre photos calculés automatiquement).

Usage :  python3 tools/build_nodes.py [--distance-max 130]

Colonnes de photos.csv (séparateur ; ou ,) :
  id       identifiant unique de la photo            ex. N1_012
  nom      libellé affiché dans la visite             ex. Couloir A - vers sortie 3
  niveau   clé du niveau (voir data/levels.json)      ex. -1
  x, y     position sur le plan du niveau (pixels de l'image, y vers le bas)
  cap      direction vers laquelle pointe le CENTRE de la photo, en degrés
           dans le sens horaire depuis le HAUT du plan (0 = haut, 90 = droite)
  fichier  chemin de la photo 360° (JPG équirectangulaire)
  liens    (option) ids reliés en plus, séparés par des espaces : escaliers,
           ascenseurs, ou photos trop éloignées pour le lien automatique
  bloque   (option) ids à ne PAS relier automatiquement (ex. deux couloirs
           parallèles séparés par un mur mais proches sur le plan)
"""
import argparse, csv, json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_rows(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    delim = ";" if text.splitlines()[0].count(";") >= text.splitlines()[0].count(",") else ","
    return list(csv.DictReader(text.splitlines(), delimiter=delim))


def ids(cell):
    return [t for t in (cell or "").replace(",", " ").replace(";", " ").split() if t]


def bearing(a, b):
    """Angle en degrés, sens horaire depuis le haut du plan, de a vers b."""
    return math.degrees(math.atan2(b["x"] - a["x"], -(b["y"] - a["y"]))) % 360


def build(rows, dmax):
    nodes = {}
    for i, r in enumerate(rows, start=2):
        try:
            n = dict(id=r["id"].strip(), name=r["nom"].strip(), level=r["niveau"].strip(),
                     x=float(r["x"]), y=float(r["y"]), cap=float(r.get("cap") or 0),
                     panorama=r["fichier"].strip())
        except (KeyError, ValueError) as e:
            sys.exit(f"Ligne {i} de photos.csv invalide ({e}) : {r}")
        if n["id"] in nodes:
            sys.exit(f"Identifiant en double : {n['id']}")
        n["_extra"] = ids(r.get("liens"))
        n["_block"] = set(ids(r.get("bloque")))
        nodes[n["id"]] = n

    pairs = set()
    for a in nodes.values():
        for b in nodes.values():
            if a is b or a["level"] != b["level"]:
                continue
            if b["id"] in a["_block"] or a["id"] in b["_block"]:
                continue
            if math.hypot(a["x"] - b["x"], a["y"] - b["y"]) <= dmax:
                pairs.add((a["id"], b["id"]))
        for t in a["_extra"]:
            if t not in nodes:
                sys.exit(f"{a['id']} : lien vers un id inconnu « {t} »")
            pairs.add((a["id"], t))
            pairs.add((t, a["id"]))  # liens toujours dans les deux sens

    for n in nodes.values():
        n["links"] = []
    for s, t in sorted(pairs):
        nodes[s]["links"].append({"nodeId": t, "yaw": round(bearing(nodes[s], nodes[t]), 2)})
    for n in nodes.values():
        n.pop("_extra"); n.pop("_block")
    return list(nodes.values())


def check(nodes, levels):
    problems = []
    for n in nodes:
        if n["level"] not in levels:
            problems.append(f"{n['id']} : niveau « {n['level']} » absent de levels.json")
        if not (ROOT / n["panorama"]).exists():
            problems.append(f"{n['id']} : fichier introuvable « {n['panorama']} »")
        if not n["links"]:
            problems.append(f"{n['id']} : AUCUN lien (photo isolée)")
    # connexité : toutes les photos doivent être atteignables depuis la première
    seen, todo = set(), [nodes[0]["id"]]
    byid = {n["id"]: n for n in nodes}
    while todo:
        c = todo.pop()
        if c in seen:
            continue
        seen.add(c)
        todo += [l["nodeId"] for l in byid[c]["links"]]
    for n in nodes:
        if n["id"] not in seen:
            problems.append(f"{n['id']} : non atteignable depuis {nodes[0]['id']} (groupe séparé)")
    return problems


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(ROOT / "data/photos.csv"))
    ap.add_argument("--levels", default=str(ROOT / "data/levels.json"))
    ap.add_argument("--out", default=str(ROOT / "data/nodes.json"))
    ap.add_argument("--distance-max", type=float, default=130,
                    help="distance max (pixels du plan) pour relier deux photos du même niveau")
    a = ap.parse_args()
    levels = json.loads(Path(a.levels).read_text(encoding="utf-8"))
    nodes = build(read_rows(a.csv), a.distance_max)
    Path(a.out).write_text(json.dumps(nodes, ensure_ascii=False, indent=1), encoding="utf-8")
    nl = sum(len(n["links"]) for n in nodes)
    print(f"{len(nodes)} photos, {nl} liens -> {a.out}")
    probs = check(nodes, levels)
    for p in probs:
        print("ATTENTION :", p)
    sys.exit(1 if probs else 0)
