// ─── Config ─────────────────────────────────────────────
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
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308'
};

const COUNTRY_NAME_MAP = {
  'Russia': 'Russia',
  'China': 'China',
  'North Korea': 'N. Korea',
  'Iran': 'Iran',
  'United States': 'United States of America',
  'Vietnam': 'Vietnam',
  'India': 'India'
};

// Region centroids for drawing attack arcs
const REGION_COORDS = {
  'North America': [-100, 45],
  'South America': [-60, -15],
  'Europe': [15, 50],
  'Middle East': [45, 28],
  'Central Asia': [65, 42],
  'East Asia': [120, 35],
  'Southeast Asia': [110, 5],
  'South Asia': [78, 22],
  'Oceania': [135, -25],
  'Africa': [20, 5],
  'Global': [0, 20],
  'Ukraine': [32, 49],
  'South Korea': [127, 36],
  'Japan': [138, 36],
  'Asia Pacific': [130, 15],
  'Americas': [-80, 20],
  'United States': [-98, 38]
};

const TOPO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

// ─── State ──────────────────────────────────────────────
let aptData = null;
let selectedGroup = null;
let activeFilter = 'all';
let svg, g, projection, path, zoom;
let mapWidth, mapHeight;

// ─── Init ───────────────────────────────────────────────
async function init() {
  const [worldRes, aptRes] = await Promise.all([
    fetch(TOPO_URL),
    fetch('data/apt-groups.json')
  ]);
  const world = await worldRes.json();
  aptData = await aptRes.json();

  renderStats();
  renderMap(world);
  renderLegend();
  renderSidebar();
  setupSearch();
  setupFilters();
  setupControls();
}

// ─── Stats ──────────────────────────────────────────────
function renderStats() {
  const el = document.getElementById('stats');
  const groups = aptData.apt_groups;
  const activeCount = groups.filter(g => g.active).length;
  const origins = new Set(groups.map(g => g.origin)).size;
  el.innerHTML = `
    <div class="stat-item"><div class="stat-value">${groups.length}</div><div class="stat-label">APT Groups</div></div>
    <div class="stat-item"><div class="stat-value">${activeCount}</div><div class="stat-label">Active</div></div>
    <div class="stat-item"><div class="stat-value">${origins}</div><div class="stat-label">Origins</div></div>
  `;
}

// ─── Map ────────────────────────────────────────────────
function renderMap(world) {
  const container = document.getElementById('world-map');
  mapWidth = container.clientWidth;
  mapHeight = container.clientHeight;

  // Projection
  projection = d3.geoNaturalEarth1()
    .fitSize([mapWidth, mapHeight], { type: 'Sphere' })
    .precision(0.1);

  path = d3.geoPath(projection);

  // SVG
  svg = d3.select(container)
    .html('')
    .append('svg')
    .attr('width', mapWidth)
    .attr('height', mapHeight);

  // Defs for glow filters and gradients
  const defs = svg.append('defs');

  // Glow filter
  const glowFilter = defs.append('filter').attr('id', 'glow');
  glowFilter.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'blur');
  glowFilter.append('feMerge').selectAll('feMergeNode')
    .data(['blur', 'SourceGraphic']).enter()
    .append('feMergeNode').attr('in', d => d);

  // Soft glow for markers
  const softGlow = defs.append('filter').attr('id', 'softGlow');
  softGlow.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur');
  softGlow.append('feMerge').selectAll('feMergeNode')
    .data(['blur', 'SourceGraphic']).enter()
    .append('feMergeNode').attr('in', d => d);

  // Zoom behavior
  zoom = d3.zoom()
    .scaleExtent([1, 8])
    .on('zoom', (event) => {
      g.attr('transform', event.transform);
    });

  svg.call(zoom);

  g = svg.append('g');

  // Sphere background
  g.append('path')
    .datum({ type: 'Sphere' })
    .attr('class', 'sphere')
    .attr('d', path);

  // Graticule
  const graticule = d3.geoGraticule().step([20, 20]);
  g.append('path')
    .datum(graticule())
    .attr('class', 'graticule')
    .attr('d', path);

  // Countries
  const countries = topojson.feature(world, world.objects.countries);

  g.selectAll('.land')
    .data(countries.features)
    .enter()
    .append('path')
    .attr('class', 'land')
    .attr('d', path)
    .attr('data-name', d => d.properties.name);

  // Country borders
  g.append('path')
    .datum(topojson.mesh(world, world.objects.countries, (a, b) => a !== b))
    .attr('class', 'country-border')
    .attr('d', path);

  // Attack arcs layer
  const arcsLayer = g.append('g').attr('class', 'arcs-layer');

  // Markers layer
  const markersLayer = g.append('g').attr('class', 'markers-layer');

  // Place APT markers
  renderMarkers(markersLayer);

  // Precompute arcs (hidden until hover/select)
  renderArcs(arcsLayer);
}

function renderMarkers(layer) {
  const groups = aptData.apt_groups;
  const byOrigin = {};
  groups.forEach(g => {
    if (!byOrigin[g.origin]) byOrigin[g.origin] = [];
    byOrigin[g.origin].push(g);
  });

  const tooltip = document.getElementById('map-tooltip');

  Object.entries(byOrigin).forEach(([origin, oGroups]) => {
    const color = ORIGIN_COLORS[origin] || '#888';

    oGroups.forEach((group, i) => {
      // Offset groups from same origin so they don't stack
      const baseCoords = group.origin_coords;
      const angle = (i / oGroups.length) * Math.PI * 2;
      const spread = oGroups.length > 1 ? 3 + i * 1.2 : 0;
      const lon = baseCoords[1] + Math.cos(angle) * spread;
      const lat = baseCoords[0] + Math.sin(angle) * spread;
      const [px, py] = projection([lon, lat]);

      if (isNaN(px) || isNaN(py)) return;

      const threat = group.threat_level;
      const r = threat === 'critical' ? 5 : threat === 'high' ? 4 : 3;

      const markerG = layer.append('g')
        .attr('class', 'apt-marker-group')
        .attr('transform', `translate(${px},${py})`)
        .attr('data-id', group.id);

      // Animated glow
      markerG.append('circle')
        .attr('class', 'marker-glow')
        .attr('r', r * 4)
        .attr('fill', color)
        .attr('filter', 'url(#softGlow)');

      // Pulsing ring
      const ring = markerG.append('circle')
        .attr('class', 'marker-ring')
        .attr('r', r + 4)
        .attr('stroke', color);

      // Pulse animation
      function pulseRing() {
        ring
          .attr('r', r + 4)
          .attr('opacity', 0.5)
          .transition()
          .duration(threat === 'critical' ? 1800 : 2500)
          .attr('r', r + 14)
          .attr('opacity', 0)
          .on('end', pulseRing);
      }
      if (group.active) pulseRing();

      // Main dot
      markerG.append('circle')
        .attr('class', 'marker-dot')
        .attr('r', r)
        .attr('fill', color);

      // Inner bright spot
      markerG.append('circle')
        .attr('class', 'marker-inner')
        .attr('r', r * 0.35)
        .attr('fill', '#fff')
        .attr('opacity', 0.5);

      // Label (hidden by default, shown on hover)
      markerG.append('text')
        .attr('class', 'marker-label')
        .attr('y', -(r + 8))
        .attr('text-anchor', 'middle')
        .attr('fill', color)
        .attr('font-size', '8px')
        .attr('opacity', 0)
        .text(group.name);

      // Events
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
        if (!selectedGroup || selectedGroup.id !== group.id) {
          hideArcs(group.id);
        }
      });

      markerG.on('click', () => {
        openDetail(group);
      });
    });
  });
}

function renderArcs(layer) {
  const groups = aptData.apt_groups;

  groups.forEach(group => {
    const color = ORIGIN_COLORS[group.origin] || '#888';
    const originLon = group.origin_coords[1];
    const originLat = group.origin_coords[0];

    group.target_regions.forEach(region => {
      const target = REGION_COORDS[region];
      if (!target) return;

      const arcPath = createGreatCircleArc([originLon, originLat], target);
      if (!arcPath) return;

      // Glow arc
      layer.append('path')
        .attr('class', `attack-arc-glow arc-${group.id}`)
        .attr('d', path(arcPath))
        .attr('stroke', color);

      // Main arc
      const mainArc = layer.append('path')
        .attr('class', `attack-arc arc-${group.id}`)
        .attr('d', path(arcPath))
        .attr('stroke', color)
        .attr('stroke-dasharray', '4,3');

      // Animated particle
      const particlePath = layer.append('circle')
        .attr('class', `arc-particle arc-particle-${group.id}`)
        .attr('r', 2)
        .attr('fill', color)
        .attr('filter', 'url(#glow)');

      // Store path ref for animation
      mainArc.node().__particleCircle = particlePath;
      mainArc.node().__group = group.id;
    });
  });
}

function createGreatCircleArc(source, target) {
  const interp = d3.geoInterpolate(source, target);
  const numPoints = 30;
  const coords = [];
  for (let i = 0; i <= numPoints; i++) {
    coords.push(interp(i / numPoints));
  }
  return { type: 'LineString', coordinates: coords };
}

function showArcs(groupId) {
  svg.selectAll(`.arc-${groupId}`).classed('visible', true);
  // Animate particles along arcs
  svg.selectAll(`.attack-arc.arc-${groupId}`).each(function() {
    const arcNode = this;
    const particle = d3.select(arcNode.__particleCircle?.node());
    if (!particle.empty()) {
      particle.classed('visible', true);
      animateParticle(arcNode, particle);
    }
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
    particle
      .attr('transform', () => {
        const p = pathNode.getPointAtLength(0);
        return `translate(${p.x},${p.y})`;
      })
      .transition()
      .duration(2000)
      .attrTween('transform', () => {
        return (t) => {
          const p = pathNode.getPointAtLength(t * totalLength);
          return `translate(${p.x},${p.y})`;
        };
      })
      .on('end', animate);
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
  el.innerHTML = Object.entries(ORIGIN_COLORS).map(([name, color]) =>
    `<div class="legend-item" data-origin="${name}">
      <span class="legend-dot" style="background:${color}"></span>${name}
    </div>`
  ).join('');

  el.querySelectorAll('.legend-item').forEach(item => {
    item.addEventListener('click', () => {
      const origin = item.dataset.origin;
      // Set filter
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      const btn = document.querySelector(`.filter-btn[data-filter="${origin}"]`);
      if (btn) btn.classList.add('active');
      activeFilter = origin;
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

  // Click handlers
  list.querySelectorAll('.apt-card').forEach(card => {
    card.addEventListener('click', () => {
      const group = aptData.apt_groups.find(g => g.id === card.dataset.id);
      if (group) openDetail(group);
    });
    card.addEventListener('mouseenter', () => {
      showArcs(card.dataset.id);
    });
    card.addEventListener('mouseleave', () => {
      if (!selectedGroup || selectedGroup.id !== card.dataset.id) {
        hideArcs(card.dataset.id);
      }
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

  if (activeFilter !== 'all') {
    filtered = filtered.filter(g => g.origin === activeFilter);
  }

  if (q) {
    filtered = filtered.filter(g =>
      g.name.toLowerCase().includes(q) ||
      g.aliases.some(a => a.toLowerCase().includes(q)) ||
      g.origin.toLowerCase().includes(q) ||
      g.targets.some(t => t.toLowerCase().includes(q)) ||
      g.malware.some(m => m.toLowerCase().includes(q))
    );
  }

  renderSidebar(filtered);

  // Highlight markers
  svg.selectAll('.apt-marker-group').attr('opacity', d => {
    if (filtered.length === aptData.apt_groups.length) return 1;
    const id = d3.select(d || this).attr('data-id');
    return 1;
  });

  // Dim non-matching markers
  const filteredIds = new Set(filtered.map(g => g.id));
  svg.selectAll('.apt-marker-group').each(function() {
    const id = this.getAttribute('data-id');
    d3.select(this).attr('opacity', filteredIds.has(id) ? 1 : 0.15);
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

// ─── Detail Panel ───────────────────────────────────────
function openDetail(group) {
  // Hide previous arcs
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
          <div class="meta-item">
            <div class="meta-label">Origin</div>
            <div class="meta-value" style="color:${color}">${group.origin}</div>
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
            <div class="meta-value" style="font-size:0.7rem">${group.target_regions.join(', ')}</div>
          </div>
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
        <div class="detail-section-title">TTPs</div>
        <div class="detail-tags">${group.ttps.map(t => `<span class="detail-tag ttp">${t}</span>`).join('')}</div>
      </div>
      <div class="detail-section">
        <div class="detail-section-title">Associated Malware</div>
        <div class="detail-tags">${group.malware.map(m => `<span class="detail-tag malware">${m}</span>`).join('')}</div>
      </div>
    </div>
  `;

  panel.classList.add('open');
  document.getElementById('overlay-dimmer').classList.add('active');

  // Show arcs for selected group
  showArcs(group.id);

  // Update sidebar selection
  document.querySelectorAll('.apt-card').forEach(c => c.classList.remove('selected'));
  const card = document.querySelector(`.apt-card[data-id="${group.id}"]`);
  if (card) {
    card.classList.add('selected');
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

function closeDetail() {
  if (selectedGroup) hideArcs(selectedGroup.id);
  selectedGroup = null;
  document.getElementById('detail-panel').classList.remove('open');
  document.getElementById('overlay-dimmer').classList.remove('active');
  document.querySelectorAll('.apt-card').forEach(c => c.classList.remove('selected'));
}

// ─── Resize ─────────────────────────────────────────────
let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(async () => {
    if (!aptData) return;
    const worldRes = await fetch(TOPO_URL);
    const world = await worldRes.json();
    renderMap(world);
  }, 300);
});

// ─── Start ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
