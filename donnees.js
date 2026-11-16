// Lit data/photos.csv et calcule les liens entre photos (remplace l'ancien script Python).

export function parseCsv(text) {
  text = text.replace(/^\uFEFF/, '');
  const first = text.split(/\r?\n/, 1)[0];
  const sep = (first.match(/;/g) || []).length >= (first.match(/,/g) || []).length ? ';' : ',';
  const rows = [];
  let row = [], cell = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (c === '"') quoted = false;
      else cell += c;
    } else if (c === '"') quoted = true;
    else if (c === sep) { row.push(cell); cell = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(cell); cell = '';
      if (row.some((v) => v.trim() !== '')) rows.push(row);
      row = [];
    } else cell += c;
  }
  row.push(cell);
  if (row.some((v) => v.trim() !== '')) rows.push(row);
  const head = rows.shift().map((h) => h.trim().toLowerCase());
  return rows.map((r, i) => {
    const o = { _ligne: i + 2 };
    head.forEach((h, k) => { o[h] = (r[k] ?? '').trim(); });
    return o;
  });
}

const ids = (cell) => (cell || '').split(/[\s,;]+/).filter(Boolean);

// écart entre deux directions, en degrés (0 à 180)
const angleDiff = (p, q) => Math.abs((((p - q) % 360) + 540) % 360 - 180);

// angle en degrés, sens horaire depuis le HAUT du plan, de a vers b
const bearing = (a, b) => ((Math.atan2(b.x - a.x, -(b.y - a.y)) * 180) / Math.PI + 360) % 360;

export function buildNodes(rows, levels) {
  const problems = [];
  const nodes = new Map();
  for (const r of rows) {
    const x = parseFloat(String(r.x).replace(',', '.'));
    const y = parseFloat(String(r.y).replace(',', '.'));
    const cap = r.cap === '' || r.cap === undefined ? 0 : parseFloat(String(r.cap).replace(',', '.'));
    if (!r.id || !r.fichier || !Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(cap)) {
      problems.push(`ligne ${r._ligne} ignorée : id, fichier, x, y (ou cap) manquant ou invalide`);
      continue;
    }
    if (nodes.has(r.id)) { problems.push(`ligne ${r._ligne} ignorée : identifiant en double « ${r.id} »`); continue; }
    if (!levels[r.niveau]) { problems.push(`${r.id} : niveau « ${r.niveau} » absent de levels.json`); continue; }
    nodes.set(r.id, {
      id: r.id, name: r.nom || r.id, level: r.niveau, x, y, cap, panorama: r.fichier,
      extra: ids(r.liens), block: new Set(ids(r.bloque)), links: [],
    });
  }

  const pairs = new Set();
  const add = (a, b) => pairs.add(a + '\u0000' + b);

  // 1. Voisines candidates de chaque photo : même niveau, dans le rayon `distance_max`, non bloquées.
  //    On les parcourt de la plus proche à la plus lointaine et on ne garde une voisine que si aucune voisine
  //    déjà gardée n'est dans la même direction (écart d'angle <= `angle_direction`, 30° par défaut).
  //    `angle_direction: 0` désactive ce tri (toutes les photos du rayon sont reliées).
  const kept = new Map();
  for (const a of nodes.values()) {
    const lv = levels[a.level];
    const dmax = lv.distance_max ?? 130;
    const angle = Number.isFinite(Number(lv.angle_direction)) && lv.angle_direction !== '' && lv.angle_direction != null
      ? Number(lv.angle_direction) : 30;
    const near = [];
    for (const b of nodes.values()) {
      if (a === b || a.level !== b.level) continue;
      if (a.block.has(b.id) || b.block.has(a.id)) continue;
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      if (d <= dmax) near.push({ id: b.id, d, brg: bearing(a, b) });
    }
    near.sort((p, q) => (Math.abs(p.d - q.d) > 1e-6 ? p.d - q.d : p.id < q.id ? -1 : 1));
    const mine = [];
    for (const c of near) {
      const sameWay = angle > 0 && mine.some((k) => angleDiff(k.brg, c.brg) <= angle + 1e-9);
      if (!sameWay) mine.push(c);
    }
    kept.set(a.id, new Set(mine.map((k) => k.id)));
  }
  // 2. Un lien n'existe que si les DEUX photos le gardent : les liens sont toujours dans les deux sens
  //    (flèche aller et retour, trait du plan cohérent) et aucune photo ne devient inaccessible.
  for (const [a, set] of kept) for (const b of set) if (kept.get(b).has(a)) add(a, b);

  // 3. Liens déclarés à la main (colonne `liens`) : toujours conservés, dans les deux sens, jamais triés.
  for (const a of nodes.values()) {
    for (const t of a.extra) {
      if (!nodes.has(t)) { problems.push(`${a.id} : lien vers un id inconnu « ${t} »`); continue; }
      add(a.id, t); add(t, a.id);
    }
  }
  for (const key of [...pairs].sort()) {
    const [s, t] = key.split('\u0000');
    nodes.get(s).links.push({ nodeId: t, yaw: Math.round(bearing(nodes.get(s), nodes.get(t)) * 100) / 100 });
  }

  const list = [...nodes.values()];
  for (const n of list) if (!n.links.length) problems.push(`${n.id} : aucun lien (photo isolée)`);
  if (list.length) {
    const seen = new Set(), todo = [list[0].id];
    while (todo.length) {
      const c = todo.pop();
      if (seen.has(c)) continue;
      seen.add(c);
      todo.push(...nodes.get(c).links.map((l) => l.nodeId));
    }
    for (const n of list) if (!seen.has(n.id)) problems.push(`${n.id} : non atteignable depuis ${list[0].id} (groupe séparé)`);
  }
  return { nodes: list, problems };
}
