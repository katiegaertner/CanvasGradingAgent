from google import genai
import os
import json
from dotenv import load_dotenv
import time
import csv
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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

CRITICAL REPLY SCORING RULE:
- If Number of replies submitted is 0: REPLY_SCORE must be 0
- If Number of replies submitted is 1: REPLY_SCORE must be 1 or 0.5, never 1.5 or 2
- If Number of replies submitted is 2 or more: score based on quality
- 1.5/2 is ONLY possible when exactly two replies are submitted and one is specific 
  and one is general
- It is impossible to score 1.5 or 2 with fewer than two replies submitted

COMMENT INSTRUCTIONS:
- If reply score is 0: comment must end with "0/2 required replies to peer posts."
- If reply score is 0.5: comment must end with "1/2 required replies to peer posts."
- If reply score is 1: comment must end with "1/2 required replies to peer posts."
- If reply score is 1.5: comment must end with "One reply was too general."
- If reply score is 2: do not mention replies in the comment.
- If post score is 3 and reply score is 2: one short sentence of genuine specific 
  praise about something in their post or replies.
- If post score is less than 3: one short sentence explaining what was missing 
  from the post.
- Keep all comments to one sentence maximum.
- Do not mention the job title, company name, or role in any comment.
- Write conversationally, not formally.
- Leave the comment blank if the student did not submit a post.

Flag for review if you are uncertain about the score.
"""

def grade_student(student):
    post = student.get("post", "")
    outgoing_replies = student.get("outgoing_replies", [])
    
    replies_text = ""
    for i, reply in enumerate(outgoing_replies, 1):
        replies_text += f"Reply {i}: {reply['reply']}\n\n"
    
    if not replies_text:
        replies_text = "No replies found."
    
    reply_count = len(outgoing_replies)

    prompt = f"""
{RUBRIC}

STUDENT SUBMISSION:

Number of replies submitted: {reply_count}

Post:
{post}

Replies this student wrote to peers:
{replies_text}

Please respond in this exact format:
POST_SCORE: [0, 1, 2, or 3]
REPLY_SCORE: [0, 0.5, 1, 1.5, or 2]
TOTAL_SCORE: [sum, may include .5]
COMMENT: [one or two sentences - specific praise if full credit, an explanation of the score if not]
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
            
            total_score = None
            for line in text.split("\n"):
                if line.startswith("TOTAL_SCORE:"):
                    try:
                        total_score = float(line.split(":")[1].strip())
                    except:
                        pass
            
            if total_score is None:
                print(f"DEBUG - could not parse score for {student['user_id']}:")
                print(text)
            elif total_score == 5:
                print(f"User {student['user_id']}: 5/5")
            else:
                print(f"User {student['user_id']}: {total_score}/5 - needs review")
            
            return text
        
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(10)
    
    return "ERROR: Could not grade this student after 3 attempts"

def parse_result(text):
    result = {
        "post_score": None,
        "reply_score": None,
        "total_score": None,
        "comment": "",
        "flag": "NO",
        "flag_reason": "NONE"
    }
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("POST_SCORE:"):
            try:
                result["post_score"] = float(line.split(":")[1].strip())
            except:
                pass
        elif line.startswith("REPLY_SCORE:"):
            try:
                raw = line.split(":")[1].strip()
                # Handle "1/2" format as well as plain floats
                if "/" in raw:
                    raw = raw.split("/")[0]
                result["reply_score"] = float(raw)
            except:
                pass
        elif line.startswith("COMMENT:"):
            result["comment"] = line.split(":", 1)[1].strip()
        elif line.startswith("FLAG:"):
            result["flag"] = line.split(":")[1].strip()
        elif line.startswith("FLAG_REASON:"):
            result["flag_reason"] = line.split(":", 1)[1].strip()

    # Calculate total ourselves rather than trusting the model
    if result["post_score"] is not None and result["reply_score"] is not None:
        result["total_score"] = result["post_score"] + result["reply_score"]
    
    return result

# Canvas gradebook column headers
SCORE_COLUMN = "Discussion 1 | AI and Careers in Finance & Accounting (3057678)"
COMMENT_COLUMN = "Discussion 1 | AI and Careers in Finance & Accounting (3057678) - Comments"

# Load data
with open("discussion_data.json", "r") as f:
    discussion_data = json.load(f)

with open("enrollment_data.json", "r") as f:
    enrollment_map = json.load(f)

# Grade students who posted
rows = []
for student in discussion_data:
    result_text = grade_student(student)
    parsed = parse_result(result_text)
    rows.append({
        "Student": student.get("student", ""),
        "ID": student.get("user_id", ""),
        "SIS User ID": student.get("sis_user_id", ""),
        "SIS Login ID": student.get("sis_login_id", ""),
        "Section": student.get("section", ""),
        SCORE_COLUMN: parsed["total_score"],
        COMMENT_COLUMN: parsed["comment"],
        "Flag": parsed["flag"],
        "Flag Reason": parsed["flag_reason"]
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

# # Temporary: test single student
# problem_ids = [574016]
# with open("discussion_data.json", "r") as f:
#     discussion_data = json.load(f)

# for student in discussion_data:
#     if student["user_id"] in problem_ids:
#         print(f"\n--- {student['user_id']} ---")
#         result = grade_student(student)
#         print(result)