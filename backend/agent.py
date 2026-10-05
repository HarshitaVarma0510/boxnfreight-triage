import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiosqlite
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

DB_PATH = Path(__file__).parent / "tickets.db"

BRD_CATEGORIES = [
    "Account & Onboarding",
    "Shipment Booking",
    "LR (Lorry Receipt) Generation",
    "LR & Shipment Tracking",
    "Pricing, Quotes & Payments",
    "Documentation & Compliance",
    "Delivery & Proof of Delivery",
    "Claims, Damage & Insurance",
    "Cancellations & Refunds",
    "Support, Escalation & Account Management",
]


class TriageDecision(BaseModel):
    category: str = Field(
        description="One of the official BoxNFreight BRD categories."
    )
    status: str = Field(
        description="'RESOLVED' if the ticket is answered with high confidence using an FAQ, or 'ESCALATED' if ambiguous, complex, or outside FAQ scope."
    )
    answer: Optional[str] = Field(
        default=None,
        description="The accurate FAQ answer if RESOLVED. A helpful default message or empty if ESCALATED.",
    )
    agent_reason: str = Field(
        description="Reasoning explaining the FAQ match or why human review is required."
    )


async def get_all_faqs(db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """Fetch all 50 FAQs asynchronously from the SQLite database."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, category, question, answer FROM faqs ORDER BY id ASC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def _call_gemini_triage(
    title: str, description: str, faqs: List[Dict[str, Any]], api_key: str
) -> Dict[str, Any]:
    """Evaluate ticket asynchronously using Google Gemini model gemini-2.5-flash via google-genai async client."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    faqs_formatted = "\n\n".join(
        [
            f"[FAQ #{f['id']}] Category: {f['category']}\nQuestion: {f['question']}\nAnswer: {f['answer']}"
            for f in faqs
        ]
    )

    categories_list = "\n".join([f"- {cat}" for cat in BRD_CATEGORIES])

    system_instruction = f"""You are the official BoxNFreight AI Support Ticket Triage Agent.
Your role is to evaluate incoming support tickets against the 50 official BoxNFreight FAQs and categorize them.

OFFICIAL BRD CATEGORIES:
{categories_list}

DECISION RULES:
1. High Confidence Match (status = "RESOLVED"):
   - Set status to 'RESOLVED' ONLY if the ticket is clearly and directly answered by one of the 50 FAQs.
   - Provide the exact/accurate FAQ answer in 'answer'.
   - State the matched FAQ and why in 'agent_reason'.

2. Escalation Required (status = "ESCALATED"):
   - Set status to 'ESCALATED' if the ticket is ambiguous, missing required details (e.g. LR number, invoice ID, specific error), describes a dispute, billing discrepancy, active delay/accident, or falls outside the scope of the 50 FAQs.
   - Provide a helpful default note in 'answer' (e.g. "Your ticket has been escalated to our human support team for manual review and resolution.").
   - Provide a clear, actionable explanation in 'agent_reason' detailing why human review is required.
   - DO NOT hallucinate, guess policies, or fabricate shipment details.

Category MUST be selected from the exact list of BRD categories above.
"""

    prompt = f"""Incoming Ticket:
Title: {title}
Description: {description}

Reference FAQs (50 total):
{faqs_formatted}
"""

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=TriageDecision,
        temperature=0.0,
    )

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config,
        )
    except Exception:
        # If gemini-2.5-flash is unavailable or deprecated, use gemini-1.5-flash
        response = await client.aio.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config=config,
        )

    result = response.parsed.model_dump()
    return result


def _tokenize(text: str) -> set:
    """Helper to tokenize and normalize words."""
    words = re.findall(r"\w+", text.lower())
    stop_words = {
        "a", "an", "the", "in", "on", "at", "for", "to", "of", "and", "or", "is",
        "are", "was", "my", "your", "i", "we", "can", "how", "what", "do", "does",
        "it", "with", "from", "be", "this", "that"
    }
    return {w for w in words if w not in stop_words and len(w) > 1}


def _fallback_heuristic_triage(
    title: str, description: str, faqs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Fallback deterministic triage engine used when GEMINI_API_KEY is not set.
    Allows testing, CI verification, and graceful degradation without crashing.
    """
    text = f"{title} {description}".lower()
    ticket_tokens = _tokenize(text)

    # Detect ambiguity or dispute triggers that require human escalation
    ambiguous_keywords = [
        "stuck", "urgent", "wrong amount", "charged twice", "where is", "help me",
        "accident", "broken", "driver refused to", "dispute", "investigate", "lost cargo",
        "stolen", "missing item", "compensation", "escalate", "agent", "refund not received",
        "something went wrong", "not working", "please help", "issue with"
    ]
    is_ambiguous = any(ak in text for ak in ambiguous_keywords) or len(ticket_tokens) < 3

    best_faq = None
    best_score = 0.0

    for faq in faqs:
        q_tokens = _tokenize(faq["question"])
        if not q_tokens:
            continue
        intersection = ticket_tokens.intersection(q_tokens)
        score = len(intersection) / len(q_tokens)

        # Boost score if question phrases match closely
        if faq["question"].lower() in text or text in faq["question"].lower():
            score += 0.5

        if score > best_score:
            best_score = score
            best_faq = faq

    # Determine primary category
    category_scores: Dict[str, int] = {cat: 0 for cat in BRD_CATEGORIES}
    for cat in BRD_CATEGORIES:
        cat_tokens = _tokenize(cat)
        category_scores[cat] += len(ticket_tokens.intersection(cat_tokens)) * 2

    if best_faq:
        category_scores[best_faq["category"]] += 3

    predicted_category = max(category_scores, key=category_scores.get)
    if category_scores[predicted_category] == 0 and best_faq:
        predicted_category = best_faq["category"]
    elif category_scores[predicted_category] == 0:
        predicted_category = "Support, Escalation & Account Management"

    # High confidence threshold for auto-resolution
    if best_faq and best_score >= 0.45 and not is_ambiguous:
        return {
            "status": "RESOLVED",
            "category": best_faq["category"],
            "answer": best_faq["answer"],
            "agent_reason": f"High confidence match with FAQ #{best_faq['id']} ('{best_faq['question']}'). Resolved based on high confidence FAQ match.",
        }
    else:
        reason = (
            "Ticket is ambiguous or requires account/operational inspection by a human agent."
            if is_ambiguous
            else "Query could not be answered with high confidence from the 50 FAQs. Escalated for human review."
        )
        return {
            "status": "ESCALATED",
            "category": predicted_category,
            "answer": "Your ticket has been escalated to our human support team for manual review and resolution.",
            "agent_reason": reason,
        }


async def triage_ticket(
    title: str, description: str, db_path: Path = DB_PATH
) -> Dict[str, Any]:
    """
    Main asynchronous triage entry point:
    1. Fetch all 50 FAQs from tickets.db asynchronously.
    2. Check for GEMINI_API_KEY.
    3. Evaluate using gemini-2.5-flash asynchronously if available, or fallback engine if key is not configured.
    """
    faqs = await get_all_faqs(db_path)
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if api_key and api_key.strip() and not api_key.strip().startswith("your_"):
        try:
            return await _call_gemini_triage(title, description, faqs, api_key.strip())
        except Exception as e:
            # If the Gemini API call encounters an error (e.g. 503 or network issue),
            # fall back gracefully without leaking raw technical error messages into agent_reason.
            print(f"[Warning] Gemini API call failed: {e}. Falling back to rule-based triage.")
            return _fallback_heuristic_triage(title, description, faqs)
    else:
        return _fallback_heuristic_triage(title, description, faqs)


def triage_ticket_sync(
    title: str, description: str, db_path: Path = DB_PATH
) -> Dict[str, Any]:
    """Synchronous helper wrapper for triage_ticket."""
    import asyncio
    return asyncio.run(triage_ticket(title, description, db_path))


if __name__ == "__main__":
    import asyncio

    async def main():
        print("Testing triage_ticket asynchronously...")
        test_faq = await triage_ticket(
            "Business Account Creation",
            "How do I create a BoxNFreight business account?",
        )
        print("Sample Clear FAQ Result:", test_faq)

        test_ambiguous = await triage_ticket(
            "Issue with shipment",
            "My shipment has a big problem, please fix this right now!",
        )
        print("Sample Ambiguous Result:", test_ambiguous)

    asyncio.run(main())
