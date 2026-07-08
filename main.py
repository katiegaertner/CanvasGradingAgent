import subprocess
import sys
import time

def run_step(script, description):
    print(f"\n{'='*50}")
    print(f"  {description}")
    print(f"{'='*50}")
    result = subprocess.run([sys.executable, script], check=True)
    return result

def main():
    print("\n Canvas Discussion Grading Agent")
    print(" Carnegie Mellon Agentic AI Capstone")
    print(" Katie Gaertner | Wisconsin School of Business")
    
    print("\n Starting pipeline...\n")
    time.sleep(1)

    # Step 1: Fetch data from Canvas
    run_step("canvas_fetch.py", "Step 1: Fetching discussion data from Canvas")
    print("✓ Canvas data fetched successfully")

    # Step 2: Grade all students
    run_step("grader.py", "Step 2: Grading student submissions")
    print("✓ Grading complete — staging.csv ready for review")

    # Step 3: Launch review interface
    print(f"\n{'='*50}")
    print(f"  Step 3: Launching instructor review interface")
    print(f"{'='*50}")
    print("\n Opening review interface at http://127.0.0.1:5000")
    print(" Review and approve grades, then export to Canvas.")
    print(" Press Ctrl+C when finished to exit.\n")
    subprocess.run([sys.executable, "review.py"])

if __name__ == "__main__":
    main()