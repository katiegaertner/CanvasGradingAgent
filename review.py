"""
review.py
---------
Flask-based instructor review interface showing only students who need attention.
Auto-approves full credit (5/5) and zero scores (no post submitted).
Flagged and partial credit students require manual review.
To review all students, use review_all.py instead.
Receives SCORE_COLUMN, COMMENT_COLUMN, COURSE_ID, and DISCUSSION_ID
as environment variables from main.py.
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

def load_students():
    """
    Load staging CSV. Auto-approves full credit and zero scores.
    Only partial credit and flagged students require manual review.
    """
    students = []
    with open(STAGING_FILE, "r") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            row["index"] = i
            try:
                score = float(row.get(SCORE_COLUMN, 0))
            except:
                score = 0
            if (score == 5 or score == 0) and row.get("Flag") != "YES":
                row["approved"] = True
            else:
                row["approved"] = False
            students.append(row)
    students.sort(key=lambda x: (x["Flag"] != "YES", x["approved"], x["Student"]))
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
        .summary { background: white; padding: 16px 24px; border-radius: 8px; margin-bottom: 24px; display: flex; gap: 32px; }
        .summary span { font-size: 14px; color: #555; }
        .summary strong { font-size: 20px; color: #333; display: block; }
        .student-card { background: white; border-radius: 8px; padding: 24px; margin-bottom: 16px; border-left: 4px solid #ddd; }
        .student-card.flagged { border-left-color: #e57373; }
        .student-card.approved { border-left-color: #81c784; opacity: 0.6; }
        .student-name { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
        .student-meta { font-size: 13px; color: #888; margin-bottom: 16px; }
        .flag-badge { background: #e57373; color: white; font-size: 11px; padding: 2px 8px; border-radius: 10px; margin-left: 8px; }
        .approved-badge { background: #81c784; color: white; font-size: 11px; padding: 2px 8px; border-radius: 10px; margin-left: 8px; }
        .section-label { font-size: 12px; font-weight: 600; color: #999; text-transform: uppercase; margin-bottom: 6px; }
        .post-text { background: #f9f9f9; border-radius: 6px; padding: 12px; font-size: 14px; line-height: 1.6; margin-bottom: 16px; white-space: pre-wrap; }
        .reply-text { background: #f0f7ff; border-radius: 6px; padding: 12px; font-size: 14px; line-height: 1.6; margin-bottom: 8px; white-space: pre-wrap; }
        .grading-row { display: flex; gap: 16px; align-items: flex-start; margin-top: 16px; }
        .grading-row label { font-size: 13px; font-weight: 600; color: #555; display: block; margin-bottom: 4px; }
        select, textarea { border: 1px solid #ddd; border-radius: 6px; padding: 8px; font-size: 14px; }
        select { width: 100px; }
        textarea { width: 100%; min-height: 80px; resize: vertical; font-family: sans-serif; }
        .comment-wrap { flex: 1; }
        .btn-approve { background: #4caf50; color: white; border: none; border-radius: 6px; padding: 10px 24px; font-size: 14px; cursor: pointer; margin-top: 8px; }
        .btn-approve:hover { background: #43a047; }
        .btn-approve:disabled { background: #aaa; cursor: default; }
        .export-bar { position: sticky; bottom: 0; background: white; border-top: 1px solid #ddd; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; }
        .btn-export { background: #1976d2; color: white; border: none; border-radius: 6px; padding: 12px 32px; font-size: 15px; cursor: pointer; }
        .btn-export:hover { background: #1565c0; }
        .progress { font-size: 14px; color: #555; }
        .btn-approve-all { background: #757575; color: white; border: none; border-radius: 6px; padding: 12px 24px; font-size: 15px; cursor: pointer; }
        .btn-approve-all:hover { background: #616161; }
    </style>
</head>
<body>
    <h1>Discussion Grading Review</h1>

    <div class="summary">
        <div><strong>{{ total_students }}</strong><span>Total students</span></div>
        <div><strong>{{ auto_approved }}</strong><span>Auto-approved</span></div>
        <div><strong>{{ students|length }}</strong><span>Needs review</span></div>
        <div><strong id="approved-count">0</strong><span>Reviewed</span></div>
    </div>

    {% for student in students %}
    <div class="student-card {% if student.Flag == 'YES' %}flagged{% elif student.approved %}approved{% endif %}"
        id="card-{{ loop.index0 }}">
        <div class="student-name">
            {{ student.Student }}
            {% if student.Flag == 'YES' %}
            <span class="flag-badge">⚑ {{ student['Flag Reason'] }}</span>
            {% endif %}
            <span class="approved-badge" id="approved-badge-{{ loop.index0 }}"
                style="display:none">✓ Approved</span>
        </div>
        <div class="student-meta">{{ student['SIS Login ID'] }} &nbsp;|&nbsp; {{ student.Section }}</div>

        {% if student[score_column] != '0' and student[score_column] != '0.0' %}
        <div class="section-label">Post</div>
        <div class="post-text">{{ student_posts[loop.index0] }}</div>

        <div class="section-label">Replies</div>
        {% for reply in student_replies[loop.index0] %}
        <div class="reply-text">{{ reply }}</div>
        {% endfor %}
        {% else %}
        <div class="post-text" style="color:#999">No post submitted.</div>
        {% endif %}

        <div class="grading-row">
            <div>
                <label>Score</label>
                <select id="score-{{ loop.index0 }}">
                    {% for score in [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5] %}
                    <option value="{{ score }}"
                        {% if score == student[score_column]|float %}selected{% endif %}>
                        {{ score }}
                    </option>
                    {% endfor %}
                </select>
            </div>
            <div class="comment-wrap">
                <label>Comment</label>
                <textarea id="comment-{{ loop.index0 }}">{{ student[comment_column] }}</textarea>
            </div>
        </div>
        <button class="btn-approve" id="btn-{{ loop.index0 }}"
            onclick="approve({{ loop.index0 }}, '{{ student.ID }}')">
            Approve
        </button>
    </div>
    {% endfor %}

    <div class="export-bar">
        <div class="progress">
            <span id="progress-count">0</span> of {{ students|length }} reviewed
        </div>
        <div style="display: flex; gap: 12px;">
            <button class="btn-approve-all" onclick="approveAll()">Approve All Remaining</button>
            <button class="btn-export" onclick="exportCSV()">Export All Grades</button>
        </div>
    </div>

    <script>
        let approvedCount = 0;

        function approve(index, studentId) {
            const score = document.getElementById(`score-${index}`).value;
            const comment = document.getElementById(`comment-${index}`).value;

            fetch('/approve', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({index: index, student_id: studentId, score: score, comment: comment})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    approvedCount++;
                    document.getElementById(`card-${index}`).classList.add('approved');
                    document.getElementById(`btn-${index}`).disabled = true;
                    document.getElementById(`btn-${index}`).textContent = 'Approved';
                    document.getElementById(`approved-badge-${index}`).style.display = 'inline';
                    document.getElementById('approved-count').textContent = approvedCount;
                    document.getElementById('progress-count').textContent = approvedCount;
                }
            });
        }

        function exportCSV() {
            window.location.href = '/export';
        }

        function approveAll() {
            const buttons = document.querySelectorAll('.btn-approve:not(:disabled)');
            buttons.forEach(btn => btn.click());
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    """Render the review interface showing only students who need attention."""
    with open("discussion_data.json", "r") as f:
        discussion_data = json.load(f)

    post_map = {str(s["user_id"]): s.get("post", "") for s in discussion_data}
    reply_map = {str(s["user_id"]): [r["reply"] for r in s.get("outgoing_replies", [])]
                 for s in discussion_data}

    review_students = [s for s in students if not s["approved"]]

    student_posts = [post_map.get(str(s["ID"]), "") for s in review_students]
    student_replies = [reply_map.get(str(s["ID"]), []) for s in review_students]

    return render_template_string(
        TEMPLATE,
        students=review_students,
        student_posts=student_posts,
        student_replies=student_replies,
        score_column=SCORE_COLUMN,
        comment_column=COMMENT_COLUMN,
        total_students=len(students),
        auto_approved=len([s for s in students if s["approved"]])
    )

@app.route("/approve", methods=["POST"])
def approve():
    """Mark a student record as approved with the edited score and comment."""
    data = request.json
    index = data["index"]
    students[index][SCORE_COLUMN] = data["score"]
    students[index][COMMENT_COLUMN] = data["comment"]
    students[index]["approved"] = True
    return jsonify({"success": True})

@app.route("/export")
def export():
    """
    Export all grades to CSV and write approved grades back to the vector store.
    Exports all students including auto-approved ones.
    """
    with open("discussion_data.json", "r") as f:
        discussion_data = json.load(f)

    post_map = {str(s["user_id"]): s for s in discussion_data}
    approved_rows = [s for s in students if s.get("approved")]

    added = 0
    for row in approved_rows:
        user_id = str(row.get("ID", ""))
        student_data = post_map.get(user_id)
        if not student_data:
            continue
        try:
            score = float(row.get(SCORE_COLUMN, 0))
            if score == 0:
                continue
            post = student_data.get("post", "")
            reply_texts = [r["reply"] for r in student_data.get("outgoing_replies", [])]
            add_to_store(
                course_id=COURSE_ID,
                discussion_id=DISCUSSION_ID,
                user_id=user_id,
                post=post,
                replies=reply_texts,
                score=score
            )
            added += 1
        except Exception as e:
            print(f"Could not add user {user_id} to vector store: {e}")

    print(f"Added {added} approved grades to vector store")

    output = io.StringIO()
    fieldnames = ["Student", "ID", "SIS User ID", "SIS Login ID", "Section",
                  SCORE_COLUMN, COMMENT_COLUMN]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(approved_rows)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=approved_grades.csv"}
    )

if __name__ == "__main__":
    app.run(debug=True)