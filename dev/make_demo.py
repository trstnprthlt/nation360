#!/usr/bin/env python3
"""Génère un jeu de DÉMO (2 niveaux, 21 panoramas factices, 2 plans) pour tester le viewer.
Sur chaque panorama factice sont dessinés : les points cardinaux (N/E/S/O du plan) et un
repère coloré dans la direction de chaque photo voisine -> permet de vérifier que les flèches
du viewer tombent bien sur les repères."""
import json, math, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dev"))
import build_nodes as bn

W, H = 2048, 1024
FONT = ImageFont.load_default(size=44)
SMALL = ImageFont.load_default(size=28)

# (id, nom, niveau, x, y, cap)
N1 = [(f"N1_{i:02d}", f"Mezzanine - couloir {i}", "-1", 100 + 100 * (i - 1), 400, 0) for i in range(1, 11)]
N1 += [("N1_11", "Mezzanine - vers sortie (1)", "-1", 600, 300, 0),
       ("N1_12", "Mezzanine - sortie", "-1", 600, 200, 0)]
N2 = [(f"N2_{i:02d}", f"Quai - {i}", "-2", 1000 - 100 * (i - 1), 500, 0) for i in range(1, 10)]
# caps variés pour tester la correction d'orientation
CAPS = {"N1_03": 90, "N1_06": 200, "N1_11": 45, "N1_12": 300, "N2_01": 180, "N2_04": 120, "N2_08": 270}
rows = [(a, b, c, d, e, CAPS.get(a, 0)) for a, b, c, d, e, _ in N1 + N2]
EXTRA = {"N1_10": "N2_01"}  # escalier

def plan(level, title, corridors):
    im = Image.new("RGB", (1200, 800), (28, 32, 40))
    d = ImageDraw.Draw(im)
    for (x1, y1, x2, y2) in corridors:
        d.line([(x1, y1), (x2, y2)], fill=(200, 205, 215), width=46)
    d.text((30, 25), title, fill=(255, 255, 255), font=FONT)
    d.text((30, 80), "plan de démonstration", fill=(160, 170, 185), font=SMALL)
    d.text((1120, 25), "N", fill=(255, 120, 120), font=FONT)
    d.polygon([(1135, 85), (1122, 115), (1148, 115)], fill=(255, 120, 120))
    im.save(ROOT / f"plans/niveau{level}.png")

def pano(n, nodes_by_id):
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):  # plafond sombre -> sol clair
        v = int(60 + 120 * abs(y - H / 2) / (H / 2)) if y > H / 2 else int(40 + 40 * y / (H / 2))
        d.line([(0, y), (W, y)], fill=(v, v, min(255, v + 15)))
    d.line([(0, H // 2), (W, H // 2)], fill=(255, 255, 255), width=3)
    def X(deg_image):  # yaw image (0 = centre de l'image) -> pixel
        return (W / 2 + deg_image / 360 * W) % W
    # points cardinaux du plan : bearing = yaw_image + cap
    for name, brg in (("N", 0), ("E", 90), ("S", 180), ("O", 270)):
        x = X(brg - n["cap"])
        d.rectangle([x - 6, 0, x + 6, H], fill=(90, 90, 110))
        d.text((x - 14, 140), name, fill=(255, 255, 255), font=FONT)
    # repères vers les voisins
    for l in n["links"]:
        x = X(l["yaw"] - n["cap"])
        d.rectangle([x - 40, 380, x + 40, 640], outline=(255, 210, 0), width=8)
        d.text((x - 38, 650), l["nodeId"], fill=(255, 210, 0), font=SMALL)
    # centre de l'image
    d.text((W / 2 - 150, 800), f"{n['id']}  cap {n['cap']:.0f}°", fill=(255, 255, 255), font=FONT)
    d.text((W / 2 - 100, 860), "(centre de l'image)", fill=(200, 200, 200), font=SMALL)
    im.save(ROOT / n["panorama"], quality=82)

if __name__ == "__main__":
    for p in ("panos", "plans", "data"):
        (ROOT / p).mkdir(exist_ok=True)
    plan("-1", "Niveau -1 : Mezzanine", [(100, 400, 1000, 400), (600, 400, 600, 200)])
    plan("-2", "Niveau -2 : Quai", [(100, 500, 1000, 500), (1000, 400, 1000, 500)])
    (ROOT / "data/levels.json").write_text(json.dumps({
        "-1": {"nom": "Niveau -1 - Mezzanine", "plan": "plans/niveau-1.png", "distance_max": 130},
        "-2": {"nom": "Niveau -2 - Quai", "plan": "plans/niveau-2.png", "distance_max": 130}}, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["id;nom;niveau;x;y;cap;fichier;liens;bloque"]
    for (i, nm, lv, x, y, cap) in rows:
        lines.append(";".join(map(str, [i, nm, lv, x, y, cap, f"panos/{i}.jpg", EXTRA.get(i, ""), ""])))
    (ROOT / "data/photos.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    nodes = bn.build(bn.read_rows(ROOT / "data/photos.csv"), 130)
    byid = {n["id"]: n for n in nodes}
    for n in nodes:
        pano(n, byid)
    print(len(nodes), "panoramas de démo générés")
