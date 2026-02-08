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

1. **`scripts/scrape.py`** - Playwright scraper loads the QiAnxin APT map in a headless browser, intercepts all JSON API responses (notably `/alpha-api/v2/apt-dossier/actor/all` and `/alpha-api/v2/apt-dossier/map/v2`), and dumps them to `qianxin_apt_dump/`
2. **`scripts/transform.py`** - Targets the `apt-dossier` endpoints first, falls back to scanning all dumps. Unwraps the `{status, message, data}` envelope, normalizes fields (Chinese-to-English country names, nested objects, etc.), and writes `docs/data/apt-groups.json`. If no groups are detected, prints full debug output showing each file's structure and keeps existing data unchanged.
3. **GitHub Action** (`.github/workflows/update-apt-data.yml`) - Runs the pipeline weekly (Monday 06:00 UTC) and commits any changes automatically. Can also be triggered manually via `workflow_dispatch`. The run summary shows update status, group count, and last-updated date. Raw dumps are uploaded as artifacts (30-day retention).

### Monitoring updates

- **On the site**: header shows "Last Updated" date from the data
- **GitHub Actions tab**: each run shows a summary table with status, group count, and dates
- **Git log**: auto-commits appear as `chore: update APT data from QiAnxin (YYYY-MM-DD)`
- **Artifacts**: raw API dumps downloadable from each Action run for inspection

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
