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
  for (const a of nodes.values()) {
    const dmax = levels[a.level].distance_max ?? 130;
    for (const b of nodes.values()) {
      if (a === b || a.level !== b.level) continue;
      if (a.block.has(b.id) || b.block.has(a.id)) continue;
      if (Math.hypot(a.x - b.x, a.y - b.y) <= dmax) add(a.id, b.id);
    }
    for (const t of a.extra) {
      if (!nodes.has(t)) { problems.push(`${a.id} : lien vers un id inconnu « ${t} »`); continue; }
      add(a.id, t); add(t, a.id); // toujours dans les deux sens
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
