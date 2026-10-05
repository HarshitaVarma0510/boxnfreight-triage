import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tickets.db"

BOXNFREIGHT_FAQS = [
    # Category: Account & Onboarding
    {
        "category": "Account & Onboarding",
        "question": "How do I create a BoxNFreight business account?",
        "answer": (
            "Go to the BoxNFreight homepage and click \"Sign Up for Business.\" "
            "You'll need your company name, GSTIN, a registered mobile number, "
            "and an email address. After submitting, you'll receive an OTP on your mobile "
            "to verify the number, followed by an email link to set your password. "
            "Your account will be in \"Pending Verification\" status until our team "
            "confirms your GST details, which usually takes 4-6 business hours during working days."
        ),
    },
    {
        "category": "Account & Onboarding",
        "question": "What documents are required to verify my business account?",
        "answer": (
            "You'll need a valid GST registration certificate, PAN card of the business, "
            "and a cancelled cheque or bank statement for the account you'll use for payments/refunds. "
            "These can be uploaded under Account Settings > Verification Documents. "
            "If you're a proprietorship without a separate business PAN, your individual "
            "PAN is accepted along with your GST certificate."
        ),
    },
    {
        "category": "Account & Onboarding",
        "question": "How do I add additional users/team members with different roles?",
        "answer": (
            "Under Account Settings > Team Members, click \"Invite User\" and enter their email address "
            "along with a role: Admin (full access), Booking Executive (can create/manage bookings "
            "and LRs but not view invoices), or Accounts (can view invoices and payment history "
            "but not create bookings). The invited user receives an email to set up their own login "
            "linked to your company account."
        ),
    },
    {
        "category": "Account & Onboarding",
        "question": "I forgot my password / how do I reset it?",
        "answer": (
            "Click \"Forgot Password\" on the login page and enter your registered email. "
            "You'll receive a reset link valid for 30 minutes. If you don't receive it within "
            "a few minutes, check your spam folder, and confirm the email matches exactly "
            "what's on your account password reset emails aren't sent for unregistered addresses, "
            "for security reasons."
        ),
    },
    {
        "category": "Account & Onboarding",
        "question": "How do I update my company's billing address or GST details after account creation?",
        "answer": (
            "Go to Account Settings > Company Profile and click \"Edit\" next to Billing Details. "
            "Changes to GSTIN specifically require re-verification (1-2 business days) since it affects "
            "invoicing, so you'll see a \"Verification Pending\" badge until it's approved. "
            "Existing invoices already generated will not be reissued automatically - contact support "
            "if you need historical invoices corrected."
        ),
    },

    # Category: Shipment Booking
    {
        "category": "Shipment Booking",
        "question": "How do I book a new shipment on the BoxNFreight platform?",
        "answer": (
            "1. From the Dashboard, click \"Book Shipment.\" 2. Enter pickup and drop addresses "
            "(you can save frequently used addresses for faster future bookings). "
            "3. Select shipment type: Full Truck Load (FTL) or Part Truck Load (PTL). "
            "4. Enter package details weight, dimensions, and nature of goods. "
            "5. Review the auto-calculated rate estimate. 6. Click \"Confirm Booking\" and "
            "choose your payment method. Once confirmed, a booking ID is generated immediately, "
            "and vehicle assignment typically happens within 2-4 hours for FTL and by end of day for PTL."
        ),
    },
    {
        "category": "Shipment Booking",
        "question": "What's the difference between FTL and PTL booking?",
        "answer": (
            "Full Truck Load (FTL) books an entire vehicle exclusively for your shipment "
            "best for large volumes or time-sensitive/fragile cargo, since the truck goes directly "
            "from pickup to drop with no other stops. Part Truck Load (PTL) shares a vehicle with other "
            "shippers' goods along a similar route, which is cheaper per unit but takes longer since "
            "the vehicle makes multiple pickups and drops along the way."
        ),
    },
    {
        "category": "Shipment Booking",
        "question": "Can I schedule a shipment booking in advance for a future pickup date?",
        "answer": (
            "Yes. On the booking form, the \"Pickup Date\" field lets you select any date up to 30 days "
            "in advance. Advance bookings are held in \"Scheduled\" status and automatically move into "
            "the active booking pipeline 24 hours before the selected pickup date, at which point vehicle "
            "assignment begins."
        ),
    },
    {
        "category": "Shipment Booking",
        "question": "How do I add multiple pickup or drop locations in a single booking?",
        "answer": (
            "On the booking form, click \"Add Stop\" below the drop address field. You can add up to 5 stops "
            "total (combined pickups and drops) for a single FTL booking. Each stop requires its own address "
            "and the specific items/weight being picked up or dropped there, since this affects both routing "
            "and how the LR is generated (see Category: LR Generation)."
        ),
    },
    {
        "category": "Shipment Booking",
        "question": "What package/item details do I need to provide when booking?",
        "answer": (
            "For each item or item group: total weight (kg), dimensions (L x W x H in cm) if it affects "
            "vehicle sizing, nature of goods (general cargo, fragile, perishable, hazardous hazardous goods "
            "require additional compliance documentation), and declared value, which is used both for rate "
            "calculation and for any insurance you opt into."
        ),
    },
    {
        "category": "Shipment Booking",
        "question": "How do I cancel a booking before the vehicle is assigned?",
        "answer": (
            "Go to My Bookings, find the booking, and click \"Cancel Booking.\" Cancellations made before "
            "a vehicle is assigned are free. Once a vehicle has been assigned (status shows \"Vehicle Assigned\" "
            "or later), cancellation charges apply see the Cancellations & Refunds section for the fee structure."
        ),
    },

    # Category: LR (Lorry Receipt) Generation
    {
        "category": "LR (Lorry Receipt) Generation",
        "question": "What is a Lorry Receipt (LR) and why is it important?",
        "answer": (
            "An LR is the legal receipt issued by the transporter (BoxNFreight) to the consignor (sender) "
            "acknowledging that goods have been handed over for transport. It's the primary proof-of-shipment "
            "document - it's required for insurance claims, GST input credit in many cases, and is what the "
            "consignee checks against the delivered goods. Always keep a copy until the shipment is confirmed "
            "delivered and any disputes are resolved."
        ),
    },
    {
        "category": "LR (Lorry Receipt) Generation",
        "question": "How do I generate an LR for my shipment on the BoxNFreight website?",
        "answer": (
            "1. Go to My Bookings and open the confirmed booking you want to generate an LR for. "
            "2. Click \"Generate LR\" (this option appears once a vehicle has been assigned). "
            "3. Confirm or edit the consignor and consignee details pulled from your booking. "
            "4. Enter the invoice number(s) and value of goods being shipped. "
            "5. Select whether insurance is being added (see Claims & Insurance section). "
            "6. Click \"Generate\" the LR number is created immediately and the document becomes available "
            "as a PDF. 7. Download or share the LR directly from the confirmation screen. "
            "The LR number generated here is what you'll use for all future tracking of this shipment."
        ),
    },
    {
        "category": "LR (Lorry Receipt) Generation",
        "question": "Can I edit an LR after it has been generated, and what fields can be changed?",
        "answer": (
            "Once generated, the LR number, consignor, and consignee names are locked to preserve document "
            "integrity. You can still edit the declared value, item description, and remarks fields up until "
            "the shipment status changes to \"Picked Up\" - after that, any correction requires a formal "
            "correction request (see Question 17)."
        ),
    },
    {
        "category": "LR (Lorry Receipt) Generation",
        "question": "How do I download or print a copy of the LR as a PDF?",
        "answer": (
            "From My Bookings, open the shipment and click \"View LR,\" then \"Download PDF\" in the top right. "
            "The PDF is print-ready and includes a QR code that links directly to the live tracking page for that "
            "LR number, so anyone with the physical copy can scan it to check status."
        ),
    },
    {
        "category": "LR (Lorry Receipt) Generation",
        "question": "What's the difference between Consignor, Consignee, and Transporter copies of the LR?",
        "answer": (
            "All three copies contain the same shipment details but are formatted for their specific recipient - "
            "the Consignor copy is retained by the sender as proof of dispatch, the Consignee copy travels with the "
            "goods for the receiver to check and sign at delivery, and the Transporter copy stays with the driver "
            "for the duration of transit. You can generate and download all three from the same \"View LR\" screen "
            "using the copy-type dropdown."
        ),
    },
    {
        "category": "LR (Lorry Receipt) Generation",
        "question": "My LR shows incorrect consignee details - how do I raise a correction request?",
        "answer": (
            "Go to My Bookings, open the shipment, and click \"Request LR Correction.\" Specify which field is wrong "
            "and the correct value. Minor corrections (spelling, address formatting) are typically processed within a "
            "few hours; corrections that change the legal consignee entirely require a signed authorization letter "
            "uploaded with the request, since it affects the document's legal standing."
        ),
    },

    # Category: LR & Shipment Tracking
    {
        "category": "LR & Shipment Tracking",
        "question": "How do I track my shipment using the LR number?",
        "answer": (
            "1. Go to the BoxNFreight homepage and click \"Track Shipment\" (no login required for basic tracking). "
            "2. Enter your LR number in the search box. 3. Click \"Track\" to see the current status, last known "
            "location, and estimated delivery date. 4. Click \"View Full Timeline\" to see every status update from "
            "pickup through to current status, with timestamps. Logged-in users can also track from the Dashboard "
            "under \"My Shipments,\" which shows all their active shipments in one list without needing to enter "
            "LR numbers individually."
        ),
    },
    {
        "category": "LR & Shipment Tracking",
        "question": "What do the different shipment status labels mean?",
        "answer": (
            "\"Booked\" booking confirmed, vehicle not yet assigned. \"Picked Up\" - goods collected from the consignor. "
            "\"In Transit\" en route to destination. \"Out for Delivery\" - on the final leg to the consignee's address, "
            "typically updated the same day as expected delivery. \"Delivered\" confirmed received, POD available. "
            "\"Exception\" - something has interrupted normal flow (documentation hold, address issue, vehicle breakdown) "
            "and requires attention."
        ),
    },
    {
        "category": "LR & Shipment Tracking",
        "question": "Can I track multiple shipments at once using a bulk tracking upload?",
        "answer": (
            "Yes, under Track Shipment > Bulk Tracking, you can upload a CSV of up to 100 LR numbers and get a status "
            "summary for all of them in one downloadable report. This is intended for businesses managing many shipments "
            "at once rather than individual tracking lookups."
        ),
    },
    {
        "category": "LR & Shipment Tracking",
        "question": "How do I set up SMS/email/WhatsApp notifications for shipment status updates?",
        "answer": (
            "Under Account Settings > Notification Preferences, toggle on the channels you want (SMS, Email, WhatsApp) "
            "and select which status changes should trigger a notification you can choose to be notified on every status "
            "change or only key milestones (Picked Up, Out for Delivery, Delivered, Exception)."
        ),
    },
    {
        "category": "LR & Shipment Tracking",
        "question": "Why does my shipment show \"In Transit\" for several days without updates, and what should I do?",
        "answer": (
            "Status updates are logged at defined checkpoints (origin hub, transit hubs, destination hub) rather than "
            "continuously, so a gap of a day or two between updates on a long-distance route is normal. If there's been "
            "no update for more than 48 hours on the tracking timeline, click \"Raise a Concern\" on the tracking page, "
            "which creates a support ticket referencing that LR automatically."
        ),
    },
    {
        "category": "LR & Shipment Tracking",
        "question": "How do I share a live tracking link with my customer/consignee?",
        "answer": (
            "On the tracking results page, click \"Share Tracking Link\" to get a public URL (no login required) that "
            "shows real-time status for that specific LR only it doesn't expose any of your other shipments or account "
            "details, so it's safe to send directly to your consignee."
        ),
    },

    # Category: Pricing, Quotes & Payments
    {
        "category": "Pricing, Quotes & Payments",
        "question": "How is freight pricing calculated on the platform?",
        "answer": (
            "Pricing is based primarily on distance, chargeable weight (the greater of actual weight or volumetric weight), "
            "and vehicle/service type (FTL vs. PTL). Additional factors like fuel surcharge, toll charges on the route, "
            "and any special handling (fragile, hazardous) are itemized separately in the quote before you confirm, "
            "so there are no hidden charges at delivery."
        ),
    },
    {
        "category": "Pricing, Quotes & Payments",
        "question": "How do I get an instant rate quote before confirming a booking?",
        "answer": (
            "On the Book Shipment page, fill in pickup/drop locations and package weight, then click \"Get Quote\" "
            "instead of \"Confirm Booking\" this shows the estimated cost breakdown without creating an actual booking, "
            "so you can compare FTL vs. PTL costs before deciding."
        ),
    },
    {
        "category": "Pricing, Quotes & Payments",
        "question": "What payment methods are accepted?",
        "answer": (
            "UPI, net banking, debit/credit cards, and for verified business accounts with sufficient shipment history "
            "a monthly credit billing cycle (see Question 27). All online payments are processed immediately and the "
            "booking confirms as soon as payment clears."
        ),
    },
    {
        "category": "Pricing, Quotes & Payments",
        "question": "How do I apply for a credit account / monthly billing cycle?",
        "answer": (
            "Under Account Settings > Billing, click \"Apply for Credit Terms.\" This requires your account to be at least "
            "60 days old with a minimum shipment history (typically 10+ completed shipments) and involves a credit check "
            "against your GST filing history. If approved, you'll be assigned a credit limit and can book shipments "
            "against it without paying upfront, with a consolidated invoice issued monthly."
        ),
    },
    {
        "category": "Pricing, Quotes & Payments",
        "question": "Where can I download my monthly invoice/GST invoice for accounting purposes?",
        "answer": (
            "Go to Account Settings > Invoices & Billing, where all invoices are listed by month. Click \"Download\" "
            "next to any invoice to get a GST-compliant PDF, or use \"Download All (ZIP)\" to get a full financial "
            "year's invoices at once for your accountant."
        ),
    },
    {
        "category": "Pricing, Quotes & Payments",
        "question": "My payment was deducted but the booking shows as failed - what should I do?",
        "answer": (
            "This usually happens when the payment gateway confirms the deduction slightly later than our booking system's "
            "timeout. Don't attempt the payment again immediately check My Bookings first to confirm whether the booking "
            "actually went through. If the booking genuinely shows failed and the amount was deducted, it is auto-refunded "
            "within 5-7 business days; if it hasn't reflected after that window, raise a support ticket with your payment "
            "reference number."
        ),
    },

    # Category: Documentation & Compliance
    {
        "category": "Documentation & Compliance",
        "question": "Do I need to generate an E-Way Bill separately, or does BoxNFreight do it for me?",
        "answer": (
            "For shipments above the E-Way Bill threshold value, you (as the consignor) are responsible for generating "
            "the E-Way Bill on the government GST portal, since it's tied to your GSTIN and invoice BoxNFreight cannot "
            "generate it on your behalf. However, once generated, you can attach the E-Way Bill number to your booking "
            "under \"Documentation\" so it travels with the LR."
        ),
    },
    {
        "category": "Documentation & Compliance",
        "question": "What documents should accompany the shipment for interstate transport?",
        "answer": (
            "At minimum: the invoice for the goods, the E-Way Bill (where applicable by value threshold), and the LR. "
            "For certain goods categories (hazardous materials, high-value electronics), additional permits may be required - "
            "these are flagged automatically on the booking form based on the \"nature of goods\" you select."
        ),
    },
    {
        "category": "Documentation & Compliance",
        "question": "How do I upload my GST invoice and E-way bill number against a booking?",
        "answer": (
            "Open the booking under My Bookings, go to the \"Documentation\" tab, and click \"Add Document.\" You can upload "
            "the invoice PDF directly and enter the E-Way Bill number in the corresponding field - this information then appears "
            "on the LR and is available to the driver and at checkpoints during transit."
        ),
    },
    {
        "category": "Documentation & Compliance",
        "question": "What happens if my shipment gets stopped for document verification during transit?",
        "answer": (
            "This shows as an \"Exception\" status with the reason \"Document Verification Hold.\" Our transit team is "
            "notified automatically and will reach out if additional documentation is needed from you. Most document holds "
            "are resolved within a few hours once the correct paperwork is provided or verified with the checkpoint authority."
        ),
    },
    {
        "category": "Documentation & Compliance",
        "question": "Do I need a separate LR for each invoice if shipping multiple invoices to the same consignee in one truck?",
        "answer": (
            "Not necessarily a single LR can reference multiple invoice numbers for the same consignor-consignee pair "
            "in one shipment, entered as a list when generating the LR. However, if the invoices have different consignees "
            "even within the same truck (a multi-drop PTL scenario), separate LRs are required for each consignee."
        ),
    },

    # Category: Delivery & Proof of Delivery
    {
        "category": "Delivery & Proof of Delivery",
        "question": "How do I get Proof of Delivery (POD) after my shipment is delivered?",
        "answer": (
            "Once the consignee signs for the goods (digitally on the driver's device, or physically with a scanned copy), "
            "the POD becomes available automatically under My Bookings > [shipment] > \"View POD,\" usually within a few hours "
            "of the \"Delivered\" status update. You'll also receive it automatically if you have delivery notifications enabled."
        ),
    },
    {
        "category": "Delivery & Proof of Delivery",
        "question": "Can the consignee refuse delivery, and what happens to the shipment?",
        "answer": (
            "Yes if the consignee refuses delivery (wrong goods, damage on arrival, etc.), the driver logs the refusal "
            "reason on the spot and the shipment status changes to \"Delivery Refused.\" You'll be notified immediately "
            "and can choose to have the goods returned to origin (return shipping charges apply) or redirected to an "
            "alternate address."
        ),
    },
    {
        "category": "Delivery & Proof of Delivery",
        "question": "How do I schedule a specific delivery time window for time-sensitive shipments?",
        "answer": (
            "On the booking form, under \"Delivery Preferences,\" you can request a specific time window "
            "(morning/afternoon/evening) for FTL bookings. This is a preference rather than a guarantee for standard service "
            "for hard delivery-time commitments, select \"Priority Delivery\" at an additional cost, which does carry "
            "a guaranteed window."
        ),
    },
    {
        "category": "Delivery & Proof of Delivery",
        "question": "What if the consignee is unavailable at the delivery address?",
        "answer": (
            "The driver will attempt delivery up to 2 times before the shipment is marked \"Delivery Attempt Failed\" "
            "and held at the nearest hub for up to 3 days, during which you or the consignee can reschedule via the tracking page. "
            "After 3 days, unclaimed shipments are automatically returned to origin."
        ),
    },
    {
        "category": "Delivery & Proof of Delivery",
        "question": "How long does BoxNFreight retain POD documents, and can I request older PODs?",
        "answer": (
            "PODs are retained and accessible in your account for 12 months from delivery date. For older PODs, submit a "
            "request through Support with the LR number archived PODs are retrievable but may take 3-5 business days since "
            "they're pulled from cold storage rather than the live system."
        ),
    },

    # Category: Claims, Damage & Insurance
    {
        "category": "Claims, Damage & Insurance",
        "question": "My shipment arrived damaged - how do I file a claim?",
        "answer": (
            "Go to My Bookings > [shipment] > \"File a Claim\" within 48 hours of delivery claims filed after this window "
            "are much harder to substantiate and may be rejected. You'll need to describe the damage, upload photos, "
            "and reference the POD, which should ideally note the damage at the time of signing."
        ),
    },
    {
        "category": "Claims, Damage & Insurance",
        "question": "Does BoxNFreight offer transit insurance, and how do I add it to a booking?",
        "answer": (
            "Yes, optional transit insurance can be added at the LR generation step, calculated as a small percentage of the "
            "declared goods value. Insured shipments have a much higher claim payout ceiling than the standard liability cap "
            "(see Question 44) and a faster claims process."
        ),
    },
    {
        "category": "Claims, Damage & Insurance",
        "question": "What is the process and timeline for claim settlement?",
        "answer": (
            "After filing, a claim is reviewed within 5 business days, during which our team may request additional evidence "
            "or coordinate with the delivery hub to review handling records. Approved claims for insured shipments are "
            "typically settled within 15 business days; non-insured claims (subject to the standard liability cap) can take "
            "longer as they go through a more manual review."
        ),
    },
    {
        "category": "Claims, Damage & Insurance",
        "question": "What evidence do I need to submit to support a damage or shortage claim?",
        "answer": (
            "Photos of the damaged goods and packaging, the POD (ideally with damage noted at signing), the original invoice "
            "showing declared value, and the LR number. Claims with damage noted directly on the POD at time of delivery are "
            "processed significantly faster than claims raised after the fact with no delivery-time documentation."
        ),
    },
    {
        "category": "Claims, Damage & Insurance",
        "question": "Is there a liability cap per shipment if goods are lost or damaged and I didn't purchase insurance?",
        "answer": (
            "Yes without additional insurance, standard carrier liability is capped at a fixed amount per kg of declared "
            "weight, as per the terms accepted at booking. This cap is often well below the actual value of high-value goods, "
            "which is why we recommend adding transit insurance for anything above typical consignment value."
        ),
    },

    # Category: Cancellations & Refunds
    {
        "category": "Cancellations & Refunds",
        "question": "What is the cancellation policy and are there cancellation charges?",
        "answer": (
            "Free before vehicle assignment. After vehicle assignment but before pickup, a flat cancellation fee applies "
            "to cover the dispatched vehicle cost. After pickup, cancellation is treated as a return-to-origin request "
            "rather than a standard cancellation, with charges equivalent to a reverse shipment."
        ),
    },
    {
        "category": "Cancellations & Refunds",
        "question": "How long does a refund take after a successful cancellation?",
        "answer": (
            "Refunds to the original payment method are initiated immediately and typically reflect within 5-7 business "
            "days, depending on your bank/payment provider's processing time. Refunds to a BoxNFreight wallet (if selected) "
            "are instant."
        ),
    },
    {
        "category": "Cancellations & Refunds",
        "question": "Can I convert a cancelled booking's paid amount into wallet credit instead of a refund?",
        "answer": (
            "Yes on the cancellation confirmation screen, choose \"Add to Wallet\" instead of \"Refund to Source.\" "
            "Wallet credit is available instantly and can be applied automatically to your next booking, which is faster "
            "than a bank refund if you plan to book again soon."
        ),
    },

    # Category: Support, Escalation & Account Management
    {
        "category": "Support, Escalation & Account Management",
        "question": "How do I escalate an issue if I'm not satisfied with the first response from support?",
        "answer": (
            "On any resolved ticket, click \"Not Satisfied? Escalate\" to route it directly to a senior support agent "
            "rather than opening a new ticket - this preserves the full history of the original conversation so you "
            "don't have to re-explain the issue."
        ),
    },
    {
        "category": "Support, Escalation & Account Management",
        "question": "What are BoxNFreight's support hours and how can I reach a human agent?",
        "answer": (
            "Chat and phone support are available 7 AM-11 PM, 7 days a week; email support is monitored 24/7 with "
            "responses typically within 4 hours during support hours. For urgent in-transit issues (accidents, major delays), "
            "the in-app \"Urgent Issue\" button routes directly to the live operations team regardless of hour."
        ),
    },
    {
        "category": "Support, Escalation & Account Management",
        "question": "How do I request a dedicated account manager for high-volume shipping accounts?",
        "answer": (
            "Accounts averaging more than a set number of shipments per month (currently 50+) automatically become "
            "eligible for a dedicated account manager - you'll see an \"Request Account Manager\" option under Account "
            "Settings > Support Preferences once you cross that threshold, or you can proactively request early review "
            "if your volume is growing quickly."
        ),
    },
]


def init_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Recreate / Create faqs table to ensure clean schema and clear existing FAQs
    cursor.execute("DROP TABLE IF EXISTS faqs")
    cursor.execute(
        """
        CREATE TABLE faqs (
            id INTEGER PRIMARY KEY,
            category TEXT,
            question TEXT,
            answer TEXT
        )
        """
    )

    # Create tickets table if not exists with required schema
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tickets'")
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) FROM tickets")
        if cursor.fetchone()[0] == 0:
            cursor.execute("DROP TABLE tickets")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY,
            title TEXT,
            description TEXT,
            status TEXT,
            category TEXT,
            agent_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Insert all 50 BoxNFreight FAQs
    cursor.executemany(
        """
        INSERT INTO faqs (category, question, answer)
        VALUES (:category, :question, :answer)
        """,
        BOXNFREIGHT_FAQS,
    )

    conn.commit()

    # Verify and print count
    cursor.execute("SELECT COUNT(*) FROM faqs")
    count = cursor.fetchone()[0]
    print(f"Total FAQs in database: {count}")

    conn.close()
    print(f"Database initialized successfully at: {db_path}")


if __name__ == "__main__":
    init_db()
