"""
Transform scraped QiAnxin APT dump into docs/data/apt-groups.json.

Run after scrape.py:
    python scripts/scrape.py
    python scripts/transform.py

The scraper captures every JSON API response the QiAnxin APT map makes.
This script scans those dumps, detects APT group data (by structure), and
merges it into the format our GitHub Pages site expects.

Since we don't know the exact API schema ahead of time, this uses
heuristics to find group-like objects and maps fields as best it can.
Unknown schemas are logged so you can extend the field mapping.
"""

import glob
import json
import os
import sys
from datetime import date

DUMP_DIR = os.path.join(os.path.dirname(__file__), "..", "qianxin_apt_dump")
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "apt-groups.json")
FALLBACK = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "apt-groups.json")

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
}

ORIGIN_COLORS = {
    "Russia": "#e74c3c",
    "China": "#e67e22",
    "North Korea": "#a855f7",
    "Iran": "#22c55e",
    "United States": "#3498db",
    "Vietnam": "#06b6d4",
    "India": "#f39c12",
}

# ─── Chinese-to-English country name mapping ────────────
COUNTRY_ZH_EN = {
    "俄罗斯": "Russia",
    "中国": "China",
    "朝鲜": "North Korea",
    "伊朗": "Iran",
    "美国": "United States",
    "越南": "Vietnam",
    "印度": "India",
    "巴基斯坦": "Pakistan",
    "韩国": "South Korea",
    "以色列": "Israel",
    "土耳其": "Turkey",
    "乌克兰": "Ukraine",
    "英国": "United Kingdom",
    "法国": "France",
    "巴西": "Brazil",
    "黎巴嫩": "Lebanon",
    "加沙": "Gaza",
    "叙利亚": "Syria",
    "日本": "Japan",
    "德国": "Germany",
    "加拿大": "Canada",
    "澳大利亚": "Australia",
}


def normalize_country(name):
    """Try to map a country name (possibly Chinese) to English."""
    if not name:
        return None
    name = name.strip()
    if name in COUNTRY_ZH_EN:
        return COUNTRY_ZH_EN[name]
    # Already English
    if name in COUNTRY_COORDS:
        return name
    return name


def slugify(name):
    """Create a safe ID from a group name."""
    return name.lower().replace(" ", "-").replace(".", "").replace("(", "").replace(")", "")


def detect_groups(data, source_file=""):
    """
    Heuristically detect APT group records from a JSON blob.
    Returns a list of raw group dicts (unnormalized).
    """
    groups = []

    # Case 1: top-level list of group objects
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and has_group_keys(item):
                groups.append(item)
        if groups:
            return groups

    # Case 2: nested under a "data" key
    if isinstance(data, dict):
        for key in ("data", "result", "results", "list", "items", "groups", "apt_list"):
            val = data.get(key)
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict) and has_group_keys(item):
                        groups.append(item)
                if groups:
                    return groups

        # Case 3: single group object
        if has_group_keys(data):
            groups.append(data)

    return groups


def has_group_keys(obj):
    """Check if a dict looks like an APT group record."""
    if not isinstance(obj, dict):
        return False
    # Look for name-like fields
    name_keys = {"name", "group_name", "apt_name", "title", "en_name", "cn_name"}
    has_name = bool(name_keys & set(obj.keys()))
    # Look for threat-intel-like fields
    intel_keys = {
        "aliases", "alias", "country", "origin", "region",
        "target", "targets", "malware", "tools", "ttps",
        "description", "first_seen", "motivation",
        "attack_target", "target_industry", "target_area",
    }
    has_intel = len(intel_keys & set(obj.keys())) >= 2
    return has_name and has_intel


def normalize_group(raw):
    """Map raw scraped fields to our standard schema."""
    # Name
    name = (
        raw.get("name")
        or raw.get("en_name")
        or raw.get("group_name")
        or raw.get("apt_name")
        or raw.get("title")
        or raw.get("cn_name")
        or "Unknown"
    )

    # Aliases
    aliases = []
    for key in ("aliases", "alias", "other_names", "aka"):
        val = raw.get(key)
        if isinstance(val, list):
            aliases.extend(val)
        elif isinstance(val, str) and val:
            aliases.extend([a.strip() for a in val.split(",")])

    # Origin / Country
    origin_raw = raw.get("country") or raw.get("origin") or raw.get("region") or raw.get("source_country") or ""
    if isinstance(origin_raw, list):
        origin_raw = origin_raw[0] if origin_raw else ""
    origin = normalize_country(origin_raw) or "Unknown"

    # Coords
    coords = COUNTRY_COORDS.get(origin, [0, 0])

    # First seen
    first_seen = str(
        raw.get("first_seen")
        or raw.get("start_time")
        or raw.get("discovered")
        or raw.get("year")
        or "Unknown"
    )[:4]  # Extract year

    # Description
    description = (
        raw.get("description")
        or raw.get("en_description")
        or raw.get("summary")
        or raw.get("intro")
        or raw.get("cn_description")
        or ""
    )

    # Targets
    targets = []
    for key in ("targets", "target", "target_industry", "attack_target", "industries"):
        val = raw.get(key)
        if isinstance(val, list):
            targets.extend(val)
        elif isinstance(val, str) and val:
            targets.extend([t.strip() for t in val.split(",")])

    # Target regions
    target_regions = []
    for key in ("target_area", "target_regions", "target_countries", "affected_regions"):
        val = raw.get(key)
        if isinstance(val, list):
            target_regions.extend(val)
        elif isinstance(val, str) and val:
            target_regions.extend([r.strip() for r in val.split(",")])
    if not target_regions:
        target_regions = ["Unknown"]

    # TTPs
    ttps = []
    for key in ("ttps", "techniques", "attack_methods", "attack_type"):
        val = raw.get(key)
        if isinstance(val, list):
            ttps.extend(val)
        elif isinstance(val, str) and val:
            ttps.extend([t.strip() for t in val.split(",")])

    # Malware
    malware = []
    for key in ("malware", "tools", "weapons", "malware_families", "tool_list"):
        val = raw.get(key)
        if isinstance(val, list):
            malware.extend(val)
        elif isinstance(val, str) and val:
            malware.extend([m.strip() for m in val.split(",")])

    # Threat level
    threat_raw = raw.get("threat_level") or raw.get("severity") or raw.get("risk_level") or ""
    threat_level = map_threat_level(threat_raw)

    # Active
    active_raw = raw.get("active") or raw.get("status") or raw.get("is_active")
    active = True
    if isinstance(active_raw, bool):
        active = active_raw
    elif isinstance(active_raw, str):
        active = active_raw.lower() not in ("inactive", "false", "0", "no")

    return {
        "id": slugify(name),
        "name": name,
        "aliases": list(dict.fromkeys(aliases)),  # dedupe preserving order
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
    """Build the origins summary from group data."""
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

    all_groups = []
    seen_names = set()

    for fpath in dump_files:
        fname = os.path.basename(fpath)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[!] Skipping {fname}: {e}")
            continue

        groups = detect_groups(data, fname)
        if groups:
            print(f"[+] Found {len(groups)} group(s) in {fname}")
            for raw in groups:
                normalized = normalize_group(raw)
                if normalized["name"] not in seen_names:
                    seen_names.add(normalized["name"])
                    all_groups.append(normalized)

    if not all_groups:
        print("[!] No APT group data detected in any dump file.")
        print("[!] Keeping existing apt-groups.json unchanged.")
        print("[*] Dump files found:")
        for fpath in dump_files:
            fname = os.path.basename(fpath)
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                print(f"     {fname}: keys={list(data.keys())[:8]}")
            elif isinstance(data, list):
                print(f"     {fname}: list[{len(data)}]")
            else:
                print(f"     {fname}: {type(data).__name__}")
        sys.exit(0)

    # Sort by threat level then name
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

    print(f"[*] Wrote {len(all_groups)} groups to {OUTPUT}")


if __name__ == "__main__":
    main()
