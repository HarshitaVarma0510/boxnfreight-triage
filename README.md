# BoxnFreight AI Support Ticket Triage System

An AI-powered customer support ticketing and automated triage platform designed for freight and logistics operations. The system automatically categorizes incoming inquiries across 10 official BRD categories, resolves known inquiries instantly using an intelligent FAQ knowledge base with Gemini AI, and escalates complex or ambiguous issues to human administrators for review.

---

## Features

- **Automated AI Triage**: Analyzes customer queries in real-time, categorizing them across 10 standardized logistics categories.
- **Intelligent Knowledge Base Resolution**: Matches queries against 50+ domain-specific logistics FAQs and automatically resolves them with detailed answers and reasoning.
- **Human Escalation Queue**: Routes edge cases, high-value disputes, or ambiguous queries to an Admin Escalation Review dashboard.
- **Modern Full-Stack Architecture**:
  - **Frontend**: Next.js 15 (App Router), React, Tailwind CSS, Lucide icons.
  - **Backend**: FastAPI, Google GenAI SDK, SQLite (via `aiosqlite`).

---

## Repository Structure

```
boxnfreight-triage/
├── backend/
│   ├── .env.example        # Example environment configuration
│   ├── agent.py            # AI triage agent using Gemini API
│   ├── main.py             # FastAPI backend application
│   ├── requirements.txt    # Python backend dependencies
│   ├── seed_faqs.py        # Database initialization & FAQ seeder
│   └── tickets.db          # SQLite database (tickets and FAQs)
├── frontend/
│   ├── public/             # Static public assets
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx    # Customer ticket submission & status UI
│   │   │   ├── admin/      # Admin escalation dashboard
│   │   │   └── layout.tsx  # Root Next.js layout
│   │   └── lib/            # Utilities (date formatting, helpers)
│   ├── package.json        # Frontend dependencies and scripts
│   └── tsconfig.json       # TypeScript configuration
├── .gitignore              # Git ignore rules
└── README.md               # Project documentation
```

---

## Quickstart Guide

### 1. Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # macOS / Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   Copy `.env.example` to `.env` and add your Gemini API key:
   ```bash
   cp .env.example .env
   # Edit .env and set GEMINI_API_KEY
   ```
5. Initialize the database and seed the FAQs:
   ```bash
   python seed_faqs.py
   ```
6. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   API runs at `https://boxnfreight-triage.onrender.com` (docs available at `/docs`).

---

### 2. Frontend Setup

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```
4. Access the web applications:
   - **Customer Portal**: [http://localhost:3000](http://localhost:3000)
   - **Admin Escalation Review**: [http://localhost:3000/admin](http://localhost:3000/admin)

## Design Decisions & Escalation Logic
### 1. Architecture & Model Choice
- **Framework & Database:** Built using FastAPI for asynchronous request handling and SQLite seeded with all 50 official BRD FAQs categorized across operational workflows.
- **LLM Provider:** Powered by Google Gemini (gemini-3.8-flash) via the Google GenAI SDK. It performs semantic reasoning across user queries, extracts intent, and maps requests to predefined BRD categories and FAQs.
### 2. Dual-Layer Resiliency & Fallback Strategy
- **Quota Exhaustion & Outage Protection:** Free-tier LLM endpoints encounter strict rate/quota thresholds (HTTP 429). To prevent system failures, the architecture includes a deterministic heuristic fallback layer (_fallback_heuristic_triage).
- **Zero Downtime:** If the Gemini API key is missing or quota is exhausted, incoming tickets automatically route through the fallback engine without crashing or degrading core functionality.
### 3. Confidence & Escalation Rules
- **Direct Resolution (RESOLVED):**
  - When a customer's query matches an existing FAQ with high confidence (semantic match via LLM or >= 60% token/phrase match via heuristic fallback), the system immediately marks the ticket as RESOLVED and serves the official documentation answer.
  - Valid FAQ inquiries containing words like "escalate" or "agent" (e.g., "How do I escalate an issue?") bypass false-positive filters and resolve directly.
- **Human Escalation (ESCALATED):**
  - Tickets are routed to the human review queue if confidence is below threshold, if no relevant FAQ exists, or if clear ambiguity triggers are present (e.g., lost cargo, payment disputes, physical accidents).
  - The agent provides clear decision reasoning alongside a suggested category, ensuring the support admin dashboard only surfaces actionable, unresolved tickets requiring human inspection.