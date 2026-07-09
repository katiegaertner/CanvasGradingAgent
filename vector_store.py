"""
vector_store.py
---------------
Shared vector store module for the Canvas Discussion Grading Agent.
Initializes ChromaDB and the sentence transformer embedding model at module level
so they are loaded once and reused across grader.py, review.py, and
consistency_reviewer.py.

Functions:
    retrieve_similar  -- query the store for past examples similar to a student submission
    add_to_store      -- add a newly approved grade to the store
    store_count       -- return the total number of records in the store
"""

import warnings
import chromadb
from sentence_transformers import SentenceTransformer

warnings.filterwarnings("ignore", category=FutureWarning)

# Initialize once at module level — reused by all importing modules
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="./chroma_store")
collection = chroma_client.get_or_create_collection("graded_discussions")

def retrieve_similar(post_text, reply_texts, n_results=3):
    """
    Query the vector store for past graded submissions similar to the current student.
    Returns a list of dicts with score, post, replies, and title.
    """
    full_text = f"POST: {post_text}\n\nREPLIES: {' | '.join(reply_texts)}"
    embedding = embedding_model.encode(full_text).tolist()

    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results
    )

    examples = []
    for i in range(len(results["ids"][0])):
        metadata = results["metadatas"][0][i]
        examples.append({
            "score": metadata.get("score"),
            "post": metadata.get("post", ""),
            "replies": metadata.get("replies", ""),
            "title": metadata.get("title", "")
        })

    return examples

def add_to_store(course_id, discussion_id, user_id, post, replies, score):
    """
    Add an instructor-approved grade to the vector store for future RAG retrieval.
    Uses a composite key of course_id, discussion_id, and user_id to prevent duplicates.
    """
    full_text = f"POST: {post}\n\nREPLIES: {' | '.join(replies)}"
    embedding = embedding_model.encode(full_text).tolist()
    doc_id = f"{course_id}_{discussion_id}_{user_id}"

    collection.add(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[full_text],
        metadatas=[{
            "course_id": str(course_id),
            "discussion_id": str(discussion_id),
            "user_id": str(user_id),
            "score": score,
            "post": post[:500],
            "replies": " | ".join(replies)[:500]
        }]
    )

def store_count():
    """Return the total number of records currently in the vector store."""
    return collection.count()