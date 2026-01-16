# Adaptive Book Compressor

**Turn 10 hours of reading into 15 minutes.**
An intelligent, constraint-based summarization engine that uses **Recursive Map-Reduce** to compress full-length books into strict time budgets without losing the author's voice.


## 🚀 The Engineering Problem

Standard LLMs (like ChatGPT) have two fatal flaws when processing large documents:

1.  **Context Window Limits:** You cannot paste a 100,000-word book into a prompt without crashing the model or losing accuracy ("The Lost in the Middle" phenomenon).
2.  **Output Hallucinations:** When asked to summarize a massive text, models tend to produce generic, high-level fluff rather than specific, actionable details.

## 🛠 The Solution: Recursive Map-Reduce

This system implements a distributed processing pipeline inspired by Big Data architectures:

1.  **Ingestion & Semantic Chunking:**
    The PDF is treated as a binary stream, extracted, and split into **semantic chunks** (keeping paragraphs intact) rather than arbitrary token limits.
2.  **Parallel "Map" Phase:**
    The system spawns **20 concurrent asynchronous workers** (using Python `asyncio`) to summarize chunks in parallel. This reduces processing time from ~10 minutes to ~45 seconds.
3.  **Recursive "Reduce" Phase (Constraint Satisfaction):**
    The system calculates a "Word Budget" based on the user's desired reading time (e.g., 15 mins). It uses a **recursive divide-and-conquer algorithm** to split the summary tree until every block is small enough to be compressed without information loss.

---

## 🏗 Tech Stack

### Backend (The Brain)

- **Language:** Python 3.11+
- **Framework:** **FastAPI** (Asynchronous I/O)
- **AI Orchestration:** **LangChain** + **OpenAI GPT-4o-mini**
- **Database:** **PostgreSQL** + **pgvector** (Storing 1,536-dimensional embeddings)
- **ORM:** SQLAlchemy (Async drivers)

### Frontend (The Interface)

- **Framework:** **Next.js 14** (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **State Management:** React Hooks

---

## ⚡️ Key Features

- **Constraint-Based Compression:** Users set a time limit (e.g., "5 minutes"). The engine mathematically enforces this limit via recursive editing.
- **High-Concurrency Processing:** Uses `asyncio.gather` and `asyncio.Semaphore` to manage rate limits while maximizing throughput.
- **Vector Storage:** All book chunks are embedded and stored in Postgres using `pgvector`, enabling future semantic search capabilities.
- **Persona Preservation:** Custom prompt engineering ensures the AI retains the original author's voice ("I argue...") rather than a third-person report ("The book says...").

---

## 💻 How to Run Locally

### Prerequisites

- Node.js & npm
- Python 3.10+
- PostgreSQL (with `pgvector` extension enabled)

### 1. Database Setup

```sql
CREATE DATABASE adaptive_compressor_db;
\c adaptive_compressor_db
CREATE EXTENSION vector;
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # (Windows: venv\Scripts\activate)
pip install -r requirements.txt
```

_Create a `.env` file in `/backend`:_

```ini
OPENAI_API_KEY=sk-proj-your-key-here
DATABASE_URL=postgresql+asyncpg://user:password@localhost/adaptive_compressor_db
```

_Run the server:_

```bash
uvicorn main:app --reload
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000` to start compressing.

---

## 🧠 Engineering Challenges & Learnings

### 1. The "Token Math" Problem

We found that GPT-4o-mini performs best when inputs are < 3000 tokens. Our recursive algorithm dynamically detects if a text block is too large and splits it geometrically until it fits the "Safety Window" before attempting compression.

### 2. Handling Async Concurrency

Initially, the Map phase ran sequentially (taking 5+ minutes). We refactored this using `asyncio.gather`, but hit OpenAI Rate Limits. We solved this by implementing a **Semaphore pattern** to cap concurrent requests at 20, balancing speed with API stability.

### 3. Verification

While the UI is simplified, the backend supports full **RAG (Retrieval Augmented Generation)** verification. Every generated summary sentence can be vector-matched against the original database to find the source of truth, minimizing hallucinations.
