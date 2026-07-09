"""
consistency_reviewer.py
-----------------------
Second agent in the grading pipeline. Compares the current grading run's
score distribution against historical patterns in the vector store.
Flags batch-level drift and identifies outlier students for instructor review.
Receives SCORE_COLUMN as an environment variable from main.py.
"""

import json
import csv
import os
import warnings
from vector_store import retrieve_similar, collection

warnings.filterwarnings("ignore")

SCORE_COLUMN = os.getenv("SCORE_COLUMN", "Discussion 1 | AI and Careers in Finance & Accounting (3057678)")
DRIFT_THRESHOLD = 0.5

def get_historical_average():
    """Get the average score across all records in the vector store."""
    results = collection.get(include=["metadatas"])
    scores = [m["score"] for m in results["metadatas"] if m.get("score") is not None]
    if not scores:
        return None
    return sum(scores) / len(scores)

def get_current_average(staging_file="staging.csv"):
    """Get the average score from the current grading run, excluding non-submitters."""
    scores = []
    with open(staging_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                score = float(row.get(SCORE_COLUMN, 0))
                if score > 0:
                    scores.append(score)
            except:
                pass
    if not scores:
        return None
    return sum(scores) / len(scores)

def find_outliers(staging_file="staging.csv", n_outliers=5):
    """
    Find students whose scores deviate most from similar historical examples.
    Returns the top n_outliers students sorted by absolute deviation.
    """
    outliers = []

    with open("discussion_data.json", "r") as f:
        discussion_data = json.load(f)

    post_map = {str(s["user_id"]): s for s in discussion_data}

    with open(staging_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                current_score = float(row.get(SCORE_COLUMN, 0))
            except:
                continue

            if current_score == 0:
                continue

            user_id = str(row.get("ID", ""))
            student_data = post_map.get(user_id)
            if not student_data:
                continue

            post = student_data.get("post", "")
            reply_texts = [r["reply"] for r in student_data.get("outgoing_replies", [])]

            similar = retrieve_similar(post, reply_texts, n_results=3)
            if not similar:
                continue

            historical_avg = sum(ex["score"] for ex in similar) / len(similar)
            deviation = current_score - historical_avg

            outliers.append({
                "student": row.get("Student", ""),
                "current_score": current_score,
                "historical_avg": round(historical_avg, 2),
                "deviation": round(deviation, 2)
            })

    outliers.sort(key=lambda x: abs(x["deviation"]), reverse=True)
    return outliers[:n_outliers]

def run_consistency_review():
    """
    Run the consistency review and print results to the terminal.
    Called by main.py after grading is complete.
    """
    print("\n" + "="*50)
    print("  Consistency Reviewer")
    print("="*50)

    historical_avg = get_historical_average()
    current_avg = get_current_average()

    if historical_avg is None or current_avg is None:
        print("  Not enough data to perform consistency review.")
        return

    print(f"\n  Historical average score : {round(historical_avg, 2)}/5")
    print(f"  Current run average score: {round(current_avg, 2)}/5")

    drift = current_avg - historical_avg
    print(f"  Drift                    : {round(drift, 2):+.2f}")

    if abs(drift) >= DRIFT_THRESHOLD:
        direction = "higher" if drift > 0 else "lower"
        print(f"\n  ⚠️  DRIFT DETECTED: Current run is scoring {round(abs(drift), 2)} points {direction} than historical average.")
        print(f"  Review the following students whose scores deviate most from similar past submissions:\n")
        outliers = find_outliers()
        for o in outliers:
            arrow = "↑" if o["deviation"] > 0 else "↓"
            print(f"  {arrow} {o['student']}")
            print(f"     Current: {o['current_score']} | Historical similar: {o['historical_avg']} | Deviation: {o['deviation']:+.2f}")
    else:
        print(f"\n  ✓ No significant drift detected. Scores are consistent with historical patterns.")

if __name__ == "__main__":
    run_consistency_review()