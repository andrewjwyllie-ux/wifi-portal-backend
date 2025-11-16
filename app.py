@app.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    # Very defensive version: never 500, always logs the error
    from pprint import pprint
    try:
        payload = request.get_data(as_text=True)
        headers = dict(request.headers)

        print("🔔 Webhook hit")
        print("Headers:")
        pprint(headers)
        print("Payload:")
        print(payload)

        # If we don't have Stripe configured yet, just log and return OK
        if not STRIPE_WEBHOOK_SECRET or not STRIPE_SECRET_KEY:
            print("⚠ Stripe secrets not fully configured; skipping verification.")
            return "", 200

        # Only do real Stripe verification if libs and secrets are present
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=headers.get("Stripe-Signature", ""),
                secret=STRIPE_WEBHOOK_SECRET,
            )
        except stripe.error.SignatureVerificationError as e:
            print("❌ Signature verification failed:", e)
            return "Invalid signature", 400
        except Exception as e:
            print("❌ Error parsing Stripe event:", repr(e))
            return "Webhook error", 400

        print("✅ Received Stripe event type:", event.get("type"))

        if event.get("type") == "checkout.session.completed":
            session = event["data"]["object"]
            print("💰 Checkout session completed:", session.get("id"))
            # Later: allocate voucher here

        return "", 200

    except Exception as e:
        # Absolute last-resort safety: never crash with 500
        print("💥 Unexpected error in webhook handler:", repr(e))
        return "Internal error", 200



