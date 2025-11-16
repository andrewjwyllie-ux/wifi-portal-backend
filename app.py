import os
from flask import Flask, request, jsonify, render_template_string
import stripe

app = Flask(__name__)

# Stripe config from environment variables
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


@app.route("/")
def index():
    return "App is running!"


@app.route("/wifi/success")
def wifi_success():
    html = """
    <html>
      <body>
        <h1>Payment received 🎉</h1>
        <p>Thanks! Your voucher feature will go here soon.</p>
      </body>
    </html>
    """
    return render_template_string(html)


@app.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    # Verify webhook signature
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature", "")

    if not STRIPE_WEBHOOK_SECRET:
        # If not configured yet, just log and return OK so deployments don’t break
        print("⚠ STRIPE_WEBHOOK_SECRET not set, skipping verification")
        print("Webhook payload:", payload)
        return "", 200

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=STRIPE_WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError as e:
        print("❌ Webhook signature verification failed:", e)
        return "Invalid signature", 400
    except Exception as e:
        print("❌ Error parsing webhook:", e)
        return "Webhook error", 400

    # Handle the event
    print("✅ Received event:", event["type"])

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        print("💰 Checkout session completed:", session.get("id"))
        # 👉 Later: allocate voucher based on session/price, store mapping, etc.

    # You can add more event types later as needed

    return "", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

