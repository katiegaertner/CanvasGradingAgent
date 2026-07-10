# Canvas Discussion Grading Agent
**Carnegie Mellon University | Agentic AI Program Capstone**  
**Katie Gaertner | Wisconsin School of Business, UW-Madison**

An agentic AI pipeline that retrieves student discussion posts from Canvas LMS, evaluates them against a participation rubric using a large language model, stages draft grades for instructor review, and exports a Canvas-ready CSV for manual gradebook import.

No grade reaches Canvas without explicit instructor approval.

---

## What It Does

1. **Fetches** student discussion posts, outgoing peer replies, and enrollment data from Canvas via the REST API
2. **Grades** each student's post and replies against a structured rubric using Gemini LLM, grounded in RAG-retrieved historical examples
3. **Checks** for batch-level score drift against 865 historically graded submissions
4. **Presents** draft grades in a browser-based review interface where the instructor can read each student's submission, edit scores and comments, and approve
5. **Exports** an instructor-approved CSV formatted for direct Canvas gradebook import, and writes approved grades back to the vector store to improve future runs

---

## Architecture

[![Architecture Diagram](CanvasDiscussionGradingAgent.png)](https://github.com/katiegaertner/CanvasGradingAgent/blob/main/CanvasDiscussionGradingAgent.pdf)

The system is a **two-agent pipeline** orchestrated by `main.py`:

- **Grading Agent** (`grader.py`) — processes students sequentially in a ReAct-style loop, retrieving similar past graded examples via RAG before evaluating each submission. Reply count is enforced deterministically in code; the LLM classifies quality only.
- **Reviewer Agent** (`consistency_reviewer.py`) — runs after grading completes, comparing the current run's score distribution against historical patterns and flagging outliers for instructor attention.

The system includes a **learning loop**: approved grades are written back to the vector store on export, so each grading run improves future calibration.

### Planned but not yet implemented
- **Canvas write-back**: API-gated grade submission after instructor approval (scaffold designed; manual CSV import is the current HITL safety gate)
- **Multi-discussion batch mode**: grade all discussions in a course term in a single run

---

## Project Structure

```
canvas-grading-agent/
├── main.py                  # Entry point — orchestrates the full pipeline
├── canvas_fetch.py          # Fetches posts, replies, and enrollment from Canvas API
├── grader.py                # Grades students using Gemini LLM + RAG
├── review.py                # Flask review interface (edge cases only)
├── review_all.py            # Flask review interface (all students)
├── consistency_reviewer.py  # Reviewer agent — detects batch-level score drift
├── vector_store.py          # Shared ChromaDB vector store for RAG retrieval
├── seed_vector_store.py     # One-time setup — seeds store from historical grades
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
└── README.md
```

---

## Setup

### Prerequisites
- Python 3.12+
- A Canvas LMS account with API access
- A Google AI Studio or Vertex AI API key

### Installation

```bash
git clone https://github.com/kgaertner/canvas-grading-agent.git
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

```
CANVAS_TOKEN=your_canvas_api_token
CANVAS_BASE_URL=https://your_institution.instructure.com
GEMINI_API_KEY=your_gemini_api_key
```

**Canvas API Token**: Canvas → Account → Settings → New Access Token  
**Gemini API Key**: aistudio.google.com → Get API Key

---

## Seeding the Vector Store (First-Time Setup)

Before your first grading run, seed the vector store with historical graded submissions. Open `seed_vector_store.py` and update `COURSE_IDS` with the Canvas course IDs for any prior course runs that used the same discussion format:

```python
COURSE_IDS = [499524, 434313, 463575]  # Replace with your historical course IDs
```

Then run:

```bash
python3 seed_vector_store.py
```

The script dynamically matches discussions to assignments by name — no manual ID lookup required. If you have no prior graded data, skip this step and the system will begin building the store from your first approved run.

---

## Usage

```bash
python3 main.py
```

The pipeline will prompt you for:
- **Course ID** — found in the Canvas URL for your course
- **Discussion ID** — found in the Canvas URL for the discussion assignment
- **Score column header** — copy exactly from your Canvas gradebook CSV export
- **Review mode** — edge cases only (auto-approves 5/5 and 0/5) or full review (all students)

Configuration is saved to `config.json` and reused on subsequent runs.

The pipeline then:
1. Fetches all discussion data from Canvas
2. Grades each student using Gemini LLM + RAG
3. Runs the consistency review and prints a drift report to the terminal
4. Opens the review interface at `http://127.0.0.1:5000`

Review grades, edit any scores or comments, click **Approve All Remaining** for unmodified cases, then click **Export All Grades** to download the Canvas-ready CSV. Import via Gradebook → Actions → Import in Canvas.

---

## Rubric

The agent grades two components:

| Component | Points | Criteria |
|---|---|---|
| Post | 3 | Job listing link, title, one-sentence description, specific interest statement |
| Reply | 2 | Two peer replies each offering a specific AI application idea |

Half-point scoring is supported for reply quality. Reply count is enforced in code — the model cannot award credit for replies that do not exist in the submission data.

The rubric is currently configured for a job-posting career discussion. To adapt it for a different assignment format, update the `RUBRIC` string in `grader.py`.

---

## Safety and Privacy

- **No grade is written to Canvas automatically.** The instructor manually imports the approved CSV — this is an intentional human-in-the-loop control point, not a limitation.
- **Prompt injection mitigation** — student post content is explicitly separated from system instructions. The model is instructed to treat post text as data, not instructions.
- **Scoped Canvas API token** — minimum required permissions only (read discussions, read enrollment, write grades). Store in `.env`, never in code.
- **Student data** is stored locally and excluded from this repository via `.gitignore`. The vector store retains anonymized embeddings only — student identifiers are stripped before indexing.
- **FERPA note** — for production use with real student data, route API calls through your institution's approved Vertex AI agreement rather than a personal Google AI Studio key.

---

## Limitations

- Grades one discussion assignment per run; six weekly discussions require six runs
- Rubric is hardcoded in `grader.py`; different assignment formats require code edits
- Production FERPA compliance requires institutional Vertex AI review
- Tested on macOS with Apple Silicon; Python 3.12+ required

---

## Acknowledgments

Developed as part of the Carnegie Mellon University School of Computer Science Executive Education Agentic AI Program.
