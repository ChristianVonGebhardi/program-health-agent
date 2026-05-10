import os
from dotenv import load_dotenv

load_dotenv()

# Source: public repo to analyze (read-only)
# Defensive approach: default to a well-known public repo if env var is missing
SOURCE_REPO = os.getenv("GITHUB_SOURCE_REPO", "eclipse-kuksa/kuksa-databroker")

# Target: your repo where health reports are posted as issues
# Defensive approach: default to a well-known public repo if env var is missing
TARGET_REPO = os.getenv("GITHUB_TARGET_REPO", "ChristianVonGebhardi/program-health-reports")

# GitHub token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Health thresholds (tunable)
THRESHOLDS = {
    "issue_age_warning_days": 30,
    "issue_age_critical_days": 90,
    "pr_review_latency_warning_days": 3,
    "pr_review_latency_critical_days": 7,
    "bus_factor_warning": 3,
    "bus_factor_critical": 2,
    "milestone_completion_warning": 0.5,
}