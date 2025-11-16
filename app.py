from flask import Flask, request, render_template_string
from pprint import pprint

app = Flask(__name__)


@app.route("/")
def index():
    print("🏠 Index (/) hit")
    return "App is running from DigitalOcean!\n"


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
        print("🔔 /stripe/webhook hit")
        print("Headers:")
        pprint(dict(request.headers))
        print("Payload:")
        print(request.get_data(as_text=True))
        return "Webhook received OK\n", 200
    except Exception as e:
        print("💥 Unexpected error in webhook handler:", repr(e))
        return "OK\n", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
