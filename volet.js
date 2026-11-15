// Volet de gauche : plan zoomable (fixe, il ne pivote pas), liste des niveaux, recherche par mot-clé,
// position de l'utilisateur avec cône d'orientation, bandeau « niveau + photo ».

const $ = (s) => document.querySelector(s);
const norm = (s) => String(s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* stockage indisponible : on ignore */ } },
};

export function createPlanPanel({ levels, nodes, onSelect }) {
  const levelKeys = Object.keys(levels);
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const levelName = (k) => levels[k]?.nom || k;
  const side = $('#side'), plan = $('#plan'), inner = $('#plan-inner'), img = $('#plan-img');
  const svg = $('#plan-lines'), dotsBox = $('#plan-dots'), tip = $('#tip'), msg = $('#plan-msg');
  const select = $('#levels'), q = $('#q'), results = $('#results');

  let shown = null, currentId = null, yaw = 0, token = 0, me = null;
  let view = { s: 1, tx: 0, ty: 0 }, size = { w: 1, h: 1 }, fit = 1, atFit = true;
  const views = {}; // vue (zoom + position) mémorisée par niveau

  // ---------------------------------------------------------------- volet : ouvrir / fermer / largeur
  const savedFrac = parseFloat(store.get('gare.sideFrac'));
  if (savedFrac > 0.15 && savedFrac < 0.75) document.documentElement.style.setProperty('--side-w', (savedFrac * 100).toFixed(2) + 'vw');
  const toggle = $('#toggle');
  function setCollapsed(c) {
    document.body.classList.toggle('collapsed', c);
    toggle.setAttribute('aria-expanded', String(!c));
    store.set('gare.panel', c ? 'closed' : 'open');
  }
  setCollapsed(store.get('gare.panel') === 'closed'); // ouvert par défaut
  toggle.addEventListener('click', () => setCollapsed(!document.body.classList.contains('collapsed')));

  $('#splitter').addEventListener('pointerdown', (e) => {
    e.preventDefault();
    const sp = e.currentTarget;
    sp.setPointerCapture(e.pointerId);
    side.classList.add('dragging');
    const move = (ev) => document.documentElement.style.setProperty('--side-w', clamp(ev.clientX, 260, innerWidth * 0.7) + 'px');
    const up = () => {
      side.classList.remove('dragging');
      sp.removeEventListener('pointermove', move);
      sp.removeEventListener('pointerup', up);
      store.set('gare.sideFrac', (side.getBoundingClientRect().width / innerWidth).toFixed(4));
    };
    sp.addEventListener('pointermove', move);
    sp.addEventListener('pointerup', up);
  });

  // ---------------------------------------------------------------- liste déroulante des niveaux
  for (const key of levelKeys) select.add(new Option(levelName(key), key));
  select.addEventListener('change', () => showLevel(select.value));
  function updateSelect() {
    const here = currentId && byId.get(currentId)?.level;
    for (const o of select.options) o.textContent = levelName(o.value) + (o.value === here ? '   ● vous êtes ici' : '');
    if (shown) select.value = shown;
  }

  // ---------------------------------------------------------------- zoom / déplacement du plan
  function apply() {
    inner.style.transform = `translate(${view.tx}px, ${view.ty}px) scale(${view.s})`;
    inner.style.setProperty('--inv', String(1 / view.s));
    plan.dataset.scale = view.s.toFixed(4);
    atFit = Math.abs(view.s - fit) < 1e-6;
  }
  function computeFit() {
    fit = Math.min(plan.clientWidth / size.w, plan.clientHeight / size.h) * 0.97;
    if (!(fit > 0)) fit = 1;
  }
  function fitView() {
    view = { s: fit, tx: (plan.clientWidth - size.w * fit) / 2, ty: (plan.clientHeight - size.h * fit) / 2 };
  }
  function clampPan() {
    const m = 60;
    view.tx = clamp(view.tx, m - size.w * view.s, plan.clientWidth - m);
    view.ty = clamp(view.ty, m - size.h * view.s, plan.clientHeight - m);
  }
  const maxScale = () => Math.max(fit * 12, 2);
  function zoomAt(cx, cy, f) {
    const r = plan.getBoundingClientRect();
    const px = cx - r.left, py = cy - r.top;
    const ns = clamp(view.s * f, fit * 0.8, maxScale());
    view.tx = px - (px - view.tx) * (ns / view.s);
    view.ty = py - (py - view.ty) * (ns / view.s);
    view.s = ns; clampPan(); apply(); hideTip();
  }
  function centerOn(x, y, scale) {
    if (scale) view.s = clamp(scale, fit * 0.8, maxScale());
    view.tx = plan.clientWidth / 2 - x * view.s;
    view.ty = plan.clientHeight / 2 - y * view.s;
    clampPan(); apply();
  }
  function ensureVisible(n) {
    const m = 40, px = n.x * view.s + view.tx, py = n.y * view.s + view.ty;
    if (px < m || py < m || px > plan.clientWidth - m || py > plan.clientHeight - m) centerOn(n.x, n.y);
  }

  plan.addEventListener('wheel', (e) => { e.preventDefault(); zoomAt(e.clientX, e.clientY, e.deltaY < 0 ? 1.25 : 1 / 1.25); }, { passive: false });
  plan.addEventListener('pointerdown', (e) => {
    if (e.target.closest('.dot, #plan-tools')) return;
    plan.setPointerCapture(e.pointerId);
    plan.classList.add('panning'); hideTip();
    let lx = e.clientX, ly = e.clientY;
    const move = (ev) => { view.tx += ev.clientX - lx; view.ty += ev.clientY - ly; lx = ev.clientX; ly = ev.clientY; clampPan(); apply(); };
    const up = () => { plan.classList.remove('panning'); plan.removeEventListener('pointermove', move); plan.removeEventListener('pointerup', up); };
    plan.addEventListener('pointermove', move);
    plan.addEventListener('pointerup', up);
  });
  const mid = () => { const r = plan.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; };
  $('#zin').addEventListener('click', () => zoomAt(...mid(), 1.5));
  $('#zout').addEventListener('click', () => zoomAt(...mid(), 1 / 1.5));
  $('#zfit').addEventListener('click', () => { fitView(); apply(); });
  $('#zme').addEventListener('click', async () => {
    const n = byId.get(currentId);
    if (!n) return;
    if (n.level !== shown) await showLevel(n.level);
    centerOn(n.x, n.y, Math.max(view.s, fit * 3));
  });
  new ResizeObserver(() => {
    if (!shown || !size.w) return;
    const wasFit = atFit;
    computeFit();
    if (wasFit) fitView(); else clampPan();
    apply();
  }).observe(plan);

  // ---------------------------------------------------------------- info-bulle
  function showTip(n, el) {
    const pr = plan.getBoundingClientRect(), r = el.getBoundingClientRect();
    const other = n.links.some((l) => byId.get(l.nodeId)?.level !== n.level);
    tip.textContent = n.name + (other ? '  ·  changement de niveau' : '');
    tip.style.left = r.left - pr.left + r.width / 2 + 'px';
    tip.style.top = r.top - pr.top - 8 + 'px';
    tip.hidden = false;
  }
  function hideTip() { tip.hidden = true; }

  // ---------------------------------------------------------------- dessin d'un niveau
  function build(key) {
    dotsBox.textContent = ''; svg.textContent = '';
    svg.setAttribute('viewBox', `0 0 ${size.w} ${size.h}`);
    const list = nodes.filter((n) => n.level === key);
    for (const n of list) {
      for (const l of n.links) {
        const t = byId.get(l.nodeId);
        if (!t || t.level !== key || n.id > t.id) continue;
        const ln = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        ln.setAttribute('x1', n.x); ln.setAttribute('y1', n.y); ln.setAttribute('x2', t.x); ln.setAttribute('y2', t.y);
        svg.appendChild(ln);
      }
    }
    me = document.createElement('div');
    me.id = 'me';
    me.innerHTML = '<svg viewBox="-40 -40 80 80"><g class="cone"><path d="M0 0 L-17 -36 A40 40 0 0 1 17 -36 Z"/></g></svg>';
    dotsBox.appendChild(me);
    for (const n of list) {
      const d = document.createElement('div');
      d.className = 'dot' + (n.links.some((l) => byId.get(l.nodeId)?.level !== key) ? ' stair' : '');
      d.dataset.id = n.id;
      d.style.left = n.x + 'px'; d.style.top = n.y + 'px';
      d.addEventListener('pointerdown', (e) => e.stopPropagation());
      d.addEventListener('click', () => { hideTip(); onSelect(n.id); });
      d.addEventListener('mouseenter', () => showTip(n, d));
      d.addEventListener('mouseleave', hideTip);
      dotsBox.appendChild(d);
    }
  }

  function updateMe() {
    const n = byId.get(currentId);
    dotsBox.querySelector('.dot.current')?.classList.remove('current');
    if (!me) return;
    if (!n || n.level !== shown) { me.style.display = 'none'; return; }
    dotsBox.querySelector(`.dot[data-id="${CSS.escape(n.id)}"]`)?.classList.add('current');
    me.style.display = '';
    me.style.left = n.x + 'px'; me.style.top = n.y + 'px';
    const a = ((yaw % 360) + 360) % 360;
    me.querySelector('.cone').setAttribute('transform', `rotate(${a.toFixed(1)})`);
    me.dataset.angle = a.toFixed(1);
  }

  // Charge le plan une seule fois (fetch -> blob). Pour un SVG, l'espace de coordonnées est celui de son viewBox
  // (sinon width/height) : c'est ce qu'affichent les éditeurs. Pour PNG/JPG, ce sont les pixels de l'image.
  let planUrl = null;
  async function loadPlan(url) {
    let blob;
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error('HTTP ' + r.status);
      blob = await r.blob();
    } catch { throw new Error('plan introuvable : ' + url); }
    let dims = null;
    if (blob.type === 'image/svg+xml' || /\.svg(\?|#|$)/i.test(url)) {
      const root = new DOMParser().parseFromString(await blob.text(), 'image/svg+xml').documentElement;
      const vb = (root.getAttribute('viewBox') || '').trim().split(/[\s,]+/).map(Number);
      const px = (a) => { const t = root.getAttribute(a) || ''; return /%$/.test(t) ? NaN : parseFloat(t); };
      if (vb.length === 4 && vb[2] > 0 && vb[3] > 0) dims = { w: vb[2], h: vb[3] };
      else if (px('width') > 0 && px('height') > 0) dims = { w: px('width'), h: px('height') };
      else throw new Error('plan SVG sans dimensions : ajoutez viewBox="0 0 largeur hauteur" dans la balise <svg> (ou width et height)');
    }
    const objectUrl = URL.createObjectURL(blob);
    try {
      await new Promise((res, rej) => { img.onload = res; img.onerror = () => rej(new Error('plan illisible : ' + url)); img.src = objectUrl; });
    } finally {
      if (planUrl) URL.revokeObjectURL(planUrl);
      planUrl = objectUrl;
    }
    if (!dims) dims = { w: img.naturalWidth, h: img.naturalHeight };
    if (!(dims.w > 0 && dims.h > 0)) throw new Error('plan illisible : ' + url);
    img.style.width = dims.w + 'px'; img.style.height = dims.h + 'px';
    return dims;
  }

  async function showLevel(key) {
    if (key === shown || !levels[key]) return;
    const my = ++token;
    if (shown && size.w > 1) views[shown] = { ...view };
    shown = key; plan.dataset.ready = ''; msg.hidden = true; updateSelect(); hideTip();
    const fail = (text) => {
      msg.textContent = text; msg.hidden = false; dotsBox.textContent = ''; svg.textContent = ''; me = null; size = { w: 1, h: 1 };
    };
    let dims;
    try {
      dims = await loadPlan(levels[key].plan);
    } catch (e) {
      if (my === token) fail(e.message);
      return;
    }
    if (my !== token) return; // un autre niveau a été demandé entre-temps
    size = dims;
    inner.style.width = size.w + 'px'; inner.style.height = size.h + 'px';
    build(key); computeFit();
    if (views[key]) { view = { ...views[key] }; clampPan(); } else fitView();
    apply(); updateMe();
    plan.dataset.level = key; plan.dataset.ready = '1';
  }

  // ---------------------------------------------------------------- recherche par mot-clé
  let found = [], active = -1;
  function renderResults() {
    results.textContent = '';
    if (!q.value.trim()) { results.hidden = true; return; }
    const toks = norm(q.value).split(/\s+/).filter(Boolean);
    found = nodes
      .map((n) => ({ n, hay: norm(n.name + ' ' + n.id + ' ' + levelName(n.level)) }))
      .filter((x) => toks.every((t) => x.hay.includes(t)))
      .sort((a, b) => (norm(b.n.name).startsWith(toks[0]) - norm(a.n.name).startsWith(toks[0])) || 0)
      .map((x) => x.n);
    active = found.length ? 0 : -1;
    const head = document.createElement('li');
    head.className = found.length ? 'count' : 'none';
    head.textContent = found.length ? `${found.length} résultat${found.length > 1 ? 's' : ''}` : 'Aucun résultat';
    results.appendChild(head);
    found.slice(0, 100).forEach((n, i) => {
      const li = document.createElement('li');
      li.setAttribute('role', 'option'); li.dataset.id = n.id;
      if (i === active) li.classList.add('active');
      const a = document.createElement('span'); a.textContent = n.name;
      const b = document.createElement('small'); b.textContent = levelName(n.level);
      li.append(a, b);
      li.addEventListener('mousedown', (e) => { e.preventDefault(); choose(n.id); });
      results.appendChild(li);
    });
    results.hidden = false;
  }
  function choose(id) { results.hidden = true; q.blur(); onSelect(id); }
  function moveActive(d) {
    const items = results.querySelectorAll('li[data-id]');
    if (!items.length) return;
    active = (active + d + items.length) % items.length;
    items.forEach((li, i) => li.classList.toggle('active', i === active));
    items[active].scrollIntoView({ block: 'nearest' });
  }
  q.addEventListener('input', renderResults);
  q.addEventListener('focus', renderResults);
  q.addEventListener('blur', () => { results.hidden = true; });
  q.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); moveActive(1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); moveActive(-1); }
    else if (e.key === 'Enter') { const li = results.querySelector('li.active'); if (li) choose(li.dataset.id); }
    else if (e.key === 'Escape') { q.value = ''; results.hidden = true; q.blur(); }
  });

  // ---------------------------------------------------------------- API
  return {
    async setCurrent(id) {
      const n = byId.get(id);
      if (!n) return;
      currentId = id;
      // bandeau « niveau + photo » : toujours à jour, même volet fermé
      $('#where-level').textContent = levelName(n.level);
      $('#where-name').textContent = n.name;
      await showLevel(n.level);
      updateMe(); updateSelect(); ensureVisible(n);
    },
    setYaw(deg) { yaw = deg; updateMe(); },
    showLevel,
  };
}
