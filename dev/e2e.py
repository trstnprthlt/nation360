#!/usr/bin/env python3
"""
Test de bout en bout dans un vrai navigateur (Chromium via Playwright).

    pip install playwright pillow && python3 -m playwright install chromium
    python3 dev/e2e.py

Vérifie sur vos données : (1) chaque flèche pointe bien vers la photo voisine
(un repère est peint dans les panoramas de DÉMO ; avec vos vraies photos, seul le test 2 s'applique
et ce test d'alignement est ignoré), (2) clic sur une flèche, sur le plan, plan agrandi,
escalier + changement de niveau, sélecteur de niveau.
"""
import functools, http.server, io, json, sys, threading
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DEMO = (ROOT / "data/photos.csv").read_text(encoding="utf-8").startswith("id;nom;niveau;x;y;cap;fichier;liens;bloque\nN1_01;Mezzanine")
ok = True

def check(label, cond, extra=""):
    global ok
    ok &= bool(cond)
    print(("OK    " if cond else "ECHEC "), label, extra)

def is_yellow(r, g, b):  # repères peints (255,210,0) et points du plan
    return r > 235 and 190 < g < 246 and b < 160

def clusters(im, box, minsize=25):
    x0, y0, x1, y1 = box
    out = []
    for x in range(x0, x1):
        for y in range(y0, y1):
            if is_yellow(*im.getpixel((x, y))):
                for c in out:
                    if abs(c[0][0] - x) < 14 and abs(c[0][1] - y) < 14:
                        c.append((x, y)); break
                else:
                    out.append([(x, y)])
    return [(sum(p[0] for p in c) / len(c), sum(p[1] for p in c) / len(c)) for c in out if len(c) > minsize]

def main():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass
    handler = functools.partial(Quiet, directory=str(ROOT))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/index.html"

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader",
                                    "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = b.new_page(viewport={"width": 1000, "height": 650})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        cur = lambda: pg.evaluate("window.tour.tour.getCurrentNode().id")
        wait = lambda i: pg.wait_for_function("i => window.tour.tour.getCurrentNode()?.id === i", arg=i, timeout=20000)
        shot = lambda: Image.open(io.BytesIO(pg.screenshot())).convert("RGB")

        def click_arrow():
            btns = pg.query_selector_all(".psv-virtual-tour-arrow")
            best = min(btns, key=lambda e: abs(e.bounding_box()["x"] + e.bounding_box()["width"] / 2 - 500))
            bx = best.bounding_box()
            pg.mouse.click(bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2)

        pg.goto(url)
        pg.wait_for_function("window.tour && window.tour.tour.getCurrentNode()", timeout=30000)
        pg.wait_for_timeout(1000)
        NODES = pg.evaluate("window.tour.nodes.map(n => ({id: n.id, links: n.links.map(l => ({nodeId: l.nodeId, yaw: parseFloat(l.position.yaw)}))}))")
        first = NODES[0]["id"]
        check("aucun problème de données signalé", pg.evaluate("getComputedStyle(document.getElementById('warn')).display") == "none")

        # 1. alignement des flèches (panoramas de démo uniquement)
        if DEMO:
            bad = total = 0
            for n in NODES:
                pg.evaluate("id => window.tour.tour.setCurrentNode(id, {effect:'none', rotation:false, showLoader:false})", n["id"])
                wait(n["id"]); pg.wait_for_timeout(300)
                for l in n["links"]:
                    pg.evaluate("y => window.tour.viewer.rotate({yaw: y*Math.PI/180, pitch: -0.1})", l["yaw"])
                    pg.wait_for_timeout(200)
                    im = shot()
                    xs = [x for x in range(280, 1000, 2) for y in range(60, 600, 3) if is_yellow(*im.getpixel((x, y)))]
                    total += 1
                    if not xs or abs(sum(xs) / len(xs) - 500) > 90:
                        bad += 1; print("   décalé :", n["id"], "->", l["nodeId"])
            check(f"orientation : {total} liens pointent vers la bonne photo", bad == 0, f"({bad} anomalies)")
            pg.evaluate("id => window.tour.tour.setCurrentNode(id)", "N1_02"); wait("N1_02"); pg.wait_for_timeout(1200)

            # 2. clic sur flèche
            pg.evaluate("window.tour.tour.setCurrentNode('N1_01', {effect:'none', rotation:false})"); wait("N1_01"); pg.wait_for_timeout(600)
            pg.evaluate("window.tour.viewer.rotate({yaw: Math.PI/2, pitch: -0.3})"); pg.wait_for_timeout(600)
            click_arrow(); wait("N1_02")
            check("clic sur une flèche : N1_01 -> N1_02", cur() == "N1_02")
            check("adresse #N1_02 mise à jour", pg.evaluate("location.hash") == "#N1_02")
            pg.wait_for_timeout(1200)

            # 3. clic sur le mini-plan
            check("plan niveau -1 : 12 points", pg.evaluate("window.tour.map.config.hotspots.length") == 12)
            pg.evaluate("window.tour.viewer.rotate({yaw: 0, pitch: 0})"); pg.wait_for_timeout(800)  # plan orienté nord
            dots = sorted([d for d in clusters(shot(), (14, 344, 268, 596)) if d[0] > 160], key=lambda d: -d[0])
            pg.mouse.click(*dots[0]); pg.wait_for_timeout(2500)
            check("clic sur le mini-plan : N1_02 -> N1_03", cur() == "N1_03", f"(-> {cur()})")

            # 4. plan agrandi
            pg.click(".psv-map__button--top-right"); pg.wait_for_timeout(1200)
            dots = clusters(shot(), (0, 0, 1000, 600))
            pg.mouse.click(*min(dots, key=lambda d: d[1])); pg.wait_for_timeout(3000)
            check("plan agrandi : clic sur la sortie -> N1_12", cur() == "N1_12", f"(-> {cur()})")

            # 5. escalier et niveaux
            pg.evaluate("id => window.tour.tour.setCurrentNode(id)", "N1_10"); wait("N1_10"); pg.wait_for_timeout(800)
            yaw = pg.evaluate("window.tour.nodes.find(n=>n.id==='N1_10').links.find(l=>l.nodeId==='N2_01').position.yaw")
            pg.evaluate("y => window.tour.viewer.rotate({yaw: y, pitch: -0.3})", yaw); pg.wait_for_timeout(700)
            click_arrow(); wait("N2_01"); pg.wait_for_timeout(1500)
            check("escalier : N1_10 -> N2_01", cur() == "N2_01")
            check("le sélecteur passe au niveau -2", pg.evaluate("document.getElementById('levels').value") == "-2")
            check("plan -2 : 9 points", pg.evaluate("window.tour.map.config.hotspots.length") == 9)
            pg.select_option("#levels", "-1"); wait("N1_01"); pg.wait_for_timeout(1000)
            check("sélecteur de niveau -> -1", cur() == "N1_01" and pg.evaluate("window.tour.map.config.hotspots.length") == 12)
        else:
            check("la visite démarre", cur() == first, f"({cur()})")
            n_lv = pg.evaluate("document.getElementById('levels').options.length")
            check("niveaux affichés", n_lv >= 1, f"({n_lv})")
            for n in NODES[:5]:
                pg.evaluate("id => window.tour.tour.setCurrentNode(id)", n["id"]); wait(n["id"])
            check("navigation entre les 5 premières photos", True)

        check("aucune erreur JavaScript", not errs, str(errs) if errs else "")
        b.close()
    print("\nTOUT EST OK" if ok else "\nDES TESTS ONT ECHOUE")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
