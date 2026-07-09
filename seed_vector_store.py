"""
seed_vector_store.py
--------------------
One-time setup script that seeds the vector store with historical graded
discussion submissions. Run this before the first grading run to give the
RAG layer prior examples to retrieve from.

Usage:
    python3 seed_vector_store.py

Configure COURSE_IDS below to point to your historical course runs.
The script dynamically matches discussions to assignments by name,
so no manual ID lookup is required.
"""

import requests
import os
import time
import warnings
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from vector_store import embedding_model, collection

warnings.filterwarnings("ignore", category=FutureWarning)
load_dotenv()

TOKEN = os.getenv("CANVAS_TOKEN")
BASE_URL = os.getenv("CANVAS_BASE_URL")
headers = {"Authorization": f"Bearer {TOKEN}"}

# ============================================================
# CONFIGURATION — add course IDs for all historical course runs
# that used the same career discussion format
# ============================================================
COURSE_IDS = [499524, 434313, 463575]

# Keywords used to identify career discussion assignments
# Update if your discussion titles use different terminology
CAREER_KEYWORDS = ["finance", "marketing", "supply chain", "management", "risk", "real estate"]
# ============================================================

def clean_html(html):
    """Strip HTML tags and return plain text."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ").strip()

def get_discussion_entries(course_id, discussion_id):
    """Fetch all top-level posts for a discussion."""
    url = f"{BASE_URL}/api/v1/courses/{course_id}/discussion_topics/{discussion_id}/entries?per_page=100"
    response = requests.get(url, headers=headers)
    return response.json()

def get_replies(course_id, discussion_id, entry_id):
    """Fetch all replies to a specific discussion entry."""
    url = f"{BASE_URL}/api/v1/courses/{course_id}/discussion_topics/{discussion_id}/entries/{entry_id}/replies?per_page=50"
    response = requests.get(url, headers=headers)
    return response.json()

def get_submissions(course_id, assignment_id):
    """Fetch all graded submissions for a discussion assignment."""
    url = f"{BASE_URL}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions?per_page=100"
    response = requests.get(url, headers=headers)
    return response.json()

def build_historical_discussions(course_ids):
    """
    Dynamically build the list of historical discussions by fetching
    course data from Canvas and matching discussions to assignments by name.
    Filters to career discussions only using CAREER_KEYWORDS.
    """
    historical = []

    for course_id in course_ids:
        print(f"Fetching discussions and assignments for course {course_id}...")

        # Fetch discussions
        url = f"{BASE_URL}/api/v1/courses/{course_id}/discussion_topics?per_page=50"
        discussions = requests.get(url, headers=headers).json()

        # Fetch assignments and build name lookup
        url = f"{BASE_URL}/api/v1/courses/{course_id}/assignments?per_page=50"
        assignments = requests.get(url, headers=headers).json()
        assignment_map = {
            a["name"].strip().lower(): a["id"]
            for a in assignments
            if a.get("submission_types") == ["discussion_topic"]
        }

        # Match discussions to assignments by name
        for d in discussions:
            title = d["title"].strip()
            if not any(keyword in title.lower() for keyword in CAREER_KEYWORDS):
                continue
            assignment_id = assignment_map.get(title.lower())
            if assignment_id:
                historical.append({
                    "course_id": course_id,
                    "discussion_id": d["id"],
                    "assignment_id": assignment_id,
                    "title": title
                })
                print(f"  Matched: {title}")
            else:
                print(f"  No assignment match for: {title}")

    print(f"\nBuilt {len(historical)} discussion configs")
    return historical

def seed_discussion(discussion_config):
    """
    Fetch posts, replies, and grades for a single discussion and
    add them to the vector store. Skips records already in the store.
    """
    course_id = discussion_config["course_id"]
    discussion_id = discussion_config["discussion_id"]
    assignment_id = discussion_config["assignment_id"]
    title = discussion_config["title"]

    print(f"\nSeeding: Course {course_id} | {title}")

    # Fetch grades
    submissions = get_submissions(course_id, assignment_id)
    grade_map = {}
    for sub in submissions:
        user_id = sub.get("user_id")
        score = sub.get("score")
        if score is not None:
            grade_map[user_id] = float(score)

    print(f"  Found {len(grade_map)} grades")

    # Fetch posts and replies
    entries = get_discussion_entries(course_id, discussion_id)
    all_replies = []
    for entry in entries:
        replies = get_replies(course_id, discussion_id, entry["id"])
        for reply in replies:
            reply["parent_author_id"] = entry.get("user_id")
            all_replies.append(reply)
        time.sleep(0.5)

    # Embed and store each graded student
    seeded = 0
    for entry in entries:
        user_id = entry.get("user_id")
        score = grade_map.get(user_id)
        if score is None:
            continue

        post = clean_html(entry.get("message", ""))
        outgoing_replies = [
            clean_html(r.get("message", ""))
            for r in all_replies
            if r.get("user_id") == user_id
        ]

        full_text = f"POST: {post}\n\nREPLIES: {' | '.join(outgoing_replies)}"
        doc_id = f"{course_id}_{discussion_id}_{user_id}"

        # Skip if already in store
        existing = collection.get(ids=[doc_id])
        if existing["ids"]:
            continue

        embedding = embedding_model.encode(full_text).tolist()
        collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[full_text],
            metadatas=[{
                "course_id": str(course_id),
                "discussion_id": str(discussion_id),
                "user_id": str(user_id),
                "score": score,
                "title": title,
                "post": post[:500],
                "replies": " | ".join(outgoing_replies)[:500]
            }]
        )
        seeded += 1

    print(f"  Seeded {seeded} records")

# Build discussion list dynamically and seed the store
HISTORICAL_DISCUSSIONS = build_historical_discussions(COURSE_IDS)

print("\nStarting vector store seeding...")
for discussion in HISTORICAL_DISCUSSIONS:
    seed_discussion(discussion)
    time.sleep(1)

print(f"\nDone. Total records in store: {collection.count()}")