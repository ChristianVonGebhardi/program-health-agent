# Known timezone offsets for common locations (fast lookup, no API needed)
# Revisit with "zoneinfo" or "pytz" if more precision is needed, but this covers major cities and countries for a quick heuristic.
KNOWN_TIMEZONES = {
    "germany": 1, "munich": 1, "berlin": 1, "hamburg": 1,
    "frankfurt": 1, "stuttgart": 1, "nuremberg": 1,
    "france": 1, "paris": 1,
    "netherlands": 1, "amsterdam": 1,
    "sweden": 1, "stockholm": 1,
    "norway": 1, "oslo": 1,
    "denmark": 1, "copenhagen": 1,
    "finland": 2, "helsinki": 2,
    "uk": 0, "london": 0, "england": 0,
    "us": -5, "usa": -5, "united states": -5,
    "california": -8, "san francisco": -8, "los angeles": -8,
    "new york": -5, "boston": -5,
    "india": 5, "bangalore": 5, "mumbai": 5, "delhi": 5,
    "china": 8, "beijing": 8, "shanghai": 8,
    "japan": 9, "tokyo": 9,
    "australia": 10, "sydney": 10,
    "canada": -5, "toronto": -5, "vancouver": -8,
    "brazil": -3, "sao paulo": -3,
    "singapore": 8,
    "israel": 2, "tel aviv": 2,
    "poland": 1, "warsaw": 1,
    "romania": 2, "bucharest": 2,
    "czech": 1, "prague": 1,
}

def location_to_utc_offset(location_str):
    """Convert location string to UTC offset. Returns None if unknown."""
    if not location_str or location_str == "Not specified":
        return None
    loc_lower = location_str.lower()
    for key, offset in KNOWN_TIMEZONES.items():
        if key in loc_lower:
            return offset
    return None

def calculate_collaboration_friction(locations):
    """Calculate timezone spread and collaboration friction index."""
    offsets = []
    resolved = []
    unresolved = []

    for c in locations:
        offset = location_to_utc_offset(c.get("location", ""))
        if offset is not None:
            offsets.append(offset)
            resolved.append({**c, "utc_offset": offset})
        else:
            unresolved.append(c)

    if len(offsets) < 2:
        return {
            "friction_score": "unknown",
            "friction_label": "⚪ UNKNOWN",
            "timezone_spread_hours": None,
            "resolved_count": len(resolved),
            "unresolved_count": len(unresolved),
            "resolved": resolved,
            "unresolved": unresolved,
            "note": "Insufficient location data for analysis"
        }

    spread = max(offsets) - min(offsets)

    if spread <= 3:
        label = "🟢 LOW"
        score = "low"
    elif spread <= 8:
        label = "🟡 MEDIUM"
        score = "medium"
    else:
        label = "🔴 HIGH"
        score = "high"

    return {
        "friction_score": score,
        "friction_label": label,
        "timezone_spread_hours": spread,
        "min_utc": min(offsets),
        "max_utc": max(offsets),
        "resolved_count": len(resolved),
        "unresolved_count": len(unresolved),
        "resolved": resolved,
        "unresolved": unresolved,
        "overlap_window_hours": max(0, 8 - spread),
        "pr_sla_recommendation": _pr_sla_recommendation(spread)
    }

def _pr_sla_recommendation(spread):
    if spread <= 3:
        return "2 business days — team has strong overlap"
    elif spread <= 6:
        return "3 business days — moderate overlap, async coordination needed"
    elif spread <= 9:
        return "4 business days — limited overlap, plan reviews in advance"
    else:
        return "5+ business days — minimal overlap, fully async workflow required"

def analyze_geo(locations):
    """Main entry point for geo analysis."""
    print("  Analyzing geographic distribution...")
    friction = calculate_collaboration_friction(locations)
    return friction