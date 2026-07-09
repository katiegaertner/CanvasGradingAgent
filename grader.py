"""
grader.py
---------
Grades student discussion posts using the Gemini LLM and RAG-grounded precedent.
Reads discussion_data.json and enrollment_data.json, writes staging.csv.
Receives COURSE_ID, DISCUSSION_ID, SCORE_COLUMN, and COMMENT_COLUMN as
environment variables from main.py.
"""

from google import genai
import os
import json
from dotenv import load_dotenv
import time
import csv
import warnings
from vector_store import retrieve_similar

warnings.filterwarnings("ignore", category=FutureWarning)
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SCORE_COLUMN = os.getenv("SCORE_COLUMN", "Discussion 1 | AI and Careers in Finance & Accounting (3057678)")
COMMENT_COLUMN = os.getenv("COMMENT_COLUMN", "Discussion 1 | AI and Careers in Finance & Accounting (3057678) - Comments")

RUBRIC = """
You are grading a student discussion post for an introductory business AI course.
Students are freshmen who are new to AI concepts.

The discussion prompt asked students to:
POST (3 points): Find a current job posting in finance or accounting. Include:
- A link to the job listing
- The job title
- A one-sentence description
- One or two sentences about why this job interests them

REPLY (2 points): Reply to at least two peers with any specific idea of how AI 
might be used in the job they posted.

SCORING:

POST:
- 3/3: Includes all four elements, interest statement is genuine and specific
- 2/3: Missing one element or interest statement is vague or shallow
- 1/3: Missing multiple elements
- 0/3: No post

REPLY:
- 2/2: Both replies offer a specific idea for how AI could be used in the peer's job.
  A specific idea is anything beyond "AI could help" or "AI would be useful here."
  Examples of passing replies: "AI could automate invoice processing",
  "machine learning could flag suspicious transactions",
  "AI tools like ChatGPT could help draft client emails."
- 1.5/2: One reply is specific, one is completely generic with no idea attached.
- 1/2: Only one reply submitted with a specific idea, or both replies are 
  completely generic.
- 0.5/2: Only one reply submitted and it is completely generic.
- 0/2: No replies submitted.

COMMENT INSTRUCTIONS:
- If post score is 3 and reply score is 2: one short sentence of genuine specific 
  praise about something in their post or replies.
- If post score is less than 3: one short sentence explaining what was missing 
  from the post.
- Keep all comments to one sentence maximum.
- Do not mention the job title, company name, role, or any specific content 
  from the job listing in your comment.
- Write conversationally, not formally.
- Leave the comment blank if the student did not submit a post.

Flag for review if you are uncertain about the score.
"""

def grade_student(student):
    """
    Grade a single student's discussion post and replies.
    Returns a dictionary with post_score, reply_score, total_score,
    comment, flag, and flag_reason.
    """
    post = student.get("post", "")
    outgoing_replies = student.get("outgoing_replies", [])
    reply_count = len(outgoing_replies)

    replies_text = ""
    for i, reply in enumerate(outgoing_replies, 1):
        replies_text += f"Reply {i}: {reply['reply']}\n\n"

    if not replies_text:
        replies_text = "No replies found."

    # Retrieve similar past examples from vector store
    reply_texts = [r["reply"] for r in outgoing_replies]
    similar_examples = retrieve_similar(post, reply_texts, n_results=3)

    examples_text = ""
    for i, ex in enumerate(similar_examples, 1):
        examples_text += f"""
Example {i} (Score: {ex['score']}/5):
Post: {ex['post']}
Replies: {ex['replies']}
"""

    # Build prompt based on reply count
    if reply_count == 0:
        prompt = f"""
{RUBRIC}

PRECEDENT EXAMPLES FROM PAST GRADED SUBMISSIONS:
{examples_text}

STUDENT SUBMISSION:

Post:
{post}

This student submitted no replies to peers.

Please evaluate the POST ONLY and respond in this exact format:
POST_SCORE: [number only: 0, 1, 2, or 3]
POST_COMMENT: [one short sentence about the post, or blank if no post]
FLAG: [YES or NO]
FLAG_REASON: [reason if flagged, otherwise NONE]
"""
    else:
        prompt = f"""
{RUBRIC}

PRECEDENT EXAMPLES FROM PAST GRADED SUBMISSIONS:
{examples_text}

STUDENT SUBMISSION:

Post:
{post}

Replies this student wrote to peers ({reply_count} replies submitted):
{replies_text}

Please evaluate the POST quality and REPLY SPECIFICITY only.
For replies, only judge whether each reply offers a specific AI idea or is generic.
A specific idea is anything beyond "AI could help" or "AI would be useful here."

Respond in this exact format:
POST_SCORE: [number only: 0, 1, 2, or 3]
POST_COMMENT: [one short sentence about the post, or blank if no post]
REPLY_QUALITY: [BOTH_SPECIFIC, ONE_SPECIFIC, or BOTH_GENERIC]
GENERAL_REPLY: [must be 1 or 2 when REPLY_QUALITY is ONE_SPECIFIC, otherwise NONE]
FLAG: [YES or NO]
FLAG_REASON: [reason if flagged, otherwise NONE]
"""

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt
            )
            text = response.text

            # Parse LLM response
            post_score = None
            post_comment = ""
            reply_quality = None
            general_reply = "NONE"
            flag = "NO"
            flag_reason = "NONE"

            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("POST_SCORE:"):
                    try:
                        post_score = float(line.split(":")[1].strip())
                    except:
                        pass
                elif line.startswith("POST_COMMENT:"):
                    post_comment = line.split(":", 1)[1].strip()
                elif line.startswith("REPLY_QUALITY:"):
                    reply_quality = line.split(":")[1].strip()
                elif line.startswith("GENERAL_REPLY:"):
                    general_reply = line.split(":")[1].strip()
                elif line.startswith("FLAG:"):
                    flag = line.split(":")[1].strip()
                elif line.startswith("FLAG_REASON:"):
                    flag_reason = line.split(":", 1)[1].strip()

            # Determine reply score and comment deterministically
            if reply_count == 0:
                reply_score = 0
                reply_comment = "0/2 required replies to peer posts."
            elif reply_count == 1:
                reply_score = 1 if reply_quality in ["BOTH_SPECIFIC", "ONE_SPECIFIC"] else 0.5
                reply_comment = "1/2 required replies to peer posts."
            else:
                if reply_quality == "BOTH_SPECIFIC":
                    reply_score = 2
                    reply_comment = ""
                elif reply_quality == "ONE_SPECIFIC":
                    reply_score = 1.5
                    if general_reply in ["1", "2"]:
                        reply_comment = f"Reply {general_reply} is too general — try being more specific about what you mean."
                    else:
                        reply_comment = "One reply is too general — try being more specific about what you mean."
                else:
                    reply_score = 1
                    reply_comment = "1/2 required replies to peer posts."

            # Build final comment
            if not post:
                comment = ""
            else:
                comment = post_comment
                if reply_comment:
                    comment = f"{comment} {reply_comment}".strip()

            # Calculate total score in code
            if post_score is None:
                post_score = 0
            total_score = post_score + reply_score

            if total_score == 5:
                print(f"User {student['user_id']}: 5/5")
            else:
                print(f"User {student['user_id']}: {total_score}/5 - needs review")

            return {
                "post_score": post_score,
                "reply_score": reply_score,
                "total_score": total_score,
                "comment": comment,
                "flag": flag,
                "flag_reason": flag_reason
            }

        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(10)

    return {
        "post_score": None,
        "reply_score": None,
        "total_score": None,
        "comment": "ERROR: Could not grade this student after 3 attempts",
        "flag": "YES",
        "flag_reason": "Grading error"
    }

# Load data
with open("discussion_data.json", "r") as f:
    discussion_data = json.load(f)

with open("enrollment_data.json", "r") as f:
    enrollment_map = json.load(f)

# Grade students who posted
rows = []
for student in discussion_data:
    result = grade_student(student)
    rows.append({
        "Student": student.get("student", ""),
        "ID": student.get("user_id", ""),
        "SIS User ID": student.get("sis_user_id", ""),
        "SIS Login ID": student.get("sis_login_id", ""),
        "Section": student.get("section", ""),
        SCORE_COLUMN: result["total_score"],
        COMMENT_COLUMN: result["comment"],
        "Flag": result["flag"],
        "Flag Reason": result["flag_reason"]
    })
    time.sleep(2)

# Add zero scores for students who never posted
graded_ids = {str(row["ID"]) for row in rows}
for user_id, enrollment in enrollment_map.items():
    if user_id not in graded_ids:
        rows.append({
            "Student": enrollment.get("student", ""),
            "ID": user_id,
            "SIS User ID": enrollment.get("sis_user_id", ""),
            "SIS Login ID": enrollment.get("sis_login_id", ""),
            "Section": enrollment.get("section", ""),
            SCORE_COLUMN: 0,
            COMMENT_COLUMN: "",
            "Flag": "YES",
            "Flag Reason": "Student did not submit a post."
        })
        print(f"User {user_id}: No post - scored 0")

# Sort by last name and write CSV
rows.sort(key=lambda x: x["Student"])
with open("staging.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "Student", "ID", "SIS User ID", "SIS Login ID", "Section",
        SCORE_COLUMN, COMMENT_COLUMN, "Flag", "Flag Reason"
    ])
    writer.writeheader()
    writer.writerows(rows)

print(f"Done. Graded {len(rows)} students. Results saved to staging.csv")