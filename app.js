import { Viewer } from '@photo-sphere-viewer/core';
import { VirtualTourPlugin } from '@photo-sphere-viewer/virtual-tour-plugin';
import { parseCsv, buildNodes } from './donnees.js';
import { createPlanPanel } from './volet.js';

function fail(msg) {
  const e = document.getElementById('error');
  e.textContent = msg;
  e.style.display = 'flex';
}

async function load(url, asText = false) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url} : HTTP ${r.status}`);
  return asText ? r.text() : r.json();
}

function warn(problems) {
  if (!problems.length) return;
  const box = document.getElementById('warn');
  box.innerHTML = `<b>${problems.length} problème(s) dans data/photos.csv</b> <a href="#" id="warn-x">fermer</a><ul>` +
    problems.slice(0, 12).map((p) => `<li>${p.replace(/</g, '&lt;')}</li>`).join('') +
    (problems.length > 12 ? `<li>… et ${problems.length - 12} autres</li>` : '') + '</ul>';
  box.style.display = 'block';
  document.getElementById('warn-x').onclick = (e) => { e.preventDefault(); box.style.display = 'none'; };
}

try {
  const [csv, levels] = await Promise.all([load('data/photos.csv', true), load('data/levels.json')]);
  const { nodes: data, problems } = buildNodes(parseCsv(csv), levels);
  warn(problems);
  if (!data.length) throw new Error('aucune photo valide dans data/photos.csv');

  const nodes = data.map((n) => ({
    id: n.id,
    name: n.name,
    panorama: n.panorama,
    // recale chaque panorama sur le plan : le centre de la photo pointe vers `cap` (degrés)
    sphereCorrection: { pan: `${-n.cap}deg` },
    x: n.x,
    y: n.y,
    links: n.links.map((l) => ({ nodeId: l.nodeId, position: { yaw: `${l.yaw}deg`, pitch: '-20deg' } })),
    level: n.level,
  }));
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));

  const wanted = decodeURIComponent(location.hash.slice(1));
  const start = byId[wanted] ?? nodes[0];

  const viewer = new Viewer({
    container: document.getElementById('viewer'),
    navbar: ['zoom', 'move', 'fullscreen'],
    plugins: [
      [VirtualTourPlugin, {
        dataMode: 'client',
        positionMode: 'manual',
        renderMode: '3d',
        nodes,
        startNodeId: start.id,
        preload: true,
        transitionOptions: { effect: 'fade', rotation: true, speed: '20rpm' },
      }],
    ],
  });
  const tour = viewer.getPlugin(VirtualTourPlugin);

  // --- volet de gauche : plan, niveaux, recherche ---------------------------------
  const panel = createPlanPanel({
    levels,
    nodes,
    onSelect: (id) => { if (tour.getCurrentNode()?.id !== id) tour.setCurrentNode(id); },
  });

  tour.addEventListener('node-changed', ({ node }) => {
    panel.setCurrent(node.id);
    history.replaceState(null, '', '#' + encodeURIComponent(node.id));
  });
  // le cône du plan suit la direction du regard ; le plan, lui, ne tourne pas
  viewer.addEventListener('position-updated', ({ position }) => panel.setYaw((position.yaw * 180) / Math.PI));
  panel.setCurrent(start.id);

  // quand le volet s'ouvre, se ferme ou change de largeur, le panorama prend la place restante
  let resizeTimer;
  new ResizeObserver(() => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => viewer.autoSize(), 60); })
    .observe(document.getElementById('stage'));

  window.tour = { viewer, tour, panel, nodes }; // pratique pour déboguer dans la console
} catch (e) {
  console.error(e);
  fail('Impossible de charger la visite : ' + e.message +
       '\n(En local, la page doit être servie par un serveur web ; sur GitHub Pages c\'est automatique.)');
}
