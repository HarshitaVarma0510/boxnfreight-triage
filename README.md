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
   API runs at `http://https://boxnfreight-triage.onrender.com` (docs available at `/docs`).

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
