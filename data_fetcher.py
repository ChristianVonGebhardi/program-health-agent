import requests
import time
from datetime import datetime, timezone
from config import SOURCE_REPO, GITHUB_TOKEN, THRESHOLDS

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}
BASE_URL = "https://api.github.com"

def get(url, params=None):
    """Simple GitHub API GET with error handling."""
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  API error: {e}")
        return None

def days_since(date_str):
    """Calculate days since a GitHub date string."""
    if not date_str:
        return 0
    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).days

def fetch_issues():
    """Fetch open issues with age analysis."""
    print("  Fetching issues...")
    url = f"{BASE_URL}/repos/{SOURCE_REPO}/issues"
    params = {"state": "open", "per_page": 100}
    data = get(url, params)
    if not data:
        return {}

    issues = [i for i in data if "pull_request" not in i]  # exclude PRs
    ages = [days_since(i["created_at"]) for i in issues]

    return {
        "total_open": len(issues),
        "avg_age_days": round(sum(ages) / len(ages), 1) if ages else 0,
        "critical_age": sum(1 for a in ages if a > THRESHOLDS["issue_age_critical_days"]),
        "warning_age": sum(1 for a in ages if THRESHOLDS["issue_age_warning_days"] < a <= THRESHOLDS["issue_age_critical_days"]),
        "oldest_days": max(ages) if ages else 0,
        "sample_titles": [i["title"] for i in issues[:5]]
    }

def fetch_pull_requests():
    """Fetch PR velocity and review latency."""
    print("  Fetching pull requests...")
    url = f"{BASE_URL}/repos/{SOURCE_REPO}/pulls"
    params = {"state": "open", "per_page": 100}
    data = get(url, params)
    if not data:
        return {}

    ages = [days_since(pr["created_at"]) for pr in data]

    return {
        "total_open": len(data),
        "avg_age_days": round(sum(ages) / len(ages), 1) if ages else 0,
        "stale_prs": sum(1 for a in ages if a > THRESHOLDS["pr_review_latency_critical_days"]),
        "oldest_days": max(ages) if ages else 0,
        "sample_titles": [pr["title"] for pr in data[:5]]
    }

def fetch_contributors():
    """Fetch contributor activity and bus factor."""
    print("  Fetching contributors...")
    url = f"{BASE_URL}/repos/{SOURCE_REPO}/contributors"
    params = {"per_page": 30}
    data = get(url, params)
    if not data:
        return {}

    total_contributions = sum(c["contributions"] for c in data)
    top_contributors = data[:5]

    # Bus factor: how many contributors make up 50% of contributions
    cumulative = 0
    bus_factor = 0
    for c in data:
        cumulative += c["contributions"]
        bus_factor += 1
        if cumulative >= total_contributions * 0.5:
            break

    return {
        "total_contributors": len(data),
        "bus_factor": bus_factor,
        "top_contributors": [
            {
                "login": c["login"],
                "contributions": c["contributions"],
                "percentage": round(c["contributions"] / total_contributions * 100, 1)
            }
            for c in top_contributors
        ],
        "total_contributions": total_contributions
    }

def fetch_contributor_locations(contributors):
    """Fetch GitHub profile locations for top contributors."""
    print("  Fetching contributor locations...")
    top = contributors.get("top_contributors", [])
    locations = []

    for c in top:
        url = f"{BASE_URL}/users/{c['login']}"
        data = get(url)
        if data:
            locations.append({
                "login": c["login"],
                "contributions": c["contributions"],
                "percentage": c["percentage"],
                "location": data.get("location") or "Not specified",
                "company": data.get("company") or "Not specified"
            })
        time.sleep(0.5)  # rate limit courtesy

    return locations

def fetch_milestones():
    """Fetch milestone completion rates."""
    print("  Fetching milestones...")
    url = f"{BASE_URL}/repos/{SOURCE_REPO}/milestones"
    params = {"state": "open", "per_page": 10}
    data = get(url, params)
    if not data:
        return {}

    milestones = []
    for m in data:
        total = m["open_issues"] + m["closed_issues"]
        completion = m["closed_issues"] / total if total > 0 else 0
        milestones.append({
            "title": m["title"],
            "completion": round(completion * 100, 1),
            "open_issues": m["open_issues"],
            "closed_issues": m["closed_issues"],
            "due_on": m.get("due_on"),
            "overdue": days_since(m.get("due_on")) > 0 if m.get("due_on") else False
        })

    return {
        "total": len(milestones),
        "overdue": sum(1 for m in milestones if m["overdue"]),
        "avg_completion": round(sum(m["completion"] for m in milestones) / len(milestones), 1) if milestones else 0,
        "details": milestones
    }

def fetch_repo_meta():
    """Fetch basic repo metadata."""
    print("  Fetching repo metadata...")
    url = f"{BASE_URL}/repos/{SOURCE_REPO}"
    data = get(url)
    if not data:
        return {}

    return {
        "name": data.get("name"),
        "description": data.get("description"),
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "open_issues_count": data.get("open_issues_count"),
        "last_push": data.get("pushed_at"),
        "days_since_last_push": days_since(data.get("pushed_at"))
    }

def fetch_all():
    """Fetch all data from GitHub. Returns structured dict."""
    print(f"\n>>> Fetching data from {SOURCE_REPO}")
    contributors = fetch_contributors()
    return {
        "repo": SOURCE_REPO,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "meta": fetch_repo_meta(),
        "issues": fetch_issues(),
        "pull_requests": fetch_pull_requests(),
        "contributors": contributors,
        "contributor_locations": fetch_contributor_locations(contributors),
        "milestones": fetch_milestones()
    }