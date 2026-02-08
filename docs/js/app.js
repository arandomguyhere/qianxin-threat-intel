let aptData = null;
let selectedGroup = null;
let activeFilter = 'all';

const ORIGIN_COLORS = {
  'Russia': '#e74c3c',
  'China': '#e67e22',
  'North Korea': '#a855f7',
  'Iran': '#22c55e',
  'United States': '#3498db',
  'Vietnam': '#06b6d4',
  'India': '#f39c12'
};

const THREAT_COLORS = {
  'critical': '#ef4444',
  'high': '#f97316',
  'medium': '#eab308',
  'low': '#22c55e'
};

// Equirectangular projection helpers
function lonLatToXY(lon, lat, width, height) {
  const x = ((lon + 180) / 360) * width;
  const y = ((90 - lat) / 180) * height;
  return { x, y };
}

async function init() {
  try {
    const resp = await fetch('data/apt-groups.json');
    aptData = await resp.json();
    renderStats();
    renderMap();
    renderLegend();
    renderSidebar();
    setupSearch();
    setupFilters();
  } catch (err) {
    console.error('Failed to load APT data:', err);
  }
}

function renderStats() {
  const el = document.getElementById('stats');
  const groups = aptData.apt_groups;
  const activeCount = groups.filter(g => g.active).length;
  const origins = new Set(groups.map(g => g.origin)).size;

  el.innerHTML = `
    <div class="stat-item">
      <div class="stat-value">${groups.length}</div>
      <div class="stat-label">APT Groups</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">${activeCount}</div>
      <div class="stat-label">Active</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">${origins}</div>
      <div class="stat-label">Origins</div>
    </div>
  `;
}

function renderMap() {
  const container = document.getElementById('world-map');
  const width = container.clientWidth;
  const height = container.clientHeight;

  // Build SVG map
  let svg = `<svg viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%">`;

  // Background
  svg += `<rect width="${width}" height="${height}" fill="#0a0e17"/>`;

  // Grid lines
  for (let lon = -180; lon <= 180; lon += 30) {
    const { x } = lonLatToXY(lon, 0, width, height);
    svg += `<line x1="${x}" y1="0" x2="${x}" y2="${height}" stroke="#151d2b" stroke-width="0.5"/>`;
  }
  for (let lat = -90; lat <= 90; lat += 30) {
    const { y } = lonLatToXY(0, lat, width, height);
    svg += `<line x1="0" y1="${y}" x2="${width}" y2="${y}" stroke="#151d2b" stroke-width="0.5"/>`;
  }

  // Simplified world landmass polygons (major continents)
  svg += renderContinents(width, height);

  // Attack connection lines between origins
  svg += renderAttackLines(width, height);

  // APT group markers
  const markerGroups = groupByOrigin(aptData.apt_groups);
  for (const [origin, groups] of Object.entries(markerGroups)) {
    const color = ORIGIN_COLORS[origin] || '#888';
    const baseCoords = aptData.origins[origin]?.coords || groups[0].origin_coords;

    groups.forEach((group, i) => {
      // Offset markers slightly so they don't overlap
      const angle = (i / groups.length) * Math.PI * 2;
      const offsetLon = baseCoords[1] + Math.cos(angle) * (groups.length > 1 ? 3 + i * 1.5 : 0);
      const offsetLat = baseCoords[0] + Math.sin(angle) * (groups.length > 1 ? 2 + i * 1 : 0);
      const { x, y } = lonLatToXY(offsetLon, offsetLat, width, height);

      const threat = group.threat_level;
      const size = threat === 'critical' ? 7 : threat === 'high' ? 5.5 : 4;
      const glowSize = size * 3;

      // Glow effect
      svg += `<circle cx="${x}" cy="${y}" r="${glowSize}" fill="${color}" opacity="0.08">
        <animate attributeName="r" values="${glowSize};${glowSize * 1.8};${glowSize}" dur="${threat === 'critical' ? '2s' : '3s'}" repeatCount="indefinite"/>
        <animate attributeName="opacity" values="0.08;0.02;0.08" dur="${threat === 'critical' ? '2s' : '3s'}" repeatCount="indefinite"/>
      </circle>`;

      // Outer ring
      svg += `<circle cx="${x}" cy="${y}" r="${size + 2}" fill="none" stroke="${color}" stroke-width="0.5" opacity="0.4">
        <animate attributeName="r" values="${size + 2};${size + 6};${size + 2}" dur="3s" repeatCount="indefinite"/>
        <animate attributeName="opacity" values="0.4;0;0.4" dur="3s" repeatCount="indefinite"/>
      </circle>`;

      // Main dot
      svg += `<circle cx="${x}" cy="${y}" r="${size}" fill="${color}" opacity="0.9"
        class="marker-circle" data-id="${group.id}" style="cursor:pointer"/>`;

      // Inner bright dot
      svg += `<circle cx="${x}" cy="${y}" r="${size * 0.4}" fill="white" opacity="0.6"
        class="marker-circle" data-id="${group.id}" style="cursor:pointer; pointer-events:none"/>`;

      // Label
      svg += `<text x="${x}" y="${y - size - 6}" text-anchor="middle" fill="${color}"
        font-size="9" font-weight="600" font-family="Inter, sans-serif" class="marker-label"
        data-id="${group.id}" opacity="0" style="pointer-events:none; text-shadow: 0 1px 3px rgba(0,0,0,0.9)">${group.name}</text>`;
    });
  }

  svg += '</svg>';
  container.innerHTML = svg;

  // Add event listeners to markers
  container.querySelectorAll('.marker-circle').forEach(el => {
    el.addEventListener('click', () => {
      const id = el.dataset.id;
      const group = aptData.apt_groups.find(g => g.id === id);
      if (group) openDetail(group);
    });
    el.addEventListener('mouseenter', () => {
      const id = el.dataset.id;
      container.querySelectorAll(`.marker-label[data-id="${id}"]`).forEach(l => l.setAttribute('opacity', '1'));
    });
    el.addEventListener('mouseleave', () => {
      const id = el.dataset.id;
      container.querySelectorAll(`.marker-label[data-id="${id}"]`).forEach(l => l.setAttribute('opacity', '0'));
    });
  });
}

function renderContinents(w, h) {
  let paths = '';

  // Simplified continent outlines as filled polygons
  const continents = [
    // North America
    { points: [[-130,55],[-125,60],[-110,68],[-95,72],[-80,72],[-65,60],[-55,47],[-65,43],[-75,35],[-80,25],[-90,18],[-100,18],[-105,22],[-115,30],[-125,48],[-130,55]], name: 'North America' },
    // South America
    { points: [[-80,10],[-75,5],[-70,-5],[-75,-15],[-70,-25],[-65,-35],[-70,-50],[-75,-55],[-68,-55],[-65,-45],[-55,-35],[-40,-22],[-35,-10],[-50,0],[-60,5],[-70,12],[-80,10]], name: 'South America' },
    // Europe
    { points: [[-10,36],[0,38],[5,44],[0,48],[-5,48],[0,52],[5,54],[10,55],[12,58],[18,58],[25,60],[30,62],[32,65],[35,68],[30,70],[20,70],[10,65],[5,62],[0,58],[-5,55],[-10,50],[-10,36]], name: 'Europe' },
    // Africa
    { points: [[-15,35],[-17,15],[-10,5],[-5,5],[5,5],[10,0],[12,-5],[15,-10],[20,-15],[30,-25],[35,-33],[30,-35],[25,-30],[20,-25],[15,-15],[10,-5],[15,5],[20,10],[30,12],[35,10],[40,12],[42,10],[45,12],[50,15],[43,15],[38,20],[35,32],[30,35],[25,37],[15,37],[5,36],[-5,35],[-15,35]], name: 'Africa' },
    // Asia
    { points: [[30,35],[35,37],[40,40],[45,38],[50,40],[55,37],[60,38],[65,35],[70,35],[75,30],[80,28],[85,28],[90,22],[95,15],[100,10],[105,15],[110,20],[115,22],[120,24],[125,30],[130,35],[135,35],[130,42],[135,45],[140,45],[145,50],[142,55],[135,55],[130,48],[125,42],[120,45],[115,48],[110,50],[100,55],[90,55],[80,58],[70,55],[65,55],[55,55],[50,52],[45,48],[40,42],[35,40],[30,35]], name: 'Asia' },
    // Oceania / Australia
    { points: [[115,-15],[120,-15],[130,-12],[135,-15],[140,-18],[145,-20],[150,-25],[152,-28],[150,-35],[145,-38],[140,-38],[135,-35],[130,-32],[125,-33],[118,-34],[115,-32],[113,-25],[115,-20],[115,-15]], name: 'Australia' },
    // Japan
    { points: [[130,31],[132,33],[135,35],[137,37],[140,40],[142,43],[145,45],[143,44],[140,42],[138,38],[136,36],[133,34],[130,31]], name: 'Japan' },
    // UK/Ireland
    { points: [[-8,50],[-5,50],[-3,52],[0,52],[2,53],[0,56],[-2,57],[-5,58],[-6,56],[-4,54],[-5,52],[-8,51],[-8,50]], name: 'UK' },
    // Indonesia
    { points: [[95,-5],[100,-3],[105,-5],[108,-7],[112,-8],[115,-8],[120,-9],[125,-8],[130,-5],[135,-4],[140,-5],[140,-8],[135,-9],[128,-10],[120,-10],[115,-9],[110,-8],[105,-7],[100,-5],[95,-5]], name: 'Indonesia' },
  ];

  continents.forEach(c => {
    const pts = c.points.map(([lon, lat]) => {
      const { x, y } = lonLatToXY(lon, lat, w, h);
      return `${x},${y}`;
    }).join(' ');
    paths += `<polygon points="${pts}" fill="#1a2332" stroke="#2a3a50" stroke-width="0.5" class="continent"/>`;
  });

  return paths;
}

function renderAttackLines(w, h) {
  let lines = '';
  const origins = aptData.origins;

  // Draw subtle connection lines between origin countries
  const pairs = [
    ['Russia', 'China'],
    ['Russia', 'Iran'],
    ['China', 'North Korea'],
  ];

  pairs.forEach(([a, b]) => {
    if (origins[a] && origins[b]) {
      const from = lonLatToXY(origins[a].coords[1], origins[a].coords[0], w, h);
      const to = lonLatToXY(origins[b].coords[1], origins[b].coords[0], w, h);
      const midX = (from.x + to.x) / 2;
      const midY = Math.min(from.y, to.y) - 20;
      lines += `<path d="M${from.x},${from.y} Q${midX},${midY} ${to.x},${to.y}"
        fill="none" stroke="#2a3a50" stroke-width="0.5" stroke-dasharray="4,4" opacity="0.3"/>`;
    }
  });

  return lines;
}

function groupByOrigin(groups) {
  const map = {};
  groups.forEach(g => {
    if (!map[g.origin]) map[g.origin] = [];
    map[g.origin].push(g);
  });
  return map;
}

function renderLegend() {
  const el = document.getElementById('map-legend');
  let html = '';
  for (const [name, color] of Object.entries(ORIGIN_COLORS)) {
    html += `<div class="legend-item">
      <span class="legend-dot" style="background:${color}"></span>
      ${name}
    </div>`;
  }
  el.innerHTML = html;
}

function renderSidebar(groups) {
  const list = document.getElementById('apt-list');
  const data = groups || aptData.apt_groups;

  if (data.length === 0) {
    list.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--text-muted)">No groups match your search.</div>';
    return;
  }

  // Sort: critical first, then high, then medium
  const sorted = [...data].sort((a, b) => {
    const order = { critical: 0, high: 1, medium: 2, low: 3 };
    return (order[a.threat_level] || 3) - (order[b.threat_level] || 3);
  });

  list.innerHTML = sorted.map(g => `
    <div class="apt-card" data-id="${g.id}" onclick="openDetail(aptData.apt_groups.find(x=>x.id==='${g.id}'))">
      <div class="apt-card-header">
        <span class="apt-name" style="color:${ORIGIN_COLORS[g.origin] || '#e2e8f0'}">${g.name}</span>
        <span class="threat-badge ${g.threat_level}">${g.threat_level}</span>
      </div>
      <div class="apt-origin">${g.origin} &middot; Since ${g.first_seen} ${g.active ? '<span style="color:#22c55e">&#9679; Active</span>' : '<span style="color:#64748b">&#9679; Inactive</span>'}</div>
      <div class="apt-aliases">${g.aliases.slice(0, 3).join(', ')}${g.aliases.length > 3 ? '...' : ''}</div>
      <div class="apt-tags">
        ${g.targets.slice(0, 4).map(t => `<span class="apt-tag">${t}</span>`).join('')}
      </div>
    </div>
  `).join('');
}

function setupSearch() {
  const input = document.getElementById('search-input');
  input.addEventListener('input', () => {
    const q = input.value.toLowerCase().trim();
    let filtered = aptData.apt_groups;

    if (q) {
      filtered = filtered.filter(g =>
        g.name.toLowerCase().includes(q) ||
        g.aliases.some(a => a.toLowerCase().includes(q)) ||
        g.origin.toLowerCase().includes(q) ||
        g.targets.some(t => t.toLowerCase().includes(q)) ||
        g.malware.some(m => m.toLowerCase().includes(q))
      );
    }

    if (activeFilter !== 'all') {
      filtered = filtered.filter(g => g.origin === activeFilter);
    }

    renderSidebar(filtered);
  });
}

function setupFilters() {
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeFilter = btn.dataset.filter;

      const q = document.getElementById('search-input').value.toLowerCase().trim();
      let filtered = aptData.apt_groups;

      if (activeFilter !== 'all') {
        filtered = filtered.filter(g => g.origin === activeFilter);
      }
      if (q) {
        filtered = filtered.filter(g =>
          g.name.toLowerCase().includes(q) ||
          g.aliases.some(a => a.toLowerCase().includes(q)) ||
          g.origin.toLowerCase().includes(q)
        );
      }

      renderSidebar(filtered);
    });
  });
}

function openDetail(group) {
  selectedGroup = group;
  const panel = document.getElementById('detail-panel');
  const dimmer = document.getElementById('overlay-dimmer');

  panel.innerHTML = `
    <div class="detail-header">
      <div>
        <div class="detail-title" style="color:${ORIGIN_COLORS[group.origin] || '#e2e8f0'}">${group.name}</div>
        <div class="active-indicator" style="margin-top:0.3rem">
          <span class="dot ${group.active ? 'active' : 'inactive'}"></span>
          <span style="color:${group.active ? 'var(--accent-green)' : 'var(--text-muted)'}">${group.active ? 'Currently Active' : 'Inactive'}</span>
        </div>
      </div>
      <button class="detail-close" onclick="closeDetail()">&times;</button>
    </div>
    <div class="detail-body">
      <div class="detail-section">
        <div class="detail-section-title">Overview</div>
        <div class="detail-description">${group.description}</div>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">Details</div>
        <div class="detail-meta">
          <div class="meta-item">
            <div class="meta-label">Origin</div>
            <div class="meta-value" style="color:${ORIGIN_COLORS[group.origin]}">${group.origin}</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">First Seen</div>
            <div class="meta-value">${group.first_seen}</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Threat Level</div>
            <div class="meta-value"><span class="threat-badge ${group.threat_level}">${group.threat_level}</span></div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Target Regions</div>
            <div class="meta-value" style="font-size:0.75rem">${group.target_regions.join(', ')}</div>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">Aliases</div>
        <div class="detail-tags">
          ${group.aliases.map(a => `<span class="detail-tag">${a}</span>`).join('')}
        </div>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">Target Sectors</div>
        <div class="detail-tags">
          ${group.targets.map(t => `<span class="detail-tag target">${t}</span>`).join('')}
        </div>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">TTPs</div>
        <div class="detail-tags">
          ${group.ttps.map(t => `<span class="detail-tag ttp">${t}</span>`).join('')}
        </div>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">Associated Malware</div>
        <div class="detail-tags">
          ${group.malware.map(m => `<span class="detail-tag malware">${m}</span>`).join('')}
        </div>
      </div>
    </div>
  `;

  panel.classList.add('open');
  dimmer.classList.add('active');

  // Highlight card in sidebar
  document.querySelectorAll('.apt-card').forEach(c => c.classList.remove('selected'));
  const card = document.querySelector(`.apt-card[data-id="${group.id}"]`);
  if (card) {
    card.classList.add('selected');
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

function closeDetail() {
  document.getElementById('detail-panel').classList.remove('open');
  document.getElementById('overlay-dimmer').classList.remove('active');
  document.querySelectorAll('.apt-card').forEach(c => c.classList.remove('selected'));
  selectedGroup = null;
}

// Handle resize
let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (aptData) renderMap();
  }, 250);
});

// Init on load
document.addEventListener('DOMContentLoaded', init);
