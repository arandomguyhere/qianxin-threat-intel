// ─── Config ─────────────────────────────────────────────
const FALLBACK_ORIGIN_COLORS = {
  'Russia': '#e74c3c', 'China': '#e67e22', 'North Korea': '#a855f7',
  'Iran': '#22c55e', 'United States': '#3498db', 'Vietnam': '#06b6d4',
  'India': '#f39c12', 'Unknown': '#888888'
};
let ORIGIN_COLORS = { ...FALLBACK_ORIGIN_COLORS };

const THREAT_COLORS = { critical: '#ef4444', high: '#f97316', medium: '#eab308' };

const REGION_COORDS = {
  'North America': [-100, 45], 'South America': [-60, -15], 'Latin America': [-70, -5],
  'Europe': [15, 50], 'Middle East': [45, 28], 'Central Asia': [65, 42],
  'East Asia': [120, 35], 'Southeast Asia': [110, 5], 'South Asia': [78, 22],
  'Oceania': [135, -25], 'Africa': [20, 5], 'North Africa': [15, 30],
  'Global': [0, 20], 'Ukraine': [32, 49], 'South Korea': [127, 36],
  'Japan': [138, 36], 'Asia Pacific': [130, 15], 'Americas': [-80, 20],
  'United States': [-98, 38], 'Israel': [35, 31], 'Palestine': [35, 32],
  'India': [78, 22], 'Pakistan': [69, 30], 'China': [104, 35],
  'Bangladesh': [90, 24], 'Nepal': [84, 28], 'Sri Lanka': [81, 7],
  'Iran': [52, 33], 'Saudi Arabia': [45, 24], 'Egypt': [31, 27],
  'Taiwan': [121, 24], 'Hong Kong': [114, 22], 'Tibet': [91, 30],
  'Afghanistan': [67, 33], 'Rwanda': [30, -2], 'Belgium': [4, 51],
  'Germany': [10, 51], 'Lithuania': [24, 55], 'Latvia': [25, 57],
  'Poland': [20, 52], 'Colombia': [-74, 4], 'Ecuador': [-78, -2],
  'Chile': [-71, -35], 'Spain': [-4, 40], 'Venezuela': [-67, 8],
  'Canada': [-106, 56], 'United Kingdom': [-2, 54],
  'CIS countries': [60, 50], 'NATO countries': [10, 50]
};

// Map TopoJSON country names → our origin names
const COUNTRY_NAME_MAP = {
  'Russia': 'Russia', 'China': 'China', 'Iran': 'Iran', 'India': 'India',
  'Vietnam': 'Vietnam', 'Turkey': 'Turkey', 'Pakistan': 'Pakistan',
  'Colombia': 'Colombia', 'Egypt': 'Egypt', 'Lebanon': 'Lebanon',
  'Syria': 'Syria', 'Belarus': 'Belarus', 'Uzbekistan': 'Uzbekistan',
  'Kazakhstan': 'Kazakhstan', 'Palestine': 'Palestine',
  'United States of America': 'United States', 'North Korea': 'North Korea',
  'Dem. Rep. Korea': 'North Korea', 'South Korea': 'South Korea',
  'Rep. Korea': 'South Korea', 'Korea': 'South Korea',
  'United Arab Emirates': 'United Arab Emirates'
};

// MITRE ATT&CK TTP mapping
const MITRE_MAP = {
  'spear-phishing': { id: 'T1566', name: 'Phishing' },
  'spear phishing': { id: 'T1566', name: 'Phishing' },
  'phishing': { id: 'T1566', name: 'Phishing' },
  'watering hole': { id: 'T1189', name: 'Drive-by Compromise' },
  'watering hole attacks': { id: 'T1189', name: 'Drive-by Compromise' },
  'zero-day exploits': { id: 'T1203', name: 'Exploitation for Client Execution' },
  'zero-day': { id: 'T1203', name: 'Exploitation for Client Execution' },
  'supply chain interdiction': { id: 'T1195', name: 'Supply Chain Compromise' },
  'supply chain compromise': { id: 'T1195', name: 'Supply Chain Compromise' },
  'supply chain attacks': { id: 'T1195', name: 'Supply Chain Compromise' },
  'firmware implants': { id: 'T1542', name: 'Pre-OS Boot' },
  'air-gap jumping': { id: 'T1091', name: 'Replication Through Removable Media' },
  'custom malware': { id: 'T1587.001', name: 'Develop Capabilities: Malware' },
  'custom rat': { id: 'T1587.001', name: 'Develop Capabilities: Malware' },
  'custom backdoors': { id: 'T1587.001', name: 'Develop Capabilities: Malware' },
  'credential theft': { id: 'T1003', name: 'OS Credential Dumping' },
  'credential harvesting': { id: 'T1003', name: 'OS Credential Dumping' },
  'lateral movement': { id: 'T1021', name: 'Remote Services' },
  'data exfiltration': { id: 'T1041', name: 'Exfiltration Over C2 Channel' },
  'dns tunneling': { id: 'T1071.004', name: 'Application Layer Protocol: DNS' },
  'living-off-the-land': { id: 'T1218', name: 'System Binary Proxy Execution' },
  'living off the land': { id: 'T1218', name: 'System Binary Proxy Execution' },
  'dll side-loading': { id: 'T1574.002', name: 'Hijack Execution Flow: DLL Side-Loading' },
  'dll sideloading': { id: 'T1574.002', name: 'Hijack Execution Flow: DLL Side-Loading' },
  'keylogging': { id: 'T1056.001', name: 'Input Capture: Keylogging' },
  'screen capture': { id: 'T1113', name: 'Screen Capture' },
  'ransomware': { id: 'T1486', name: 'Data Encrypted for Impact' },
  'ransomware deployment': { id: 'T1486', name: 'Data Encrypted for Impact' },
  'destructive malware': { id: 'T1485', name: 'Data Destruction' },
  'destructive wipers': { id: 'T1485', name: 'Data Destruction' },
  'wiper malware': { id: 'T1485', name: 'Data Destruction' },
  'powershell': { id: 'T1059.001', name: 'Command and Scripting Interpreter: PowerShell' },
  'social engineering': { id: 'T1598', name: 'Phishing for Information' },
  'usb spreading': { id: 'T1091', name: 'Replication Through Removable Media' },
  'exploit kits': { id: 'T1190', name: 'Exploit Public-Facing Application' },
  'web exploitation': { id: 'T1190', name: 'Exploit Public-Facing Application' },
  'strategic web compromise': { id: 'T1189', name: 'Drive-by Compromise' },
  'rootkits': { id: 'T1014', name: 'Rootkit' },
  'bootkit': { id: 'T1542.003', name: 'Pre-OS Boot: Bootkit' },
  'network implants': { id: 'T1557', name: 'Adversary-in-the-Middle' },
  'browser exploitation': { id: 'T1189', name: 'Drive-by Compromise' },
  'mobile malware': { id: 'T1474', name: 'Supply Chain Compromise (Mobile)' },
  'c2 over https': { id: 'T1071.001', name: 'Application Layer Protocol: Web Protocols' },
  'encrypted c2': { id: 'T1573', name: 'Encrypted Channel' },
  'process injection': { id: 'T1055', name: 'Process Injection' },
  'registry persistence': { id: 'T1547.001', name: 'Boot or Logon Autostart Execution: Registry Run Keys' },
  'scheduled tasks': { id: 'T1053.005', name: 'Scheduled Task/Job: Scheduled Task' },
  'sql injection': { id: 'T1190', name: 'Exploit Public-Facing Application' },
  'vpn exploitation': { id: 'T1133', name: 'External Remote Services' },
  'fileless malware': { id: 'T1059', name: 'Command and Scripting Interpreter' }
};

const TOPO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';
const NEWS_URL = 'https://raw.githubusercontent.com/arandomguyhere/Drone_news/main/data/latest_news.json';

// ─── State ──────────────────────────────────────────────
let aptData = null;
let selectedGroup = null;
let activeFilter = 'all';
let activeTab = 'map';
let svg, g, projection, path, zoom;
let mapWidth, mapHeight;
let newsData = null;
let statsRendered = false;
let timelineRendered = false;

// ─── Init ───────────────────────────────────────────────
async function init() {
  const [worldRes, aptRes] = await Promise.all([
    fetch(TOPO_URL),
    fetch('data/apt-groups.json')
  ]);
  const world = await worldRes.json();
  aptData = await aptRes.json();

  loadOriginColors();
  renderStats();
  renderFilterButtons();
  renderMap(world);
  renderLegend();
  renderSidebar();
  setupSearch();
  setupFilters();
  setupControls();
  setupTabs();
}

function loadOriginColors() {
  if (aptData.origins) {
    Object.entries(aptData.origins).forEach(([name, info]) => {
      if (info.color) ORIGIN_COLORS[name] = info.color;
    });
  }
}

function renderFilterButtons() {
  const row = document.querySelector('.filter-row');
  if (!row) return;
  const SHORT_NAMES = {
    'North Korea': 'DPRK', 'United States': 'USA',
    'United Arab Emirates': 'UAE', 'South Korea': 'S. Korea'
  };
  const origins = Object.entries(aptData.origins || {})
    .filter(([name]) => name !== 'Unknown')
    .sort((a, b) => b[1].groups_count - a[1].groups_count);
  row.innerHTML = '<button class="filter-btn active" data-filter="all">All</button>';
  origins.forEach(([name]) => {
    const label = SHORT_NAMES[name] || name;
    row.innerHTML += `<button class="filter-btn" data-filter="${name}">${label}</button>`;
  });
}

// ─── Stats ──────────────────────────────────────────────
function renderStats() {
  const el = document.getElementById('stats');
  const groups = aptData.apt_groups;
  const activeCount = groups.filter(g => g.active).length;
  const origins = new Set(groups.map(g => g.origin).filter(o => o !== 'Unknown')).size;
  const updated = aptData.metadata?.last_updated || 'Unknown';
  el.innerHTML = `
    <div class="stat-item"><div class="stat-value">${groups.length}</div><div class="stat-label">APT Groups</div></div>
    <div class="stat-item"><div class="stat-value">${activeCount}</div><div class="stat-label">Active</div></div>
    <div class="stat-item"><div class="stat-value">${origins}</div><div class="stat-label">Origins</div></div>
    <div class="stat-item"><div class="stat-value" style="font-size:0.8rem">${updated}</div><div class="stat-label">Last Updated</div></div>
  `;
}

// ─── Tabs ───────────────────────────────────────────────
function setupTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      if (tab === activeTab) return;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      document.getElementById(`tab-${tab}`).classList.add('active');
      activeTab = tab;

      if (tab === 'stats' && !statsRendered) {
        renderStatsCharts();
        statsRendered = true;
      }
      if (tab === 'timeline' && !timelineRendered) {
        renderTimeline();
        timelineRendered = true;
      }
      if (tab === 'news' && !newsData) {
        loadNews();
      }
    });
  });
}

// ─── Map ────────────────────────────────────────────────
function renderMap(world) {
  const container = document.getElementById('world-map');
  mapWidth = container.clientWidth;
  mapHeight = container.clientHeight;

  projection = d3.geoNaturalEarth1()
    .fitSize([mapWidth, mapHeight], { type: 'Sphere' })
    .precision(0.1);
  path = d3.geoPath(projection);

  svg = d3.select(container).html('').append('svg')
    .attr('width', mapWidth).attr('height', mapHeight);

  const defs = svg.append('defs');
  const glowFilter = defs.append('filter').attr('id', 'glow');
  glowFilter.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'blur');
  glowFilter.append('feMerge').selectAll('feMergeNode')
    .data(['blur', 'SourceGraphic']).enter()
    .append('feMergeNode').attr('in', d => d);

  const softGlow = defs.append('filter').attr('id', 'softGlow');
  softGlow.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur');
  softGlow.append('feMerge').selectAll('feMergeNode')
    .data(['blur', 'SourceGraphic']).enter()
    .append('feMergeNode').attr('in', d => d);

  zoom = d3.zoom().scaleExtent([1, 8])
    .on('zoom', (event) => g.attr('transform', event.transform));
  svg.call(zoom);
  g = svg.append('g');

  g.append('path').datum({ type: 'Sphere' }).attr('class', 'sphere').attr('d', path);
  g.append('path').datum(d3.geoGraticule().step([20, 20])())
    .attr('class', 'graticule').attr('d', path);

  const countries = topojson.feature(world, world.objects.countries);
  g.selectAll('.land').data(countries.features).enter().append('path')
    .attr('class', 'land').attr('d', path)
    .attr('data-name', d => d.properties.name)
    .on('click', (event, d) => {
      const countryName = d.properties.name;
      const origin = COUNTRY_NAME_MAP[countryName];
      if (origin && aptData.apt_groups.some(g => g.origin === origin)) {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        const btn = document.querySelector(`.filter-btn[data-filter="${origin}"]`);
        if (btn) btn.classList.add('active');
        activeFilter = origin;
        applyFilters();
      }
    });

  g.append('path')
    .datum(topojson.mesh(world, world.objects.countries, (a, b) => a !== b))
    .attr('class', 'country-border').attr('d', path);

  const arcsLayer = g.append('g').attr('class', 'arcs-layer');
  const markersLayer = g.append('g').attr('class', 'markers-layer');
  renderMarkers(markersLayer);
  renderArcs(arcsLayer);
}

function renderMarkers(layer) {
  const groups = aptData.apt_groups;
  const byOrigin = {};
  groups.forEach(g => {
    if (!byOrigin[g.origin]) byOrigin[g.origin] = [];
    byOrigin[g.origin].push(g);
  });

  Object.entries(byOrigin).forEach(([origin, oGroups]) => {
    const color = ORIGIN_COLORS[origin] || '#888';
    oGroups.forEach((group, i) => {
      const baseCoords = group.origin_coords;
      if (baseCoords[0] === 0 && baseCoords[1] === 0) return;

      const [basePx, basePy] = projection([baseCoords[1], baseCoords[0]]);
      if (isNaN(basePx) || isNaN(basePy)) return;

      const n = oGroups.length;
      const angle = (i / n) * Math.PI * 2;
      const pixelRadius = n > 1 ? Math.min(8 + n * 1.5, 25) : 0;
      const px = basePx + Math.cos(angle) * pixelRadius;
      const py = basePy + Math.sin(angle) * pixelRadius;

      const threat = group.threat_level;
      const r = threat === 'critical' ? 5 : threat === 'high' ? 4 : 3;

      const markerG = layer.append('g')
        .attr('class', 'apt-marker-group')
        .attr('transform', `translate(${px},${py})`)
        .attr('data-id', group.id);

      markerG.append('circle').attr('class', 'marker-glow')
        .attr('r', r * 4).attr('fill', color).attr('filter', 'url(#softGlow)');

      const ring = markerG.append('circle').attr('class', 'marker-ring')
        .attr('r', r + 4).attr('stroke', color);

      function pulseRing() {
        ring.attr('r', r + 4).attr('opacity', 0.5).transition()
          .duration(threat === 'critical' ? 1800 : 2500)
          .attr('r', r + 14).attr('opacity', 0).on('end', pulseRing);
      }
      if (group.active) pulseRing();

      markerG.append('circle').attr('class', 'marker-dot').attr('r', r).attr('fill', color);
      markerG.append('circle').attr('class', 'marker-inner')
        .attr('r', r * 0.35).attr('fill', '#fff').attr('opacity', 0.5);

      markerG.append('text').attr('class', 'marker-label')
        .attr('y', -(r + 8)).attr('text-anchor', 'middle')
        .attr('fill', color).attr('font-size', '8px').attr('opacity', 0)
        .text(group.name);

      markerG.on('mouseenter', (event) => {
        markerG.select('.marker-label').attr('opacity', 1);
        markerG.select('.marker-glow').attr('opacity', 0.3);
        showTooltip(event, group, color);
        showArcs(group.id);
      });
      markerG.on('mouseleave', () => {
        markerG.select('.marker-label').attr('opacity', 0);
        markerG.select('.marker-glow').attr('opacity', 0.15);
        hideTooltip();
        if (!selectedGroup || selectedGroup.id !== group.id) hideArcs(group.id);
      });
      markerG.on('click', () => openDetail(group));
    });
  });
}

function renderArcs(layer) {
  aptData.apt_groups.forEach(group => {
    if (group.origin_coords[0] === 0 && group.origin_coords[1] === 0) return;
    const color = ORIGIN_COLORS[group.origin] || '#888';
    const originLon = group.origin_coords[1];
    const originLat = group.origin_coords[0];

    group.target_regions.forEach(region => {
      const target = REGION_COORDS[region];
      if (!target) return;
      const arcPath = createGreatCircleArc([originLon, originLat], target);
      if (!arcPath) return;

      layer.append('path').attr('class', `attack-arc-glow arc-${group.id}`)
        .attr('d', path(arcPath)).attr('stroke', color);
      const mainArc = layer.append('path').attr('class', `attack-arc arc-${group.id}`)
        .attr('d', path(arcPath)).attr('stroke', color).attr('stroke-dasharray', '4,3');
      const particlePath = layer.append('circle')
        .attr('class', `arc-particle arc-particle-${group.id}`)
        .attr('r', 2).attr('fill', color).attr('filter', 'url(#glow)');
      mainArc.node().__particleCircle = particlePath;
    });
  });
}

function createGreatCircleArc(source, target) {
  const interp = d3.geoInterpolate(source, target);
  const coords = [];
  for (let i = 0; i <= 30; i++) coords.push(interp(i / 30));
  return { type: 'LineString', coordinates: coords };
}

function showArcs(groupId) {
  svg.selectAll(`.arc-${groupId}`).classed('visible', true);
  svg.selectAll(`.attack-arc.arc-${groupId}`).each(function() {
    const particle = d3.select(this.__particleCircle?.node());
    if (!particle.empty()) { particle.classed('visible', true); animateParticle(this, particle); }
  });
}

function hideArcs(groupId) {
  svg.selectAll(`.arc-${groupId}`).classed('visible', false);
  svg.selectAll(`.arc-particle-${groupId}`).classed('visible', false);
}

function animateParticle(pathNode, particle) {
  const totalLength = pathNode.getTotalLength();
  if (!totalLength) return;
  function animate() {
    if (!particle.classed('visible')) return;
    particle.attr('transform', () => {
      const p = pathNode.getPointAtLength(0);
      return `translate(${p.x},${p.y})`;
    }).transition().duration(2000).attrTween('transform', () => (t) => {
      const p = pathNode.getPointAtLength(t * totalLength);
      return `translate(${p.x},${p.y})`;
    }).on('end', animate);
  }
  animate();
}

// ─── Tooltip ────────────────────────────────────────────
function showTooltip(event, group, color) {
  const tt = document.getElementById('map-tooltip');
  const threatColor = THREAT_COLORS[group.threat_level] || '#888';
  tt.innerHTML = `
    <div class="tt-name" style="color:${color}">${group.name}</div>
    <div class="tt-origin">${group.origin} &middot; Since ${group.first_seen}</div>
    <div class="tt-threat" style="background:${threatColor}22;color:${threatColor};border:1px solid ${threatColor}44">${group.threat_level}</div>
  `;
  tt.style.left = (event.pageX + 14) + 'px';
  tt.style.top = (event.pageY - 10) + 'px';
  tt.classList.add('show');
}

function hideTooltip() {
  document.getElementById('map-tooltip').classList.remove('show');
}

// ─── Legend ─────────────────────────────────────────────
function renderLegend() {
  const el = document.getElementById('map-legend');
  const activeOrigins = Object.entries(aptData.origins || {})
    .filter(([name]) => name !== 'Unknown')
    .sort((a, b) => b[1].groups_count - a[1].groups_count);
  el.innerHTML = activeOrigins.map(([name, info]) => {
    const color = ORIGIN_COLORS[name] || info.color || '#888';
    return `<div class="legend-item" data-origin="${name}">
      <span class="legend-dot" style="background:${color}"></span>${name}
    </div>`;
  }).join('');

  el.querySelectorAll('.legend-item').forEach(item => {
    item.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      const btn = document.querySelector(`.filter-btn[data-filter="${item.dataset.origin}"]`);
      if (btn) btn.classList.add('active');
      activeFilter = item.dataset.origin;
      applyFilters();
    });
  });
}

// ─── Sidebar ────────────────────────────────────────────
function renderSidebar(groups) {
  const list = document.getElementById('apt-list');
  const data = groups || aptData.apt_groups;

  if (data.length === 0) {
    list.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--text-muted);font-size:0.8rem">No groups match your search.</div>';
    return;
  }

  const sorted = [...data].sort((a, b) => {
    const order = { critical: 0, high: 1, medium: 2, low: 3 };
    return (order[a.threat_level] ?? 3) - (order[b.threat_level] ?? 3);
  });

  list.innerHTML = sorted.map(g => {
    const color = ORIGIN_COLORS[g.origin] || '#e2e8f0';
    return `
    <div class="apt-card${selectedGroup?.id === g.id ? ' selected' : ''}" data-id="${g.id}">
      <div class="apt-card-header">
        <span class="apt-name" style="color:${color}">${g.name}</span>
        <span class="threat-badge ${g.threat_level}">${g.threat_level}</span>
      </div>
      <div class="apt-origin">${g.origin} &middot; ${g.first_seen} ${g.active
        ? '<span style="color:#22c55e">&#9679; Active</span>'
        : '<span style="color:#586374">&#9679; Inactive</span>'}</div>
      <div class="apt-aliases">${g.aliases.slice(0, 3).join(', ')}</div>
      <div class="apt-tags">${g.targets.slice(0, 4).map(t => `<span class="apt-tag">${t}</span>`).join('')}</div>
    </div>`;
  }).join('');

  list.querySelectorAll('.apt-card').forEach(card => {
    card.addEventListener('click', () => {
      const group = aptData.apt_groups.find(g => g.id === card.dataset.id);
      if (group) openDetail(group);
    });
    card.addEventListener('mouseenter', () => showArcs(card.dataset.id));
    card.addEventListener('mouseleave', () => {
      if (!selectedGroup || selectedGroup.id !== card.dataset.id) hideArcs(card.dataset.id);
    });
  });
}

// ─── Search & Filters ───────────────────────────────────
function setupSearch() {
  document.getElementById('search-input').addEventListener('input', applyFilters);
}

function setupFilters() {
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeFilter = btn.dataset.filter;
      applyFilters();
    });
  });
}

function applyFilters() {
  const q = document.getElementById('search-input').value.toLowerCase().trim();
  let filtered = aptData.apt_groups;
  if (activeFilter !== 'all') filtered = filtered.filter(g => g.origin === activeFilter);
  if (q) {
    filtered = filtered.filter(g =>
      g.name.toLowerCase().includes(q) || g.aliases.some(a => a.toLowerCase().includes(q)) ||
      g.origin.toLowerCase().includes(q) || g.targets.some(t => t.toLowerCase().includes(q)) ||
      g.malware.some(m => m.toLowerCase().includes(q))
    );
  }
  renderSidebar(filtered);
  const filteredIds = new Set(filtered.map(g => g.id));
  svg.selectAll('.apt-marker-group').each(function() {
    d3.select(this).attr('opacity', filteredIds.has(this.getAttribute('data-id')) ? 1 : 0.15);
  });
}

// ─── Map Controls ───────────────────────────────────────
function setupControls() {
  document.getElementById('zoom-in').addEventListener('click', () => {
    svg.transition().duration(300).call(zoom.scaleBy, 1.5);
  });
  document.getElementById('zoom-out').addEventListener('click', () => {
    svg.transition().duration(300).call(zoom.scaleBy, 0.67);
  });
  document.getElementById('zoom-reset').addEventListener('click', () => {
    svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
  });
}

// ─── Detail Panel (with MITRE ATT&CK) ──────────────────
function ttpToMitre(ttp) {
  const key = ttp.toLowerCase().trim();
  const match = MITRE_MAP[key];
  if (match) {
    const url = `https://attack.mitre.org/techniques/${match.id.replace('.', '/')}/`;
    return `<a href="${url}" target="_blank" rel="noopener" class="detail-tag ttp mitre-link" title="${match.id}: ${match.name}">${ttp} <span class="mitre-id">${match.id}</span></a>`;
  }
  return `<span class="detail-tag ttp">${ttp}</span>`;
}

function openDetail(group) {
  if (selectedGroup) hideArcs(selectedGroup.id);
  selectedGroup = group;
  const color = ORIGIN_COLORS[group.origin] || '#e2e8f0';
  const panel = document.getElementById('detail-panel');

  panel.innerHTML = `
    <div class="detail-header">
      <div>
        <div class="detail-title" style="color:${color}">${group.name}</div>
        <div style="margin-top:4px;font-size:0.75rem">
          <span class="active-dot ${group.active ? 'on' : 'off'}"></span>
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
          <div class="meta-item"><div class="meta-label">Origin</div><div class="meta-value" style="color:${color}">${group.origin}</div></div>
          <div class="meta-item"><div class="meta-label">First Seen</div><div class="meta-value">${group.first_seen}</div></div>
          <div class="meta-item"><div class="meta-label">Threat Level</div><div class="meta-value"><span class="threat-badge ${group.threat_level}">${group.threat_level}</span></div></div>
          <div class="meta-item"><div class="meta-label">Target Regions</div><div class="meta-value" style="font-size:0.7rem">${group.target_regions.join(', ')}</div></div>
        </div>
      </div>
      <div class="detail-section">
        <div class="detail-section-title">Aliases</div>
        <div class="detail-tags">${group.aliases.map(a => `<span class="detail-tag alias">${a}</span>`).join('')}</div>
      </div>
      <div class="detail-section">
        <div class="detail-section-title">Target Sectors</div>
        <div class="detail-tags">${group.targets.map(t => `<span class="detail-tag target">${t}</span>`).join('')}</div>
      </div>
      <div class="detail-section">
        <div class="detail-section-title">Target Regions</div>
        <div class="detail-tags">${group.target_regions.map(r => `<span class="detail-tag region">${r}</span>`).join('')}</div>
      </div>
      <div class="detail-section">
        <div class="detail-section-title">TTPs <span class="mitre-badge">MITRE ATT&CK</span></div>
        <div class="detail-tags">${group.ttps.map(t => ttpToMitre(t)).join('')}</div>
      </div>
      <div class="detail-section">
        <div class="detail-section-title">Associated Malware</div>
        <div class="detail-tags">${group.malware.map(m => `<span class="detail-tag malware">${m}</span>`).join('')}</div>
      </div>
    </div>
  `;

  panel.classList.add('open');
  document.getElementById('overlay-dimmer').classList.add('active');
  showArcs(group.id);
  document.querySelectorAll('.apt-card').forEach(c => c.classList.remove('selected'));
  const card = document.querySelector(`.apt-card[data-id="${group.id}"]`);
  if (card) { card.classList.add('selected'); card.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }
}

function closeDetail() {
  if (selectedGroup) hideArcs(selectedGroup.id);
  selectedGroup = null;
  document.getElementById('detail-panel').classList.remove('open');
  document.getElementById('overlay-dimmer').classList.remove('active');
  document.querySelectorAll('.apt-card').forEach(c => c.classList.remove('selected'));
}

// ─── Statistics Dashboard ───────────────────────────────
function renderStatsCharts() {
  const groups = aptData.apt_groups;

  // 1. Groups by Origin (horizontal bar)
  renderHorizontalBar('chart-origins',
    countBy(groups, g => g.origin).filter(d => d.key !== 'Unknown'),
    d => ORIGIN_COLORS[d.key] || '#888');

  // 2. Threat Level (donut)
  renderDonut('chart-threats',
    countBy(groups, g => g.threat_level),
    d => THREAT_COLORS[d.key] || '#888');

  // 3. Top Target Sectors (horizontal bar)
  renderHorizontalBar('chart-sectors',
    countByArray(groups, g => g.targets).slice(0, 15),
    () => 'var(--accent-green)');

  // 4. Top Malware (horizontal bar)
  renderHorizontalBar('chart-malware',
    countByArray(groups, g => g.malware).slice(0, 15),
    () => 'var(--accent-red)');
}

function countBy(arr, fn) {
  const counts = {};
  arr.forEach(item => { const k = fn(item); counts[k] = (counts[k] || 0) + 1; });
  return Object.entries(counts).map(([key, count]) => ({ key, count }))
    .sort((a, b) => b.count - a.count);
}

function countByArray(arr, fn) {
  const counts = {};
  arr.forEach(item => fn(item).forEach(v => { if (v) counts[v] = (counts[v] || 0) + 1; }));
  return Object.entries(counts).map(([key, count]) => ({ key, count }))
    .sort((a, b) => b.count - a.count);
}

function renderHorizontalBar(containerId, data, colorFn) {
  const container = document.getElementById(containerId);
  const margin = { top: 8, right: 50, bottom: 8, left: 120 };
  const width = container.clientWidth - margin.left - margin.right;
  const barH = 22;
  const height = data.length * barH;

  const svgEl = d3.select(container).append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom);
  const gEl = svgEl.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

  const x = d3.scaleLinear().domain([0, d3.max(data, d => d.count)]).range([0, width]);
  const y = d3.scaleBand().domain(data.map(d => d.key)).range([0, height]).padding(0.3);

  gEl.selectAll('rect').data(data).enter().append('rect')
    .attr('x', 0).attr('y', d => y(d.key))
    .attr('width', d => x(d.count)).attr('height', y.bandwidth())
    .attr('fill', d => colorFn(d)).attr('rx', 2).attr('opacity', 0.85);

  gEl.selectAll('.bar-label').data(data).enter().append('text')
    .attr('x', -6).attr('y', d => y(d.key) + y.bandwidth() / 2)
    .attr('text-anchor', 'end').attr('dominant-baseline', 'central')
    .attr('fill', 'var(--text-secondary)').attr('font-size', '0.65rem')
    .text(d => d.key.length > 16 ? d.key.slice(0, 15) + '...' : d.key);

  gEl.selectAll('.bar-count').data(data).enter().append('text')
    .attr('x', d => x(d.count) + 6).attr('y', d => y(d.key) + y.bandwidth() / 2)
    .attr('dominant-baseline', 'central')
    .attr('fill', 'var(--text-muted)').attr('font-size', '0.65rem').attr('font-weight', '700')
    .text(d => d.count);
}

function renderDonut(containerId, data, colorFn) {
  const container = document.getElementById(containerId);
  const size = Math.min(container.clientWidth, 280);
  const radius = size / 2;
  const inner = radius * 0.55;

  const svgEl = d3.select(container).append('svg')
    .attr('width', size).attr('height', size);
  const gEl = svgEl.append('g').attr('transform', `translate(${radius},${radius})`);

  const pie = d3.pie().value(d => d.count).sort(null);
  const arc = d3.arc().innerRadius(inner).outerRadius(radius - 4);

  const arcs = gEl.selectAll('.arc').data(pie(data)).enter().append('g');
  arcs.append('path').attr('d', arc).attr('fill', d => colorFn(d.data))
    .attr('stroke', 'var(--bg-primary)').attr('stroke-width', 2);
  arcs.append('text').attr('transform', d => `translate(${arc.centroid(d)})`)
    .attr('text-anchor', 'middle').attr('fill', '#fff').attr('font-size', '0.65rem')
    .attr('font-weight', '700')
    .text(d => d.data.count > 2 ? `${d.data.key} (${d.data.count})` : '');

  // Center label
  gEl.append('text').attr('text-anchor', 'middle').attr('dy', '-0.2em')
    .attr('fill', 'var(--text-primary)').attr('font-size', '1.5rem').attr('font-weight', '800')
    .text(data.reduce((s, d) => s + d.count, 0));
  gEl.append('text').attr('text-anchor', 'middle').attr('dy', '1.2em')
    .attr('fill', 'var(--text-muted)').attr('font-size', '0.6rem').text('TOTAL');
}

// ─── Timeline ───────────────────────────────────────────
function renderTimeline() {
  const container = document.getElementById('timeline-container');
  const groups = aptData.apt_groups
    .filter(g => g.first_seen && g.first_seen !== 'Unknown')
    .map(g => ({ ...g, year: parseInt(g.first_seen) }))
    .filter(g => !isNaN(g.year))
    .sort((a, b) => a.year - b.year);

  if (groups.length === 0) {
    container.innerHTML = '<div style="padding:3rem;text-align:center;color:var(--text-muted)">No timeline data available.</div>';
    return;
  }

  const margin = { top: 40, right: 40, bottom: 60, left: 40 };
  const width = container.clientWidth - margin.left - margin.right;
  const height = container.clientHeight - margin.top - margin.bottom;

  const svgEl = d3.select(container).append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom);
  const gEl = svgEl.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

  const yearMin = d3.min(groups, d => d.year);
  const yearMax = d3.max(groups, d => d.year);
  const x = d3.scaleLinear().domain([yearMin - 1, yearMax + 1]).range([0, width]);

  // Group by year for vertical stacking
  const byYear = {};
  groups.forEach(g => {
    if (!byYear[g.year]) byYear[g.year] = [];
    byYear[g.year].push(g);
  });

  const maxStack = d3.max(Object.values(byYear), arr => arr.length);
  const dotR = Math.min(12, Math.max(6, height / (maxStack * 3)));

  // Axis
  const years = d3.range(yearMin, yearMax + 1);
  gEl.append('g').attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(x).tickValues(years.filter((_, i) => i % 2 === 0)).tickFormat(d3.format('d')))
    .selectAll('text').attr('fill', 'var(--text-muted)').attr('font-size', '0.6rem');
  gEl.selectAll('.domain, .tick line').attr('stroke', 'var(--border)');

  // Timeline base line
  gEl.append('line').attr('x1', 0).attr('x2', width)
    .attr('y1', height).attr('y2', height)
    .attr('stroke', 'var(--border-light)').attr('stroke-width', 1);

  // Draw dots
  Object.entries(byYear).forEach(([year, yearGroups]) => {
    yearGroups.forEach((group, i) => {
      const cx = x(parseInt(year));
      const cy = height - (i + 1) * (dotR * 2.2);
      const color = ORIGIN_COLORS[group.origin] || '#888';

      const dot = gEl.append('g').attr('class', 'timeline-dot')
        .attr('transform', `translate(${cx},${cy})`).style('cursor', 'pointer');

      dot.append('circle').attr('r', dotR).attr('fill', color).attr('opacity', 0.85)
        .attr('stroke', color).attr('stroke-width', 1).attr('stroke-opacity', 0.3);

      dot.append('text').attr('text-anchor', 'middle').attr('dy', '0.35em')
        .attr('fill', '#fff').attr('font-size', `${Math.max(5, dotR - 2)}px`)
        .attr('font-weight', '600')
        .text(group.name.length > 5 ? group.name.slice(0, 4) : group.name);

      dot.on('mouseenter', function(event) {
        d3.select(this).select('circle').attr('opacity', 1).attr('stroke-width', 2);
        showTooltip(event, group, color);
      });
      dot.on('mouseleave', function() {
        d3.select(this).select('circle').attr('opacity', 0.85).attr('stroke-width', 1);
        hideTooltip();
      });
      dot.on('click', () => openDetail(group));
    });
  });

  // Title
  svgEl.append('text').attr('x', margin.left).attr('y', 24)
    .attr('fill', 'var(--text-secondary)').attr('font-size', '0.75rem').attr('font-weight', '600')
    .text(`APT Group Timeline (${yearMin} - ${yearMax})`);
}

// ─── News Feed ──────────────────────────────────────────
async function loadNews() {
  const container = document.getElementById('news-container');
  try {
    const res = await fetch(NEWS_URL);
    newsData = await res.json();
    renderNews();
  } catch (e) {
    container.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--text-muted)">Failed to load news feed. Check connection.</div>';
  }
}

function renderNews() {
  const container = document.getElementById('news-container');
  if (!newsData || newsData.length === 0) {
    container.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--text-muted)">No news articles available.</div>';
    return;
  }

  // Relevant categories for APT/threat intel
  const aptKeywords = ['apt', 'threat', 'cyber', 'hack', 'malware', 'ransomware', 'zero-day',
    'nation-state', 'espionage', 'phishing', 'vulnerability', 'exploit', 'breach', 'attack',
    'china', 'russia', 'iran', 'north korea', 'dprk', 'typhoon', 'panda', 'bear', 'lazarus',
    'sandworm', 'cozy', 'fancy', 'apt28', 'apt29', 'apt41', 'volt', 'salt', 'charcoal'];

  // Sort by datetime (most recent first)
  const sorted = [...newsData].sort((a, b) =>
    new Date(b.Datetime || 0) - new Date(a.Datetime || 0));

  // Partition: APT-relevant first, then others
  const relevant = [];
  const other = [];
  sorted.forEach(article => {
    const text = `${article.Title} ${article.Category}`.toLowerCase();
    if (aptKeywords.some(k => text.includes(k))) relevant.push(article);
    else other.push(article);
  });

  const allArticles = [...relevant.slice(0, 60), ...other.slice(0, 40)];

  container.innerHTML = `
    <div class="news-header">
      <div class="news-title-bar">
        <span class="news-count">${newsData.length} articles</span>
        <span class="news-source">via Drone_news aggregator</span>
      </div>
    </div>
    <div class="news-grid">
      ${allArticles.map(a => {
        const date = a.Datetime ? new Date(a.Datetime) : null;
        const timeStr = date ? date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : a.Published;
        const isRelevant = relevant.includes(a);
        return `
          <a href="${a.Link}" target="_blank" rel="noopener" class="news-card ${isRelevant ? 'relevant' : ''}">
            <div class="news-card-cat">${a.Category}</div>
            <div class="news-card-title">${a.Title}</div>
            <div class="news-card-meta">
              <span>${timeStr}</span>
              <span>${a.Source}</span>
            </div>
          </a>`;
      }).join('')}
    </div>
  `;
}

// ─── Resize ─────────────────────────────────────────────
let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(async () => {
    if (!aptData) return;
    if (activeTab === 'map') {
      const worldRes = await fetch(TOPO_URL);
      const world = await worldRes.json();
      renderMap(world);
    }
    if (activeTab === 'stats') {
      document.querySelectorAll('.chart-container').forEach(c => c.innerHTML = '');
      renderStatsCharts();
    }
    if (activeTab === 'timeline') {
      document.getElementById('timeline-container').innerHTML = '';
      renderTimeline();
    }
  }, 300);
});

// ─── Start ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
