import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiosqlite
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Setup logger
logger = logging.getLogger("boxnfreight.agent")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

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

# The 10 User-Facing Business Categories (with in-bracket hints for non-technical users)
BUSINESS_CATEGORIES = [
    "Shipment Tracking (Track consignment, ETA, delay status)",
    "Proof of Delivery (POD / Signed copy download)",
    "Lorry Receipt / Bilty (LR copy, LR status, consignment note)",
    "Freight Booking & Orders (New vehicle placement, capacity)",
    "Billing & Invoicing (Freight bills, GST invoice, credit notes)",
    "Payment & Outstanding (Ledger balance, payment reconciliation)",
    "Transit Damage & Claims (Damaged goods, insurance claims, shortage)",
    "Driver & Vehicle Details (Driver number, truck GPS location)",
    "Account & Portal Access (Login, password reset, user roles)",
    "Other / General Inquiry (Custom query or general help)",
]

# Mapping from business categories and prefixes to official BRD operational categories
INTAKE_CATEGORY_MAPPING = {
    # 1. Shipment Tracking
    "Shipment Tracking": ["LR & Shipment Tracking"],
    "Shipment Tracking (Track consignment, ETA, delay status)": ["LR & Shipment Tracking"],
    # 2. Proof of Delivery
    "Proof of Delivery": ["Delivery & Proof of Delivery"],
    "Proof of Delivery (POD / Signed copy download)": ["Delivery & Proof of Delivery"],
    # 3. Lorry Receipt / Bilty
    "Lorry Receipt / Bilty": ["LR (Lorry Receipt) Generation", "LR & Shipment Tracking"],
    "Lorry Receipt / Bilty (LR copy, LR status, consignment note)": ["LR (Lorry Receipt) Generation", "LR & Shipment Tracking"],
    # 4. Freight Booking & Orders
    "Freight Booking & Orders": ["Shipment Booking", "Cancellations & Refunds"],
    "Freight Booking & Orders (New vehicle placement, capacity)": ["Shipment Booking", "Cancellations & Refunds"],
    # 5. Billing & Invoicing
    "Billing & Invoicing": ["Pricing, Quotes & Payments", "Documentation & Compliance"],
    "Billing & Invoicing (Freight bills, GST invoice, credit notes)": ["Pricing, Quotes & Payments", "Documentation & Compliance"],
    # 6. Payment & Outstanding
    "Payment & Outstanding": ["Pricing, Quotes & Payments"],
    "Payment & Outstanding (Ledger balance, payment reconciliation)": ["Pricing, Quotes & Payments"],
    # 7. Transit Damage & Claims
    "Transit Damage & Claims": ["Claims, Damage & Insurance"],
    "Transit Damage & Claims (Damaged goods, insurance claims, shortage)": ["Claims, Damage & Insurance"],
    # 8. Driver & Vehicle Details
    "Driver & Vehicle Details": ["LR & Shipment Tracking", "Support, Escalation & Account Management"],
    "Driver & Vehicle Details (Driver number, truck GPS location)": ["LR & Shipment Tracking", "Support, Escalation & Account Management"],
    # 9. Account & Portal Access
    "Account & Portal Access": ["Account & Onboarding"],
    "Account & Portal Access (Login, password reset, user roles)": ["Account & Onboarding"],
    # 10. Other / General Inquiry
    "Other / General Inquiry": ["Support, Escalation & Account Management"],
    "Other / General Inquiry (Custom query or general help)": ["Support, Escalation & Account Management"],
    "Conversational Greeting / Inquiry": ["Support, Escalation & Account Management"],
    # Legacy fallbacks
    "Shipment & Tracking (POD / LR)": ["LR & Shipment Tracking", "Delivery & Proof of Delivery"],
    "Booking & Orders": ["Shipment Booking"],
    "Billing & Invoices": ["Pricing, Quotes & Payments"],
    "Account & Login": ["Account & Onboarding"],
    "General Inquiry": ["Support, Escalation & Account Management"],
}


def get_gemini_api_keys() -> List[str]:
    """
    Extensible API key pool read from environment variables.
    Supports:
      1. GEMINI_API_KEYS (comma-separated list)
      2. GEMINI_API_KEY_PRIMARY, GEMINI_API_KEY_SECONDARY, GEMINI_API_KEY_TERTIARY
      3. Legacy GEMINI_API_KEY or GOOGLE_API_KEY
    Deduplicates keys while preserving order, and filters out placeholders and empty strings.
    """
    raw_keys: List[str] = []

    keys_csv = os.getenv("GEMINI_API_KEYS", "")
    if keys_csv:
        for k in keys_csv.split(","):
            raw_keys.append(k.strip())

    for var_name in [
        "GEMINI_API_KEY_PRIMARY",
        "GEMINI_API_KEY_SECONDARY",
        "GEMINI_API_KEY_TERTIARY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
    ]:
        val = os.getenv(var_name, "").strip()
        if val:
            raw_keys.append(val)

    valid_keys: List[str] = []
    seen = set()
    for k in raw_keys:
        if not k:
            continue
        k_lower = k.lower()
        if k_lower.startswith("your_") or k_lower.startswith("your-") or "<" in k:
            continue
        if k not in seen:
            seen.add(k)
            valid_keys.append(k)

    return valid_keys


class TriageDecision(BaseModel):
    category: str = Field(
        description="One of the official BoxNFreight BRD categories."
    )
    status: str = Field(
        description="'RESOLVED_BY_AI' if clearly and directly answered from FAQs, or 'NEEDS_HUMAN' if ambiguous, complex, dispute, or outside FAQ scope."
    )
    answer: Optional[str] = Field(
        default=None,
        description="Detailed point-by-point structured bullet answer if RESOLVED_BY_AI, or helpful guidance note if NEEDS_HUMAN.",
    )
    agent_reason: str = Field(
        description="Clear explanation of the match or reason for human escalation."
    )


async def get_all_faqs(db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """Fetch all 50 FAQs asynchronously from SQLite."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, category, question, answer FROM faqs ORDER BY id ASC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


KEYBOARD_ROWS = [
    "qwertyuiop",
    "asdfghjkl",
    "zxcvbnm",
    "poiuytrewq",
    "lkjhgfdsa",
    "mnbvcxz",
    "1234567890",
    "0987654321",
    "qazwsxedcrfvtgbyhnujmikolp",
]

COMMON_WORDS = {
    "i", "a", "to", "the", "is", "in", "it", "you", "that", "he", "was", "for", "on", "are", "with",
    "as", "at", "be", "this", "have", "from", "or", "one", "had", "by", "word", "but", "not", "what",
    "all", "were", "we", "when", "your", "can", "said", "there", "use", "an", "each", "which", "she",
    "do", "how", "their", "if", "will", "up", "other", "about", "out", "many", "then", "them", "these",
    "so", "some", "her", "would", "make", "like", "him", "into", "time", "has", "look", "two", "more",
    "write", "go", "see", "number", "no", "way", "could", "people", "my", "than", "first", "water",
    "been", "call", "who", "oil", "its", "now", "find", "long", "down", "day", "did", "get", "come",
    "made", "may", "part", "over", "new", "sound", "take", "only", "little", "work", "know", "place",
    "year", "live", "me", "back", "give", "most", "very", "after", "thing", "our", "just", "name",
    "good", "sentence", "man", "think", "say", "great", "where", "help", "through", "much", "before",
    "line", "right", "too", "means", "old", "any", "same", "tell", "boy", "follow", "came", "want",
    "show", "also", "around", "farm", "three", "small", "set", "put", "end", "does", "another",
    "well", "large", "must", "big", "even", "such", "because", "turn", "here", "why", "ask", "went",
    "men", "read", "need", "different", "home", "us", "move", "try", "kind", "hand", "picture",
    "again", "change", "off", "play", "spell", "air", "away", "house", "point", "page", "letter",
    "mother", "answer", "found", "study", "still", "learn", "should", "world", "high",
    "every", "near", "add", "food", "between", "own", "below", "country", "plant", "last", "school",
    "father", "keep", "tree", "never", "start", "city", "earth", "eye", "light", "thought", "head",
    "under", "story", "saw", "left", "dont", "few", "while", "along", "might", "close", "something",
    "seem", "next", "hard", "open", "example", "begin", "life", "always", "those", "both", "paper",
    "together", "got", "group", "often", "run", "important", "until", "children", "side", "feet",
    "car", "mile", "night", "walk", "white", "sea", "began", "grow", "took", "river", "four", "carry",
    "state", "once", "book", "hear", "stop", "without", "second", "late", "miss", "idea", "enough",
    "eat", "face", "watch", "far", "indian", "really", "almost", "let", "above", "girl", "sometimes",
    "cut", "young", "talk", "soon", "list", "song", "being", "leave", "family",
    # Greetings & polite terms
    "hi", "hello", "hey", "greetings", "namaste", "morning", "afternoon", "evening", "thanks", "thank",
    "please", "pls", "welcome", "support", "team", "agent", "human", "representative", "sir", "madam",
    "ok", "okay", "yes", "no", "sure", "fine", "good", "bye", "yo", "sup",
    # Logistics domain terms
    "lr", "pod", "bilty", "track", "tracking", "shipment", "consignment", "freight", "cargo",
    "invoice", "billing", "bill", "payment", "paid", "unpaid", "outstanding", "balance", "ledger",
    "damage", "damaged", "transit", "claim", "insurance", "shortage", "loss", "lost", "delay", "delayed",
    "eta", "delivery", "deliver", "delivered", "consignee", "consignor", "shipper", "truck", "driver",
    "vehicle", "lorry", "container", "trailer", "booking", "order", "placement", "capacity", "advance",
    "rate", "rates", "quote", "quotation", "price", "pricing", "cost", "charge", "charges", "gst",
    "eway", "tax", "tds", "credit", "debit", "note", "refund", "cancellation", "cancel",
    "dispatch", "dispatched", "loaded", "unloaded", "hub", "warehouse", "origin", "destination",
    "route", "pickup", "toll", "permit", "fitness", "rc", "gps", "location", "phone", "number",
    "contact", "portal", "login", "password", "reset", "account", "register", "email", "kyc", "pan",
    "issue", "problem", "status", "dispute", "urgent", "help", "inquiry", "query", "check", "view",
    "download", "copy", "pdf", "original", "signed", "stamp", "details", "info", "information",
    "update", "service", "branch", "office", "head", "customer", "care", "executive", "call",
    "ftl", "ltl", "delhi", "mumbai", "bengaluru", "bangalore", "pune", "kolkata", "chennai", "hyderabad",
    "jaipur", "ahmedabad", "carton", "cartons", "box", "boxes", "pallet", "pallets", "weight", "ton", "tons",
    "detention", "demurrage", "unloading", "loading", "refused", "refusal", "address", "missing", "breakdown"
}


def is_gibberish_or_spam(text: str) -> bool:
    """
    Detects random keystrokes, repetitive characters, or meaningless spam queries
    (e.g., 'jhhhhh', 'khflivfly', 'asdfghjkl', strings without valid words or digits).
    Used to prevent junk spam tickets from entering the SQLite database or Admin queues.
    """
    if not text or not text.strip():
        return True

    raw = text.strip()

    # 1. Pure non-alphanumeric or single character
    alphanumeric = re.findall(r"[a-zA-Z0-9]", raw)
    if len(alphanumeric) < 2:
        return True

    # If the input is just 1-3 digits with no words (e.g. '12', '123')
    if raw.isdigit() and len(raw) < 4:
        return True

    # 2. Check for repeated single character (e.g. 'aaaaaa', 'jhhhhh', '11111')
    if re.search(r"(.)\1{3,}", raw.lower()):
        return True

    cleaned = re.sub(r"[^\w\s]", " ", raw.lower())
    words = [w for w in cleaned.split() if w]
    if not words:
        return True

    has_valid_identifier = bool(re.search(r"\b\d{4,}\b", raw))

    valid_word_count = 0
    gibberish_word_count = 0

    for word in words:
        if word.isdigit():
            if len(word) >= 4 or len(words) > 1:
                valid_word_count += 1
            else:
                gibberish_word_count += 1
            continue

        # Repetitive short pattern like 'asdasd', 'qweqwe'
        if len(word) >= 4 and re.match(r"^(.{2,4})\1+$", word):
            gibberish_word_count += 1
            continue

        # Keyboard walk substrings
        is_kb = False
        if len(word) >= 4:
            for kb in KEYBOARD_ROWS:
                if word in kb:
                    is_kb = True
                    break
        if is_kb:
            gibberish_word_count += 1
            continue

        # Check dictionary
        if word in COMMON_WORDS:
            valid_word_count += 1
            continue

        # Check vowel presence in alphabetic words of length >= 4
        vowels = set("aeiouy")
        word_letters = [c for c in word if c.isalpha()]
        if len(word_letters) >= 4 and not any(c in vowels for c in word_letters):
            gibberish_word_count += 1
            continue

        # Abnormal consonant clusters (4+ consecutive consonants in Latin script)
        if re.search(r"[bcdfghjklmnpqrstvwxz]{4,}", word):
            if not any(exc in word for exc in ["length", "strength", "catch", "match", "batch", "watch", "patch", "dispatch", "right", "weight", "flight", "consign"]):
                gibberish_word_count += 1
                continue

        gibberish_word_count += 1

    if valid_word_count == 0 and not has_valid_identifier:
        return True

    if gibberish_word_count > valid_word_count and valid_word_count == 0:
        return True

    return False


def is_conversational_greeting(text: str) -> bool:
    """
    Check if the user input is purely conversational / a greeting rather than a concrete logistics inquiry.
    Examples: "hello", "hi", "good morning", "good evening", "how are you", "what can you do", "who are you"
    """
    cleaned = re.sub(r"[^\w\s]", " ", text.strip().lower())
    words = [w for w in cleaned.split() if w]
    if not words:
        return False

    greeting_words = {
        "hi", "hello", "hey", "good", "morning", "afternoon", "evening",
        "day", "greetings", "howdy", "sup", "yo", "namaste", "hola",
        "there", "team", "support", "boxnfreight", "everyone", "all", "sir", "madam",
        "to", "you", "a", "very", "how", "are", "doing", "whats", "up", "what", "can",
        "who", "assist", "help", "today", "buddy", "bot", "assistant",
        "do", "for", "me", "i", "am", "please", "thanks", "thank", "nice", "meet",
        "fine", "well",
        # Hindi / Hinglish colloquial greeting tokens
        "kaise", "ho", "kya", "haal", "hai"
    }

    issue_words = {
        "track", "tracking", "pod", "lr", "lorry", "bilty", "receipt", "invoice", "payment",
        "bill", "billing", "shipment", "cargo", "order", "delivery", "delivered",
        "cancel", "cancellation", "refund", "claim", "damage", "booking", "book",
        "stuck", "delay", "delayed", "rate", "quote", "cost", "price", "eway", "gst",
        "account", "password", "login", "register", "signup", "problem", "damaged", "lost",
        "wrong", "dispute", "accident"
    }

    # If all tokens are conversational/greeting words
    if all(w in greeting_words for w in words):
        return True

    # If begins with a greeting and contains no concrete logistics issue words
    starts_greeting = (
        words[0] in {"hi", "hello", "hey", "greetings", "howdy", "namaste"}
        or (len(words) >= 2 and words[0] == "good" and words[1] in {"morning", "afternoon", "evening", "day"})
        or (len(words) >= 3 and words[0] == "how" and words[1] == "are" and words[2] in {"you", "things"})
        or (len(words) >= 4 and words[0] == "what" and words[1] == "can" and words[2] == "you" and words[3] == "do")
        or (len(words) >= 3 and words[0] == "who" and words[1] == "are" and words[2] == "you")
    )
    no_issues = not any(w in issue_words for w in words)
    has_large_number = bool(re.search(r"\b\d{4,}\b", text))

    if starts_greeting and no_issues and not has_large_number and len(words) <= 12:
        return True

    return False


def extract_greeting_salutation(text: str) -> Optional[str]:
    """
    Extract a warm, appropriate salutation if the user query contains a greeting.
    Prioritizes specific time-of-day greetings over generic greetings.
    """
    if not text:
        return None
    lower = text.lower()

    if re.search(r"\bgood\s+morning\b", lower):
        return "Good morning!"
    if re.search(r"\bgood\s+afternoon\b", lower):
        return "Good afternoon!"
    if re.search(r"\bgood\s+evening\b", lower):
        return "Good evening!"
    if re.search(r"\bgood\s+day\b", lower):
        return "Good day!"
    if re.search(r"\bnamaste\b", lower):
        return "Namaste!"
    if re.search(r"\b(how\s+are\s+you|how\s+are\s+things|how\s+do\s+you\s+do|hope\s+you\s+are\s+doing\s+well)\b", lower):
        return "Hello! Thank you for reaching out."
    if re.search(r"\b(hello|hi|hey|howdy|greetings)\b", lower):
        return "Hello!"

    return None


def polish_answer_with_greeting(answer: Optional[str], query: str) -> Optional[str]:
    """
    Ensure answers to composite queries with greetings are prefixed with a warm,
    contextual greeting (e.g., 'Good morning! To reset your password...'), avoiding
    blunt, dry responses while preserving exact verified details and professional tone.
    """
    if not answer or not answer.strip():
        return answer

    salutation = extract_greeting_salutation(query)
    if not salutation:
        return answer

    stripped_ans = answer.strip()
    lower_ans = stripped_ans.lower()

    # Avoid duplicate greeting if the answer already starts with a salutation
    greeting_starters = (
        "hello", "hi", "hey", "good morning", "good afternoon",
        "good evening", "good day", "namaste", "welcome", "greetings"
    )
    if any(lower_ans.startswith(starter) for starter in greeting_starters):
        return stripped_ans

    # If the answer starts with bullet points or numbers, separate cleanly
    if stripped_ans.startswith(("-", "*", "•", "1.", "1)")):
        return f"{salutation}\n\n{stripped_ans}"

    return f"{salutation} {stripped_ans}"


async def _call_gemini_conversational_greeting(user_query: str) -> str:
    """
    Invokes the Gemini LLM with a dedicated conversational prompt to dynamically
    respond to greetings in a warm, contextual manner.
    """
    api_keys = get_gemini_api_keys()

    system_instruction = (
        "You are the BoxnFreight Logistics Virtual Assistant. "
        "The customer just reached out with a greeting or conversational inquiry. "
        "Respond naturally, warmly, and contextually to their specific greeting "
        "(e.g., echo 'Good morning' if they said good morning, respond politely if they asked how you are doing). "
        "Briefly explain that you assist with BoxnFreight logistics (tracking, POD, LR, billing, freight booking), "
        "and politely invite them to provide their tracking/LR number or issue details. "
        "Keep it within 2-3 friendly sentences."
    )

    prompt = f"The customer just said: '{user_query}'"

    for idx, key in enumerate(api_keys):
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=key)
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
                max_output_tokens=220,
            )

            try:
                response = await client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=config,
                )
            except Exception as e:
                err_str = str(e).lower()
                if "not_found" in err_str or "no longer available" in err_str or "404" in err_str:
                    response = await client.aio.models.generate_content(
                        model="gemini-3.8-flash",
                        contents=prompt,
                        config=config,
                    )
                else:
                    raise

            text = response.text.strip() if response.text else ""
            if text:
                return text
        except Exception as exc:
            logger.warning(
                f"Conversational greeting with key [{idx + 1}/{len(api_keys)}] failed: {exc}. Rolling over..."
            )
            continue

    # Adaptive contextual fallback if all keys are unavailable
    lower = user_query.lower()
    salutation = "Hello!"
    if "good morning" in lower:
        salutation = "Good morning!"
    elif "good afternoon" in lower:
        salutation = "Good afternoon!"
    elif "good evening" in lower:
        salutation = "Good evening!"
    elif "how are you" in lower:
        salutation = "Hello! I'm doing very well, thank you for asking."
    elif "what can you do" in lower or "who are you" in lower:
        salutation = "Hello! I'm the BoxnFreight Virtual Assistant."

    return (
        f"{salutation} Welcome to BoxnFreight Support. "
        "I can help you with shipment tracking, POD downloads, LR status, freight booking, and billing inquiries. "
        "Please provide your tracking LR number or details of your request so I can assist you right away!"
    )


def check_fast_track(
    text: str, category: Optional[str], faqs: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Question-First Fast-Track Matching:
    Immediate pattern checks for logistics acronyms (POD, LR, tracking, E-way bill, password,
    billing/invoices, bookings, claims, etc.) against the 50 FAQ base to eliminate unnecessary
    LLM latency and guarantee category-independent resolution.
    The customer category dropdown is only a soft hint and NEVER overrides question intent.
    """
    lower = text.lower()
    cleaned = re.sub(r"[^\w\s]", " ", lower)

    # Do not fast-track if active operational emergency / dispute incident is reported
    # Evaluated strictly on the user's issue text, never on category dropdown!
    emergency_keywords = [
        "driver refused delivery", "accident on highway", "truck in accident", "truck accident",
        "stolen cargo", "cargo stolen", "lost cargo on highway", "police complaint",
        "legal notice", "court summon", "truck caught fire", "vehicle seized",
        "driver detained", "demanding bribe"
    ]
    if any(ek in lower for ek in emergency_keywords):
        return None

    def find_faq(faq_id: int) -> Optional[Dict[str, Any]]:
        for f in faqs:
            if f.get("id") == faq_id:
                return f
        return None

    def make_res(faq: Dict[str, Any], acronym_label: str) -> Dict[str, Any]:
        reason = (
            f"Question-first semantic match ({acronym_label}) matched with FAQ #{faq['id']} "
            f"('{faq['question']}'). Resolved immediately via verified FAQ base."
        )
        if category and category.strip():
            mapped_cats = INTAKE_CATEGORY_MAPPING.get(category, [category])
            if faq["category"] not in mapped_cats:
                reason += f" Automatically classified under '{faq['category']}' based on question intent (overriding selected category '{category}')."

        return {
            "status": "RESOLVED_BY_AI",
            "category": faq["category"],
            "answer": faq["answer"],
            "agent_reason": reason,
        }

    # 1. POD (Proof of Delivery)
    has_pod = bool(re.search(r"\bpod\b", lower)) or "proof of delivery" in lower or "signed copy" in lower
    if has_pod:
        if any(w in lower for w in ["retain", "retention", "older", "archive", "how long", "past year"]):
            faq = find_faq(39)
            if faq:
                return make_res(faq, "POD Retention")
        if any(w in lower for w in ["refuse", "reject", "consignee refused"]):
            faq = find_faq(36)
            if faq:
                return make_res(faq, "Consignee Delivery Refusal")
        if any(w in lower for w in ["time window", "schedule delivery", "appointment"]):
            faq = find_faq(37)
            if faq:
                return make_res(faq, "Delivery Time Window")
        if any(w in lower for w in ["unavailable", "absent", "not available"]):
            faq = find_faq(38)
            if faq:
                return make_res(faq, "Consignee Unavailable")
        if any(w in lower for w in ["how", "get", "download", "find", "obtain", "view", "receive", "where", "copy", "request", "need"]):
            faq = find_faq(35)
            if faq:
                return make_res(faq, "POD Download & Receipt")
        faq = find_faq(35)
        if faq:
            return make_res(faq, "Proof of Delivery")

    # 2. Tracking (Shipment & LR tracking)
    has_tracking = (
        bool(re.search(r"\btrack(ing)?\b", lower))
        or "where is my" in lower
        or "status of my" in lower
        or "consignment status" in lower
        or "live tracking" in lower
    )
    if has_tracking:
        if any(p in lower for p in ["bulk track", "bulk tracking", "multiple shipments", "csv track"]):
            faq = find_faq(20)
            if faq:
                return make_res(faq, "Bulk Shipment Tracking")
        if any(p in lower for p in ["status label", "status mean", "status meaning", "what does in transit mean", "what do status labels"]):
            faq = find_faq(19)
            if faq:
                return make_res(faq, "Shipment Status Labels")
        if any(p in lower for p in ["share tracking", "share link", "customer tracking link", "consignee link"]):
            faq = find_faq(23)
            if faq:
                return make_res(faq, "Share Tracking Link")
        if any(p in lower for p in ["notification", "sms", "whatsapp", "email alert", "status alert"]):
            faq = find_faq(21)
            if faq:
                return make_res(faq, "Shipment Tracking Notifications")
        if any(p in lower for p in ["several days", "stuck in transit", "without updates", "no update in transit"]):
            faq = find_faq(22)
            if faq:
                return make_res(faq, "In Transit Delays")
        if any(p in lower for p in ["how do i track", "how to track", "track shipment", "track using lr", "track my shipment", "tracking my shipment", "track lr", "track my lr", "lr tracking", "where is my shipment", "where is my lr", "where is my truck", "track consignment", "tracking status", "check status"]):
            faq = find_faq(18)
            if faq:
                return make_res(faq, "LR Shipment Tracking")
        faq = find_faq(18)
        if faq:
            return make_res(faq, "LR Shipment Tracking")

    # 3. LR (Lorry Receipt / Bilty) Details & Management
    has_lr = bool(re.search(r"\blr\b", lower)) or "lorry receipt" in lower or "bilty" in lower
    if has_lr:
        if any(p in lower for p in ["what is an lr", "what is lr", "what is a lorry receipt", "meaning of lr", "why is lr important", "what is bilty", "meaning of bilty"]):
            faq = find_faq(12)
            if faq:
                return make_res(faq, "LR Definition")
        if any(p in lower for p in ["generate lr", "create lr", "how to generate", "make lr", "issue lr"]):
            faq = find_faq(13)
            if faq:
                return make_res(faq, "LR Generation")
        if any(p in lower for p in ["edit lr", "change lr", "modify lr", "update lr", "alter lr"]):
            faq = find_faq(14)
            if faq:
                return make_res(faq, "LR Modification")
        if any(p in lower for p in ["download lr", "print lr", "lr pdf", "copy of lr", "get lr copy"]):
            faq = find_faq(15)
            if faq:
                return make_res(faq, "LR PDF Download")
        if any(p in lower for p in ["consignor consignee transporter", "different copies", "three copies", "types of copies"]):
            faq = find_faq(16)
            if faq:
                return make_res(faq, "LR Copy Types")
        if any(p in lower for p in ["lr correction", "incorrect consignee", "correction request", "wrong name on lr", "wrong address on lr"]):
            faq = find_faq(17)
            if faq:
                return make_res(faq, "LR Correction Request")

    # 4. Password & Account Access
    if "password" in lower:
        if any(w in lower for w in ["forgot", "reset", "change", "recover", "lost", "how do i", "how to", "cant login", "can't login"]):
            faq = find_faq(4)
            if faq:
                return make_res(faq, "Password Reset")
        faq = find_faq(4)
        if faq:
            return make_res(faq, "Password Reset")

    if any(p in lower for p in ["create account", "create a business account", "sign up for business", "new account", "how do i create a boxnfreight", "register business account", "open an account"]):
        faq = find_faq(1)
        if faq:
            return make_res(faq, "Business Account Creation")

    if any(p in lower for p in ["documents required", "verify my business account", "verify business account", "account verification documents", "kyc documents", "documents are required to verify"]):
        faq = find_faq(2)
        if faq:
            return make_res(faq, "Account Verification Documents")

    if any(p in lower for p in ["add additional users", "add team member", "invite user", "user roles", "different roles", "team members"]):
        faq = find_faq(3)
        if faq:
            return make_res(faq, "User & Role Management")

    if any(p in lower for p in ["update billing address", "change gst", "update gst", "edit billing details", "update company profile"]):
        faq = find_faq(5)
        if faq:
            return make_res(faq, "Update Billing & GST Details")

    # 5. Invoices, Billing, Pricing & Quotes
    if any(p in lower for p in ["download invoice", "download my invoice", "gst invoice", "monthly invoice", "tax invoice", "where can i download my invoice", "get invoice", "where to download invoice", "invoice copy", "download gst invoice"]):
        faq = find_faq(28)
        if faq:
            return make_res(faq, "Download Monthly / GST Invoice")

    if any(p in lower for p in ["instant rate quote", "get quote", "rate estimate", "instant quote"]):
        faq = find_faq(25)
        if faq:
            return make_res(faq, "Instant Freight Quote")

    if any(p in lower for p in ["pricing calculated", "how is freight pricing", "how are rates calculated", "rate calculation"]):
        faq = find_faq(24)
        if faq:
            return make_res(faq, "Freight Pricing Calculation")

    if any(p in lower for p in ["payment method", "methods of payment", "accepted payment", "payment options", "how to pay"]):
        faq = find_faq(26)
        if faq:
            return make_res(faq, "Accepted Payment Methods")

    if any(p in lower for p in ["credit account", "monthly billing cycle", "apply for credit"]):
        faq = find_faq(27)
        if faq:
            return make_res(faq, "Credit Account & Monthly Billing")

    if any(p in lower for p in ["payment deducted", "charged twice", "money deducted booking failed", "payment debited"]):
        faq = find_faq(29)
        if faq:
            return make_res(faq, "Payment Deducted on Failed Booking")

    # 6. Booking & Cancellations
    if any(p in lower for p in ["cancel booking before", "cancel a booking before", "cancel my booking", "cancel booking", "how do i cancel"]):
        if any(w in lower for w in ["policy", "charge", "fee"]):
            faq = find_faq(45)
            if faq:
                return make_res(faq, "Cancellation Policy & Charges")
        faq = find_faq(11)
        if faq:
            return make_res(faq, "Cancel Booking Before Vehicle Assignment")

    if any(p in lower for p in ["cancellation policy", "cancellation charges", "cancellation fee"]):
        faq = find_faq(45)
        if faq:
            return make_res(faq, "Cancellation Policy & Charges")

    if any(p in lower for p in ["how long refund", "refund timeline", "refund take", "when will i receive refund"]):
        faq = find_faq(46)
        if faq:
            return make_res(faq, "Refund Timeline")

    if any(p in lower for p in ["wallet credit", "convert refund to wallet"]):
        faq = find_faq(47)
        if faq:
            return make_res(faq, "Wallet Credit Conversion")

    if any(p in lower for p in ["ftl vs ptl", "ftl and ptl", "difference between ftl and ptl"]):
        faq = find_faq(7)
        if faq:
            return make_res(faq, "FTL vs PTL Booking Difference")

    if any(p in lower for p in ["schedule a shipment", "schedule booking", "advance booking", "future pickup date"]):
        faq = find_faq(8)
        if faq:
            return make_res(faq, "Advance Shipment Booking")

    if any(p in lower for p in ["multiple pickup", "multiple drop", "multi stop"]):
        faq = find_faq(9)
        if faq:
            return make_res(faq, "Multiple Pickup & Drop Locations")

    if any(p in lower for p in ["package details", "item details", "dimensions weight"]):
        faq = find_faq(10)
        if faq:
            return make_res(faq, "Booking Item & Package Details")

    if any(p in lower for p in ["book a new shipment", "how do i book a shipment", "how to book a shipment", "book shipment"]):
        faq = find_faq(6)
        if faq:
            return make_res(faq, "Book New Shipment")

    # 7. Documentation & E-Way Bill
    if "eway bill" in cleaned or "e way bill" in cleaned or "e-way bill" in lower:
        if any(w in lower for w in ["who generate", "generate", "separately", "portal", "do i need"]):
            faq = find_faq(30)
            if faq:
                return make_res(faq, "E-Way Bill Compliance")
        if any(w in lower for w in ["upload", "attach", "add document"]):
            faq = find_faq(32)
            if faq:
                return make_res(faq, "E-Way Bill Upload")

    if any(p in lower for p in ["interstate transport", "documents accompany shipment", "interstate documents"]):
        faq = find_faq(31)
        if faq:
            return make_res(faq, "Interstate Transport Documents")

    if any(p in lower for p in ["stopped for document", "document verification during transit", "stopped at checkpost"]):
        faq = find_faq(33)
        if faq:
            return make_res(faq, "Inspection & Document Verification")

    if any(p in lower for p in ["separate lr for each invoice", "multiple invoices to the same consignee", "multiple invoices one truck"]):
        faq = find_faq(34)
        if faq:
            return make_res(faq, "Multiple Invoices LR Handling")

    # 8. Claims & Transit Insurance
    if any(p in lower for p in ["how do i file a claim", "how to file a claim", "file a claim", "file damage claim", "claim for damaged", "how do i claim"]):
        faq = find_faq(40)
        if faq:
            return make_res(faq, "Filing a Damage Claim")

    if any(p in lower for p in ["transit insurance", "offer transit insurance", "add insurance to a booking"]):
        faq = find_faq(41)
        if faq:
            return make_res(faq, "Transit Insurance Options")

    if any(p in lower for p in ["claim settlement", "timeline for claim", "process and timeline for claim"]):
        faq = find_faq(42)
        if faq:
            return make_res(faq, "Claim Settlement Timeline")

    if any(p in lower for p in ["evidence do i need", "evidence to submit", "evidence for claim", "proof for damage"]):
        faq = find_faq(43)
        if faq:
            return make_res(faq, "Damage Claim Evidence Requirements")

    if any(p in lower for p in ["liability cap", "compensation limit", "maximum liability"]):
        faq = find_faq(44)
        if faq:
            return make_res(faq, "Shipment Liability Cap")

    # 9. Support & Escalations
    if any(p in lower for p in ["support hours", "reach a human agent", "reach human agent", "talk to human", "customer care number", "support phone number", "contact support"]):
        faq = find_faq(49)
        if faq:
            return make_res(faq, "Support Hours & Human Agent Contact")

    if any(p in lower for p in ["how do i escalate", "escalate an issue", "complaint escalation", "higher escalation"]):
        faq = find_faq(48)
        if faq:
            return make_res(faq, "Support Escalation Procedure")

    if any(p in lower for p in ["dedicated account manager", "key account manager", "request account manager"]):
        faq = find_faq(50)
        if faq:
            return make_res(faq, "Dedicated Account Manager Request")

    return None


async def _call_gemini_triage(
    category: Optional[str], description: str, faqs: List[Dict[str, Any]], api_key: str
) -> Dict[str, Any]:
    """
    Evaluate ticket asynchronously using Google Gemini model 'gemini-2.5-flash'
    via the official google-genai async client.
    """
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
1. QUESTION-FIRST SEMANTIC TRIAGE:
   - The user's issue description is the PRIMARY and AUTHORITATIVE source of truth for intent classification and FAQ matching.
   - The user-selected category dropdown is ONLY a soft hint or secondary context and is frequently inaccurate or accidentally misclicked by customers (e.g., selecting 'Billing & Invoicing' while asking 'How do I track LR?', or selecting 'Shipment Tracking' while asking 'I forgot my password').
   - You MUST NEVER allow a mismatched dropdown category to override an obvious semantic match with a verified FAQ or cause unnecessary escalation.
   - If the user's issue clearly matches a verified FAQ (e.g., tracking, POD, password, billing, etc.), return status 'RESOLVED_BY_AI', provide the exact verified answer, and set 'category' to the official BRD category of the matched FAQ, regardless of which dropdown option the user accidentally selected.
   - If there is a mismatch (e.g. user selected 'Billing' but asked 'How do I track LR?'), provide the correct tracking FAQ answer and automatically classify it under the correct category of that FAQ.

2. High Confidence Match (status = "RESOLVED_BY_AI"):
   - Set status to 'RESOLVED_BY_AI' if the ticket is clearly and directly answered by verified knowledge base SOPs.
   - Provide the exact, helpful FAQ answer in 'answer'.
   - State the matched FAQ #(s) and why in 'agent_reason'.

3. Escalation Required (status = "NEEDS_HUMAN"):
   - Set status to 'NEEDS_HUMAN' if the ticket is ambiguous, describes an active unresolved dispute, cargo damage, vehicle accident, theft, missing cargo, legal threat, or query not covered in verified knowledge base SOPs. Escalated for human review.
   - Provide a helpful reassurance note in 'answer' (e.g. "Your ticket has been escalated to our human operations team for priority review and manual resolution.").
   - Provide a clear, actionable explanation in 'agent_reason' detailing why human review is required.

4. MULTI-PART QUESTION HANDLING:
   - If the user query contains multiple split questions (e.g., asking for support contact/Gmail AND how to track a shipment LR, or invoice details AND cancellation policy):
     * Parse each question systematically.
     * Provide a structured, point-by-point bulleted answer addressing each part strictly based on the FAQ context.
     * If one part is covered by the FAQs and another part requires private account access or is outside the FAQs, answer the FAQ portion clearly and note that the remaining portion is flagged for human support.

5. GREETING POLISH ON COMPOSITE QUERIES:
   - When the user query combines a greeting and a real issue (e.g., "hello good morning, i forgot my password" or "hi, how do i track my shipment"):
     * Do NOT return a blunt, dry FAQ answer.
     * Prefix the verified answer with a warm, contextual greeting acknowledging the user (e.g., "Good morning! To reset your password, click 'Forgot Password' on the login page...").
     * Keep the tone polite, human, and professional.

6. Category Selection:
   - Category MUST be chosen from the exact list of 10 official BRD categories above.
   - For verified FAQ matches, category MUST match the canonical BRD category of the matched FAQ.
   - Only use the dropdown category as a soft fallback if the issue description is genuinely ambiguous and does not match any FAQ.
"""

    prompt = f"""Incoming Ticket:
Issue Description (PRIMARY SOURCE OF TRUTH): {description}
User-Selected Category Dropdown (Soft Hint / Fallback Only): {category or 'Not specified'}

Reference Knowledge Base (50 official FAQs):
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
    except Exception as e:
        err_str = str(e).lower()
        if "not_found" in err_str or "no longer available" in err_str or "404" in err_str:
            logger.info("gemini-2.5-flash returned 404/unavailable. Falling back to gemini-3.8-flash with the current key.")
            response = await client.aio.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config=config,
            )
        else:
            raise

    result = response.parsed.model_dump()
    return result


def _tokenize(text: str) -> set:
    """Helper to tokenize and normalize words with logistics acronym expansion."""
    words = re.findall(r"\w+", text.lower())
    stop_words = {
        "a", "an", "the", "in", "on", "at", "for", "to", "of", "and", "or", "is",
        "are", "was", "my", "your", "i", "we", "can", "how", "what", "do", "does",
        "it", "with", "from", "be", "this", "that", "me", "please", "help", "you"
    }
    tokens = {w for w in words if w not in stop_words and len(w) > 1}
    # Domain synonym expansion
    if "pod" in tokens:
        tokens.update({"proof", "delivery"})
    if "lr" in tokens or "bilty" in tokens:
        tokens.update({"lorry", "receipt"})
    return tokens


def _fallback_heuristic_triage(
    category: Optional[str], description: str, faqs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Fallback deterministic triage engine used when all GEMINI_API_KEYS are exhausted or unavailable.
    Guarantees 100% uptime, zero downtime, and strictly enforces QUESTION-FIRST semantic triage:
    1. Evaluates user query text independently of category dropdown to eliminate category bias.
    2. Category dropdown only acts as a soft fallback if query is ambiguous or outside FAQ base.
    3. If query matches a verified FAQ, automatically returns verified FAQ answer and assigns true category.
    """
    desc_lower = description.lower()
    ticket_tokens = _tokenize(description)

    # Operational emergency incidents that require immediate human intervention
    # (Evaluated strictly on user's description, never on category dropdown)
    emergency_keywords = [
        "driver refused delivery", "accident on highway", "truck in accident", "truck accident",
        "stolen cargo", "cargo stolen", "lost cargo on highway", "police complaint",
        "legal notice", "court summon", "truck caught fire", "vehicle seized",
        "driver detained", "demanding bribe"
    ]
    is_emergency_incident = any(ek in desc_lower for ek in emergency_keywords)

    best_faq = None
    best_score = 0.0

    if not is_emergency_incident:
        for faq in faqs:
            q_lower = faq["question"].lower()
            q_tokens = _tokenize(q_lower)
            if not q_tokens:
                continue

            intersection = ticket_tokens.intersection(q_tokens)
            if not intersection:
                continue

            coverage = len(intersection) / len(ticket_tokens) if ticket_tokens else 0.0
            recall = len(intersection) / len(q_tokens)
            f1 = (2.0 * len(intersection)) / (len(ticket_tokens) + len(q_tokens))
            score = f1

            # High user coverage bonus
            if coverage >= 0.75:
                score += 0.35
            elif coverage >= 0.5:
                score += 0.2

            # Substring or exact phrase match bonus
            if q_lower in desc_lower or desc_lower in q_lower:
                score += 0.5

            if score > best_score:
                best_score = score
                best_faq = faq

    # If verified FAQ match found with high confidence
    if best_faq and (best_score >= 0.40 or (ticket_tokens and len(ticket_tokens.intersection(_tokenize(best_faq["question"]))) / len(ticket_tokens) >= 0.65)):
        reason = (
            f"Question-first semantic match with FAQ #{best_faq['id']} ('{best_faq['question']}'). "
            "Resolved automatically via verified FAQ database."
        )
        if category and category.strip():
            mapped_cats = INTAKE_CATEGORY_MAPPING.get(category, [category])
            if best_faq["category"] not in mapped_cats:
                reason += f" Automatically classified under '{best_faq['category']}' based on question intent (overriding selected category '{category}')."

        return {
            "status": "RESOLVED_BY_AI",
            "category": best_faq["category"],
            "answer": best_faq["answer"],
            "agent_reason": reason,
        }

    # Otherwise, ticket requires human operational review (NEEDS_HUMAN)
    # Determine classification: Question-first BRD matching, with dropdown category as soft fallback
    predicted_category = None

    # Step 1: Detect category keywords from user description text
    category_scores: Dict[str, int] = {cat: 0 for cat in BRD_CATEGORIES}
    for cat in BRD_CATEGORIES:
        cat_tokens = _tokenize(cat)
        category_scores[cat] += len(ticket_tokens.intersection(cat_tokens)) * 2

    highest_cat = max(category_scores, key=category_scores.get)
    if category_scores[highest_cat] > 0:
        predicted_category = highest_cat

    # Step 2: If description has no clear category, use dropdown as soft fallback
    if not predicted_category and category:
        mapped = INTAKE_CATEGORY_MAPPING.get(category)
        if mapped:
            predicted_category = mapped[0]
        elif category in BRD_CATEGORIES:
            predicted_category = category

    # Step 3: Default fallback
    if not predicted_category:
        predicted_category = "Support, Escalation & Account Management"

    return {
        "status": "NEEDS_HUMAN",
        "category": predicted_category,
        "answer": "Your ticket has been escalated to our human support team for manual review and resolution.",
        "agent_reason": (
            "Inquiry involves specific operational details or exception handling. Routed to human operations team for specialized review."
        ),
    }


async def triage_ticket(
    category: Optional[str], description: str, db_path: Path = DB_PATH
) -> Dict[str, Any]:
    """
    Main asynchronous triage entry point:
    1. Dynamic Conversational AI Intent (Zero-Persistence Pure Greetings):
       If purely conversational/greeting, invokes Gemini or contextual fallback.
       Classification: "Conversational Greeting / Inquiry", Status: 'CONVERSATIONAL', ticket_id: None.
    2. Acronym & Fast-Track Matching:
       Evaluates POD, LR, tracking, etc. against FAQs to eliminate latency when a direct answer exists.
    3. Multi-Key Failover Pool:
       Iterates through keys on HTTP 429 / ResourceExhausted / errors.
    4. Heuristic Fallback Engine:
       Only invoked if ALL keys in the failover pool are exhausted.
    """
    # 0. Gibberish / Meaningless Input Filtering (Zero-Persistence)
    if is_gibberish_or_spam(description):
        invalid_guidance = (
            "We could not understand your inquiry. Please describe your logistics issue clearly "
            "(e.g., provide your LR number, delivery status request, or billing question) to submit a support ticket."
        )
        return {
            "ticket_id": None,
            "is_conversational": True,
            "category": "Invalid Inquiry",
            "status": "INVALID",
            "resolution_guidance": invalid_guidance,
            "answer": invalid_guidance,
            "agent_reason": "Meaningless input or spam query detected. Discarded without database persistence.",
        }

    # 1. Dynamic Conversational AI Intent (Pure Greetings Zero-Persistence)
    if is_conversational_greeting(description):
        dynamic_answer = await _call_gemini_conversational_greeting(description)
        return {
            "ticket_id": None,
            "is_conversational": True,
            "category": "Conversational Greeting / Inquiry",
            "resolution_guidance": dynamic_answer,
            "answer": dynamic_answer,
            "agent_reason": "Conversational greeting handled by Virtual Assistant (zero-persistence).",
            "status": "CONVERSATIONAL",
        }

    # 2. Fetch FAQs from database
    faqs = await get_all_faqs(db_path)

    # 3. Fast-Track Acronym Check for concrete logistics queries
    fast_track_res = check_fast_track(description, category, faqs)
    if fast_track_res:
        if fast_track_res.get("answer"):
            fast_track_res["answer"] = polish_answer_with_greeting(fast_track_res["answer"], description)
        return fast_track_res

    # 4. Multi-Key Failover Pool for Strict FAQ Vector/Lookup Matching
    api_keys = get_gemini_api_keys()

    if api_keys:
        for idx, api_key in enumerate(api_keys):
            masked = f"...{api_key[-6:]}" if len(api_key) > 6 else "***"
            try:
                logger.info(f"Attempting Gemini triage with key pool [{idx + 1}/{len(api_keys)}] ({masked})")
                decision = await _call_gemini_triage(category, description, faqs, api_key)
                if decision.get("status") in ("RESOLVED", "RESOLVED_BY_AI"):
                    decision["status"] = "RESOLVED_BY_AI"
                elif decision.get("status") in ("ESCALATED", "NEEDS_HUMAN"):
                    decision["status"] = "NEEDS_HUMAN"
                if decision.get("answer"):
                    decision["answer"] = polish_answer_with_greeting(decision["answer"], description)
                return decision
            except Exception as exc:
                logger.warning(
                    f"Gemini API key [{idx + 1}/{len(api_keys)}] ({masked}) hit error: {exc}. "
                    "Rolling over to next key in failover pool..."
                )
                continue

        logger.warning(
            "All Gemini API keys in the failover pool were exhausted or failed. "
            "Executing local heuristic fallback triage."
        )
    else:
        logger.info("No Gemini API keys configured. Executing local heuristic fallback triage.")

    # 5. Local Heuristic Fallback
    res = _fallback_heuristic_triage(category, description, faqs)
    if res.get("status") in ("ESCALATED", "NEEDS_HUMAN"):
        res["status"] = "NEEDS_HUMAN"
    elif res.get("status") == "RESOLVED":
        res["status"] = "RESOLVED_BY_AI"
    if res.get("answer"):
        res["answer"] = polish_answer_with_greeting(res["answer"], description)
    return res


def triage_ticket_sync(
    category: Optional[str], description: str, db_path: Path = DB_PATH
) -> Dict[str, Any]:
    """Synchronous wrapper for triage_ticket."""
    import asyncio
    return asyncio.run(triage_ticket(category, description, db_path))
