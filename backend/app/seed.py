from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from .database import SessionLocal
from .models import Note, Ticket

DEMO_TICKETS = [
    ("Priya Sharma", "priya.sharma@acme.co", "Invoice shows duplicate charge",
     "I was billed twice for the Pro plan on the same day. Transaction IDs differ by 8 seconds. Need refund of the second charge."),
    ("Daniel Chen", "daniel@liftlabs.io", "Cannot reset account password",
     "The 'reset password' email never arrives even though the UI says it was sent. Checked spam folder too."),
    ("Amara Okafor", "amara.okafor@northstar.example", "API returning 500 on bulk import",
     "POST /api/import with a CSV of ~2k rows intermittently returns 500. Works for smaller batches. Stack trace attached."),
    ("Tom Brady", "tom.b@greenfield.dev", "Feature request: dark mode",
     "Would love a dark theme for the dashboard. The team works late and the white background is harsh on the eyes."),
    ("Sana Iqbal", "sana.i@petalmarket.com", "Refund status stuck in 'Processing'",
     "Refund has been in processing for 7 days. Payment was reversed on our side already. Please confirm the status."),
    ("Marcelo Silva", "m.silva@verda.example", "Emails marked as spam by receivers",
     "Several customers report our order confirmations land in spam. DKIM/SPF checks look okay on our end."),
    ("Hannah Lee", "hannah.lee@quokka.craft", "Order #4821 delivered to wrong address",
     "Package was delivered to an old address even though the shipping address was updated before dispatch."),
    ("Ravi Kulkarni", "ravi.k@simplysync.app", "Mobile app crashes on startup",
     "Since the last update, app crashes immediately after the splash screen on Android 14. Reinstalling didn't help."),
    ("Emma Watson", "emma.w@brightbyte.co", "Question about data export format",
     "Can exports include custom fields we defined on tickets? The CSV export currently only has default columns."),
    ("Kenji Nakamura", "kenji.n@tokyohost.jp", "Domain verification keeps failing",
     "I added the TXT record as instructed but verification stays pending for 12 hours. Record confirmed present via dig."),
    ("Layla Hassan", "layla.h@muna.example", "Double subscription renewal",
     "Auto-renew bounced out of retries and charged twice. First charge failed, second succeeded — I now have two active seats."),
    ("Oscar Nilsson", "oscar.n@nordheim.se", "Webhook deliveries delayed",
     "Webhooks for successful payments arrive 20–40 minutes late. Our Stripe dashboard shows instant delivery."),
    ("Grace Kim", "grace.k@blooma.app", "SSO users cannot see inherited permissions",
     "Users created via SAML don't inherit role permissions until they log out and back in."),
    ("Ivan Petrov", "ivan.p@coldstorage.ru", "Storage plan upgrade not applied",
     "Upgraded from 50GB to 200GB, billing updated, but the account still reports 50GB capacity."),
    ("Fatima Zahra", "fatima.z@atlasfiber.net", "Incident: service degraded briefly",
     "Reporting a 4-minute outage we observed on our uptime monitor at 02:10 UTC. No email from you about it."),
]

DEMO_NOTES = {
    "refund_duplicate": [
        ("Confirmed duplicate charge with payment gateway. Issued refund for order #88321.", "Priya"),
        ("Refund processed, customer notified. Closing ticket after 48h observation.", "Support Lead"),
    ],
    "password_reset": [
        ("Whitelisted the notification domain; checked our email provider logs.", "Daniel"),
        ("Asked customer to retry; email delivery confirmed this time.", "Support Lead"),
    ],
    "api_import": [
        ("Reproduced the 500 — root cause is a 3s timeout on the import worker. Bumped to 30s.", "Riley"),
        ("Fix deployed to staging; monitoring prod rollout.", "Riley"),
    ],
    "spam_mails": [
        ("Added SPF record for subdomain; rerunning deliverability tests.", "Hannah"),
    ],
}


def maybe_seed() -> None:
    """Populate a little demo data on first boot so the app looks alive."""
    db = SessionLocal()
    try:
        ticket_count = db.scalar(select(func.count(Ticket.id))) or 0
        if ticket_count:
            return

        now = datetime.now(timezone.utc)
        note_pool = list(DEMO_NOTES.values())
        for i, (name, email, subject, description) in enumerate(DEMO_TICKETS):
            status = ("Open", "In Progress", "Closed")[i % 3]
            created_at = now - timedelta(days=(len(DEMO_TICKETS) - i) % 7, hours=(i * 3) % 12)
            ticket = Ticket(
                ticket_id=f"TKT-{i + 1:04d}",
                customer_name=name,
                customer_email=email,
                subject=subject,
                description=description,
                status=status,
                created_at=created_at,
                updated_at=created_at,
            )
            db.add(ticket)
            db.flush()

            for text, author in note_pool[i % len(note_pool)]:
                db.add(
                    Note(
                        ticket_id=ticket.ticket_id,
                        note_text=text,
                        author=author,
                        created_at=created_at + timedelta(hours=4),
                    )
                )
        db.commit()
    finally:
        db.close()