import os
import json
from datetime import datetime
from flask import Flask, request, render_template_string, abort
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# === CONFIG ===
GRANDSTREAM_URL = os.getenv("GRANDSTREAM_URL", "http://192.168.1.67/cp/index.html")
GOOGLE_SHEETS_CREDS_JSON = os.getenv("GOOGLE_SHEETS_CREDS_JSON")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

# Map product query param -> worksheet/tab name
PRODUCT_SHEET_MAP = {
    "1device": "1device",
    "3devices": "3devices",
    "5devices": "5devices",
}

# === GOOGLE SHEETS CLIENT SETUP ===
if not GOOGLE_SHEETS_CREDS_JSON or not GOOGLE_SHEET_ID:
    raise RuntimeError("Missing GOOGLE_SHEETS_CREDS_JSON or GOOGLE_SHEET_ID env variables")

creds_dict = json.loads(GOOGLE_SHEETS_CREDS_JSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(credentials)

sheet = gc.open_by_key(GOOGLE_SHEET_ID)


def get_next_voucher(product_key: str) -> str:
    """
    Returns next unused voucher code for the given product_key
    and marks it as used in the sheet.
    """
    if product_key not in PRODUCT_SHEET_MAP:
        raise ValueError("Unknown product")

    worksheet_name = PRODUCT_SHEET_MAP[product_key]
    ws = sheet.worksheet(worksheet_name)

    # Assumes:
    # Col A: voucher code
    # Col B: used flag (blank = unused)
    # Col C: timestamp (optional)
    all_rows = ws.get_all_values()
    # Skip header if you have one; if no header, start at row 1
    start_row = 2 if all_rows and all_rows[0][0].lower() == "code" else 1

    for i in range(start_row, len(all_rows) + 1):
        used_cell = ws.cell(i, 2).value  # Column B
        if not used_cell:
            code = ws.cell(i, 1).value  # Column A
            if not code:
                continue

            # Mark as used
            ws.update_cell(i, 2, "yes")
            ws.update_cell(i, 3, datetime.utcnow().isoformat() + "Z")
            return code

    # If we get here, no codes left
    raise RuntimeError("No voucher codes available for this product")


SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>WiFi Access Voucher</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background-color: #f5f5f5;
      margin: 0;
      padding: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
    }
    .card {
      background: white;
      padding: 1.5rem;
      border-radius: 12px;
      max-width: 480px;
      width: 100%;
      box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    }
    h1 {
      font-size: 1.4rem;
      margin-top: 0;
      margin-bottom: 0.75rem;
      text-align: center;
    }
    .voucher-box {
      margin: 1rem 0;
      padding: 1rem;
      border-radius: 8px;
      border: 2px dashed #0070f3;
      font-size: 1.3rem;
      font-weight: 600;
      text-align: center;
      word-break: break-all;
      background-color: #f0f7ff;
    }
    p {
      margin: 0.4rem 0;
    }
    .hint {
      font-size: 0.9rem;
      color: #555;
    }
    .btn {
      display: inline-block;
      width: 100%;
      text-align: center;
      margin-top: 1rem;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      background: #0070f3;
      color: white;
      text-decoration: none;
      font-weight: 600;
    }
    .btn:hover {
      background: #0059c1;
    }
  </style>
</head>
<body>
  <div class="card">
    <h1>Payment Successful</h1>
    <p>Your WiFi access voucher code is:</p>
    <div class="voucher-box">{{ voucher_code }}</div>
    <p class="hint">
      Please copy and save this code for your records.
      You will need it on the WiFi login page.
    </p>
    <a class="btn" href="{{ grandstream_url }}">Back to WiFi Login Page</a>
  </div>
</body>
</html>
"""


@app.route("/success")
def success():
    product = request.args.get("product")
    if not product:
        abort(400, description="Missing product parameter")

    try:
        voucher_code = get_next_voucher(product)
    except Exception as e:
        # Show a graceful error if something goes wrong
        return f"Error retrieving voucher: {str(e)}", 500

    return render_template_string(
        SUCCESS_TEMPLATE,
        voucher_code=voucher_code,
        grandstream_url=GRANDSTREAM_URL,
    )


@app.route("/")
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
