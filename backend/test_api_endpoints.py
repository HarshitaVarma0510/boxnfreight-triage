import asyncio
from fastapi.testclient import TestClient
from main import app, init_db_schema

client = TestClient(app)

def test_api_deduplication_and_triage():
    # 1. First submission: Billing & Invoicing dropdown, but question is about tracking LR
    res1 = client.post(
        "/api/tickets",
        json={
            "category": "Billing & Invoicing (Freight bills, GST invoice, credit notes)",
            "description": "How do I track LR?",
        },
    )
    assert res1.status_code == 200, f"Expected 200, got {res1.status_code}: {res1.text}"
    data1 = res1.json()
    print("Submission 1 (Billing Dropdown):")
    print(f"  ID: {data1['id']}, Ref: {data1['reference_id']}, Status: {data1['status']}, Category: {data1['category']}, Idempotent: {data1['is_idempotent']}")
    
    assert data1["status"] == "RESOLVED_BY_AI"
    assert data1["category"] == "LR & Shipment Tracking", f"Expected 'LR & Shipment Tracking', got '{data1['category']}'"
    assert data1["answer"] is not None and "BoxNFreight" in data1["answer"]

    # 2. Second submission: Exact same question but user selected Account & Portal Access dropdown
    res2 = client.post(
        "/api/tickets",
        json={
            "category": "Account & Portal Access (Login, password reset, user roles)",
            "description": "How do I track LR?",
        },
    )
    assert res2.status_code == 200
    data2 = res2.json()
    print("\nSubmission 2 (Account & Portal Access Dropdown):")
    print(f"  ID: {data2['id']}, Ref: {data2['reference_id']}, Status: {data2['status']}, Category: {data2['category']}, Idempotent: {data2['is_idempotent']}")

    # Must hit deduplication within 5-minute cooldown window
    assert data2["is_idempotent"] is True, "Second submission should hit idempotency deduplication"
    assert data2["id"] == data1["id"], f"Expected same ticket ID {data1['id']}, got {data2['id']}"
    assert data2["reference_id"] == data1["reference_id"]
    assert data2["status"] == "RESOLVED_BY_AI"
    assert data2["category"] == "LR & Shipment Tracking"

    # 3. Third submission: Password reset question with Tracking dropdown
    res3 = client.post(
        "/api/tickets",
        json={
            "category": "Shipment Tracking (Track consignment, ETA, delay status)",
            "description": "I forgot my password / how do I reset it?",
        },
    )
    assert res3.status_code == 200
    data3 = res3.json()
    print("\nSubmission 3 (Password query with Tracking Dropdown):")
    print(f"  ID: {data3['id']}, Ref: {data3['reference_id']}, Status: {data3['status']}, Category: {data3['category']}, Idempotent: {data3['is_idempotent']}")

    assert data3["status"] == "RESOLVED_BY_AI"
    assert data3["category"] == "Account & Onboarding", f"Expected 'Account & Onboarding', got '{data3['category']}'"
    assert data3["answer"] is not None and "Forgot Password" in data3["answer"]

    # 4. Fourth submission: Same password query with Billing dropdown (dedup check)
    res4 = client.post(
        "/api/tickets",
        json={
            "category": "Billing & Invoicing (Freight bills, GST invoice, credit notes)",
            "description": "I forgot my password / how do I reset it?",
        },
    )
    assert res4.status_code == 200
    data4 = res4.json()
    print("\nSubmission 4 (Password query with Billing Dropdown):")
    print(f"  ID: {data4['id']}, Ref: {data4['reference_id']}, Status: {data4['status']}, Category: {data4['category']}, Idempotent: {data4['is_idempotent']}")

    assert data4["is_idempotent"] is True
    assert data4["id"] == data3["id"]
    assert data4["category"] == "Account & Onboarding"

    # 5. Pure conversational greeting test (Zero-Persistence)
    initial_tickets = client.get("/api/tickets").json()
    initial_count = len(initial_tickets)

    res_greeting = client.post(
        "/api/tickets",
        json={
            "category": "Other / General Inquiry (Custom query or general help)",
            "description": "Good morning team!",
        },
    )
    assert res_greeting.status_code == 200
    data_greeting = res_greeting.json()
    print("\nSubmission 5 (Pure Greeting Zero-Persistence):")
    print(f"  ticket_id: {data_greeting['ticket_id']}, is_conversational: {data_greeting['is_conversational']}, answer: {data_greeting['answer'][:60]}...")
    assert data_greeting["ticket_id"] is None, "ticket_id must be null for pure greetings"
    assert data_greeting["id"] is None, "id must be null for pure greetings"
    assert data_greeting["is_conversational"] is True, "is_conversational must be True"
    assert data_greeting["status"] == "CONVERSATIONAL", "status must be CONVERSATIONAL"
    assert data_greeting.get("resolution_guidance") is not None, "resolution_guidance must be returned"

    after_tickets = client.get("/api/tickets").json()
    assert len(after_tickets) == initial_count, "Pure greeting interaction must NOT insert into SQLite tickets database"

    # 6. Composite query with Greeting + Real Issue under mismatched category
    res_composite = client.post(
        "/api/tickets",
        json={
            "category": "Billing & Invoicing (Freight bills, GST invoice, credit notes)",
            "description": "Good morning! How do I track my shipment using the LR number on BoxNFreight?",
        },
    )
    assert res_composite.status_code == 200
    data_composite = res_composite.json()
    print("\nSubmission 6 (Greeting + Tracking under Billing Category):")
    print(f"  ID: {data_composite['id']}, Status: {data_composite['status']}, Category: {data_composite['category']}, Answer: {data_composite['answer'][:50]}...")
    assert data_composite["status"] == "RESOLVED_BY_AI"
    assert data_composite["category"] == "LR & Shipment Tracking", "Must resolve to tracking category regardless of Billing dropdown"
    assert data_composite["answer"].startswith("Good morning!"), "Answer must be prefixed with friendly greeting"
    assert data_composite["ticket_id"] is not None
    assert data_composite["is_conversational"] is False

    # 7. Gibberish / Meaningless spam inputs (Zero-Persistence & STRICT INVALID status)
    gibberish_samples = ["jhhhhh", "khflivfly", "asdfghjkl", ".....", "qweqweqwe"]
    count_before_gibberish = len(client.get("/api/tickets").json())

    for sample in gibberish_samples:
        res_gibberish = client.post(
            "/api/tickets",
            json={
                "category": "Other / General Inquiry (Custom query or general help)",
                "description": sample,
            },
        )
        assert res_gibberish.status_code == 200, f"Expected 200 for gibberish sample '{sample}', got {res_gibberish.status_code}"
        data_g = res_gibberish.json()
        print(f"\nSubmission Gibberish ('{sample}'):")
        print(f"  ticket_id: {data_g['ticket_id']}, status: {data_g['status']}, category: {data_g['category']}, is_conversational: {data_g['is_conversational']}")
        assert data_g["ticket_id"] is None, f"ticket_id must be null for gibberish '{sample}'"
        assert data_g["id"] is None, f"id must be null for gibberish '{sample}'"
        assert data_g["status"] == "INVALID", f"status must be INVALID for '{sample}', got '{data_g['status']}'"
        assert data_g["category"] == "Invalid Inquiry", f"category must be 'Invalid Inquiry', got '{data_g['category']}'"
        assert data_g["is_conversational"] is True, f"is_conversational must be True for '{sample}'"
        assert "We could not understand your inquiry" in data_g["resolution_guidance"]

    count_after_gibberish = len(client.get("/api/tickets").json())
    assert count_after_gibberish == count_before_gibberish, "Gibberish spam inputs must STRICTLY NOT insert into SQLite tickets database!"

    print("\n=============================================")
    print("ALL API ENDPOINT & DEDUPLICATION TESTS PASSED!")
    print("=============================================")

if __name__ == "__main__":
    test_api_deduplication_and_triage()

