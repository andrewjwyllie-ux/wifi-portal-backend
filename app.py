from flask import Flask, render_template_string

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
