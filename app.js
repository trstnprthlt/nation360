import { Viewer } from '@photo-sphere-viewer/core';
import { VirtualTourPlugin } from '@photo-sphere-viewer/virtual-tour-plugin';
import { MapPlugin } from '@photo-sphere-viewer/map-plugin';
import { parseCsv, buildNodes } from './donnees.js';

const LINK_ID = '__tour-link__'; // préfixe attendu par le plugin pour que le clic sur le plan change de photo

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
    caption: n.name,
    panorama: n.panorama,
    // recale chaque panorama sur le plan : le centre de la photo pointe vers `cap` (degrés)
    sphereCorrection: { pan: `${-n.cap}deg` },
    map: { x: n.x, y: n.y },
    links: n.links.map((l) => ({ nodeId: l.nodeId, position: { yaw: `${l.yaw}deg`, pitch: '-20deg' } })),
    level: n.level,
  }));
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));

  const wanted = decodeURIComponent(location.hash.slice(1));
  const start = byId[wanted] ?? nodes[0];

  const viewer = new Viewer({
    container: document.getElementById('viewer'),
    navbar: ['zoom', 'move', 'caption', 'fullscreen'],
    plugins: [
      [MapPlugin, {
        imageUrl: levels[start.level].plan,
        center: { x: start.map.x, y: start.map.y },
        size: '260px',
        shape: 'square',
        position: 'bottom left',
        defaultZoom: 120,
        spotStyle: { size: 16, color: '#ffd200', borderSize: 2, borderColor: '#000', hoverSize: 22 },
      }],
      [VirtualTourPlugin, {
        dataMode: 'client',
        positionMode: 'manual',
        renderMode: '3d',
        nodes,
        startNodeId: start.id,
        map: { imageUrl: levels[start.level].plan },
        preload: true,
        transitionOptions: { effect: 'fade', rotation: true, speed: '20rpm' },
      }],
    ],
  });

  const tour = viewer.getPlugin(VirtualTourPlugin);
  const map = viewer.getPlugin(MapPlugin);

  // --- sélecteur de niveau + plan filtré par niveau -------------------------------
  const select = document.getElementById('levels');
  for (const [key, lv] of Object.entries(levels)) {
    select.add(new Option(lv.nom, key));
  }
  let shownLevel = start.level;

  function showLevel(level, node) {
    if (shownLevel !== level) {
      map.setImage(levels[level].plan, { x: node.map.x, y: node.map.y });
      shownLevel = level;
    }
    map.setHotspots(
      nodes.filter((n) => n.level === level)
        .map((n) => ({ id: LINK_ID + n.id, tooltip: n.name, x: n.map.x, y: n.map.y })),
    );
    select.value = level;
  }

  tour.addEventListener('node-changed', ({ node }) => {
    showLevel(byId[node.id].level, byId[node.id]);
    history.replaceState(null, '', '#' + encodeURIComponent(node.id));
  });

  select.addEventListener('change', () => {
    const first = nodes.find((n) => n.level === select.value);
    if (first) tour.setCurrentNode(first.id);
  });

  window.tour = { viewer, tour, map, nodes }; // pratique pour déboguer dans la console
} catch (e) {
  console.error(e);
  fail('Impossible de charger la visite : ' + e.message +
       '\n(En local, la page doit être servie par un serveur web ; sur GitHub Pages c\'est automatique.)');
}
