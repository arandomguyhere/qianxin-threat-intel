# QiAnxin APT Threat Intelligence Map

Interactive APT threat group map visualization based on [QiAnxin Threat Intelligence Center](https://ti.qianxin.com/apt/apt?type=map) data.

**Live site:** https://arandomguyhere.github.io/qianxin-threat-intel/

## Features

- **D3.js world map** with real country boundaries via TopoJSON (Natural Earth projection)
- **23 APT groups** across 7 nation-state origins (Russia, China, North Korea, Iran, India, USA, Vietnam)
- **Animated attack arcs** showing great-circle paths from origin to target regions
- **Pulsing markers** with glow effects, color-coded by origin country
- **Zoom & pan** with scroll, drag, and +/-/reset controls
- **Searchable sidebar** - filter by group name, aliases, malware, or target sectors
- **Country filters** - one-click filtering by origin nation
- **Detail panel** - click any group for full intel: description, aliases, TTPs, target sectors, malware

## Data Pipeline

APT group data is scraped from QiAnxin's live APT map and updated automatically.

### How it works

1. **`scripts/scrape.py`** - Playwright scraper loads the QiAnxin APT map in a headless browser, intercepts all JSON API responses, and dumps them to `qianxin_apt_dump/`
2. **`scripts/transform.py`** - Scans the raw dumps, detects APT group records by structure, normalizes fields (including Chinese-to-English country names), and writes `docs/data/apt-groups.json`
3. **GitHub Action** (`.github/workflows/update-apt-data.yml`) - Runs the pipeline weekly (Monday 06:00 UTC) and commits any changes automatically. Can also be triggered manually via `workflow_dispatch`.

### Run manually

```bash
pip install -r requirements.txt
playwright install chromium

python scripts/scrape.py      # Scrape QiAnxin API responses
python scripts/transform.py   # Transform into apt-groups.json
```

### Data fields per group

- Origin country and coordinates
- Known aliases
- First seen date and active status
- Threat level (critical / high / medium)
- Target sectors and regions
- Tactics, techniques, and procedures (TTPs)
- Associated malware families

## Setup

Enable GitHub Pages from repo Settings > Pages > source branch > `/docs` folder. No build step required -- the site is all static HTML/CSS/JS.
