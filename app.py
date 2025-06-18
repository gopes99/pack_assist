from flask import Flask, render_template, request, redirect, session, jsonify, send_file, abort
import sqlite3
import os
from flask_cors import CORS
from fido2.server import Fido2Server
from fido2.webauthn import PublicKeyCredentialRpEntity
from fido2 import cbor
from fido2.webauthn import AuthenticatorAssertionResponse
import qrcode
from io import BytesIO
from base64 import b64decode
from hashlib import sha256

app = Flask(__name__)
app.secret_key = os.urandom(32)
CORS(app)

rp = PublicKeyCredentialRpEntity("localhost", "Secure QR App")
server = Fido2Server(rp)

# ======== DB UTILITY ========
def get_db():
    return sqlite3.connect("users.db")

# ======== ROUTES ========
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate_qr", methods=["POST"])
def generate_qr():
    container_id = request.form.get("container_id")
    contents = request.form.get("contents")

    if not container_id or not contents:
        return "Missing fields", 400

    # Encrypt content
    key = sha256((container_id + "biometric").encode()).digest()
    enc = bytes([a ^ b for a, b in zip(contents.encode(), key)])  # simple XOR for demo
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO containers (id, content) VALUES (?, ?)", (container_id, enc))
    conn.commit()
    conn.close()

    # Generate QR linking to /view/<id>
    qr = qrcode.make(request.host_url + "view/" + container_id)
    buf = BytesIO()
    qr.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    elif request.method == "POST":
        username = request.form.get("username")
        if not username:
            return "Missing username", 400
        session["username"] = username
        registration_data, state = server.register_begin(
            {"id": username.encode(), "name": username, "displayName": username},
            user_verification="preferred"
        )
        session["state"] = state
        return cbor.encode(registration_data)

@app.route("/register/complete", methods=["POST"])
def register_complete():
    data = cbor.decode(request.get_data())
    state = session.get("state")
    username = session.get("username")

    auth_data = server.register_complete(state, data)

    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO credentials (username, credential_id, public_key) VALUES (?, ?, ?)", (
        username,
        auth_data.credential_id,
        auth_data.public_key
    ))
    conn.commit()
    conn.close()
    return cbor.encode({"status": "ok"})

@app.route("/auth/options", methods=["POST"])
def auth_options():
    username = request.get_json().get("username")
    if not username:
        return "Missing username", 400

    conn = get_db()
    cursor = conn.execute("SELECT credential_id, public_key FROM credentials WHERE username=?", (username,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return abort(404)

    credentials = [{"id": row[0], "publicKey": row[1], "type": "public-key"}]
    auth_data, state = server.authenticate_begin(credentials)
    session["auth_state"] = state
    session["auth_user"] = username
    return cbor.encode(auth_data)

@app.route("/auth/verify", methods=["POST"])
def auth_verify():
    data = cbor.decode(request.get_data())
    state = session.get("auth_state")

    conn = get_db()
    cursor = conn.execute("SELECT credential_id, public_key FROM credentials WHERE username=?", (session["auth_user"],))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return abort(404)

    auth_data = {
        "type": "public-key",
        "id": row[0],
        "publicKey": row[1]
    }

    server.authenticate_complete(state, [auth_data], data)
    session["authenticated"] = True
    return cbor.encode({"status": "ok"})

@app.route("/view/<container_id>")
def view(container_id):
    if not session.get("authenticated"):
        return redirect("/login.html")

    conn = get_db()
    cursor = conn.execute("SELECT content FROM containers WHERE id=?", (container_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return "Container not found", 404

    key = sha256((container_id + "biometric").encode()).digest()
    decrypted = bytes([a ^ b for a, b in zip(row[0], key)])
    return render_template("view.html", container_id=container_id, contents=decrypted.decode(errors="ignore"))

@app.route("/static/<path:path>")
def static_proxy(path):
    return app.send_static_file(path)

# ======== MAIN ========
if __name__ == "__main__":
    app.run(debug=True)
