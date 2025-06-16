from flask import Flask, render_template, request, send_file, redirect, url_for
import qrcode
import sqlite3
import io
from PIL import Image, ImageDraw, ImageFont
import os

app = Flask(__name__)

# Always run init_db, even on Render
def init_db():
    conn = sqlite3.connect("containers.db")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS containers (id TEXT PRIMARY KEY, content TEXT)"
    )
    conn.close()

init_db()  # <<< this is the important part, outside __main__


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/view')
def view():
    return render_template('view.html')

@app.route('/add', methods=['POST'])
def add_container():
    cid = request.form['container_id']
    content = request.form['contents']
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR REPLACE INTO containers (id, content) VALUES (?, ?)", (cid, content))
    return redirect(url_for('download_qr', container_id=cid))

@app.route('/download/<container_id>')
def download_qr(container_id):
    url = request.host_url.rstrip('/') + '/view?container=' + container_id
    img = generate_qr_with_label(url, container_id)

    byte_io = io.BytesIO()
    img.save(byte_io, 'PNG')
    byte_io.seek(0)
    return send_file(byte_io, mimetype='image/png', as_attachment=True,
                     download_name=f"{container_id}_qr.png")

@app.route('/get_content')
def get_content():
    cid = request.args.get('container')
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT content FROM containers WHERE id=?", (cid,))
        row = cur.fetchone()
    return row[0] if row else "No content found."

def generate_qr_with_label(data, label):
    qr = qrcode.QRCode(
        version=1, error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10, border=4
    )
    qr.add_data(data)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    font = ImageFont.load_default()
    label_height = 40
    new_img = Image.new("RGB", (img_qr.width, img_qr.height + label_height), "white")
    new_img.paste(img_qr, (0, 0))

    draw = ImageDraw.Draw(new_img)
    text_width, _ = draw.textsize(label, font=font)
    draw.text(((img_qr.width - text_width) // 2, img_qr.height + 10), label, fill="black", font=font)

    return new_img
init_db()
if __name__ == "__main__":
    app.run(debug=True)
