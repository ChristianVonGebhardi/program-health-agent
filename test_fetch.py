from data_fetcher import fetch_all
from analyzer import run_analysis
from github_reporter import post_report
import json

data = fetch_all()
result = run_analysis(data)

print("\n=== ANALYSIS RESULT ===")
print(f"Overall: {result['rag']['overall']}")
print(f"Schedule: {result['rag']['schedule']}")
print(f"Quality: {result['rag']['quality']}")
print(f"Team: {result['rag']['team']}")
print(f"\nExecutive Summary:")
print(result['analysis'].get('executive_summary', ''))

url = post_report(result)
if url:
    print(f"\n>>> Report posted: {url}")