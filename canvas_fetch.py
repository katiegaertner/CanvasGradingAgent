import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("CANVAS_TOKEN")
BASE_URL = os.getenv("CANVAS_BASE_URL")

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

#Retrieve infrormation for grading upload

## section information
def get_sections(course_id):
    url = f"{BASE_URL}/api/v1/courses/{course_id}/sections?per_page=50"
    response = requests.get(url, headers=headers)
    return response.json()

sections = get_sections(531715)

section_map = {}
for s in sections:
    section_map[s.get('id')] = s.get('name')

##enrollment information
def get_enrollments(course_id):
    url = f"{BASE_URL}/api/v1/courses/{course_id}/enrollments?type[]=StudentEnrollment&per_page=100"
    response = requests.get(url, headers=headers)
    return response.json()

enrollments = get_enrollments(531715)
enrollment_map = {}

for e in enrollments:
    user_id = e.get('user_id')
    enrollment_map[user_id] = {
        "student": e.get('user', {}).get('sortable_name', ''),
        "id": user_id,
        "sis_user_id": e.get('user', {}).get('sis_user_id', ''),
        "sis_login_id": e.get('user', {}).get('login_id', ''),
        "section": section_map.get(e.get('course_section_id'), '')
    }

with open("enrollment_data.json", "w") as f:
    json.dump(enrollment_map, f, indent=2)

print(f"Saved {len(enrollment_map)} enrollments to enrollment_data.json")

##Retrieve discussion entries
def get_discussion_entries(course_id, discussion_id):
    url = f"{BASE_URL}/api/v1/courses/{course_id}/discussion_topics/{discussion_id}/entries?per_page=50"
    response = requests.get(url, headers=headers)
    return response.json()

#parse student posts
from bs4 import BeautifulSoup
def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ").strip()

##etrieve discussion replies
def get_replies(course_id, discussion_id, entry_id):
    url = f"{BASE_URL}/api/v1/courses/{course_id}/discussion_topics/{discussion_id}/entries/{entry_id}/replies?per_page=50"
    response = requests.get(url, headers=headers)
    return response.json()

entries = get_discussion_entries(531715, 2421451)

#Coalesce information

##First Pass: collect all entries and all replies

all_entries = entries
all_replies = []

for entry in all_entries:
    replies = get_replies(531715, 2421451, entry['id'])
    for reply in replies:
        reply['parent_author_id'] = entry.get('user_id')
        all_replies.append(reply)

##Second pass: Build per-student records with enrollment info, posts, and replies

discussion_data = []
for entry in all_entries:
    student_id = entry.get('user_id')
    outgoing_replies = [
        {
            "to_user": r.get('parent_author_id'),
            "reply": clean_html(r.get('message', ''))
        }
        for r in all_replies
        if r.get('user_id') == student_id
    ]
    enrollment = enrollment_map.get(student_id, {})
    discussion_data.append({
        "user_id": student_id,
        "student": enrollment.get("student", ""),
        "sis_user_id": enrollment.get("sis_user_id", ""),
        "sis_login_id": enrollment.get("sis_login_id", ""),
        "section": enrollment.get("section", ""),
        "posted_at": entry.get("created_at"),
        "post": clean_html(entry.get("message", "")),
        "outgoing_replies": outgoing_replies
    })

with open("discussion_data.json", "w") as f:
    json.dump(discussion_data, f, indent=2)

print(f"Saved {len(discussion_data)} student entries to discussion_data.json")