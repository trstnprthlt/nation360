#!/usr/bin/env python3
"""
Test de bout en bout dans un vrai navigateur (Chromium via Playwright), écran 1400x800.

    pip install playwright pillow && python3 -m playwright install chromium
    python3 dev/e2e.py

Sur le jeu de DÉMO : teste tout (orientation des flèches et du cône, plan fixe, clics, recherche, niveaux,
bandeau niveau + photo, volet replié, plans PNG et SVG...).
Avec vos propres données : seuls quelques contrôles de base sont faits.
"""
import functools, http.server, io, math, sys, threading
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

def is_yellow(r, g, b):  # repères peints dans les panoramas de démo
    return r > 235 and 190 < g < 246 and b < 160

SVG_PLAN = ('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800">'
            '<rect width="1200" height="800" fill="#1c2028"/>'
            '<path d="M1000 400 V500 H100" stroke="#ccd" stroke-width="46" fill="none"/></svg>')
SVG_VIEWBOX = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800"><rect width="1200" height="800" fill="#345"/></svg>')
SVG_PCT = ('<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 1200 800"><rect width="1200" height="800" fill="#345"/></svg>')
SVG_NO_SIZE = ('<svg xmlns="http://www.w3.org/2000/svg"><rect width="1200" height="800" fill="#345"/></svg>')

def main():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/index.html"

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader",
                                    "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        ctx = b.new_context(viewport={"width": 1400, "height": 800})
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)

        cur = lambda: pg.evaluate("window.tour.tour.getCurrentNode().id")
        wait = lambda i: pg.wait_for_function("i => window.tour.tour.getCurrentNode()?.id === i", arg=i, timeout=20000)
        level = lambda l: pg.wait_for_selector(f"#plan[data-ready='1'][data-level='{l}']", timeout=10000)
        box = lambda sel: pg.locator(sel).bounding_box()
        dot = lambda i: pg.locator(f'.dot[data-id="{i}"]')
        ndots = lambda: pg.locator(".dot").count()
        shot = lambda: Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
        scale = lambda: float(pg.evaluate("document.getElementById('plan').dataset.scale"))
        vwidth = lambda: pg.evaluate("window.tour.viewer.getSize().width")
        shown_level = lambda: pg.input_value("#levels")
        where = lambda: (pg.inner_text("#where-level"), pg.inner_text("#where-name"))
        def center(i):
            bx = dot(i).bounding_box(); return bx["x"] + bx["width"]/2, bx["y"] + bx["height"]/2
        def click_dot(i):
            pg.mouse.click(*center(i))
        def click_arrow():
            v = box("#viewer"); cx = v["x"] + v["width"]/2
            btns = pg.query_selector_all(".psv-virtual-tour-arrow")
            best = min(btns, key=lambda e: abs(e.bounding_box()["x"] + e.bounding_box()["width"]/2 - cx))
            bx = best.bounding_box(); pg.mouse.click(bx["x"] + bx["width"]/2, bx["y"] + bx["height"]/2)
        def look(yaw_deg, pitch=-0.1):
            pg.evaluate("([y,p]) => window.tour.viewer.rotate({yaw: y*Math.PI/180, pitch: p})", [yaw_deg, pitch])
            pg.wait_for_timeout(300)
        def reload(hash_=""):
            pg.goto(url + hash_); pg.reload()
            pg.wait_for_function("window.tour && window.tour.tour.getCurrentNode()", timeout=30000)
            pg.wait_for_selector("#plan[data-ready='1']", timeout=10000); pg.wait_for_timeout(500)

        pg.goto(url)
        pg.wait_for_function("window.tour && window.tour.tour.getCurrentNode()", timeout=30000)
        pg.wait_for_selector("#plan[data-ready='1']", timeout=10000)
        pg.wait_for_timeout(800)
        NODES = pg.evaluate("window.tour.nodes.map(n => ({id: n.id, level: n.level, links: n.links.map(l => ({nodeId: l.nodeId, yaw: parseFloat(l.position.yaw)}))}))")
        check("aucun problème de données signalé", pg.evaluate("getComputedStyle(document.getElementById('warn')).display") == "none")
        w = box("#side")["width"]
        check("volet ouvert par défaut, environ 1/3 de l'écran", abs(w - 1400/3) < 6, f"({w:.0f} px sur 1400)")

        if not DEMO:
            check("liste des niveaux remplie", pg.locator("#levels option").count() >= 1)
            check("points affichés sur le plan", ndots() >= 1)
            check("bandeau niveau + photo renseigné", all(where()), str(where()))
            for n in NODES[:5]:
                pg.evaluate("id => window.tour.tour.setCurrentNode(id)", n["id"]); wait(n["id"])
            check("navigation entre les 5 premières photos", True)
        else:
            # ---------------- structure du volet
            check("liste déroulante : 2 niveaux", pg.locator("#levels option").count() == 2)
            check("niveau affiché au départ : -1", shown_level() == "-1")
            check("le niveau courant est signalé « vous êtes ici »", "vous êtes ici" in pg.locator("#levels option[value='-1']").inner_text())
            check("niveau -1 : 12 points visibles sur le plan", ndots() == 12, f"({ndots()})")
            check("niveau -1 : 11 segments de liaison", pg.locator("#plan-lines line").count() == 11)
            check("position de l'utilisateur = N1_01 (point bleu)", dot("N1_01").evaluate("e => e.classList.contains('current')") and pg.locator("#me").evaluate("e => e.style.display") != "none")
            check("point d'escalier (N1_10) distinct", dot("N1_10").evaluate("e => e.classList.contains('stair')"))
            check("bandeau : niveau + photo", where() == ("Niveau -1 - Mezzanine", "Mezzanine - couloir 1"), str(where()))

            # ---------------- orientation : flèches ET cône du plan ; le plan, lui, ne pivote pas
            bad = bad_cone = total = 0
            for n in NODES:
                pg.evaluate("id => window.tour.tour.setCurrentNode(id, {effect:'none', rotation:false, showLoader:false})", n["id"])
                wait(n["id"]); level(n["level"]); pg.wait_for_timeout(300)
                v = box("#viewer"); cx = v["x"] + v["width"]/2
                for l in n["links"]:
                    look(l["yaw"])
                    im = shot()
                    xs = [x for x in range(int(v["x"]) + 10, int(v["x"] + v["width"]) - 10, 2)
                          for y in range(60, 700, 3) if is_yellow(*im.getpixel((x, y)))]
                    total += 1
                    if not xs or abs(sum(xs)/len(xs) - cx) > 90:
                        bad += 1; print("   flèche décalée :", n["id"], "->", l["nodeId"])
                    tgt = next(m for m in NODES if m["id"] == l["nodeId"])
                    if tgt["level"] == n["level"]:   # le cône doit viser le voisin sur le plan
                        (x0, y0), (x1, y1) = center(n["id"]), center(l["nodeId"])
                        brg = math.degrees(math.atan2(x1 - x0, -(y1 - y0))) % 360
                        ang = float(pg.locator("#me").get_attribute("data-angle"))
                        d = abs((ang - brg + 180) % 360 - 180)
                        if d > 4:
                            bad_cone += 1; print(f"   cône décalé : {n['id']} -> {l['nodeId']} (cône {ang}°, plan {brg:.0f}°)")
            check(f"orientation : {total} flèches pointent vers la bonne photo", bad == 0, f"({bad} anomalies)")
            check("orientation : le cône du plan vise la photo voisine", bad_cone == 0, f"({bad_cone} anomalies)")
            # plan fixe : on tourne la tête dans toutes les directions, le plan et ses points ne bougent pas, seul le cône tourne
            pg.evaluate("id => window.tour.tour.setCurrentNode(id, {effect:'none', rotation:false})", "N1_05"); wait("N1_05"); level("-1"); pg.wait_for_timeout(500)
            look(0); ref_tf = pg.evaluate("document.getElementById('plan-inner').style.transform"); ref_pt = center("N1_01"); ref_cone = pg.locator("#me").get_attribute("data-angle")
            moved = False; cones = set()
            for yw in (90, 180, 270, 45):
                look(yw)
                moved |= pg.evaluate("document.getElementById('plan-inner').style.transform") != ref_tf
                pt = center("N1_01"); moved |= abs(pt[0] - ref_pt[0]) > 0.5 or abs(pt[1] - ref_pt[1]) > 0.5
                cones.add(pg.locator("#me").get_attribute("data-angle"))
            check("le plan ne pivote pas quand l'utilisateur tourne la tête", not moved)
            check("seul le cône d'orientation tourne (4 directions, 4 angles différents)", len(cones | {ref_cone}) == 5 and {"90.0", "180.0", "270.0", "45.0"} <= cones, str(sorted(cones)))

            # ---------------- navigation de base + bandeau
            pg.evaluate("id => window.tour.tour.setCurrentNode(id, {effect:'none', rotation:false})", "N1_01"); wait("N1_01"); pg.wait_for_timeout(600)
            look(90, -0.3)
            click_arrow(); wait("N1_02")
            check("clic sur une flèche : N1_01 -> N1_02", cur() == "N1_02")
            check("adresse #N1_02 mise à jour", pg.evaluate("location.hash") == "#N1_02")
            pg.wait_for_timeout(600)
            check("le point bleu suit l'utilisateur : N1_02", dot("N1_02").evaluate("e => e.classList.contains('current')"))
            check("le bandeau suit : « couloir 2 »", where() == ("Niveau -1 - Mezzanine", "Mezzanine - couloir 2"), str(where()))

            # ---------------- clic sur un point du plan
            click_dot("N1_05"); wait("N1_05")
            check("clic sur un point du plan : -> N1_05", cur() == "N1_05")

            # ---------------- info-bulle
            pg.mouse.move(700, 400); pg.mouse.move(*center("N1_12"), steps=8); pg.wait_for_timeout(250)
            check("info-bulle au survol (nom de la photo)", pg.inner_text("#tip") == "Mezzanine - sortie", pg.inner_text("#tip"))
            pg.mouse.move(700, 400); pg.wait_for_timeout(150)
            pg.mouse.move(*center("N1_10"), steps=8); pg.wait_for_timeout(250)
            check("info-bulle : changement de niveau signalé", "changement de niveau" in pg.inner_text("#tip"), repr(pg.inner_text("#tip")))
            pg.mouse.move(700, 400)

            # ---------------- recherche par mot-clé
            pg.fill("#q", "quai 3"); pg.wait_for_timeout(200)
            check("recherche « quai 3 » : 1 résultat (N2_03)", pg.locator("#results li[data-id]").count() == 1 and pg.locator("#results li[data-id]").get_attribute("data-id") == "N2_03")
            pg.keyboard.press("Enter"); wait("N2_03"); level("-2"); pg.wait_for_timeout(500)
            check("recherche + Entrée : va à N2_03 et affiche le niveau -2", cur() == "N2_03" and shown_level() == "-2")
            check("bandeau : niveau -2 et photo « Quai - 3 »", where() == ("Niveau -2 - Quai", "Quai - 3"), str(where()))
            pg.fill("#q", "MEZZANINE sortie"); pg.wait_for_timeout(200)
            check("recherche sans accent ni casse : « MEZZANINE sortie »", pg.locator("#results li[data-id]").count() == 2)
            check("compteur de résultats affiché", "2 résultats" in pg.inner_text("#results"))
            pg.fill("#q", "zzzz"); pg.wait_for_timeout(150)
            check("recherche sans résultat : message", "Aucun résultat" in pg.inner_text("#results"))
            pg.fill("#q", "sortie"); pg.wait_for_timeout(150)
            pg.locator('#results li[data-id="N1_12"]').click(); wait("N1_12"); level("-1")
            check("clic sur un résultat : N1_12 (niveau -1)", cur() == "N1_12" and shown_level() == "-1")
            pg.fill("#q", "quai"); pg.keyboard.press("Escape")
            check("Echap vide et ferme la recherche", pg.input_value("#q") == "" and pg.locator("#results").is_hidden())

            # ---------------- liste des niveaux : consulter un autre niveau sans bouger
            pg.select_option("#levels", "-2"); level("-2"); pg.wait_for_timeout(300)
            check("niveau -2 choisi dans la liste : 9 points", ndots() == 9, f"({ndots()})")
            check("consulter un niveau ne change pas la photo", cur() == "N1_12")
            check("le bandeau reste sur la photo réellement affichée", where() == ("Niveau -1 - Mezzanine", "Mezzanine - sortie"), str(where()))
            check("ma position masquée sur l'autre niveau", pg.locator("#me").evaluate("e => e.style.display") == "none")
            check("la liste indique toujours où je suis (niveau -1)", "vous êtes ici" in pg.locator("#levels option[value='-1']").inner_text())
            click_dot("N2_05"); wait("N2_05")
            check("clic sur un point d'un autre niveau : -> N2_05", cur() == "N2_05")

            # ---------------- escalier par flèche : la liste suit
            pg.evaluate("id => window.tour.tour.setCurrentNode(id)", "N1_10"); wait("N1_10"); level("-1"); pg.wait_for_timeout(700)
            yaw = pg.evaluate("window.tour.nodes.find(n=>n.id==='N1_10').links.find(l=>l.nodeId==='N2_01').position.yaw")
            look(float(yaw.replace('deg', '')), -0.3)
            click_arrow(); wait("N2_01"); level("-2"); pg.wait_for_timeout(500)
            check("escalier : N1_10 -> N2_01, niveau -2 affiché", cur() == "N2_01" and shown_level() == "-2")
            check("bandeau après l'escalier", where() == ("Niveau -2 - Quai", "Quai - 1"), str(where()))

            # ---------------- zoom / déplacement du plan
            s0 = scale()
            pg.mouse.move(200, 400); pg.mouse.wheel(0, -300); pg.wait_for_timeout(150)
            s1 = scale()
            check("molette : zoom avant", s1 > s0 * 1.2, f"({s0:.3f} -> {s1:.3f})")
            wd = dot("N2_05").bounding_box()["width"]
            check("taille des points constante malgré le zoom", 10 < wd < 17, f"({wd:.1f}px)")
            pg.click("#zout"); pg.wait_for_timeout(100)
            check("bouton − : zoom arrière", scale() < s1)
            pg.click("#zfit"); pg.wait_for_timeout(100)
            check("bouton ⤢ : retour à la vue d'ensemble", abs(scale() - s0) < 1e-3, f"({scale():.3f})")
            pg.click("#zin"); pg.click("#zin"); pg.click("#zin"); pg.wait_for_timeout(100)
            x0, y0 = center("N2_01")
            pg.mouse.move(250, 500); pg.mouse.down(); pg.mouse.move(280, 520, steps=5); pg.mouse.up(); pg.wait_for_timeout(100)
            x1, y1 = center("N2_01")
            check("glisser-déposer : le plan se déplace", abs((x1 - x0) - 30) < 4 and abs((y1 - y0) - 20) < 4, f"(dx={x1-x0:.0f}, dy={y1-y0:.0f})")
            pg.select_option("#levels", "-1"); level("-1")
            pg.fill("#q", "sortie"); pg.locator('#results li[data-id]').nth(1).click(); pg.wait_for_timeout(600)
            pb = box("#plan"); target = cur()
            db = dot(target).bounding_box()
            check("la photo courante est ramenée dans le cadre du plan",
                  pb["x"] < db["x"] < pb["x"] + pb["width"] and pb["y"] < db["y"] < pb["y"] + pb["height"], f"({target})")
            pg.click("#zme"); pg.wait_for_timeout(150)
            check("bouton ◎ : centre sur ma position", abs(center(target)[0] - (pb["x"] + pb["width"]/2)) < 6)
            sm = scale()
            pg.select_option("#levels", "-2"); level("-2"); pg.select_option("#levels", "-1"); level("-1"); pg.wait_for_timeout(100)
            check("la vue (zoom) de chaque niveau est mémorisée", abs(scale() - sm) < 1e-3, f"({sm:.3f} -> {scale():.3f})")
            pg.click("#zfit")

            # ---------------- plans : introuvable, SVG (3 variantes), SVG sans dimensions
            n_err = len(errs)
            pg.select_option("#levels", "-2"); level("-2"); pg.click("#zfit"); pg.wait_for_timeout(200)
            ref = center("N2_01"); ref_scale = scale()      # position de référence avec le plan PNG
            pg.select_option("#levels", "-1"); level("-1")
            def svg_case(label, body, expect_same=True):
                pg.route("**/plans/niveau-2.png*", lambda r: r.fulfill(status=200, body=body, content_type="image/svg+xml"))
                pg.select_option("#levels", "-2"); level("-2"); pg.click("#zfit"); pg.wait_for_timeout(250)
                c = center("N2_01")
                check(f"plan SVG ({label}) : mêmes coordonnées que le PNG 1200x800",
                      pg.locator("#plan-msg").is_hidden() and ndots() == 9 and abs(c[0] - ref[0]) < 1.5 and abs(c[1] - ref[1]) < 1.5 and abs(scale() - ref_scale) < 1e-3,
                      f"(échelle {scale():.3f} / {ref_scale:.3f}, point {c[0]:.0f},{c[1]:.0f} / {ref[0]:.0f},{ref[1]:.0f})")
                pg.unroute("**/plans/niveau-2.png*")
                pg.select_option("#levels", "-1"); level("-1")
            svg_case("width + height", SVG_PLAN)
            svg_case("viewBox seul", SVG_VIEWBOX)
            svg_case("width=100% + viewBox", SVG_PCT)
            pg.route("**/plans/niveau-2.png*", lambda r: r.fulfill(status=200, body=SVG_NO_SIZE, content_type="image/svg+xml"))
            pg.select_option("#levels", "-2"); pg.wait_for_timeout(800)
            check("SVG sans aucune dimension : message explicite", pg.locator("#plan-msg").is_visible() and "viewBox" in pg.inner_text("#plan-msg"), pg.inner_text("#plan-msg")[:70])
            pg.unroute("**/plans/niveau-2.png*")
            pg.route("**/plans/niveau-2.png*", lambda r: r.fulfill(status=404, body=""))
            pg.select_option("#levels", "-1"); level("-1"); pg.select_option("#levels", "-2"); pg.wait_for_timeout(800)
            check("plan introuvable : message clair", pg.locator("#plan-msg").is_visible() and "plan introuvable" in pg.inner_text("#plan-msg"), pg.inner_text("#plan-msg"))
            pg.unroute("**/plans/niveau-2.png*")
            pg.select_option("#levels", "-1"); level("-1"); pg.wait_for_timeout(200)
            check("retour à un plan valide : message effacé", pg.locator("#plan-msg").is_hidden() and ndots() == 12)
            del errs[n_err:]  # erreurs réseau volontaires de ce bloc de tests

            # ---------------- volet replié : le bandeau reste visible et suit la navigation
            pg.evaluate("id => window.tour.tour.setCurrentNode(id, {effect:'none', rotation:false})", "N1_01"); wait("N1_01"); pg.wait_for_timeout(500)
            pg.click("#toggle"); pg.wait_for_timeout(700)
            check("volet replié : largeur 0", box("#side") is None or box("#side")["width"] < 2)
            check("volet replié : le panorama prend tout l'écran", abs(vwidth() - 1400) < 3, f"({vwidth()})")
            check("volet replié : bouton « ▶ Plan » visible", "Plan" in pg.inner_text("#toggle"))
            check("volet replié : niveau et photo visibles", pg.locator("#where-level").is_visible() and pg.locator("#where-name").is_visible() and where() == ("Niveau -1 - Mezzanine", "Mezzanine - couloir 1"), str(where()))
            look(90, -0.3); click_arrow(); wait("N1_02"); pg.wait_for_timeout(400)
            check("volet replié : le bandeau suit la navigation (couloir 2)", where() == ("Niveau -1 - Mezzanine", "Mezzanine - couloir 2") and pg.locator("#where-name").is_visible(), str(where()))
            pg.evaluate("id => window.tour.tour.setCurrentNode(id)", "N2_04"); wait("N2_04"); pg.wait_for_timeout(500)
            check("volet replié : changement de niveau reflété dans le bandeau", where() == ("Niveau -2 - Quai", "Quai - 4"), str(where()))
            reload()
            check("l'état replié est mémorisé après rechargement", pg.evaluate("document.body.classList.contains('collapsed')"))
            pg.click("#toggle"); pg.wait_for_timeout(700)
            w = box("#side")["width"]
            check("volet rouvert (1/3) et panorama réduit en conséquence", abs(w - 1400/3) < 6 and abs(vwidth() - (1400 - w)) < 25, f"(volet {w:.0f}, vue {vwidth()})")

            # ---------------- poignée de largeur
            pg.mouse.move(w - 3, 400); pg.mouse.down(); pg.mouse.move(700, 400, steps=6); pg.mouse.up(); pg.wait_for_timeout(500)
            check("poignée : le volet s'élargit (≈700 px)", 680 < box("#side")["width"] < 720, f"({box('#side')['width']:.0f})")
            check("poignée : le panorama se redimensionne", abs(vwidth() - (1400 - box('#side')['width'])) < 25)
            reload()
            check("la largeur choisie est mémorisée", 680 < box("#side")["width"] < 720, f"({box('#side')['width']:.0f})")

        check("aucune erreur JavaScript", not errs, str(errs) if errs else "")
        b.close()
    print("\nTOUT EST OK" if ok else "\nDES TESTS ONT ECHOUE")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
