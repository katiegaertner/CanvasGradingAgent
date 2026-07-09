"""
main.py
-------
Entry point for the Canvas Discussion Grading Agent.
Prompts the instructor for configuration, then orchestrates the full pipeline:
  1. Fetch discussion data from Canvas
  2. Grade student submissions using Gemini LLM + RAG
  3. Run consistency review against historical patterns
  4. Launch instructor review interface

Configuration is saved to config.json and reused on subsequent runs.
"""

import subprocess
import sys
import time
import json
import os
import warnings
from consistency_reviewer import run_consistency_review

warnings.filterwarnings("ignore", category=FutureWarning)

CONFIG_FILE = "config.json"

def load_config():
    """Load saved configuration from config.json if it exists."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return None

def save_config(config):
    """Save configuration to config.json for reuse on subsequent runs."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def prompt_config():
    """
    Prompt the instructor for course configuration.
    Course ID and Discussion ID are found in the Canvas URL.
    Score and Comment column headers are copied from the Canvas gradebook CSV export.
    """
    print("\nLet's configure this grading run.")
    print("(Course ID and Discussion ID are in your Canvas URL)")
    print("(Copy Score and Comment column headers exactly from your Canvas gradebook CSV)\n")

    config = {}
    config["course_id"] = input("Course ID: ").strip()
    config["discussion_id"] = input("Discussion ID: ").strip()
    config["score_column"] = input("Score column header: ").strip()
    config["comment_column"] = input("Comment column header: ").strip()

    return config

def prompt_review_mode():
    """
    Ask the instructor which review mode to use.
    Returns the filename of the appropriate review script.
    """
    print("\nReview mode:")
    print("  1. Edge cases only (auto-approve full credit and zero scores)")
    print("  2. Full review (review all students)")
    
    while True:
        choice = input("\nSelect mode (1 or 2): ").strip()
        if choice == "1":
            print("  → Edge cases only. Full credit and zero scores will be auto-approved.")
            return "review.py"
        elif choice == "2":
            print("  → Full review. All students will require manual approval.")
            return "review_all.py"
        else:
            print("  Please enter 1 or 2.")

def get_config():
    """
    Load existing config if available and offer to reuse it.
    Otherwise prompt for new configuration and save it.
    """
    existing = load_config()

    if existing:
        print("\nPrevious configuration found:")
        print(f"  Course ID      : {existing['course_id']}")
        print(f"  Discussion ID  : {existing['discussion_id']}")
        print(f"  Score column   : {existing['score_column']}")
        print(f"  Comment column : {existing['comment_column']}")

        use_existing = input("\nUse these settings? (y/n): ").strip().lower()
        if use_existing == "y":
            return existing

    config = prompt_config()
    save_config(config)
    print("\nConfiguration saved to config.json")
    return config

def run_step(script, description, env_vars=None):
    """Run a pipeline script as a subprocess, passing config via environment variables."""
    print(f"\n{'='*50}")
    print(f"  {description}")
    print(f"{'='*50}")
    env = os.environ.copy()
    if env_vars:
        env.update({k: str(v) for k, v in env_vars.items()})
    result = subprocess.run([sys.executable, script], check=True, env=env)
    return result

def main():
    print("\n" + "="*50)
    print("  Canvas Discussion Grading Agent")
    print("  Carnegie Mellon Agentic AI Capstone")
    print("  Katie Gaertner | Wisconsin School of Business")
    print("="*50)

    # Get course configuration
    config = get_config()

    # Get review mode
    review_script = prompt_review_mode()

    print("\nStarting pipeline...\n")
    time.sleep(1)

    # Pass config to each script via environment variables
    env_vars = {
        "COURSE_ID": config["course_id"],
        "DISCUSSION_ID": config["discussion_id"],
        "SCORE_COLUMN": config["score_column"],
        "COMMENT_COLUMN": config["comment_column"]
    }

    # Step 1: Fetch data from Canvas
    run_step("canvas_fetch.py", "Step 1: Fetching discussion data from Canvas", env_vars)
    print("✓ Canvas data fetched successfully")

    # Step 2: Grade all students
    run_step("grader.py", "Step 2: Grading student submissions", env_vars)
    print("✓ Grading complete — staging.csv ready for review")

    # Step 3: Run consistency review
    print(f"\n{'='*50}")
    print(f"  Step 3: Running consistency review")
    print(f"{'='*50}")
    run_consistency_review()

    # Step 4: Launch review interface
    print(f"\n{'='*50}")
    print(f"  Step 4: Launching instructor review interface")
    print(f"{'='*50}")
    print(f"\n  Mode: {'Edge cases only' if review_script == 'review.py' else 'Full review'}")
    print("\n  Opening review interface at http://127.0.0.1:5000")
    print("  Review and approve grades, then export to Canvas.")
    print("  Press Ctrl+C when finished to exit.\n")
    subprocess.run(
        [sys.executable, review_script],
        env={**os.environ, **{k: str(v) for k, v in env_vars.items()}}
    )

if __name__ == "__main__":
    main()