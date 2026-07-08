from flask import Flask, render_template_string, request, jsonify
import csv
import json
import os

app = Flask(__name__)

STAGING_FILE = "staging.csv"
APPROVED_FILE = "approved.csv"

SCORE_COLUMN = "Discussion 1 | AI and Careers in Finance & Accounting (3057678)"
COMMENT_COLUMN = "Discussion 1 | AI and Careers in Finance & Accounting (3057678) - Comments"

def load_students():
    students = []
    with open(STAGING_FILE, "r") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            row["index"] = i
            try:
                score = float(row.get(SCORE_COLUMN, 0))
            except:
                score = 0
            # Auto-approve full credit and no-post students
            if score == 5 or score == 0:
                row["approved"] = True
            else:
                row["approved"] = False
            students.append(row)
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
    <div class="student-card {% if student.Flag == 'YES' %}flagged{% elif student.approved %}approved{% endif %}" id="card-{{ loop.index0 }}">
        <div class="student-name">
            {{ student.Student }}
            {% if student.Flag == 'YES' %}
            <span class="flag-badge">⚑ {{ student['Flag Reason'] }}</span>
            {% endif %}
            <span class="approved-badge" id="approved-badge-{{ loop.index0 }}" style="{% if student.approved %}display:inline{% else %}display:none{% endif %}">✓ Approved</span>
        </div>
        <div class="student-meta">{{ student['SIS Login ID'] }} &nbsp;|&nbsp; {{ student.Section }}</div>

        {% if student[score_column] != '0' %}
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
                    <option value="{{ score }}" {% if score == student[score_column]|float %}selected{% endif %}>{{ score }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="comment-wrap">
                <label>Comment</label>
                <textarea id="comment-{{ loop.index0 }}">{{ student[comment_column] }}</textarea>
            </div>
        </div>
        <button class="btn-approve" id="btn-{{ loop.index0 }}"
            onclick="approve({{ loop.index0 }}, '{{ student.ID }}')"
            {% if student.approved %}disabled{% endif %}>
            {% if student.approved %}Approved{% else %}Approve{% endif %}
        </button>
    </div>
    {% endfor %}

    <div class="export-bar">
        <div class="progress"><span id="progress-count">0</span> of {{ students|length }} reviewed</div>
        <button class="btn-export" onclick="exportCSV()">Export All Grades</button>
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
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    with open("discussion_data.json", "r") as f:
        discussion_data = json.load(f)
    
    post_map = {str(s["user_id"]): s.get("post", "") for s in discussion_data}
    reply_map = {str(s["user_id"]): [r["reply"] for r in s.get("outgoing_replies", [])] for s in discussion_data}
    
    # Only show students who need review
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
    data = request.json
    index = data["index"]
    students[index][SCORE_COLUMN] = data["score"]
    students[index][COMMENT_COLUMN] = data["comment"]
    students[index]["approved"] = True
    return jsonify({"success": True})

@app.route("/export")
def export():
    from flask import Response
    rows = [s for s in students if s.get("approved")]
    
    import io
    output = io.StringIO()
    fieldnames = ["Student", "ID", "SIS User ID", "SIS Login ID", "Section",
                  SCORE_COLUMN, COMMENT_COLUMN]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=approved_grades.csv"}
    )

if __name__ == "__main__":
    app.run(debug=True)