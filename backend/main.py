from datetime import datetime
import hashlib
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import aiosqlite
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import (
    DB_PATH,
    triage_ticket,
    is_conversational_greeting,
    is_gibberish_or_spam,
    _call_gemini_conversational_greeting,
)

# Setup logger
logger = logging.getLogger("boxnfreight.api")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(
    title="BoxnFreight Triage SaaS API",
    version="2.1.0",
    description="Resilient AI Support Ticket Triage and Admin Management API for BoxnFreight.",
)

# Enable CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TicketCreate(BaseModel):
    category: Optional[str] = "Other / General Inquiry (Custom query or general help)"
    description: str
    title: Optional[str] = None  # Optional for backwards compatibility


class TriageResponse(BaseModel):
    id: Optional[int] = None
    reference_id: Optional[str] = None
    ticket_id: Optional[str] = None
    status: str
    category: str
    answer: Optional[str] = None
    resolution_guidance: Optional[str] = None
    agent_reason: Optional[str] = None
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None
    is_idempotent: bool = False
    notice: Optional[str] = None
    is_conversational: bool = False


def compute_query_hash(category: Optional[str], description: str) -> str:
    """
    Generate deterministic SHA-256 hash for deduplication based primarily on normalized query text.
    Selecting a different dropdown category for the exact same user question produces the identical hash,
    preventing duplicate ticket records, contradictory triage states, and cache bypasses.
    """
    normalized_desc = " ".join(re.findall(r"\w+", description.lower()))
    if not normalized_desc:
        normalized_cat = (category or "").strip().lower()
        normalized_desc = f"{normalized_cat}::{description.strip().lower()}"
    return hashlib.sha256(normalized_desc.encode("utf-8")).hexdigest()



async def init_db_schema():
    """Ensure database schema, required lifecycle columns, and indexes are up to date."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference_id TEXT,
                category TEXT,
                description TEXT,
                title TEXT,
                status TEXT,
                answer TEXT,
                agent_reason TEXT,
                query_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP DEFAULT NULL
            )
            """
        )

        async with db.execute("PRAGMA table_info(tickets)") as cursor:
            existing_cols = {row[1] for row in await cursor.fetchall()}

        if "reference_id" not in existing_cols:
            await db.execute("ALTER TABLE tickets ADD COLUMN reference_id TEXT")
        if "answer" not in existing_cols:
            await db.execute("ALTER TABLE tickets ADD COLUMN answer TEXT")
        if "query_hash" not in existing_cols:
            await db.execute("ALTER TABLE tickets ADD COLUMN query_hash TEXT")
        if "resolved_at" not in existing_cols:
            await db.execute("ALTER TABLE tickets ADD COLUMN resolved_at TIMESTAMP DEFAULT NULL")

        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_tickets_query_hash ON tickets(query_hash, created_at)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)"
        )

        # Purge any spam, gibberish, or conversational greeting test tickets
        await db.execute(
            """
            DELETE FROM tickets
            WHERE description LIKE '%jhhhhh%'
               OR description LIKE '%khflivfly%'
               OR category = 'Conversational Greeting / Inquiry'
               OR LENGTH(TRIM(description)) < 4
            """
        )

        # Secondary heuristic check: Purge any remaining gibberish tickets
        async with db.execute("SELECT id, description FROM tickets") as cursor:
            all_rows = await cursor.fetchall()
            gibberish_ids = [row[0] for row in all_rows if is_gibberish_or_spam(row[1])]
            if gibberish_ids:
                placeholders = ",".join("?" for _ in gibberish_ids)
                await db.execute(f"DELETE FROM tickets WHERE id IN ({placeholders})", gibberish_ids)
                logger.info(f"Purged {len(gibberish_ids)} legacy gibberish tickets: {gibberish_ids}")

        await db.commit()


@app.on_event("startup")
async def on_startup():
    await init_db_schema()


@app.get("/")
async def health_check():
    return {
        "status": "healthy",
        "service": "BoxnFreight AI Triage SaaS API",
        "version": "2.1.0",
    }


@app.get("/faqs")
async def get_faqs():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, category, question, answer FROM faqs ORDER BY id ASC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


@app.post("/tickets", response_model=TriageResponse)
@app.post("/api/tickets", response_model=TriageResponse)
async def create_ticket(ticket: TicketCreate):
    """
    Accepts incoming support ticket (category and description).
    1. Zero-Persistence Greeting Detection:
       Detects pure conversational greetings/queries (e.g., 'hello', 'good morning', 'how are you', 'who are you')
       before database persistence:
       - Returns warm, context-aware AI greeting response without failing.
       - Does NOT execute any SQLite INSERT query into the tickets table.
       - Does NOT generate a ticket ID (#TKT-xxxx) or persist this interaction in the database.
       - Sets ticket_id: null and is_conversational: true in the API response payload.
    2. Checks for deduplication via deterministic SHA-256 hash and 5-minute cooldown window.
    3. Runs AI triage (acronym fast-track matching, multi-key pool, heuristic fallback).
    4. Persists actionable ticket records with unique readable reference ID (#TKT-<id>).
    """
    description = ticket.description.strip()
    if not description:
        raise HTTPException(status_code=400, detail="Description is required and cannot be empty.")

    category = (ticket.category or "Other / General Inquiry (Custom query or general help)").strip()
    title = ticket.title.strip() if ticket.title else description[:80]

    # 0. ZERO-PERSISTENCE FOR GIBBERISH / MEANINGLESS SPAM QUERIES
    if is_gibberish_or_spam(description):
        logger.info(f"Gibberish / meaningless input detected for '{description}'. Returning zero-persistence INVALID response.")
        invalid_guidance = (
            "We could not understand your inquiry. Please describe your logistics issue clearly "
            "(e.g., provide your LR number, delivery status request, or billing question) to submit a support ticket."
        )
        return {
            "id": None,
            "reference_id": None,
            "ticket_id": None,
            "status": "INVALID",
            "category": "Invalid Inquiry",
            "answer": invalid_guidance,
            "resolution_guidance": invalid_guidance,
            "agent_reason": "Meaningless input or spam query detected. Discarded without database persistence.",
            "created_at": None,
            "resolved_at": None,
            "is_idempotent": False,
            "notice": None,
            "is_conversational": True,
        }

    # 1. ZERO-PERSISTENCE FOR PURE GREETINGS
    if is_conversational_greeting(description):
        logger.info(f"Pure conversational greeting detected for '{description}'. Returning zero-persistence AI response.")
        dynamic_answer = await _call_gemini_conversational_greeting(description)
        return {
            "id": None,
            "reference_id": None,
            "ticket_id": None,
            "status": "CONVERSATIONAL",
            "category": "Conversational Greeting / Inquiry",
            "answer": dynamic_answer,
            "resolution_guidance": dynamic_answer,
            "agent_reason": "Dynamic conversational greeting handled by Virtual Assistant (zero-persistence).",
            "created_at": None,
            "resolved_at": None,
            "is_idempotent": False,
            "notice": None,
            "is_conversational": True,
        }

    query_hash = compute_query_hash(category, description)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Check for duplicate ticket within the 5-minute (300 seconds) cooldown window
        async with db.execute(
            """
            SELECT id, reference_id, category, description, title, status, answer, agent_reason, created_at, resolved_at
            FROM tickets
            WHERE query_hash = ?
              AND (strftime('%s', 'now') - strftime('%s', created_at)) < 300
            ORDER BY id DESC
            LIMIT 1
            """,
            (query_hash,),
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            ref_id = existing["reference_id"] or f"#TKT-{1000 + existing['id']}"
            logger.info(f"Deduplication hit for ticket #{existing['id']} ({ref_id}). Returning idempotent record.")
            return {
                "id": existing["id"],
                "reference_id": ref_id,
                "ticket_id": ref_id,
                "status": existing["status"],
                "category": existing["category"],
                "answer": existing["answer"],
                "resolution_guidance": existing["answer"],
                "agent_reason": existing["agent_reason"],
                "created_at": existing["created_at"],
                "resolved_at": existing["resolved_at"],
                "is_idempotent": True,
                "notice": "Existing ticket returned (idempotent submission within 5-minute cooldown window).",
                "is_conversational": False,
            }

        # Run AI triage agent
        triage_result = await triage_ticket(category, description, db_path=DB_PATH)

        # Check if triage agent flagged as conversational or invalid
        if triage_result.get("is_conversational") or triage_result.get("status") == "INVALID":
            logger.info(f"Triage agent flagged '{description}' as {triage_result.get('status')}. Returning zero-persistence AI response.")
            ans = triage_result.get("answer") or triage_result.get("resolution_guidance")
            return {
                "id": None,
                "reference_id": None,
                "ticket_id": None,
                "status": triage_result.get("status", "CONVERSATIONAL"),
                "category": triage_result.get("category", "Invalid Inquiry" if triage_result.get("status") == "INVALID" else "Conversational Greeting / Inquiry"),
                "answer": ans,
                "resolution_guidance": ans,
                "agent_reason": triage_result.get("agent_reason", "Zero-persistence response handled by Virtual Assistant."),
                "created_at": None,
                "resolved_at": None,
                "is_idempotent": False,
                "notice": None,
                "is_conversational": True,
            }

        final_status = triage_result["status"]
        final_category = triage_result.get("category") or category
        final_answer = triage_result.get("answer")
        agent_reason = triage_result.get("agent_reason", "")

        now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        resolved_at = now_utc if final_status in ("RESOLVED_BY_AI", "CONVERSATIONAL") else None

        cursor = await db.execute(
            """
            INSERT INTO tickets (category, description, title, status, answer, agent_reason, query_hash, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                final_category,
                description,
                title,
                final_status,
                final_answer,
                agent_reason,
                query_hash,
                resolved_at,
            ),
        )
        ticket_id = cursor.lastrowid
        reference_id = f"#TKT-{1000 + ticket_id}"

        # Store generated reference_id
        await db.execute(
            "UPDATE tickets SET reference_id = ? WHERE id = ?",
            (reference_id, ticket_id),
        )
        await db.commit()

        # Fetch inserted row with server created_at timestamp
        async with db.execute(
            "SELECT created_at, resolved_at FROM tickets WHERE id = ?",
            (ticket_id,),
        ) as cur:
            row = await cur.fetchone()
            created_at = row["created_at"] if row else now_utc

    return {
        "id": ticket_id,
        "reference_id": reference_id,
        "ticket_id": reference_id,
        "status": final_status,
        "category": final_category,
        "answer": final_answer,
        "agent_reason": agent_reason,
        "created_at": created_at,
        "resolved_at": resolved_at,
        "is_idempotent": False,
        "notice": None,
        "is_conversational": False,
    }


@app.get("/tickets")
@app.get("/api/tickets")
async def get_tickets(
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = Query(None, alias="q"),
):
    """
    Fetches tickets from tickets.db with unified status filtering:
    - 'NEEDS_HUMAN': ONLY actionable support tickets requiring manual staff intervention
    - 'USER_ESCALATED': priority queue of users who clicked 'Talk to an Agent'
    - 'RESOLVED_BY_AI': resolved automatically by AI or conversational virtual assistant
    - 'HUMAN_RESOLVED': resolved by admin staff
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        query = (
            "SELECT id, reference_id, title, description, status, category, answer, agent_reason, created_at, resolved_at "
            "FROM tickets WHERE 1=1"
        )
        params: List[Any] = []

        if status and status.upper() != "ALL":
            st = status.upper()
            if st in ("NEEDS_HUMAN", "ESCALATED"):
                # ONLY actionable support tickets requiring manual staff intervention
                query += " AND status IN ('NEEDS_HUMAN', 'ESCALATED')"
            elif st in ("RESOLVED", "RESOLVED_BY_AI"):
                query += " AND status IN ('RESOLVED_BY_AI', 'CONVERSATIONAL')"
            else:
                query += " AND status = ?"
                params.append(status)

        if category and category.upper() != "ALL":
            query += " AND category LIKE ?"
            params.append(f"%{category}%")

        if search and search.strip():
            term = f"%{search.strip()}%"
            query += (
                " AND (reference_id LIKE ? "
                "OR ('#TKT-' || (1000 + id)) LIKE ? "
                "OR description LIKE ? "
                "OR title LIKE ? "
                "OR agent_reason LIKE ? "
                "OR answer LIKE ?)"
            )
            params.extend([term, term, term, term, term, term])

        query += " ORDER BY id DESC"

        async with db.execute(query, tuple(params)) as cursor:
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                d = dict(row)
                if not d.get("reference_id") and d.get("id"):
                    d["reference_id"] = f"#TKT-{1000 + d['id']}"
                results.append(d)
            return results


@app.patch("/tickets/{ticket_id}/escalate")
@app.post("/tickets/{ticket_id}/escalate")
@app.patch("/api/tickets/{ticket_id}/escalate")
@app.post("/api/tickets/{ticket_id}/escalate")
async def escalate_ticket_user(ticket_id: int):
    """
    'Talk to an Agent' Action:
    Immediately updates ticket status to 'USER_ESCALATED'
    and assigns it to the priority specialist human queue.
    Pure conversational greetings cannot be escalated.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, category, description FROM tickets WHERE id = ?", (ticket_id,)) as cursor:
            ticket_row = await cursor.fetchone()
            if not ticket_row:
                raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found.")

        # Prevent pure greetings from being escalated to human staff
        if ticket_row["category"] == "Conversational Greeting / Inquiry":
            raise HTTPException(
                status_code=400,
                detail="Conversational greetings cannot be escalated to human agents. Please provide shipment or issue details first."
            )

        await db.execute(
            """
            UPDATE tickets
            SET status = 'USER_ESCALATED',
                resolved_at = NULL,
                agent_reason = 'User explicitly clicked "Talk to an Agent" - assigned to priority support specialist queue.'
            WHERE id = ?
            """,
            (ticket_id,),
        )
        await db.commit()

        async with db.execute(
            "SELECT id, reference_id, category, description, title, status, answer, agent_reason, created_at, resolved_at FROM tickets WHERE id = ?",
            (ticket_id,),
        ) as cursor:
            row = await cursor.fetchone()
            d = dict(row)
            if not d.get("reference_id"):
                d["reference_id"] = f"#TKT-{1000 + d['id']}"
            return {"success": True, "ticket": d}


# ==========================================
# ADMIN API ENDPOINTS
# ==========================================


@app.get("/api/admin/metrics")
@app.get("/admin/metrics")
async def get_admin_metrics():
    """
    Admin KPI Summary Endpoint:
    Returns counts for:
      - needs_review: count(status IN ('NEEDS_HUMAN', 'ESCALATED')) [actionable issues only]
      - user_escalated: count(status == 'USER_ESCALATED')
      - resolved: count(status IN ('RESOLVED_BY_AI', 'CONVERSATIONAL', 'HUMAN_RESOLVED'))
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Actionable manual review queue (ONLY actionable support tickets requiring manual staff intervention)
        async with db.execute(
            "SELECT COUNT(*) FROM tickets WHERE status IN ('NEEDS_HUMAN', 'ESCALATED')"
        ) as c1:
            needs_review = (await c1.fetchone())[0]

        # Priority User Escalated queue ('Talk to an Agent')
        async with db.execute(
            "SELECT COUNT(*) FROM tickets WHERE status = 'USER_ESCALATED'"
        ) as c2:
            user_escalated = (await c2.fetchone())[0]

        # Human resolved
        async with db.execute(
            "SELECT COUNT(*) FROM tickets WHERE status = 'HUMAN_RESOLVED'"
        ) as c3:
            human_resolved = (await c3.fetchone())[0]

        # AI resolved (includes auto-closed conversational greetings and instant FAQ answers)
        async with db.execute(
            "SELECT COUNT(*) FROM tickets WHERE status IN ('RESOLVED_BY_AI', 'CONVERSATIONAL')"
        ) as c4:
            ai_resolved = (await c4.fetchone())[0]

        # Total tickets
        async with db.execute("SELECT COUNT(*) FROM tickets") as c5:
            total_tickets = (await c5.fetchone())[0]

        resolved = human_resolved + ai_resolved

        return {
            "needs_review": needs_review,
            "user_escalated": user_escalated,
            "resolved": resolved,
            "pending_review": needs_review + user_escalated,
            "human_resolved": human_resolved,
            "ai_resolved": ai_resolved,
            "total_tickets": total_tickets,
        }


@app.get("/api/admin/tickets")
@app.get("/admin/tickets")
async def get_admin_tickets(
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = Query(None, alias="q"),
):
    """
    Admin Management Table Endpoint:
    Supports filtering by tab status ('NEEDS_HUMAN', 'USER_ESCALATED', 'RESOLVED_BY_AI')
    and text search.
    """
    return await get_tickets(status=status, category=category, search=search)


@app.patch("/api/admin/tickets/{ticket_id}/resolve")
@app.patch("/admin/tickets/{ticket_id}/resolve")
async def resolve_ticket_admin(ticket_id: int):
    """
    Admin Action:
    One-click 'Mark as Resolved' that updates ticket status to 'HUMAN_RESOLVED'
    and sets the resolved_at timestamp.
    """
    now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,)) as cursor:
            existing = await cursor.fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found.")

        await db.execute(
            """
            UPDATE tickets
            SET status = 'HUMAN_RESOLVED',
                resolved_at = ?
            WHERE id = ?
            """,
            (now_utc, ticket_id),
        )
        await db.commit()

        async with db.execute(
            "SELECT id, reference_id, category, description, title, status, answer, agent_reason, created_at, resolved_at FROM tickets WHERE id = ?",
            (ticket_id,),
        ) as cursor:
            row = await cursor.fetchone()
            d = dict(row)
            if not d.get("reference_id"):
                d["reference_id"] = f"#TKT-{1000 + d['id']}"
            return {"success": True, "ticket": d}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, app_dir=str(Path(__file__).parent))
