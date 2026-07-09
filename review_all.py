"""
review_all.py
---------
Flask-based instructor review interface for grading approval.
Loads staging.csv, displays student posts and draft grades,
and allows the instructor to edit and approve before export.
Approved grades are written back to the vector store on export.
Receives SCORE_COLUMN and COMMENT_COLUMN as environment variables from main.py.
"""

from flask import Flask, render_template_string, request, jsonify, Response
from vector_store import add_to_store
import csv
import json
import os
import io
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

app = Flask(__name__)

STAGING_FILE = "staging.csv"
SCORE_COLUMN = os.getenv("SCORE_COLUMN", "Discussion 1 | AI and Careers in Finance & Accounting (3057678)")
COMMENT_COLUMN = os.getenv("COMMENT_COLUMN", "Discussion 1 | AI and Careers in Finance & Accounting (3057678) - Comments")
COURSE_ID = int(os.getenv("COURSE_ID", 531715))
DISCUSSION_ID = int(os.getenv("DISCUSSION_ID", 2421451))

# Set to True to auto-approve full credit and zero scores
# Set to False to review all students
AUTO_APPROVE = False

def load_students():
    """Load staging CSV and optionally auto-approve full credit and zero scores."""
    students = []
    with open(STAGING_FILE, "r") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            row["index"] = i
            try:
                score = float(row.get(SCORE_COLUMN, 0))
            except:
                score = 0
            if AUTO_APPROVE and (score == 5 or score == 0):
                row["approved"] = True
            else:
                row["approved"] = False
            students.append(row)
    # Flagged students first, then by last name
    students.sort(key=lambda x: (x["Flag"] != "YES", x["Student"]))
    return students

students = load_students()

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Grading Review</title>
    <style>
        body { font-family: sans-serif; max-width: 1100px; margin: 40px auto; padding: 0 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .summary { background: white; padding: 16px 24px; border-radius: 8px; margin-bottom: