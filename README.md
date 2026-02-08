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

## Data

APT group data is compiled from open-source threat intelligence reports and QiAnxin research. Each group includes:

- Origin country and coordinates
- Known aliases
- First seen date and active status
- Threat level (critical / high / medium)
- Target sectors and regions
- Tactics, techniques, and procedures (TTPs)
- Associated malware families

## Setup

Enable GitHub Pages from repo Settings > Pages > source branch > `/docs` folder. No build step required — it's all static HTML/CSS/JS.
