import anthropic
import json
from datetime import datetime, timezone
from config import ANTHROPIC_API_KEY, THRESHOLDS
from geo_analyzer import analyze_geo

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def score_to_rag(score):
    """Convert numeric score to RAG status."""
    if score >= 70:
        return "🟢 GREEN"
    elif score >= 40:
        return "🟡 AMBER"
    else:
        return "🔴 RED"

def calculate_schedule_score(data):
    """Deterministic schedule health score."""
    score = 100
    milestones = data.get("milestones", {})
    issues = data.get("issues", {})

    # No milestones = significant deduction
    if not milestones or milestones.get("total", 0) == 0:
        score -= 30

    # Critical age issues
    critical = issues.get("critical_age", 0)
    total = issues.get("total_open", 1)
    critical_ratio = critical / total if total > 0 else 0
    score -= int(critical_ratio * 40)

    # Average issue age
    avg_age = issues.get("avg_age_days", 0)
    if avg_age > THRESHOLDS["issue_age_critical_days"]:
        score -= 20
    elif avg_age > THRESHOLDS["issue_age_warning_days"]:
        score -= 10

    return max(0, score)

def calculate_quality_score(data):
    """Deterministic quality health score."""
    score = 100
    issues = data.get("issues", {})
    prs = data.get("pull_requests", {})

    # High ratio of critical age issues
    critical = issues.get("critical_age", 0)
    total = issues.get("total_open", 1)
    if total > 0:
        score -= int((critical / total) * 30)

    # Stale PRs
    stale = prs.get("stale_prs", 0)
    score -= min(stale * 5, 20)

    # Oldest issue age
    oldest = issues.get("oldest_days", 0)
    if oldest > 365:
        score -= 20
    elif oldest > 180:
        score -= 10

    return max(0, score)

def calculate_team_score(data):
    """Deterministic team health score."""
    score = 100
    contributors = data.get("contributors", {})
    meta = data.get("meta", {})

    # Bus factor
    bus_factor = contributors.get("bus_factor", 1)
    if bus_factor <= THRESHOLDS["bus_factor_critical"]:
        score -= 30
    elif bus_factor <= THRESHOLDS["bus_factor_warning"]:
        score -= 15

    # Top contributor concentration
    top = contributors.get("top_contributors", [])
    if top and top[0].get("percentage", 0) > 30:
        score -= 20
    elif top and top[0].get("percentage", 0) > 20:
        score -= 10

    # Days since last push
    days_inactive = meta.get("days_since_last_push", 0)
    if days_inactive > 60:
        score -= 20
    elif days_inactive > 30:
        score -= 10

    return max(0, score)

def analyze_with_claude(data, scores, geo):
    """Use Claude to reason over data and generate executive summary."""
    print("  Claude reasoning over data...")

    prompt = f"""You are an experienced Engineering Manager reviewing the health of an open source automotive software project.

Here is the raw project data:
{json.dumps(data, indent=2)}

Here are the calculated health scores:
- Schedule Health: {scores['schedule']} ({score_to_rag(scores['schedule'])})
- Quality Health: {scores['quality']} ({score_to_rag(scores['quality'])})
- Team Health: {scores['team']} ({score_to_rag(scores['team'])})

Here is the geographic distribution of top contributors:
{json.dumps(geo, indent=2)}

Please provide:
1. A brief executive summary (3-4 sentences) of the overall program health
2. Top 3 risks — each with fields "title" and "description" ONLY
3. Top 3 concrete recommendations to address the identified risks — each with fields "title" and "description" ONLY
4. One positive finding — genuinely distinct from recommendations, highlighting something already working well

IMPORTANT: risks and recommendations must use EXACTLY these field names: "title" and "description". No other field names.
The positive_finding must NOT overlap with any recommendation.
Format your response as JSON with keys: executive_summary, risks, recommendations, positive_finding
Respond ONLY with valid JSON, no markdown, no preamble."""

    messages = [{"role": "user", "content": prompt}]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        temperature=0,
        messages=messages
    )

    text = response.content[0].text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        return {
            "executive_summary": text,
            "risks": [],
            "recommendations": [],
            "positive_finding": ""
        }

def run_analysis(data):
    """Run full analysis. Returns structured result."""
    print(f"\n>>> Analyzing {data['repo']}")

    scores = {
        "schedule": calculate_schedule_score(data),
        "quality": calculate_quality_score(data),
        "team": calculate_team_score(data)
    }

    # Geo analysis
    geo = analyze_geo(data.get("contributor_locations", []))

    overall = int((scores["schedule"] + scores["quality"] + scores["team"]) / 3)
    scores["overall"] = overall

    print(f"  Schedule: {scores['schedule']} {score_to_rag(scores['schedule'])}")
    print(f"  Quality:  {scores['quality']} {score_to_rag(scores['quality'])}")
    print(f"  Team:     {scores['team']} {score_to_rag(scores['team'])}")
    print(f"  Overall:  {overall} {score_to_rag(overall)}")

    claude_analysis = analyze_with_claude(data, scores, geo)

    return {
        "repo": data["repo"],
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "scores": scores,
        "rag": {
            "schedule": score_to_rag(scores["schedule"]),
            "quality": score_to_rag(scores["quality"]),
            "team": score_to_rag(scores["team"]),
            "overall": score_to_rag(overall)
        },
        "raw_data": data,
        "analysis": claude_analysis,
        "geo": geo
    }