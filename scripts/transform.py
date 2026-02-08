"""
Transform scraped QiAnxin APT dump into docs/data/apt-groups.json.

Run after scrape.py:
    python scripts/scrape.py
    python scripts/transform.py

Targets two specific QiAnxin API endpoints:
  - /alpha-api/v2/apt-dossier/actor/all  → lightweight actor list (actorName, alias, name, type)
  - /alpha-api/v2/apt-dossier/map/v2     → map/geo data with country groupings

The actor endpoint is minimal (only name + aliases). Country attribution comes
from the map endpoint and a built-in known-APT database as fallback.
"""

import glob
import json
import os
import re
import sys
from datetime import date

DUMP_DIR = os.path.join(os.path.dirname(__file__), "..", "qianxin_apt_dump")
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "apt-groups.json")

# ─── Known country coords [lat, lon] ─────────────────────
COUNTRY_COORDS = {
    "Russia": [55.75, 37.62],
    "China": [35.86, 104.20],
    "North Korea": [39.02, 125.75],
    "Iran": [35.69, 51.39],
    "United States": [38.90, -77.04],
    "Vietnam": [21.03, 105.85],
    "India": [28.61, 77.21],
    "Pakistan": [30.38, 69.35],
    "South Korea": [37.57, 126.98],
    "Israel": [31.77, 35.22],
    "Turkey": [39.93, 32.86],
    "Ukraine": [50.45, 30.52],
    "United Kingdom": [51.51, -0.13],
    "France": [48.86, 2.35],
    "Brazil": [-15.79, -47.88],
    "Lebanon": [33.89, 35.50],
    "Gaza": [31.50, 34.47],
    "Syria": [33.51, 36.29],
    "Japan": [36.20, 138.25],
    "Germany": [51.17, 10.45],
    "Canada": [56.13, -106.35],
    "Australia": [-25.27, 133.78],
    "Taiwan": [23.70, 120.96],
    "Saudi Arabia": [23.89, 45.08],
    "Thailand": [15.87, 100.99],
    "Philippines": [12.88, 121.77],
    "Myanmar": [21.91, 95.96],
    "Malaysia": [4.21, 101.98],
    "Singapore": [1.35, 103.82],
    "Indonesia": [-0.79, 113.92],
    "Bangladesh": [23.68, 90.36],
    "Sri Lanka": [7.87, 80.77],
    "Nepal": [28.39, 84.12],
    "Egypt": [26.82, 30.80],
    "Nigeria": [9.08, 7.49],
    "South Africa": [-30.56, 22.94],
    "Mexico": [23.63, -102.55],
    "Colombia": [4.57, -74.30],
    "Argentina": [-38.42, -63.62],
    "Chile": [-35.68, -71.54],
    "Spain": [40.46, -3.75],
    "Italy": [41.87, 12.57],
    "Poland": [51.92, 19.15],
    "Netherlands": [52.13, 5.29],
    "Sweden": [60.13, 18.64],
    "Norway": [60.47, 8.47],
    "Finland": [61.92, 25.75],
    "Denmark": [56.26, 9.50],
    "Belgium": [50.50, 4.47],
    "Switzerland": [46.82, 8.23],
    "Austria": [47.52, 14.55],
    "Czech Republic": [49.82, 15.47],
    "Romania": [45.94, 24.97],
    "Hungary": [47.16, 19.50],
    "Greece": [39.07, 21.82],
    "Portugal": [39.40, -8.22],
    "Belarus": [53.71, 27.95],
    "Georgia": [42.32, 43.36],
    "Azerbaijan": [40.14, 47.58],
    "Kazakhstan": [48.02, 66.92],
    "Uzbekistan": [41.38, 64.59],
    "Tajikistan": [38.86, 71.28],
    "Kyrgyzstan": [41.20, 74.77],
    "Mongolia": [46.86, 103.85],
    "Afghanistan": [33.94, 67.71],
    "Iraq": [33.22, 43.68],
    "Yemen": [15.55, 48.52],
    "Jordan": [30.59, 36.24],
    "United Arab Emirates": [23.42, 53.85],
    "Qatar": [25.35, 51.18],
    "Bahrain": [26.07, 50.56],
    "Kuwait": [29.31, 47.48],
    "Oman": [21.47, 55.98],
    "Palestine": [31.95, 35.23],
    "Ethiopia": [9.15, 40.49],
    "Kenya": [-0.02, 37.91],
    "Tanzania": [-6.37, 34.89],
    "Morocco": [31.79, -7.09],
    "Algeria": [28.03, 1.66],
    "Tunisia": [33.89, 9.54],
    "Libya": [26.34, 17.23],
    "Sudan": [12.86, 30.22],
}

ORIGIN_COLORS = {
    "Russia": "#e74c3c",
    "China": "#e67e22",
    "North Korea": "#a855f7",
    "Iran": "#22c55e",
    "United States": "#3498db",
    "Vietnam": "#06b6d4",
    "India": "#f39c12",
    "Pakistan": "#10b981",
    "South Korea": "#6366f1",
    "Israel": "#0ea5e9",
    "Turkey": "#ec4899",
    "Lebanon": "#84cc16",
    "Palestine": "#84cc16",
    "Gaza": "#84cc16",
    "Belarus": "#d946ef",
    "Kazakhstan": "#f97316",
    "Uzbekistan": "#14b8a6",
    "United Arab Emirates": "#0284c7",
    "Colombia": "#eab308",
    "Egypt": "#b45309",
    "Syria": "#64748b",
    "China": "#e67e22",
}

# ─── Chinese-to-English country name mapping ────────────
COUNTRY_ZH_EN = {
    "俄罗斯": "Russia", "中国": "China", "朝鲜": "North Korea",
    "伊朗": "Iran", "美国": "United States", "越南": "Vietnam",
    "印度": "India", "巴基斯坦": "Pakistan", "韩国": "South Korea",
    "以色列": "Israel", "土耳其": "Turkey", "乌克兰": "Ukraine",
    "英国": "United Kingdom", "法国": "France", "巴西": "Brazil",
    "黎巴嫩": "Lebanon", "加沙": "Gaza", "叙利亚": "Syria",
    "日本": "Japan", "德国": "Germany", "加拿大": "Canada",
    "澳大利亚": "Australia", "台湾": "Taiwan", "泰国": "Thailand",
    "菲律宾": "Philippines", "缅甸": "Myanmar", "马来西亚": "Malaysia",
    "新加坡": "Singapore", "印度尼西亚": "Indonesia", "孟加拉国": "Bangladesh",
    "斯里兰卡": "Sri Lanka", "尼泊尔": "Nepal", "埃及": "Egypt",
    "沙特阿拉伯": "Saudi Arabia", "阿联酋": "United Arab Emirates",
    "巴勒斯坦": "Palestine", "伊拉克": "Iraq", "也门": "Yemen",
    "约旦": "Jordan", "卡塔尔": "Qatar", "科威特": "Kuwait",
    "阿曼": "Oman", "格鲁吉亚": "Georgia", "阿塞拜疆": "Azerbaijan",
    "哈萨克斯坦": "Kazakhstan", "乌兹别克斯坦": "Uzbekistan",
    "阿富汗": "Afghanistan", "蒙古": "Mongolia", "墨西哥": "Mexico",
    "哥伦比亚": "Colombia", "西班牙": "Spain", "意大利": "Italy",
    "波兰": "Poland", "荷兰": "Netherlands", "瑞典": "Sweden",
    "挪威": "Norway", "芬兰": "Finland", "比利时": "Belgium",
    "瑞士": "Switzerland", "白俄罗斯": "Belarus", "罗马尼亚": "Romania",
    "希腊": "Greece", "南非": "South Africa", "尼日利亚": "Nigeria",
    "肯尼亚": "Kenya", "摩洛哥": "Morocco", "阿根廷": "Argentina",
}

# ─── Known APT attributions from public threat intel ─────
# Keyed by any name or alias (lowercase). Sources: MITRE ATT&CK, QiAnxin naming.
# QiAnxin uses APT-C-xx (by country) and APT-Q-xx naming conventions.
KNOWN_APT_ORIGINS = {
    # ── Russia ──
    "apt28": "Russia", "apt 28": "Russia", "fancy bear": "Russia",
    "sofacy": "Russia", "sednit": "Russia", "strontium": "Russia",
    "pawn storm": "Russia", "snakemackerel": "Russia", "t-apt-12": "Russia",
    "forest blizzard": "Russia",
    "apt29": "Russia", "apt 29": "Russia", "cozy bear": "Russia",
    "the dukes": "Russia", "nobelium": "Russia", "midnight blizzard": "Russia",
    "seaduke": "Russia", "hammer toss": "Russia", "dukes": "Russia",
    "turla": "Russia", "turla team": "Russia", "turla group": "Russia",
    "hippo team": "Russia", "venomous bear": "Russia", "secret blizzard": "Russia",
    "uroburos": "Russia", "waterbug": "Russia", "snake": "Russia",
    "sandworm": "Russia", "sandworm team": "Russia", "electrum": "Russia",
    "voodoo bear": "Russia", "iridium": "Russia", "seashell blizzard": "Russia",
    "ghost blizzard": "Russia", "koala team": "Russia",
    "gamaredon": "Russia", "gamaredon group": "Russia", "primitive bear": "Russia",
    "aqua blizzard": "Russia", "actinium": "Russia", "shuckworm": "Russia",
    "armageddon": "Russia",
    "energetic bear": "Russia", "dragonfly": "Russia", "crouching yeti": "Russia",
    "berserk bear": "Russia",
    "ember bear": "Russia", "cadet blizzard": "Russia",
    "star blizzard": "Russia", "callisto": "Russia", "cold river": "Russia",
    "gossamer bear": "Russia",
    "apt-c-20": "Russia",
    # ── China ──
    "apt1": "China", "apt 1": "China", "comment crew": "China",
    "comment panda": "China",
    "apt10": "China", "apt 10": "China", "stone panda": "China",
    "menupass": "China", "red apollo": "China",
    "apt41": "China", "apt 41": "China", "double dragon": "China",
    "wicked panda": "China", "winnti": "China", "barium": "China",
    "apt3": "China", "apt 3": "China", "gothic panda": "China",
    "buckeye": "China",
    "apt40": "China", "apt 40": "China", "leviathan": "China",
    "kryptonite panda": "China", "gingham typhoon": "China",
    "apt31": "China", "apt 31": "China", "zirconium": "China",
    "judgment panda": "China", "violet typhoon": "China",
    "apt27": "China", "apt 27": "China", "emissary panda": "China",
    "lucky mouse": "China", "iron tiger": "China",
    "mustang panda": "China", "bronze president": "China",
    "stately taurus": "China", "earth preta": "China",
    "hafnium": "China", "silk typhoon": "China",
    "volt typhoon": "China", "bronze silhouette": "China",
    "salt typhoon": "China", "ghost emperor": "China",
    "flax typhoon": "China", "ethereal panda": "China",
    "charcoal typhoon": "China",
    "naikon": "China", "override panda": "China",
    "lotus panda": "China", "spring dragon": "China",
    "ke3chang": "China", "vixen panda": "China", "nickel": "China",
    "gallium": "China",
    "blacktech": "China", "palmerworm": "China",
    "tonto team": "China", "cactuspete": "China",
    "tick": "China", "bronze butler": "China",
    "apt-c-01": "China", "apt-c-06": "China",
    "apt-q-12": "China", "apt-q-27": "China", "apt-q-29": "China",
    "apt-q-31": "China", "apt-q-36": "China", "apt-q-77": "China",
    "apt-q-78": "China",
    # ── North Korea ──
    "lazarus": "North Korea", "lazarus group": "North Korea",
    "hidden cobra": "North Korea", "labyrinth chollima": "North Korea",
    "diamond sleet": "North Korea", "zinc": "North Korea",
    "apt38": "North Korea", "apt 38": "North Korea",
    "bluenoroff": "North Korea", "stardust chollima": "North Korea",
    "sapphire sleet": "North Korea",
    "kimsuky": "North Korea", "velvet chollima": "North Korea",
    "emerald sleet": "North Korea", "thallium": "North Korea",
    "black banshee": "North Korea",
    "andariel": "North Korea", "silent chollima": "North Korea",
    "onyx sleet": "North Korea", "plutonium": "North Korea",
    "scarcruft": "North Korea", "scarcraft": "North Korea",
    "reaper": "North Korea", "ricochet chollima": "North Korea",
    "ruby sleet": "North Korea", "apt37": "North Korea", "apt 37": "North Korea",
    "konni": "North Korea",
    "operation ghostsecret": "North Korea", "hastati group": "North Korea",
    "newromanic cyber army": "North Korea",
    "operation dream job": "North Korea",
    "apt-c-26": "North Korea",
    "apt-q-11": "North Korea",
    # ── Iran ──
    "apt33": "Iran", "apt 33": "Iran", "elfin": "Iran",
    "refined kitten": "Iran", "peach sandstorm": "Iran",
    "apt34": "Iran", "apt 34": "Iran", "oilrig": "Iran",
    "helix kitten": "Iran", "hazel sandstorm": "Iran",
    "apt35": "Iran", "apt 35": "Iran", "charming kitten": "Iran",
    "phosphorus": "Iran", "mint sandstorm": "Iran", "newscaster": "Iran",
    "apt39": "Iran", "apt 39": "Iran", "chafer": "Iran",
    "remix kitten": "Iran",
    "apt42": "Iran", "apt 42": "Iran",
    "muddywater": "Iran", "muddy water": "Iran", "mercury": "Iran",
    "mango sandstorm": "Iran", "static kitten": "Iran",
    "cleaver": "Iran", "cutting kitten": "Iran",
    "cotton sandstorm": "Iran", "crimson sandstorm": "Iran",
    "lyceum": "Iran", "hexane": "Iran",
    "agrius": "Iran",
    "apt-c-34": "Iran",
    # ── Vietnam ──
    "apt32": "Vietnam", "apt 32": "Vietnam", "oceanlotus": "Vietnam",
    "ocean lotus": "Vietnam", "cobalt kitty": "Vietnam",
    "sectorf01": "Vietnam", "canvas cyclone": "Vietnam",
    "apt-c-00": "Vietnam", "apt-q-31": "Vietnam",
    # ── India ──
    "sidewinder": "India", "rattlesnake": "India", "razor tiger": "India",
    "apt-c-17": "India", "baby elephant": "India",
    "patchwork": "India", "dropping elephant": "India",
    "monsoon": "India", "quilted tiger": "India", "atk 11": "India",
    "hangover": "India", "operation hangover": "India",
    "donot": "India", "donot team": "India", "apt-c-35": "India",
    "origami elephant": "India", "sectore02": "India",
    "mint tempest": "India", "apt-q-38": "India",
    "confucius": "India", "apt-c-16": "India",
    "apt-q-37": "India", "sectore08": "India",
    # ── Pakistan ──
    "transparent tribe": "Pakistan", "apt36": "Pakistan", "apt 36": "Pakistan",
    "mythic leopard": "Pakistan", "copper fieldstone": "Pakistan",
    "apt-c-56": "Pakistan",
    "sidecopy": "Pakistan", "apt-c-36": "Pakistan",
    "rusticweb": "Pakistan", "operation rusticweb": "Pakistan",
    # ── South Korea ──
    "darkhotel": "South Korea", "tapaoux": "South Korea",
    "apt-c-06": "South Korea",
    # ── United States ──
    "equation group": "United States", "equation": "United States",
    "longhorn": "United States", "lamberts": "United States",
    "apt-c-39": "United States",
    # ── Israel ──
    "candiru": "Israel", "sourgum": "Israel",
    "nso group": "Israel",
    # ── Lebanon ──
    "volatile cedar": "Lebanon", "lebanese cedar": "Lebanon",
    "dark caracal": "Lebanon",
    # ── Turkey ──
    "sea turtle": "Turkey",
    "silicon": "Turkey",
    # ── Palestine / Gaza ──
    "aridviper": "Palestine", "arid viper": "Palestine",
    "desert falcons": "Palestine", "apt-c-23": "Palestine",
    # ── Belarus ──
    "ghostwriter": "Belarus", "unc1151": "Belarus",
    # ── Uzbekistan ──
    "sandcat": "Uzbekistan", "apt-c-32": "Uzbekistan",
    # ── United Arab Emirates ──
    "stealth falcon": "United Arab Emirates",
    "project raven": "United Arab Emirates", "fruityarmor": "United Arab Emirates",
    # ── Kazakhstan ──
    "yorotrooper": "Kazakhstan", "warsunflower": "Kazakhstan",
    "silent lynx": "Kazakhstan",
    "dustsquad": "Kazakhstan", "nomadic octopus": "Kazakhstan",
    "golden falcon": "Kazakhstan",
    "apt-q-67": "Kazakhstan", "pat bear": "Kazakhstan", "racquet bear": "Kazakhstan",
    "apt-q-90": "Kazakhstan",
    # ── Colombia ──
    "blind eagle": "Colombia", "blindeagle": "Colombia", "aguilaciega": "Colombia",
    "apt-q-98": "Colombia",
    # ── Egypt ──
    "sphinx": "Egypt", "apt-c-15": "Egypt",
    # ── Syria ──
    "goldmouse": "Syria", "golden rat": "Syria", "apt-c-27": "Syria",
    # ── Additional Russia ──
    "invisimole": "Russia",
    "triton": "Russia", "temp.veles": "Russia", "xenotime": "Russia",
    "wellmess": "Russia", "apt-c-42": "Russia",
    # ── Additional United States ──
    "slingshot": "United States",
    "projectsauron": "United States", "strider": "United States",
    # ── Additional Iran ──
    "infy": "Iran", "infy group": "Iran", "prince of persia": "Iran",
    "apt-q-61": "Iran", "apt-c-07": "Iran", "operation mermaid": "Iran",
    "zoopark": "Iran", "saber lion": "Iran", "apt-c-38": "Iran",
    # ── Additional North Korea ──
    "apt43": "North Korea",
    # ── Additional Pakistan ──
    "aggah": "Pakistan", "hagga": "Pakistan",
    "snow leopard": "Pakistan",
    # ── Additional Turkey ──
    "promethium": "Turkey", "strongpity": "Turkey", "apt-c-41": "Turkey",
    # ── Additional South Korea ──
    "bluemushroom": "South Korea", "apt-c-12": "South Korea",
    # ── Additional China ──
    "platinum": "China",
}


# ─── Enrichment database for well-known APT groups ────────
# Provides descriptions, targets, TTPs, malware, first_seen when the API lacks them.
# Keyed by lowercase group name as it appears in the data.
KNOWN_APT_ENRICHMENT = {
    "apt28": {
        "description": "Russian military intelligence (GRU Unit 26165) cyber espionage group targeting government, military, and media organizations worldwide.",
        "targets": ["Government", "Military", "Defense", "Media", "Political organizations"],
        "target_regions": ["United States", "Europe", "Ukraine"],
        "ttps": ["Spear-phishing", "Zero-day exploits", "Credential harvesting", "Watering hole attacks"],
        "malware": ["Sofacy", "X-Agent", "Zebrocy", "Seduploader"],
        "first_seen": "2004",
        "threat_level": "critical",
    },
    "apt29": {
        "description": "Russian foreign intelligence (SVR) cyber espionage group known for sophisticated, long-duration operations including the SolarWinds supply chain attack.",
        "targets": ["Government", "Technology", "Think tanks", "Healthcare"],
        "target_regions": ["United States", "Europe"],
        "ttps": ["Supply chain attacks", "Spear-phishing", "Cloud exploitation", "Custom malware"],
        "malware": ["SUNBURST", "WellMess", "EnvyScout", "FoggyWeb", "MagicWeb"],
        "first_seen": "2008",
        "threat_level": "critical",
    },
    "turla": {
        "description": "Russian FSB-linked cyber espionage group known for highly sophisticated operations against government and diplomatic targets since the late 1990s.",
        "targets": ["Government", "Diplomatic", "Military", "Research"],
        "target_regions": ["Europe", "Central Asia", "Middle East"],
        "ttps": ["Watering hole attacks", "Satellite-based C2", "Rootkits", "Backdoors"],
        "malware": ["Snake", "Carbon", "Kazuar", "ComRAT", "Gazer"],
        "first_seen": "1996",
        "threat_level": "critical",
    },
    "sandworm": {
        "description": "Russian GRU (Unit 74455) destructive threat group responsible for NotPetya, Ukraine power grid attacks, and Olympic Destroyer.",
        "targets": ["Energy", "Government", "Critical infrastructure", "Elections"],
        "target_regions": ["Ukraine", "Europe", "United States"],
        "ttps": ["Destructive attacks", "Supply chain compromise", "ICS/SCADA targeting", "Wiper malware"],
        "malware": ["NotPetya", "Industroyer", "Olympic Destroyer", "CaddyWiper", "BlackEnergy"],
        "first_seen": "2009",
        "threat_level": "critical",
    },
    "gamaredon": {
        "description": "Russian FSB-linked group primarily targeting Ukrainian government organizations with high-volume spear-phishing campaigns.",
        "targets": ["Government", "Military", "Law enforcement", "NGOs"],
        "target_regions": ["Ukraine"],
        "ttps": ["Spear-phishing", "Macro-laden documents", "Template injection", "USB spreading"],
        "malware": ["Pteranodon", "Gamaredon VBS scripts", "EvilGnome"],
        "first_seen": "2013",
        "threat_level": "high",
    },
    "blackenergy": {
        "description": "Russian-linked group known for targeting energy sector and industrial control systems, particularly in Ukraine and Western countries.",
        "targets": ["Energy", "Industrial control systems", "Government"],
        "target_regions": ["Ukraine", "Europe", "United States"],
        "ttps": ["ICS/SCADA attacks", "Watering holes", "Spear-phishing", "Supply chain attacks"],
        "malware": ["BlackEnergy", "Havex", "Goodor", "Karagany"],
        "first_seen": "2011",
        "threat_level": "critical",
    },
    "invisimole": {
        "description": "Russia-linked cyber espionage group conducting highly targeted surveillance operations with ties to Gamaredon for initial access.",
        "targets": ["Diplomatic", "Military", "Government"],
        "target_regions": ["Europe", "Central Asia"],
        "ttps": ["Spear-phishing", "Targeted surveillance", "Zero-day exploits"],
        "malware": ["InvisiMole", "RC2FM", "RC2CL"],
        "first_seen": "2013",
        "threat_level": "high",
    },
    "triton": {
        "description": "Russian state-linked group (CNIIHM) targeting industrial safety systems, responsible for the TRITON/TRISIS attack on a Saudi petrochemical facility.",
        "targets": ["Critical infrastructure", "Energy", "Industrial safety systems"],
        "target_regions": ["Middle East", "North America"],
        "ttps": ["ICS/SCADA attacks", "Safety system manipulation", "Custom ICS malware"],
        "malware": ["TRITON", "TRISIS", "HATMAN"],
        "first_seen": "2014",
        "threat_level": "critical",
    },
    "wellmess": {
        "description": "Russia-linked (SVR) group that targeted COVID-19 vaccine research organizations using WellMess and WellMail malware.",
        "targets": ["Healthcare", "Pharmaceutical", "Research", "Government"],
        "target_regions": ["United States", "United Kingdom", "Canada"],
        "ttps": ["Spear-phishing", "Vulnerability exploitation", "Custom malware"],
        "malware": ["WellMess", "WellMail", "SoreFang"],
        "first_seen": "2018",
        "threat_level": "high",
    },
    "lazarus": {
        "description": "North Korean state-sponsored group (RGB) conducting espionage, financial theft, and destructive attacks, responsible for Sony hack and WannaCry.",
        "targets": ["Financial", "Cryptocurrency", "Defense", "Technology", "Entertainment"],
        "target_regions": ["United States", "South Korea", "Global"],
        "ttps": ["Spear-phishing", "Watering holes", "Supply chain attacks", "Cryptocurrency theft"],
        "malware": ["Manuscrypt", "Fallchill", "Ratankba", "BLINDINGCAN", "AppleJeus"],
        "first_seen": "2009",
        "threat_level": "critical",
    },
    "kimsuky": {
        "description": "North Korean espionage group targeting South Korean government, think tanks, and academics to gather intelligence on foreign policy and national security.",
        "targets": ["Government", "Think tanks", "Academia", "Media"],
        "target_regions": ["South Korea", "United States", "Japan"],
        "ttps": ["Spear-phishing", "Credential theft", "Web shells", "Social engineering"],
        "malware": ["BabyShark", "AppleSeed", "GoldDragon", "KimJongRAT"],
        "first_seen": "2012",
        "threat_level": "high",
    },
    "group123": {
        "description": "North Korean espionage group (also known as ScarCruft/APT37) targeting South Korean organizations, defectors, and journalists.",
        "targets": ["Government", "Military", "Media", "Defectors", "Human rights"],
        "target_regions": ["South Korea", "Japan", "Middle East"],
        "ttps": ["Spear-phishing", "Zero-day exploits", "Watering holes", "Strategic web compromise"],
        "malware": ["RokRAT", "Bluelight", "Dolphin", "Goldbackdoor"],
        "first_seen": "2012",
        "threat_level": "high",
    },
    "hermit": {
        "description": "North Korean umbrella group encompassing Lazarus-related operations focused on financial theft and espionage across multiple subgroups.",
        "targets": ["Financial", "Cryptocurrency", "Defense", "Government"],
        "target_regions": ["Global", "South Korea", "United States"],
        "ttps": ["Spear-phishing", "Supply chain attacks", "Cryptocurrency theft"],
        "malware": ["AppleJeus", "TraderTraitor", "BLINDINGCAN"],
        "first_seen": "2009",
        "threat_level": "critical",
    },
    "apt43": {
        "description": "North Korean espionage group collecting strategic intelligence on nuclear policy and geopolitics, overlapping with Kimsuky operations.",
        "targets": ["Government", "Think tanks", "Academia", "Cryptocurrency"],
        "target_regions": ["South Korea", "United States", "Japan", "Europe"],
        "ttps": ["Spear-phishing", "Credential harvesting", "Cryptocurrency theft", "Social engineering"],
        "malware": ["LATEOP", "FastFire", "QuietSky"],
        "first_seen": "2018",
        "threat_level": "high",
    },
    "apt33": {
        "description": "Iranian cyber espionage group targeting aerospace, energy, and petrochemical sectors, linked to IRGC.",
        "targets": ["Aerospace", "Energy", "Petrochemical", "Military"],
        "target_regions": ["United States", "Saudi Arabia", "South Korea"],
        "ttps": ["Spear-phishing", "Password spraying", "Credential stuffing", "Domain spoofing"],
        "malware": ["Shamoon", "StoneDrill", "TURNEDUP", "Nanocore"],
        "first_seen": "2013",
        "threat_level": "high",
    },
    "apt35": {
        "description": "Iranian cyber espionage group targeting government, military, and diplomatic personnel, known for social engineering campaigns.",
        "targets": ["Government", "Military", "Diplomatic", "Media", "Energy"],
        "target_regions": ["United States", "Israel", "Middle East"],
        "ttps": ["Spear-phishing", "Social engineering", "Credential theft", "Fake personas"],
        "malware": ["POWERSTAR", "CharmPower", "Hyperscrape"],
        "first_seen": "2014",
        "threat_level": "high",
    },
    "charmingkitten": {
        "description": "Iranian IRGC-linked group targeting academics, journalists, and dissidents with sophisticated social engineering and credential theft.",
        "targets": ["Academia", "Journalists", "Dissidents", "Government", "Think tanks"],
        "target_regions": ["United States", "Israel", "Europe", "Middle East"],
        "ttps": ["Social engineering", "Credential phishing", "Fake news sites", "Impersonation"],
        "malware": ["POWERSTAR", "NokNok", "Hyperscrape", "MediaPl"],
        "first_seen": "2011",
        "threat_level": "high",
    },
    "oilrig": {
        "description": "Iranian state-sponsored group targeting Middle Eastern governments and critical infrastructure, known for DNS tunneling and supply chain attacks.",
        "targets": ["Government", "Financial", "Telecommunications", "Energy"],
        "target_regions": ["Middle East", "Israel", "North Africa"],
        "ttps": ["DNS tunneling", "Supply chain attacks", "Web shells", "Credential dumping"],
        "malware": ["RDAT", "Karkoff", "Shark", "Milan", "SideTwist"],
        "first_seen": "2014",
        "threat_level": "high",
    },
    "muddywater": {
        "description": "Iranian MOIS-affiliated group targeting government and telecommunications across Middle East and Central Asia with living-off-the-land techniques.",
        "targets": ["Government", "Telecommunications", "Oil and gas", "Defense"],
        "target_regions": ["Middle East", "Central Asia", "Europe"],
        "ttps": ["Spear-phishing", "Living-off-the-land", "PowerShell abuse", "Macro documents"],
        "malware": ["MuddyC2Go", "PhonyC2", "POWERSTATS", "MoriAgent"],
        "first_seen": "2017",
        "threat_level": "high",
    },
    "agrius": {
        "description": "Iranian threat group conducting destructive wiper attacks and ransomware operations against Israeli targets.",
        "targets": ["Government", "Technology", "Diamond industry"],
        "target_regions": ["Israel", "South Africa", "Hong Kong"],
        "ttps": ["Web shell exploitation", "Wiper attacks", "Ransomware as cover"],
        "malware": ["Apostle", "Fantasy", "IPsec Helper"],
        "first_seen": "2020",
        "threat_level": "high",
    },
    "hexane": {
        "description": "Iranian group targeting telecommunications, energy, and Internet service providers in the Middle East and Africa.",
        "targets": ["Telecommunications", "Energy", "Internet service providers"],
        "target_regions": ["Middle East", "Africa", "Central Asia"],
        "ttps": ["DNS tunneling", "Credential theft", "Spear-phishing"],
        "malware": ["DanBot", "Shark", "Milan"],
        "first_seen": "2018",
        "threat_level": "high",
    },
    "apt-q-61": {
        "description": "Iranian cyber espionage group (Infy/Prince of Persia) conducting long-running surveillance campaigns against Iranian dissidents and regional targets.",
        "targets": ["Dissidents", "Government", "Diplomatic"],
        "target_regions": ["Iran", "Europe", "North America"],
        "ttps": ["Spear-phishing", "Custom malware", "Surveillance"],
        "malware": ["Infy", "Foudre", "Tonnerre"],
        "first_seen": "2007",
        "threat_level": "high",
    },
    "zoopark": {
        "description": "Iranian-linked group conducting mobile surveillance campaigns targeting Middle Eastern political figures and activists.",
        "targets": ["Political figures", "Activists", "Journalists", "Government"],
        "target_regions": ["Middle East", "Egypt", "Iran"],
        "ttps": ["Watering holes", "Mobile malware", "Fake apps"],
        "malware": ["ZooPark Android malware"],
        "first_seen": "2015",
        "threat_level": "high",
    },
    "sidewinder": {
        "description": "Indian state-linked group targeting military and government entities in Pakistan, China, and neighboring countries.",
        "targets": ["Military", "Government", "Defense", "Diplomatic"],
        "target_regions": ["Pakistan", "China", "Nepal", "Sri Lanka", "Bangladesh"],
        "ttps": ["Spear-phishing", "RTF exploits", "DLL sideloading", "LNK files"],
        "malware": ["WarHawk", "SideWinder.StealerPy", "Custom .NET implants"],
        "first_seen": "2012",
        "threat_level": "high",
    },
    "patchwork": {
        "description": "Indian-origin group targeting think tanks, government, and diplomatic organizations in South and Central Asia.",
        "targets": ["Government", "Think tanks", "Diplomatic", "Defense"],
        "target_regions": ["Pakistan", "China", "Bangladesh", "Sri Lanka"],
        "ttps": ["Spear-phishing", "Macro documents", "DLL sideloading", "Code reuse"],
        "malware": ["BADNEWS", "Ragnatela", "MEGACORTEX"],
        "first_seen": "2009",
        "threat_level": "high",
    },
    "donot": {
        "description": "Indian-linked group targeting government and military in South Asia, particularly Pakistan and Kashmir-related entities.",
        "targets": ["Government", "Military", "Diplomatic"],
        "target_regions": ["Pakistan", "Bangladesh", "Nepal", "Sri Lanka"],
        "ttps": ["Spear-phishing", "Macro documents", "Mobile malware"],
        "malware": ["YTY framework", "Jaca", "EHDevel"],
        "first_seen": "2016",
        "threat_level": "high",
    },
    "confucius": {
        "description": "Indian-origin group targeting Pakistani military and government entities with spear-phishing and mobile surveillance campaigns.",
        "targets": ["Military", "Government", "Nuclear"],
        "target_regions": ["Pakistan", "South Asia"],
        "ttps": ["Spear-phishing", "Mobile malware", "Fake apps"],
        "malware": ["SunBird", "Hornbill", "ChatSpy"],
        "first_seen": "2013",
        "threat_level": "high",
    },
    "bitter": {
        "description": "Indian-linked espionage group targeting government, energy, and engineering organizations in South and Southeast Asia.",
        "targets": ["Government", "Energy", "Engineering", "Military"],
        "target_regions": ["Pakistan", "China", "Bangladesh", "Saudi Arabia"],
        "ttps": ["Spear-phishing", "Exploit documents", "Mobile malware", "Zero-day exploits"],
        "malware": ["BitterRAT", "ArtraDownloader", "Dracarys"],
        "first_seen": "2013",
        "threat_level": "high",
    },
    "projectm": {
        "description": "Pakistani military-linked group (Transparent Tribe) conducting espionage against Indian military and government targets.",
        "targets": ["Military", "Government", "Defense", "Education"],
        "target_regions": ["India", "Afghanistan"],
        "ttps": ["Spear-phishing", "Macro documents", "Fake apps", "Honey trapping"],
        "malware": ["CrimsonRAT", "ObliqueRAT", "CapraRAT", "Peppy"],
        "first_seen": "2013",
        "threat_level": "high",
    },
    "operation sidecopy": {
        "description": "Pakistani group mimicking Indian SideWinder TTPs to target Indian defense and military entities.",
        "targets": ["Military", "Defense", "Government"],
        "target_regions": ["India"],
        "ttps": ["Spear-phishing", "DLL sideloading", "LNK files", "TTP mimicry"],
        "malware": ["ActionRAT", "AuTo Stealer", "ReverseRAT"],
        "first_seen": "2019",
        "threat_level": "high",
    },
    "rusticweb": {
        "description": "Pakistani-linked campaign targeting Indian government and defense personnel with Rust-based payloads.",
        "targets": ["Government", "Defense", "Military"],
        "target_regions": ["India"],
        "ttps": ["Spear-phishing", "Rust-based payloads", "PowerShell scripts"],
        "malware": ["Rust-based stealers"],
        "first_seen": "2023",
        "threat_level": "high",
    },
    "aggah": {
        "description": "Pakistan-linked group conducting widespread malware campaigns using commodity RATs and public paste sites for C2.",
        "targets": ["Manufacturing", "Technology", "Financial", "Government"],
        "target_regions": ["Middle East", "Europe", "Asia"],
        "ttps": ["Spear-phishing", "Macro documents", "Paste site C2", "Commodity RATs"],
        "malware": ["RevengeRAT", "NanoCore", "AgentTesla", "AZORult"],
        "first_seen": "2019",
        "threat_level": "medium",
    },
    "snow leopard": {
        "description": "Pakistan-linked group targeting South Asian entities with mobile surveillance and espionage operations.",
        "targets": ["Government", "Military", "Activists"],
        "target_regions": ["South Asia"],
        "ttps": ["Mobile malware", "Spear-phishing", "Fake apps"],
        "malware": ["Custom Android RAT"],
        "first_seen": "2019",
        "threat_level": "medium",
    },
    "oceanlotus": {
        "description": "Vietnamese state-linked group conducting espionage against government, media, and dissidents in Southeast Asia.",
        "targets": ["Government", "Media", "Dissidents", "Manufacturing", "Maritime"],
        "target_regions": ["Southeast Asia", "China", "Germany"],
        "ttps": ["Spear-phishing", "Watering holes", "Supply chain attacks", "macOS malware"],
        "malware": ["Denis", "Kerrdown", "Cobalt Strike variants", "PhantomNet"],
        "first_seen": "2012",
        "threat_level": "high",
    },
    "darkhotel": {
        "description": "South Korean-linked group targeting business executives and government officials through hotel Wi-Fi networks and spear-phishing.",
        "targets": ["Government", "Business executives", "Defense", "Technology"],
        "target_regions": ["Japan", "China", "Russia", "North Korea"],
        "ttps": ["Hotel Wi-Fi attacks", "Spear-phishing", "Zero-day exploits", "Watering holes"],
        "malware": ["Tapaoux", "Inexsmar", "Ramsay"],
        "first_seen": "2007",
        "threat_level": "high",
    },
    "bluemushroom": {
        "description": "South Korean-linked espionage group associated with the DarkHotel ecosystem, targeting diplomatic and government entities.",
        "targets": ["Diplomatic", "Government", "Nuclear"],
        "target_regions": ["East Asia", "Europe", "Russia"],
        "ttps": ["Spear-phishing", "Zero-day exploits"],
        "malware": ["Custom backdoors"],
        "first_seen": "2012",
        "threat_level": "high",
    },
    "equation": {
        "description": "Highly sophisticated US-linked (NSA/TAO) group using advanced firmware-level implants and interdiction capabilities.",
        "targets": ["Government", "Military", "Telecommunications", "Energy", "Research"],
        "target_regions": ["Iran", "Russia", "Pakistan", "Afghanistan", "Global"],
        "ttps": ["Firmware implants", "Air-gap jumping", "Zero-day exploits", "Supply chain interdiction"],
        "malware": ["EquationDrug", "Fanny", "GrayFish", "DoubleFantasy"],
        "first_seen": "2001",
        "threat_level": "critical",
    },
    "apt-q-92": {
        "description": "US intelligence-linked group (Lamberts/Longhorn) conducting targeted espionage using sophisticated custom toolsets.",
        "targets": ["Government", "Military", "Aerospace", "Energy", "Telecommunications"],
        "target_regions": ["Middle East", "Europe", "Asia", "Africa"],
        "ttps": ["Zero-day exploits", "Custom malware", "Air-gap targeting"],
        "malware": ["Lambert toolkit", "Black Lambert", "Green Lambert"],
        "first_seen": "2008",
        "threat_level": "critical",
    },
    "slingshot": {
        "description": "US military-linked (JSOC) group that compromised MikroTik routers to conduct surveillance operations in the Middle East and Africa.",
        "targets": ["Telecommunications", "Government", "Military"],
        "target_regions": ["Middle East", "Africa"],
        "ttps": ["Router exploitation", "Kernel-level implants", "Multi-layer infection"],
        "malware": ["Cahnadr", "GollumApp"],
        "first_seen": "2012",
        "threat_level": "critical",
    },
    "projectsauron": {
        "description": "Highly advanced Western intelligence-linked platform (Strider) designed for long-term, stealthy espionage against government networks.",
        "targets": ["Government", "Military", "Telecommunications", "Financial"],
        "target_regions": ["Russia", "Iran", "Rwanda", "Belgium", "China"],
        "ttps": ["Air-gap jumping", "Memory-only implants", "One-time encryption keys"],
        "malware": ["ProjectSauron", "Remsec"],
        "first_seen": "2011",
        "threat_level": "critical",
    },
    "ghostwriter": {
        "description": "Belarus-linked group (UNC1151) conducting influence operations and cyber espionage targeting NATO countries and neighboring states.",
        "targets": ["Government", "Military", "Media", "Political organizations"],
        "target_regions": ["Lithuania", "Latvia", "Poland", "Ukraine", "Germany"],
        "ttps": ["Credential phishing", "Compromised websites", "Information operations", "Spear-phishing"],
        "malware": ["Cobalt Strike", "MicroBackdoor", "PicassoLoader"],
        "first_seen": "2016",
        "threat_level": "high",
    },
    "darkcaracal": {
        "description": "Lebanese intelligence-linked group conducting mobile and desktop surveillance campaigns across multiple countries.",
        "targets": ["Government", "Military", "Journalists", "Activists", "Defense"],
        "target_regions": ["Middle East", "Europe", "North America"],
        "ttps": ["Mobile malware", "Spear-phishing", "Watering holes", "Fake apps"],
        "malware": ["Pallas", "CrossRAT", "Bandook"],
        "first_seen": "2012",
        "threat_level": "high",
    },
    "stealth falcon": {
        "description": "UAE-linked group (Project Raven) targeting journalists, activists, and dissidents using zero-day exploits and commercial spyware.",
        "targets": ["Journalists", "Activists", "Dissidents", "Government"],
        "target_regions": ["Middle East", "United Kingdom", "Global"],
        "ttps": ["Zero-day exploits", "Commercial spyware", "Social engineering"],
        "malware": ["FruityArmor", "Win32/StealthFalcon"],
        "first_seen": "2012",
        "threat_level": "high",
    },
    "aridviper": {
        "description": "Palestinian (Hamas-linked) group conducting espionage and surveillance against Israeli and Palestinian targets.",
        "targets": ["Government", "Military", "Education", "Transportation"],
        "target_regions": ["Israel", "Palestine", "Egypt"],
        "ttps": ["Spear-phishing", "Mobile malware", "Fake apps", "Social engineering"],
        "malware": ["Micropsia", "PyMICROPSIA", "Arid Gopher", "SpyC23"],
        "first_seen": "2013",
        "threat_level": "high",
    },
    "promethium": {
        "description": "Turkish state-linked group (StrongPity) conducting watering hole attacks and trojanized software distribution against targets in Turkey and neighboring regions.",
        "targets": ["Government", "Telecommunications", "Technology"],
        "target_regions": ["Turkey", "Middle East", "Europe", "North Africa"],
        "ttps": ["Watering hole attacks", "Trojanized installers", "ISP-level interception"],
        "malware": ["StrongPity", "StrongPity2", "StrongPity3"],
        "first_seen": "2012",
        "threat_level": "high",
    },
    "sandcat": {
        "description": "Uzbekistan intelligence-linked group conducting targeted espionage operations using commercial and custom surveillance tools.",
        "targets": ["Dissidents", "Journalists", "Government", "Foreign diplomats"],
        "target_regions": ["Central Asia", "Middle East"],
        "ttps": ["Spear-phishing", "Commercial exploit kits", "Surveillance malware"],
        "malware": ["Hacking Team tools", "NSO Group tools", "Custom Android implants"],
        "first_seen": "2018",
        "threat_level": "medium",
    },
    "yorotrooper": {
        "description": "Kazakhstan-linked group targeting government and energy organizations in CIS countries using credential theft and custom tools.",
        "targets": ["Government", "Energy", "International organizations"],
        "target_regions": ["CIS countries", "Europe"],
        "ttps": ["Spear-phishing", "Credential theft", "Python-based tools", "Telegram C2"],
        "malware": ["Custom Python stealers", "Stink stealer"],
        "first_seen": "2022",
        "threat_level": "medium",
    },
    "apt-q-67": {
        "description": "Kazakhstan-linked group conducting cyber espionage operations targeting regional government and diplomatic entities.",
        "targets": ["Government", "Diplomatic", "NGOs"],
        "target_regions": ["Central Asia", "CIS countries"],
        "ttps": ["Spear-phishing", "Custom malware"],
        "malware": ["Custom backdoors"],
        "first_seen": "2019",
        "threat_level": "medium",
    },
    "dustsquad": {
        "description": "Kazakhstan-linked group targeting Central Asian government and diplomatic entities with custom espionage tools.",
        "targets": ["Government", "Diplomatic", "Political organizations"],
        "target_regions": ["Central Asia"],
        "ttps": ["Spear-phishing", "Android malware", "Custom backdoors"],
        "malware": ["Octopus", "DustSquad Android implant"],
        "first_seen": "2014",
        "threat_level": "medium",
    },
    "apt-q-90": {
        "description": "Kazakhstan-linked group (overlaps with DustSquad/Nomadic Octopus) targeting government entities in Central Asia.",
        "targets": ["Government", "Diplomatic", "Political organizations"],
        "target_regions": ["Central Asia"],
        "ttps": ["Spear-phishing", "Android malware", "Custom backdoors"],
        "malware": ["Octopus", "Paperbug"],
        "first_seen": "2014",
        "threat_level": "medium",
    },
    "apt-q-98": {
        "description": "South American group (Blind Eagle) targeting government, financial, and energy sectors primarily in Colombia and Ecuador.",
        "targets": ["Government", "Financial", "Energy", "Health"],
        "target_regions": ["Colombia", "Ecuador", "Chile", "Spain"],
        "ttps": ["Spear-phishing", "Commodity RATs", "Phishing kits"],
        "malware": ["AsyncRAT", "NjRAT", "QuasarRAT", "LimeRAT"],
        "first_seen": "2018",
        "threat_level": "high",
    },
    "sphinx": {
        "description": "Egyptian state-linked group conducting surveillance operations targeting domestic dissidents and regional political targets.",
        "targets": ["Dissidents", "Journalists", "Political activists", "Government"],
        "target_regions": ["Egypt", "Middle East"],
        "ttps": ["Social engineering", "Mobile malware", "Phishing"],
        "malware": ["FinSpy", "Custom Android surveillance"],
        "first_seen": "2015",
        "threat_level": "medium",
    },
    "goldmouse": {
        "description": "Middle Eastern group targeting Arabic-speaking users with mobile surveillance and desktop malware campaigns.",
        "targets": ["Military", "Government", "Activists"],
        "target_regions": ["Middle East", "North Africa"],
        "ttps": ["Watering holes", "Social engineering", "Mobile malware"],
        "malware": ["SpyNote", "Custom Android RAT", "Golden Rat malware"],
        "first_seen": "2017",
        "threat_level": "medium",
    },
    "platinum": {
        "description": "China-linked group conducting highly targeted espionage against government and defense entities in South and Southeast Asia.",
        "targets": ["Government", "Defense", "Intelligence agencies", "Diplomatic"],
        "target_regions": ["South Asia", "Southeast Asia"],
        "ttps": ["Spear-phishing", "Hot-patching", "Steganography", "Custom frameworks"],
        "malware": ["Titanium", "Platinum framework", "Dipsind"],
        "first_seen": "2009",
        "threat_level": "critical",
    },
    "poisonvine": {
        "description": "Chinese-linked group (GreenSpot) targeting government and military entities in China's neighboring countries.",
        "targets": ["Government", "Military", "Defense", "Think tanks"],
        "target_regions": ["Taiwan", "Hong Kong", "Tibet"],
        "ttps": ["Spear-phishing", "Watering holes", "Social engineering"],
        "malware": ["PoisonIvy", "Gh0st RAT", "Custom backdoors"],
        "first_seen": "2007",
        "threat_level": "high",
    },
    "el machete": {
        "description": "Spanish-speaking cyber espionage group targeting Latin American military and government organizations.",
        "targets": ["Military", "Government", "Intelligence agencies", "Diplomatic"],
        "target_regions": ["Latin America", "Venezuela", "Colombia", "Ecuador"],
        "ttps": ["Spear-phishing", "Social engineering", "USB propagation"],
        "malware": ["Machete", "Pyark"],
        "first_seen": "2010",
        "threat_level": "high",
    },
}


def normalize_country(name):
    """Map a country name (possibly Chinese) to English."""
    if not name:
        return None
    name = str(name).strip()
    if name in COUNTRY_ZH_EN:
        return COUNTRY_ZH_EN[name]
    if name in COUNTRY_COORDS:
        return name
    return name


def is_object_id(s):
    """Check if a string looks like a MongoDB ObjectID (24-char hex)."""
    if not isinstance(s, str):
        return False
    s = s.strip()
    return len(s) >= 16 and all(c in '0123456789abcdef' for c in s.lower())


def lookup_origin(name, aliases):
    """Look up origin from the known APT database using name and aliases."""
    candidates = [name] + aliases
    for candidate in candidates:
        key = candidate.lower().strip()
        if key in KNOWN_APT_ORIGINS:
            return KNOWN_APT_ORIGINS[key]
        # Try without spaces/hyphens
        normalized = key.replace("-", "").replace(" ", "")
        for db_key, country in KNOWN_APT_ORIGINS.items():
            if db_key.replace("-", "").replace(" ", "") == normalized:
                return country
    return None


def slugify(name):
    """Create a safe ID from a group name."""
    return (
        name.lower()
        .replace(" ", "-")
        .replace(".", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "-")
    )


def find_file(pattern):
    """Find a dump file whose name contains the pattern."""
    for fpath in sorted(glob.glob(os.path.join(DUMP_DIR, "*.json"))):
        if pattern in os.path.basename(fpath):
            return fpath
    return None


def load_json(fpath):
    with open(fpath, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_list(val):
    """Extract a flat list of strings from various formats."""
    if val is None:
        return []
    if isinstance(val, str):
        if not val.strip():
            return []
        return [s.strip() for s in val.split(",") if s.strip()]
    if isinstance(val, list):
        result = []
        for item in val:
            if isinstance(item, str):
                result.append(item.strip())
            elif isinstance(item, dict):
                for k in ("name", "label", "value", "title", "en_name", "cn_name",
                           "actorName"):
                    if k in item:
                        result.append(str(item[k]).strip())
                        break
        return [r for r in result if r]
    return []


def get_nested(obj, *keys, default=None):
    """Get a value from nested keys, trying each in order."""
    for key in keys:
        val = obj.get(key)
        if val is not None and val != "" and val != []:
            return val
    return default


def try_extract_groups(data):
    """Extract group records from a QiAnxin API response."""
    payload = data
    if isinstance(data, dict) and "data" in data:
        payload = data["data"]

    if isinstance(payload, list) and len(payload) > 0 and isinstance(payload[0], dict):
        return payload

    if isinstance(payload, dict):
        for key in ("list", "items", "records", "results", "groups", "actors"):
            if isinstance(payload.get(key), list):
                items = payload[key]
                if items and isinstance(items[0], dict):
                    return items
        for key, val in payload.items():
            if isinstance(val, list) and len(val) > 3 and isinstance(val[0], dict):
                return val

    return []


def build_map_origin_index(map_file):
    """
    Parse the map endpoint to build actor-name → country mapping.

    The map endpoint structure varies, but typically groups actors by country.
    We try multiple strategies to extract these mappings.
    """
    origin_index = {}
    if not map_file:
        return origin_index

    print(f"[*] Parsing map endpoint for country data: {os.path.basename(map_file)}")
    data = load_json(map_file)

    payload = data
    if isinstance(data, dict) and "data" in data:
        payload = data["data"]

    # Debug: print the full map structure
    if isinstance(payload, list):
        print(f"    map data: list[{len(payload)}]")
        for i, record in enumerate(payload):
            if isinstance(record, dict):
                print(f"    record[{i}] keys: {list(record.keys())}")
                for k, v in record.items():
                    vtype = type(v).__name__
                    if isinstance(v, list):
                        sample = f"list[{len(v)}]"
                        if v and isinstance(v[0], dict):
                            sample += f" first={list(v[0].keys())}"
                        elif v and isinstance(v[0], str):
                            sample += f" first={v[0][:50]}"
                    elif isinstance(v, dict):
                        sample = f"dict keys={list(v.keys())[:5]}"
                    else:
                        sample = str(v)[:80]
                    print(f"      {k} ({vtype}): {sample}")

                # Try to extract country → actors mapping
                country_raw = None
                actors_list = None
                for ck in ("country", "name", "area", "region", "label",
                           "countryName", "belong_country"):
                    if ck in record and isinstance(record[ck], str):
                        country_raw = record[ck]
                        break

                for ak in ("actors", "groups", "items", "list", "children",
                           "actorList", "group_list"):
                    if ak in record and isinstance(record[ak], list):
                        actors_list = record[ak]
                        break

                # If no explicit actors list, check all list values
                if actors_list is None:
                    for k, v in record.items():
                        if isinstance(v, list) and v:
                            if isinstance(v[0], dict):
                                actors_list = v
                                break
                            elif isinstance(v[0], str) and not is_object_id(v[0]):
                                actors_list = v
                                break

                if country_raw and actors_list:
                    country = normalize_country(country_raw)
                    if country:
                        for actor in actors_list:
                            if isinstance(actor, str):
                                origin_index[actor.lower().strip()] = country
                            elif isinstance(actor, dict):
                                for nk in ("actorName", "name", "actor_name",
                                           "label", "title"):
                                    if nk in actor and isinstance(actor[nk], str):
                                        aname = actor[nk].strip()
                                        if not is_object_id(aname):
                                            origin_index[aname.lower()] = country
                                        break

    elif isinstance(payload, dict):
        print(f"    map data: dict, keys={list(payload.keys())[:10]}")
        # The map might be keyed by country name
        for key, val in payload.items():
            country = normalize_country(key)
            if country and country in COUNTRY_COORDS and isinstance(val, (list, dict)):
                if isinstance(val, list):
                    for actor in val:
                        if isinstance(actor, str):
                            origin_index[actor.lower().strip()] = country
                        elif isinstance(actor, dict):
                            for nk in ("actorName", "name"):
                                if nk in actor:
                                    origin_index[str(actor[nk]).lower().strip()] = country

    if origin_index:
        print(f"[+] Built origin index: {len(origin_index)} actor→country mappings")
    else:
        print("[!] Could not extract country→actor mappings from map endpoint")

    return origin_index


def normalize_actor(raw, map_origins, idx=0):
    """
    Map a raw QiAnxin actor record to our standard schema.

    QiAnxin actor/all endpoint returns: {actorName, alias, name (ObjectID), type}
    Most fields are not available and must come from map endpoint or known DB.
    """
    if idx == 0:
        print(f"\n[*] First actor record keys: {list(raw.keys())}")
        for k, v in raw.items():
            vtype = type(v).__name__
            sample = str(v)[:120] if v is not None else "null"
            print(f"    {k} ({vtype}): {sample}")
        print()

    # ─── Name: prefer actorName over name (which is ObjectID) ──
    name = get_nested(raw, "actorName", "actor_name", "display_name",
                      "en_name", "label", "title", default=None)
    if name is None or is_object_id(str(name)):
        name = raw.get("name", "Unknown")
    name = str(name).strip()

    # ─── Aliases ──
    aliases = extract_list(get_nested(
        raw, "alias", "aliases", "other_names", "aka", "alt_names",
    ))

    # If name is still an ObjectID, use the first alias
    if is_object_id(name) and aliases:
        name = aliases.pop(0)

    # ─── Origin: try map index, then known DB, then field scan ──
    origin = "Unknown"

    # 1. Check map endpoint index
    name_lower = name.lower().strip()
    if name_lower in map_origins:
        origin = map_origins[name_lower]
    else:
        # Check aliases in map index
        for alias in aliases:
            if alias.lower().strip() in map_origins:
                origin = map_origins[alias.lower().strip()]
                break

    # 2. Check known APT database
    if origin == "Unknown":
        known = lookup_origin(name, aliases)
        if known:
            origin = known

    # 3. Check raw record fields (for enriched endpoints)
    if origin == "Unknown":
        origin_raw = get_nested(
            raw, "country", "origin", "region", "belong_country",
            "area", "belong_area", "nationality",
        )
        if origin_raw:
            if isinstance(origin_raw, list):
                origin_raw = origin_raw[0] if origin_raw else ""
            if isinstance(origin_raw, dict):
                origin_raw = (origin_raw.get("name") or origin_raw.get("en")
                              or origin_raw.get("cn") or "")
            result = normalize_country(str(origin_raw))
            if result and result in COUNTRY_COORDS:
                origin = result

    coords = COUNTRY_COORDS.get(origin, [0, 0])

    # ─── Other fields (mostly unavailable from lightweight endpoint) ──
    description = str(get_nested(
        raw, "en_description", "description", "summary", "intro",
        "desc", default=""
    ))

    first_seen_raw = get_nested(
        raw, "first_seen", "start_time", "discovered", "year",
        "firstSeen", "createTime",
    )
    first_seen = "Unknown"
    if first_seen_raw:
        m = re.search(r'\d{4}', str(first_seen_raw))
        if m:
            first_seen = m.group(0)

    targets = extract_list(get_nested(
        raw, "target_industry", "targets", "target",
        "targetIndustry", "industry",
    ))

    target_regions = extract_list(get_nested(
        raw, "target_area", "target_regions", "target_countries",
        "targetArea", "targetCountry",
    ))
    target_regions = [normalize_country(r) or r for r in target_regions]
    if not target_regions:
        target_regions = ["Unknown"]

    ttps = extract_list(get_nested(raw, "ttps", "techniques", "attack_methods"))
    malware = extract_list(get_nested(raw, "malware", "tools", "weapons", "arsenal"))

    threat_raw = get_nested(raw, "threat_level", "severity", "level", "threatLevel")
    threat_level = "high"
    if threat_raw:
        raw_str = str(threat_raw).lower()
        if raw_str in ("critical", "severe", "4", "5"):
            threat_level = "critical"
        elif raw_str in ("medium", "moderate", "2"):
            threat_level = "medium"

    active_raw = get_nested(raw, "active", "is_active", "status", "isActive")
    active = True
    if isinstance(active_raw, bool):
        active = active_raw
    elif isinstance(active_raw, str):
        active = active_raw.lower() not in ("inactive", "false", "0", "no")

    # ─── Apply enrichment from known APT intelligence database ──
    _enrich_key = name.lower().strip()
    _enrichment = KNOWN_APT_ENRICHMENT.get(_enrich_key)
    if not _enrichment:
        for _a in aliases:
            _enrichment = KNOWN_APT_ENRICHMENT.get(_a.lower().strip())
            if _enrichment:
                break
    if _enrichment:
        if not description:
            description = _enrichment.get("description", "")
        if not targets:
            targets = _enrichment.get("targets", [])
        if target_regions == ["Unknown"]:
            target_regions = _enrichment.get("target_regions", ["Unknown"])
        if not ttps:
            ttps = _enrichment.get("ttps", [])
        if not malware:
            malware = _enrichment.get("malware", [])
        if first_seen == "Unknown" and _enrichment.get("first_seen"):
            first_seen = _enrichment["first_seen"]
        if _enrichment.get("threat_level"):
            threat_level = _enrichment["threat_level"]

    return {
        "id": slugify(name),
        "name": name,
        "aliases": list(dict.fromkeys(aliases)),
        "origin": origin,
        "origin_coords": coords,
        "first_seen": first_seen,
        "description": description,
        "targets": targets or ["Unknown"],
        "target_regions": list(dict.fromkeys(target_regions)),
        "ttps": ttps or ["Unknown"],
        "malware": malware or ["Unknown"],
        "threat_level": threat_level,
        "active": active,
    }


def build_origins(groups):
    origins = {}
    for g in groups:
        o = g["origin"]
        if o not in origins:
            origins[o] = {
                "coords": g["origin_coords"],
                "color": ORIGIN_COLORS.get(o, "#888888"),
                "groups_count": 0,
            }
        origins[o]["groups_count"] += 1
    return origins


def main():
    dump_files = sorted(glob.glob(os.path.join(DUMP_DIR, "*.json")))

    if not dump_files:
        print(f"[!] No dump files found in {DUMP_DIR}")
        print("[!] Run 'python scripts/scrape.py' first.")
        sys.exit(1)

    print(f"[*] Scanning {len(dump_files)} dump files...")

    # ─── Step 1: Build origin index from map endpoint ────
    map_file = find_file("apt-dossier_map")
    map_origins = build_map_origin_index(map_file)

    # ─── Step 2: Load per-actor detail files (from enhanced scraper) ──
    actor_details = {}  # actorName → detail record
    detail_files = sorted(glob.glob(os.path.join(DUMP_DIR, "actor_*.json")))
    if detail_files:
        print(f"[*] Found {len(detail_files)} actor detail files")
        for fpath in detail_files:
            try:
                data = load_json(fpath)
                payload = data.get("data", data) if isinstance(data, dict) else data
                if isinstance(payload, dict):
                    # Print first detail file structure for debugging
                    if not actor_details:
                        print(f"[*] First detail record keys: {list(payload.keys())}")
                        for k, v in payload.items():
                            vtype = type(v).__name__
                            sample = str(v)[:100] if v is not None else "null"
                            print(f"    {k} ({vtype}): {sample}")
                    # Index by actorName or name
                    aname = payload.get("actorName") or payload.get("name") or ""
                    if aname and not is_object_id(str(aname)):
                        actor_details[str(aname).lower().strip()] = payload
            except Exception:
                continue
        print(f"[+] Loaded {len(actor_details)} actor detail records")
    else:
        print("[*] No actor detail files found (scraper may not have captured them)")

    # ─── Step 3: Process actors ──────────────────────────
    all_groups = []
    seen_names = set()

    actor_file = find_file("apt-dossier_actor_all")
    if actor_file:
        print(f"[*] Found actor list: {os.path.basename(actor_file)}")
        data = load_json(actor_file)
        records = try_extract_groups(data)
        if records:
            print(f"[+] Extracted {len(records)} records from actor endpoint")
            for i, raw in enumerate(records):
                # Merge detail data if available
                aname = raw.get("actorName", "").lower().strip()
                if aname in actor_details:
                    detail = actor_details[aname]
                    # Merge detail fields into raw (detail takes precedence for new fields)
                    merged = dict(raw)
                    for k, v in detail.items():
                        if k not in merged or merged[k] is None or merged[k] == "":
                            merged[k] = v
                        elif k not in ("name", "actorName", "alias", "type"):
                            merged[k] = v  # Detail has richer data
                    raw = merged

                group = normalize_actor(raw, map_origins, idx=i)
                if group["name"] != "Unknown" and group["name"] not in seen_names:
                    seen_names.add(group["name"])
                    all_groups.append(group)

    # ─── Step 4: Fallback - scan all dump files ──────────
    if not all_groups:
        print("[*] Actor endpoint didn't yield groups, scanning all files...")
        count = 0
        for fpath in dump_files:
            fname = os.path.basename(fpath)
            if "global_state" in fname:
                continue
            try:
                data = load_json(fpath)
            except Exception:
                continue
            records = try_extract_groups(data)
            for raw in records:
                group = normalize_actor(raw, map_origins, idx=count)
                count += 1
                if group["name"] != "Unknown" and group["name"] not in seen_names:
                    seen_names.add(group["name"])
                    all_groups.append(group)
        if all_groups:
            print(f"[+] Found {len(all_groups)} groups from general scan")

    if not all_groups:
        print("[!] No APT group data detected. Keeping existing file.")
        sys.exit(0)

    # ─── Sort and write ──────────────────────────────────
    order = {"critical": 0, "high": 1, "medium": 2}
    all_groups.sort(key=lambda g: (order.get(g["threat_level"], 3), g["name"]))

    output = {
        "apt_groups": all_groups,
        "origins": build_origins(all_groups),
        "metadata": {
            "source": "QiAnxin Threat Intelligence Center - APT Encyclopedia",
            "source_url": "https://ti.qianxin.com/apt/apt?type=map",
            "last_updated": date.today().isoformat(),
            "total_groups": len(all_groups),
            "description": "Auto-scraped APT group data from QiAnxin Threat Intelligence Center.",
        },
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Summary
    known = [g for g in all_groups if g["origin"] != "Unknown"]
    unknown = [g for g in all_groups if g["origin"] == "Unknown"]
    origins_set = set(g["origin"] for g in all_groups if g["origin"] != "Unknown")
    print(f"\n[*] Wrote {len(all_groups)} groups to {OUTPUT}")
    print(f"    {len(known)} with known origin ({len(origins_set)} countries), "
          f"{len(unknown)} unknown")
    if origins_set:
        print(f"    Origins: {sorted(origins_set)}")
    if unknown:
        print(f"    Unresolved: {[g['name'] for g in unknown[:15]]}")


if __name__ == "__main__":
    main()
