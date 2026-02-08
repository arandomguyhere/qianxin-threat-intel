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

    # ─── Step 2: Process actors ──────────────────────────
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
                group = normalize_actor(raw, map_origins, idx=i)
                if group["name"] != "Unknown" and group["name"] not in seen_names:
                    seen_names.add(group["name"])
                    all_groups.append(group)

    # ─── Step 3: Fallback - scan all dump files ──────────
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
