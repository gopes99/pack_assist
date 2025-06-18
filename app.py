from flask import Flask, render_template, request, redirect, session, jsonify, abort
import sqlite3
import os
from flask_cors import CORS
from fido2.server import Fido2Server
from fido2.webauthn import PublicKeyCredentialRpEntity
from fido2 import cbor

app = Flask(__name__)
app.secret_key = os.urandom(32)
CORS(app)

rp = PublicKeyCredentialRpEntity("localhost", "Secure QR App")
server = Fido2Server(rp)

def get_db():
    return sqlite3.connect("users.db")

@app.route("/")
def index():
    return render_template("index.html")

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

@app.route("/view", methods=["GET"])
def view():
    return render_template("view.html")

# Add QR generation routes or any others as needed

if __name__ == "__main__":
    app.run(debug=True)
