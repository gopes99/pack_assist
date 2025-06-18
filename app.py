from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, send_from_directory
import sqlite3
import qrcode
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import base64
import os

app = Flask(__name__)

# ====== Database Initialization ======
def init_db():
    conn = sqlite3.connect("database.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS containers (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            credential_id TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

app = Flask(__name__)

# Initialize DB on startup (instead of @app.before_first_request)
with app.app_context():
    init_db()


# ====== Home (QR Generator) ======
@app.route("/", methods=["GET"])
def index():
    conn = sqlite3.connect("database.db")
    containers = conn.execute("SELECT * FROM containers").fetchall()
    conn.close()
    return render_template("index.html", containers=containers)

# ====== Add Container ======
@app.route("/add", methods=["POST"])
def add_container():
    cid = request.form["container_id"]
    content = request.form["content"]
    conn = sqlite3.connect("database.db")
    conn.execute("INSERT OR REPLACE INTO containers (id, content) VALUES (?, ?)", (cid, content))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

# ====== QR Generation with Label ======
def generate_qr_with_label(url, label):
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img_qr = qr.make_image(fill="black", back_color="white").convert("RGB")

    draw = ImageDraw.Draw(img_qr)
    font = ImageFont.load_default()

    # Calculate label size
    text_width = draw.textlength(label, font=font)
    text_height = 10

    new_img = Image.new("RGB", (img_qr.width, img_qr.height + text_height + 10), "white")
    new_img.paste(img_qr, (0, 0))
    draw = ImageDraw.Draw(new_img)
    draw.text(((new_img.width - text_width) // 2, img_qr.height + 5), label, fill="black", font=font)

    return new_img

# ====== QR Download Endpoint ======
@app.route("/download/<path:container_id>")
def download_qr(container_id):
    print("QR requested for:", container_id)
    url = request.url_root + f"static/view.html?id={container_id}"
    img = generate_qr_with_label(url, container_id)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png", as_attachment=True, download_name=f"{container_id}.png")

# ====== Credential Registration ======
@app.route("/register_credential", methods=["POST"])
def register_credential():
    data = request.get_json()
    credential_id = data.get("credential_id")
    if not credential_id:
        return jsonify({"status": "error", "message": "Missing credential_id"}), 400

    conn = sqlite3.connect("database.db")
    conn.execute("INSERT INTO credentials (credential_id) VALUES (?)", (credential_id,))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})

# ====== List of Allowed Credentials ======
@app.route("/allowed_credentials", methods=["GET"])
def allowed_credentials():
    conn = sqlite3.connect("database.db")
    rows = conn.execute("SELECT credential_id FROM credentials").fetchall()
    conn.close()
    ids = [r[0] for r in rows]
    return jsonify({"allowed": ids})

# ====== Get Container Content (View page fetches this) ======
@app.route("/get_container/<cid>", methods=["GET"])
def get_container(cid):
    conn = sqlite3.connect("database.db")
    row = conn.execute("SELECT content FROM containers WHERE id=?", (cid,)).fetchone()
    conn.close()
    if row:
        return jsonify({"status": "ok", "content": row[0]})
    else:
        return jsonify({"status": "error", "message": "Not found"}), 404
# ========== Register Page ===========
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Handle WebAuthn registration here
        data = request.get_json()
        # Process and store the credential in the DB
        return jsonify({'status': 'ok'})

    # On GET, serve the HTML page
    return send_from_directory('static', 'register.html')




# ====== Run Local Dev Server ======
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
