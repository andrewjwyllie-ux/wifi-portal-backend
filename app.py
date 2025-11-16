import os
from pprint import pprint

from flask import Flask, request, render_template_string
import stripe

app = Flask(__name__)

# --- Stripe configuration from environment variables ---
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
    print("✅ STRIPE_SECRET_KEY loaded", flush=True)
else:
    print("⚠ STRIPE_SECRET_KEY is not set", flush=True)

# --- VERY SIMPLE VOUCHER STORAGE (for testing only) ---

# Pretend these came from Google Sheets / Grandstream
VOUCHER_POOL = [
    "VOUCHER-TEST-001",
    "VOUCHER-TEST-002",
    "VOUCHER-TEST-003",
]

# session_id -> voucher_code
SESSION_VOUCHERS = {}


def allocate_voucher(session_id: str) -> str:
    """
    Take the next voucher from the pool and assign it to this session.
    """
    if session_id in SESSION_VOUCHERS:
        # Already assigned
        return SESSION_VOUCHERS[session_id]

    if not VOUCHER_POOL:
        # No vouchers left – in real life you'd handle this better
        return "NO-VOUCHERS-AVAILABLE"

    code = VOUCHER_POOL.pop(0)
    SESSION_VOUCHERS[session_id] = code
    print(f"🎟 Assigned voucher {code} to session {session_id}", flush=True)
    return code


@app.route("/")
def index():
    print("🏠 Index (/) hit", flush=True)
    return "App is running from DigitalOcean with Stripe + vouchers!\n"


@app.route("/wifi/success")
def wifi_success():
    # We expect Stripe to redirect here with ?session_id=cs_xxx
    session_id = request.args.get("session_id")

    if not session_id:
        html = """
        <html>
          <body>
            <h1>Payment received 🎉</h1>
            <p>We could not find a session_id in the URL.</p>
            <p>For testing, open: /wifi/success?session_id=cs_test_...</p>
          </body>
        </html>
        """
        return render_template_string(html)

    voucher = SESSION_VOUCHERS.get(session_id)

    if not voucher:
        html = f"""
        <html>
          <body>
            <h1>Payment found, but no voucher yet 🤔</h1>
            <p>Session ID: {session_id}</p>
            <p>Either the webhook hasn’t run yet, or this session didn’t get a voucher.</p>
          </body>
        </html>
        """
        return render_template_string(html)

    html = f"""
    <html>
      <body>
        <h1>Payment received 🎉</h1>
        <p>Your WiFi voucher code is:</p>
        <h2>{voucher}</h2>
        <p>Session ID: {session_id}</p>
      </body>
    </html>
    """
    return render_template_string(html)


@app.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    """
    Stripe webhook endpoint.
    - If Stripe secrets or signature header are missing: log and return 200.
    - If present: verify event, handle checkout.session.completed.
    - Never crash with 500; always log errors.
    """
    from flask import Response

    print("🔔 /stripe/webhook hit", flush=True)

    payload = request.get_data(as_text=True)
    headers = dict(request.headers)
    sig_header = headers.get("Stripe-Signature")

    print("Headers:", flush=True)
    pprint(headers)
    print("Payload:", flush=True)
    print(payload, flush=True)

    # If we're just testing with curl or secrets aren't set, don't try to verify
    if not STRIPE_SECRET_KEY or not STRIPE_WEBHOOK_SECRET or not sig_header:
        print("⚠ Missing Stripe config or signature header; "
              "skipping Stripe verification and returning 200.",
              flush=True)
        return Response("OK\n", status=200)

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=STRIPE_WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError as e:
        print("❌ Signature verification failed:", repr(e), flush=True)
        # Still return 200 so Stripe doesn't keep retrying forever
        return Response("Invalid signature\n", status=200)
    except Exception as e:
        print("❌ Error parsing Stripe event:", repr(e), flush=True)
        return Response("Webhook error\n", status=200)

    event_type = event.get("type")
    print(f"✅ Verified Stripe event type: {event_type}", flush=True)

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session.get("id")
        amount_total = session.get("amount_total")
        currency = session.get("currency")
        print(f"💰 checkout.session.completed: id={session_id}, "
              f"amount={amount_total}, currency={currency}",
              flush=True)

        if session_id:
            allocate_voucher(session_id)

    return Response("Received\n", status=200)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
