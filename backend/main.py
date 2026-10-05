from pathlib import Path
from typing import List, Optional
import aiosqlite
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import triage_ticket

DB_PATH = Path(__file__).parent / "tickets.db"

app = FastAPI(
    title="BoxnFreight Triage API",
    version="1.0.0",
    description="Backend API for BoxnFreight ticket triage and FAQs.",
)

# Enable CORS middleware
app.add_middleware(
    CORSMiddleware,
   allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://boxnfreight-triage.vercel.app",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TicketCreate(BaseModel):
    title: str
    description: str


class TriageResponse(BaseModel):
    id: Optional[int] = None
    status: str
    category: str
    answer: Optional[str] = None
    agent_reason: str
    created_at: Optional[str] = None


@app.get("/")
async def health_check():
    return {
        "status": "healthy",
        "message": "BoxnFreight Triage API is running",
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
async def create_ticket(ticket: TicketCreate):
    """
    Accepts incoming support ticket (title and description),
    runs the AI triage agent asynchronously, saves ticket to tickets table in tickets.db asynchronously,
    and returns the triage result (status, category, answer, agent_reason).
    """
    triage_result = await triage_ticket(ticket.title, ticket.description, db_path=DB_PATH)

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO tickets (title, description, status, category, agent_reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                ticket.title,
                ticket.description,
                triage_result["status"],
                triage_result["category"],
                triage_result["agent_reason"],
            ),
        )
        ticket_id = cursor.lastrowid
        await db.commit()

    return {
        "id": ticket_id,
        "status": triage_result["status"],
        "category": triage_result["category"],
        "answer": triage_result.get("answer"),
        "agent_reason": triage_result["agent_reason"],
    }


@app.get("/tickets")
async def get_tickets(status: Optional[str] = None):
    """
    Fetches tickets asynchronously from tickets.db.
    Supports optional ?status= query parameter (e.g. ?status=ESCALATED)
    for admin escalation review, or returns all tickets if no status is specified.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if status:
            async with db.execute(
                """
                SELECT id, title, description, status, category, agent_reason, created_at
                FROM tickets
                WHERE status = ?
                ORDER BY id DESC
                """,
                (status,),
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute(
                """
                SELECT id, title, description, status, category, agent_reason, created_at
                FROM tickets
                ORDER BY id DESC
                """
            ) as cursor:
                rows = await cursor.fetchall()

        return [dict(row) for row in rows]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
