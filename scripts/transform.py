"""
Transform scraped QiAnxin APT dump into docs/data/apt-groups.json.

Run after scrape.py:
    python scripts/scrape.py
    python scripts/transform.py

Targets two specific QiAnxin API endpoints:
  - /alpha-api/v2/apt-dossier/actor/all  → APT group list
  - /alpha-api/v2/apt-dossier/map/v2     → map/geo data (merged if available)

Response format is {status, message, data} where data holds the payload.
"""

import glob
import json
import os
import re
import sys
from datetime import date

DUMP_DIR = os.path.join(os.path.dirname(__file__), "..", "qianxin_apt_dump")
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "apt-groups.json")

# ─── Known country coords ───────────────────────────────
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


def scan_for_country(raw):
    """Last resort: scan ALL field values for a known country name."""
    all_known = set(COUNTRY_COORDS.keys()) | set(COUNTRY_ZH_EN.keys())
    for key, val in raw.items():
        if key in ("_id", "id", "name"):
            continue
        if isinstance(val, str) and val.strip() in all_known:
            return normalize_country(val.strip())
        if isinstance(val, dict):
            for subkey, subval in val.items():
                if isinstance(subval, str) and subval.strip() in all_known:
                    return normalize_country(subval.strip())
        if isinstance(val, list) and val and isinstance(val[0], str):
            for item in val[:3]:
                if item.strip() in all_known:
                    return normalize_country(item.strip())
    return "Unknown"


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
                # Try common sub-keys: name, label, value, title
                for k in ("name", "label", "value", "title", "en_name", "cn_name"):
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


def normalize_group(raw, idx=0):
    """Map a raw QiAnxin record to our standard schema."""

    # ─── Debug: print first record's full structure ──
    if idx == 0:
        print(f"\n[*] First record keys: {list(raw.keys())}")
        for k, v in raw.items():
            vtype = type(v).__name__
            sample = str(v)[:120] if v is not None else "null"
            print(f"    {k} ({vtype}): {sample}")
        print()

    # ─── Aliases (extract FIRST, needed for name fallback) ──
    aliases = extract_list(get_nested(
        raw, "alias", "aliases", "other_names", "aka", "alt_names",
        "other_name", "nick_name", "nick_names", "otherName",
    ))
    cn_name = raw.get("cn_name") or raw.get("cnName")

    # ─── Name ────────────────────────────────────────
    name = get_nested(raw, "name", "en_name", "group_name", "apt_name",
                      "title", "cn_name", "display_name", "label",
                      "en_label", "actor_name", default="Unknown")
    if isinstance(name, dict):
        name = name.get("en") or name.get("cn") or name.get("name") or "Unknown"
    name = str(name).strip()

    # If name looks like a MongoDB ObjectID, use the first alias instead
    if is_object_id(name) and aliases:
        name = aliases.pop(0)
    elif is_object_id(name) and cn_name:
        name = str(cn_name).strip()

    # Add cn_name to aliases if it differs from name
    if cn_name and str(cn_name).strip() != name:
        cn = str(cn_name).strip()
        if cn not in aliases:
            aliases.insert(0, cn)

    # ─── Origin / Country ────────────────────────────
    origin_raw = get_nested(
        raw, "country", "origin", "region", "source_country",
        "attribution", "nation", "belong_country",
        "area", "belong_area", "location", "loc",
        "source_area", "home_country", "homeland",
        "from", "nationality", "state", "country_name",
        "belongCountry", "sourceCountry", "homeCountry",
    )
    if isinstance(origin_raw, list):
        origin_raw = origin_raw[0] if origin_raw else ""
    if isinstance(origin_raw, dict):
        origin_raw = (origin_raw.get("name") or origin_raw.get("en") or
                      origin_raw.get("cn") or origin_raw.get("en_name") or
                      origin_raw.get("cn_name") or origin_raw.get("label") or
                      origin_raw.get("value") or "")
    origin = normalize_country(str(origin_raw)) if origin_raw else "Unknown"

    # Last resort: scan all fields for a known country value
    if origin == "Unknown":
        origin = scan_for_country(raw)

    # ─── Coords ──────────────────────────────────────
    coords = COUNTRY_COORDS.get(origin, [0, 0])

    # ─── First seen ──────────────────────────────────
    first_seen_raw = get_nested(
        raw, "first_seen", "start_time", "discovered", "year",
        "first_activity", "active_since", "begin_time", "earliest_time",
        "startTime", "firstSeen", "createTime", "create_time",
    )
    first_seen = "Unknown"
    if first_seen_raw:
        s = str(first_seen_raw).strip()
        m = re.search(r'\d{4}', s)
        if m:
            first_seen = m.group(0)

    # ─── Description ─────────────────────────────────
    description = str(get_nested(
        raw, "en_description", "description", "summary", "intro",
        "cn_description", "overview", "brief", "en_intro", "cn_intro",
        "desc", "enDescription", "cnDescription",
        default=""
    ))

    # ─── Targets (sectors) ───────────────────────────
    targets = extract_list(get_nested(
        raw, "target_industry", "targets", "target", "attack_target",
        "industries", "target_sector", "victim_industry",
        "targetIndustry", "industry",
    ))

    # ─── Target regions ──────────────────────────────
    target_regions = extract_list(get_nested(
        raw, "target_area", "target_regions", "target_countries",
        "affected_regions", "victim_country", "target_country",
        "victim_region", "targetArea", "targetCountry",
    ))
    target_regions = [normalize_country(r) or r for r in target_regions]
    if not target_regions:
        target_regions = ["Unknown"]

    # ─── TTPs ────────────────────────────────────────
    ttps = extract_list(get_nested(
        raw, "ttps", "techniques", "attack_methods", "attack_type",
        "ttp", "attack_technique", "technique", "attackType",
    ))

    # ─── Malware / Tools ─────────────────────────────
    malware = extract_list(get_nested(
        raw, "malware", "tools", "weapons", "malware_families",
        "tool_list", "weapon", "trojan", "arsenal",
        "malwareFamily", "toolList",
    ))

    # ─── Threat level ────────────────────────────────
    threat_raw = get_nested(
        raw, "threat_level", "severity", "risk_level",
        "danger_level", "level", "threatLevel",
    )
    threat_level = map_threat_level(threat_raw)

    # ─── Active ──────────────────────────────────────
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
        "targets": list(dict.fromkeys(targets)) or ["Unknown"],
        "target_regions": list(dict.fromkeys(target_regions)),
        "ttps": list(dict.fromkeys(ttps)) or ["Unknown"],
        "malware": list(dict.fromkeys(malware)) or ["Unknown"],
        "threat_level": threat_level,
        "active": active,
    }


def map_threat_level(raw):
    if not raw:
        return "high"
    raw = str(raw).lower()
    if raw in ("critical", "severe", "4", "5"):
        return "critical"
    if raw in ("high", "3"):
        return "high"
    if raw in ("medium", "moderate", "2"):
        return "medium"
    return "high"


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


def try_extract_groups(data):
    """
    Try to extract group records from a QiAnxin API response.
    Handles: {status, message, data: [...]}, {status, message, data: {items: [...]}}, etc.
    """
    payload = data
    # Unwrap {status, message, data} envelope
    if isinstance(data, dict) and "data" in data:
        payload = data["data"]

    # payload is a list of records
    if isinstance(payload, list) and len(payload) > 0 and isinstance(payload[0], dict):
        return payload

    # payload is a dict with a list inside
    if isinstance(payload, dict):
        for key in ("list", "items", "records", "results", "groups", "actors"):
            if isinstance(payload.get(key), list):
                items = payload[key]
                if items and isinstance(items[0], dict):
                    return items
        # Try any list value
        for key, val in payload.items():
            if isinstance(val, list) and len(val) > 3 and isinstance(val[0], dict):
                return val

    return []


def dump_debug(dump_files):
    """Print detailed structure info for debugging."""
    print("\n[*] Dump file analysis:")
    for fpath in dump_files:
        fname = os.path.basename(fpath)
        try:
            data = load_json(fpath)
        except Exception:
            continue

        if isinstance(data, dict) and "data" in data:
            payload = data["data"]
            if isinstance(payload, list):
                print(f"\n  {fname}")
                print(f"    data: list[{len(payload)}]")
                if payload and isinstance(payload[0], dict):
                    print(f"    first record keys: {list(payload[0].keys())}")
                    # Show sample values for first record
                    for k, v in payload[0].items():
                        sample = str(v)[:80] if v is not None else "null"
                        print(f"      {k}: {sample}")
            elif isinstance(payload, dict):
                print(f"\n  {fname}")
                print(f"    data: dict, keys={list(payload.keys())[:10]}")
                for k, v in payload.items():
                    if isinstance(v, list):
                        print(f"      {k}: list[{len(v)}]")
                        if v and isinstance(v[0], dict):
                            print(f"        first item keys: {list(v[0].keys())}")
                    elif isinstance(v, dict):
                        print(f"      {k}: dict, keys={list(v.keys())[:8]}")
                    else:
                        print(f"      {k}: {str(v)[:60]}")
            else:
                print(f"\n  {fname}")
                print(f"    data: {type(payload).__name__} = {str(payload)[:80]}")
        elif isinstance(data, list):
            print(f"\n  {fname}")
            print(f"    list[{len(data)}]")
            if data and isinstance(data[0], dict):
                print(f"    first item keys: {list(data[0].keys())[:10]}")
        elif isinstance(data, dict):
            print(f"\n  {fname}")
            print(f"    keys: {list(data.keys())[:10]}")


def main():
    dump_files = sorted(glob.glob(os.path.join(DUMP_DIR, "*.json")))

    if not dump_files:
        print(f"[!] No dump files found in {DUMP_DIR}")
        print("[!] Run 'python scripts/scrape.py' first.")
        sys.exit(1)

    print(f"[*] Scanning {len(dump_files)} dump files...")

    # ─── Strategy 1: target known QiAnxin endpoints ──
    all_groups = []
    seen_names = set()

    # Primary: actor/all endpoint (the main group list)
    actor_file = find_file("apt-dossier_actor_all")
    if actor_file:
        print(f"[*] Found actor list: {os.path.basename(actor_file)}")
        data = load_json(actor_file)
        records = try_extract_groups(data)
        if records:
            print(f"[+] Extracted {len(records)} records from actor endpoint")
            for i, raw in enumerate(records):
                group = normalize_group(raw, idx=i)
                if group["name"] != "Unknown" and group["name"] not in seen_names:
                    seen_names.add(group["name"])
                    all_groups.append(group)

    # Secondary: map endpoint (may have geo data to merge)
    map_file = find_file("apt-dossier_map")
    map_data = {}
    if map_file:
        print(f"[*] Found map data: {os.path.basename(map_file)}")
        data = load_json(map_file)
        records = try_extract_groups(data)
        if records:
            print(f"[+] Found {len(records)} records in map endpoint")
            # If we didn't get actors from the actor endpoint, use map data
            if not all_groups:
                for i, raw in enumerate(records):
                    group = normalize_group(raw, idx=i)
                    if group["name"] != "Unknown" and group["name"] not in seen_names:
                        seen_names.add(group["name"])
                        all_groups.append(group)

    # ─── Strategy 2: scan ALL dump files ─────────────
    if not all_groups:
        print("[*] Actor/map endpoints didn't yield groups, scanning all files...")
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
                group = normalize_group(raw, idx=count)
                count += 1
                if group["name"] != "Unknown" and group["name"] not in seen_names:
                    seen_names.add(group["name"])
                    all_groups.append(group)

        if all_groups:
            print(f"[+] Found {len(all_groups)} groups from general scan")

    # ─── No data found ───────────────────────────────
    if not all_groups:
        print("[!] No APT group data detected in any dump file.")
        print("[!] Keeping existing apt-groups.json unchanged.")
        dump_debug(dump_files)
        sys.exit(0)

    # ─── Sort and write ──────────────────────────────
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
    print(f"[*] Wrote {len(all_groups)} groups to {OUTPUT}")
    print(f"    {len(known)} with known origin ({len(origins_set)} countries), {len(unknown)} unknown")
    if unknown:
        print(f"    Unknown origin groups: {[g['name'] for g in unknown[:10]]}")
    if origins_set:
        print(f"    Origins: {sorted(origins_set)}")


if __name__ == "__main__":
    main()
