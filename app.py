from flask import Flask, request, render_template_string
from pprint import pprint

app = Flask(__name__)


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
    try:
        # Log headers and body so we can see what arrives
        print("🔔 Webhook hit")
        print("Headers:")
        pprint(dict(request.headers))
        print("Payload:")
        print(request.get_data(as_text=True))

        # Always succeed for now – no Stripe verification yet
        return "", 200
    except Exception as e:
        # Even if something weird happens, do NOT crash the app
        print("💥 Unexpected error in webhook handler:", repr(e))
        return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
