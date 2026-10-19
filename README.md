# BoxnFreight AI Support Ticket Triage SaaS

A production-grade, highly resilient AI-powered customer support ticketing and automated triage platform tailored for freight, trucking, and logistics operations. The platform automatically evaluates incoming customer inquiries against 50 official BoxNFreight FAQs across 10 BRD operational categories, delivers instant verified answers, fast-tracks logistics acronyms (POD, LR, tracking), and seamlessly escalates ambiguous issues or disputes to an administrative queue for human review.

---

## Key Features & Production Upgrades

### 1. Backend & API Resilience (FastAPI + Google GenAI)
- **Multi-Key Failover Pool (No Hardcoded Conditionals)**:
  - Dynamically pools API keys from `GEMINI_API_KEYS` (comma-separated) or `GEMINI_API_KEY_PRIMARY`, `GEMINI_API_KEY_SECONDARY`, `GEMINI_API_KEY_TERTIARY`.
  - Integrates the official Google GenAI SDK using model `"gemini-2.5-flash"` (with adaptive fallback to `"gemini-3.8-flash"`).
  - Iterates through the pool upon encountering quota limits (`HTTP 429` / `ResourceExhausted`) or transient network errors, logging masked warnings and rolling over seamlessly.
  - Automatically executes a local deterministic heuristic triage engine if all keys in the pool are exhausted.
- **Database Deduplication & Idempotency (SQLite + `aiosqlite`)**:
  - Deterministic SHA-256 hashing across `(category, normalized user query)` with a 5-minute cooldown window.
  - Returns the existing ticket record and ID with an idempotency notice upon repeated submissions without duplicate database rows.
  - Full lifecycle tracking with columns: `RESOLVED_BY_AI`, `ESCALATED`, `HUMAN_RESOLVED`, `NEEDS_INFO`, alongside `created_at` and `resolved_at` timestamps.
- **Intelligent Fast-Track & Greeting Detection**:
  - **Greeting Detection**: Conversational greetings ("hello", "good morning", "hi") immediately return polite prompts for shipment/LR details without LLM latency (`status: NEEDS_INFO`).
  - **Logistics Acronym Fast-Track**: Pattern matching for POD (Proof of Delivery), LR (Lorry Receipt), tracking, and E-Way bills directly against the FAQ base to eliminate latency for frequent inquiries.
  - **Multi-Part Question Parsing**: Enforces structured bulleted answers addressing split multi-part questions strictly from FAQ context.
  - **Human-Readable Reference Token**: Generates unique ticket references (e.g. `#TKT-1082`) with every response.
- **Admin Management API**:
  - `GET /api/admin/metrics`: Real-time KPI counts `{ pending_review, human_resolved, total_tickets, ai_resolved }`.
  - `GET /api/admin/tickets`: Filter by category, status, and search query across reference ID or query text.
  - `PATCH /api/admin/tickets/{ticket_id}/resolve`: Instantly updates status to `HUMAN_RESOLVED` and stamps `resolved_at`.
  - `PATCH /api/tickets/{ticket_id}/escalate`: Enables users to escalate AI-resolved tickets to human staff.

### 2. Frontend & User Experience (Next.js 16 / React 19 / Tailwind CSS)
- **Simplified Ticket Intake**:
  - Clean Category dropdown:
    * *Shipment & Tracking (POD / LR)*
    * *Booking & Orders*
    * *Billing & Invoices*
    * *Account & Login*
    * *General Inquiry*
  - Single focused textarea for issue details (open-ended title/subject field removed).
- **Auto-Scroll & Dynamic Visual Feedback**:
  - React `useRef` automatically and smoothly scrolls down to the triage verdict card on submission.
  - Multi-stage animated loading state cycling through status updates ("Analyzing issue...", "Checking knowledge base...", "Formulating triage response...").
- **User Actions & Human Escalation**:
  - Prominent Ticket Reference ID display (e.g., `#TKT-1082`) with a one-click copy-to-clipboard action.
  - Explicit *"Still need help? Talk to an Agent"* escalation button for AI-resolved tickets.
  - Cooldown deduplication notice banner for idempotent repeated requests.

### 3. Admin Operations Dashboard
- **Top KPI Summary Cards**:
  - **Pending Review**: Live count of escalated queue awaiting human inspection.
  - **Human Resolved**: Count of tickets resolved and closed by staff.
  - **Total Volume Handled**: Overall ticket volume processed.
- **Management Table & Instant Actions**:
  - Category filter dropdown and status tabs (*All*, *Pending Review*, *Human Resolved*, *AI Resolved*).
  - Search input filtering by `#TKT-<id>` or description text.
  - Inline *"Mark as Resolved"* button that hits the PATCH endpoint, immediately updating both the row and the top KPI counters.

---

## Repository Structure

```
boxnfreight-triage/
├── backend/
│   ├── .env.example        # Environment variables & multi-key pool documentation
│   ├── agent.py            # AI triage agent, failover pool, fast-track, and heuristics
│   ├── main.py             # FastAPI backend application & admin management endpoints
│   ├── requirements.txt    # Python backend dependencies
│   ├── seed_faqs.py        # Database schema migrations & 50 FAQ seed dataset
│   └── tickets.db          # SQLite database
├── frontend/
│   ├── public/             # Static public assets
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx    # Simplified ticket intake & AI triage portal
│   │   │   ├── admin/      # Upgraded admin KPI & ticket management dashboard
│   │   │   └── layout.tsx  # Root layout
│   │   └── lib/
│   │       ├── api.ts      # Type-safe API client and endpoint helpers
│   │       └── dateUtils.ts# IST date/time formatting utilities
│   ├── package.json        # Frontend dependencies & Next.js scripts
│   └── tsconfig.json       # TypeScript configuration
├── .gitignore              # Git ignore rules
└── README.md               # Architecture and setup documentation
```

---

## Quickstart Guide

### 1. Backend Setup

1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Activate your virtual environment (if not already active):
   ```bash
   # Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # macOS / Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables in `.env`:
   ```bash
   # Option 1: Comma-separated list
   GEMINI_API_KEYS=your_primary_key,your_secondary_key

   # Option 2: Individual prioritized keys
   # GEMINI_API_KEY_PRIMARY=your_primary_key
   # GEMINI_API_KEY_SECONDARY=your_secondary_key
   # GEMINI_API_KEY_TERTIARY=your_tertiary_key
   ```
5. Initialize the database and apply schema migrations:
   ```bash
   python seed_faqs.py
   ```
6. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   API interactive docs: `http://localhost:8000/docs`.

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
3. Run the Next.js development server:
   ```bash
   npm run dev
   ```
4. Access the web applications:
   - **Customer Portal**: [http://localhost:3000](http://localhost:3000)
   - **Admin Operations Dashboard**: [http://localhost:3000/admin](http://localhost:3000/admin)

---

## API Reference Summary

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/tickets` | Submit a ticket for AI triage with deduplication & fast-track |
| `GET` | `/api/tickets` | Query tickets with status, category, and keyword filters |
| `PATCH` | `/api/tickets/{id}/escalate` | Customer escalation: marks AI-resolved ticket as `ESCALATED` |
| `GET` | `/api/admin/metrics` | Returns `{ pending_review, human_resolved, total_tickets }` |
| `GET` | `/api/admin/tickets` | Admin search & filter query table |
| `PATCH` | `/api/admin/tickets/{id}/resolve`| Admin resolution: marks ticket as `HUMAN_RESOLVED` with timestamp |