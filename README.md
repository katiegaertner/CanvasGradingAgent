# Canvas Discussion Grading Agent
**Carnegie Mellon University | Agentic AI Program Capstone**  
**Katie Gaertner | Wisconsin School of Business, UW-Madison**

An agentic AI pipeline that retrieves student discussion posts from Canvas LMS, 
evaluates them against a rubric using a large language model, and stages draft 
grades for instructor review before writing anything back to Canvas.

---

## What It Does

1. **Fetches** student discussion posts and replies from Canvas via the REST API
2. **Grades** each student's post and peer replies against a structured rubric
3. **Stages** draft grades in a CSV file for instructor review
4. **Presents** grades in a browser-based review interface where the instructor 
   can edit scores and comments before approving
5. **Exports** an approved CSV formatted for direct Canvas gradebook import

No grade reaches Canvas without explicit instructor approval.

---

## Architecture

CanvasDiscussionGradingAgent.png

The system uses a ReAct-style reasoning loop, grounding each evaluation against 
a structured rubric. Ambiguous cases are flagged for instructor review. 
Full-credit and zero-score students are auto-approved; all other cases require 
manual review.

### Designed But Not Yet Implemented
- **RAG layer**: vector store of prior graded examples for precedent-grounded scoring
- **Tree of Thought**: multi-candidate reasoning for ambiguous reply scoring
- **Consistency Reviewer**: second agent monitoring batch-level score drift
- **Canvas write-back**: API-gated grade submission after instructor approval

---

## Project Structure
canvas-grading-agent/
|-- main.py              # Entry point - runs full pipeline
|-- canvas_fetch.py      # Fetches Canvas data via REST API
|-- grader.py            # Grades students using Gemini LLM
|-- review.py            # Flask review interface
|-- requirements.txt     # Python dependencies
|-- .env.example         # Environment variable template
|__ README.md

---

## Setup

### Prerequisites
- Python 3.12+
- A Canvas LMS account with API access
- A Google AI Studio or Vertex AI API key

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/canvas-grading-agent.git
cd canvas-grading-agent
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```
CANVAS_TOKEN=your_canvas_api_token
CANVAS_BASE_URL=https://your_institution.instructure.com
GEMINI_API_KEY=your_gemini_api_key

**Canvas API Token**: Canvas → Account → Settings → New Access Token  
**Gemini API Key**: aistudio.google.com → Get API Key

### Configuration

Before running, update the following constants in `canvas_fetch.py` and `grader.py` 
to match your course:

```python
COURSE_ID = 531715        # Your Canvas course ID
DISCUSSION_ID = 2421451   # Your discussion assignment ID
SCORE_COLUMN = "Discussion 1 | ..."   # Exact Canvas gradebook column name
COMMENT_COLUMN = "Discussion 1 | ... - Comments"
```

---

## Usage

```bash
python3 main.py
```

This will:
1. Fetch all discussion posts and replies from Canvas
2. Grade each student using the Gemini LLM
3. Open the review interface at http://127.0.0.1:5000

Review flagged and partial-credit students, edit any scores or comments, 
then click **Export All Grades** to download the Canvas-ready CSV.

Import the CSV into Canvas via Gradebook → Actions → Import.

---

## Rubric

The agent grades two components:

| Component | Points | Criteria |
|---|---|---|
| Post | 3 | Job listing link, title, description, specific interest statement |
| Reply | 2 | Two peer replies with specific AI application ideas |

Half-point scoring is supported. The agent auto-approves scores of 0 and 5; 
all other scores require instructor review.

---

## Safety and Privacy

- **No grade is written to Canvas automatically.** All grades pass through 
  instructor review first.
- **Canvas API token** is scoped to minimum required permissions.
- **Student data** is stored locally only and excluded from this repository 
  via `.gitignore`.
- **FERPA note**: For production use with real student data, route API calls 
  through your institution's approved Vertex AI agreement rather than a personal 
  Google AI Studio key.
- **Prompt injection mitigation**: student post content is explicitly separated 
  from system instructions in the prompt.

---

## Limitations and Next Steps

- Currently configured for a single discussion assignment; multi-discussion 
  support is planned
- Python 3.12+ required; tested on macOS with Apple Silicon

---

## Acknowledgments

Developed as part of the Carnegie Mellon University School of Computer Science 
Executive Education Agentic AI Program.
