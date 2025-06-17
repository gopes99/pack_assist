from flask import Flask, render_template, request, redirect, send_file, jsonify
import qrcode
import sqlite3
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from urllib.parse import quote

app = Flask(__name__)
DATABASE = 'containers.db'

# Ensure database and tables exist
def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute('CREATE TABLE IF NOT EXISTS containers (id TEXT PRIMARY KEY, content TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS users (username TEXT, credential_id TEXT)')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect(DATABASE)
    containers = conn.execute("SELECT * FROM containers").fetchall()
    conn.close()
    return render_template('index.html', containers=containers)

@app.route('/add', methods=['POST'])
def add_container():
    cid = request.form['container_id']
    content = request.form['content']
    conn = sqlite3.connect(DATABASE)
    conn.execute("INSERT OR REPLACE INTO containers (id, content) VALUES (?, ?)", (cid, content))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/download/<container_id>')
def download_qr(container_id):
    container_id = container_id.strip()
    url = request.host_url + 'view.html?cid=' + quote(container_id)
    img = generate_qr_with_label(url, container_id)
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png', as_attachment=True, download_name=f"{container_id}.png")

def generate_qr_with_label(url, label):
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    font = ImageFont.load_default()
    draw = ImageDraw.Draw(img)
    text_width, text_height = draw.textbbox((0, 0), label, font=font)[2:]
    width, height = img.size
    new_img = Image.new("RGB", (width, height + 30), "white")
    new_img.paste(img, (0, 0))
    draw = ImageDraw.Draw(new_img)
    draw.text(((width - text_width) / 2, height + 5), label, font=font, fill="black")

    return new_img

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    credential_id = data.get('credential_id')

    if not username or not credential_id:
        return "Missing data", 400

    conn = sqlite3.connect(DATABASE)
    conn.execute("INSERT INTO users (username, credential_id) VALUES (?, ?)", (username, credential_id))
    conn.commit()
    conn.close()

    return "Registration successful!"

@app.route('/auth-credentials')
def auth_credentials():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT credential_id FROM users")
    credentials = [row[0] for row in cur.fetchall()]
    conn.close()
    return jsonify(credentials)

@app.route('/get-content/<container_id>')
def get_content(container_id):
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT content FROM containers WHERE id = ?", (container_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return row[0]
    return "Not found", 404

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
