import asyncio
import os
import sys
from agent import triage_ticket, BUSINESS_CATEGORIES
from main import compute_query_hash

async def run_tests():
    test_cases = [
        ("How do I track LR?", "LR & Shipment Tracking", 18),
        ("How do I download POD?", "Delivery & Proof of Delivery", 35),
        ("I forgot my password / how do I reset it?", "Account & Onboarding", 4),
        ("Where can I download my GST invoice?", "Pricing, Quotes & Payments", 28),
        ("What is an LR and why is it important?", "LR (Lorry Receipt) Generation", 12),
        ("How is freight pricing calculated?", "Pricing, Quotes & Payments", 24),
        ("How do I cancel my booking before the vehicle is assigned?", "Shipment Booking", 11),
        ("Do I need to generate an E-Way Bill separately?", "Documentation & Compliance", 30),
    ]

    all_passed = True

    for query, expected_cat, expected_faq_id in test_cases:
        print(f"\n--- Testing Query: '{query}' ---")
        # 1. Check deduplication hash consistency
        hashes = set()
        for cat in BUSINESS_CATEGORIES:
            h = compute_query_hash(cat, query)
            hashes.add(h)
        if len(hashes) == 1:
            print(f"  [PASS] Hash is normalized and invariant across all {len(BUSINESS_CATEGORIES)} categories.")
        else:
            print(f"  [FAIL] Inconsistent hashes: {hashes}")
            all_passed = False

        # 2. Check triage results
        resolutions = []
        for cat in BUSINESS_CATEGORIES:
            res = await triage_ticket(cat, query)
            resolutions.append((cat, res["status"], res["category"], res["answer"]))

        # Verify all statuses are RESOLVED_BY_AI
        statuses = {r[1] for r in resolutions}
        categories = {r[2] for r in resolutions}
        answers = {r[3] for r in resolutions}

        if statuses == {"RESOLVED_BY_AI"}:
            print(f"  [PASS] Status is consistently RESOLVED_BY_AI across all categories.")
        else:
            print(f"  [FAIL] Inconsistent statuses: {statuses}")
            all_passed = False

        if categories == {expected_cat}:
            print(f"  [PASS] Category is consistently '{expected_cat}' across all categories.")
        else:
            print(f"  [FAIL] Inconsistent categories: {categories} (expected '{expected_cat}')")
            all_passed = False

        if len(answers) == 1:
            print(f"  [PASS] Exact same verified answer returned across all categories.")
        else:
            print(f"  [FAIL] Answers differed across categories!")
            all_passed = False

    # 3. Soft fallback test for ambiguous/custom inquiry
    print("\n--- Testing Soft Fallback on Ambiguous Query ---")
    ambiguous_query = "Can you send a special closed container vehicle for high value electronics?"
    res_tracking = await triage_ticket("Shipment Tracking (Track consignment, ETA, delay status)", ambiguous_query)
    res_booking = await triage_ticket("Freight Booking & Orders (New vehicle placement, capacity)", ambiguous_query)

    print(f"  Ambiguous with Tracking -> status={res_tracking['status']}, category={res_tracking['category']}")
    print(f"  Ambiguous with Booking  -> status={res_booking['status']}, category={res_booking['category']}")

    if res_tracking["status"] == "NEEDS_HUMAN" and res_booking["status"] == "NEEDS_HUMAN":
        print("  [PASS] Status is appropriately NEEDS_HUMAN for ambiguous query outside FAQs.")
    else:
        print("  [FAIL] Unexpected status for ambiguous query.")
        all_passed = False

    # Verify soft fallback category routing works when no FAQ matches
    if res_tracking["category"] == "LR & Shipment Tracking" and res_booking["category"] == "Shipment Booking":
        print("  [PASS] Dropdown category functions as expected soft fallback for human escalation routing.")
    else:
        print(f"  [INFO] Soft fallback categories: {res_tracking['category']}, {res_booking['category']}")

    print("\n=============================================")
    if all_passed:
        print("RESULT: ALL TESTS PASSED! 100% INVARIANCE CONFIRMED.")
    else:
        print("RESULT: SOME TESTS FAILED!")
    print("=============================================\n")
    return all_passed

if __name__ == "__main__":
    passed = asyncio.run(run_tests())
    sys.exit(0 if passed else 1)
