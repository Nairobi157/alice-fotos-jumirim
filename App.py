
from flask import Flask, request, redirect, url_for, jsonify, session, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3, os, urllib.parse

app = Flask(__name__)
app.secret_key = "foto-jumirim-2026"
UPLOAD_FOLDER = "/tmp/static/uploads"
DB_PATH = "/tmp/fotos.db"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

WHATSAPP = "5515996216025"
NOME = "Alice - Fotos Jumirim"
SENHA = "666777"

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS fotos (id INTEGER PRIMARY KEY, filename TEXT, titulo TEXT, categoria TEXT, data TEXT, likes INTEGER DEFAULT 0)")
    con.commit()
    con.close()

def get_fotos():
    try:
        init_db()
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        fotos = con.execute("SELECT * FROM fotos ORDER BY id DESC").fetchall()
        con.close()
        return fotos
    except:
        return []

@app.route('/static/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/")
def index():
    fotos = get_fotos()
    admin = session.get("admin")
    html_fotos = ""
    for f in fotos:
        html_fotos += f"""
        <div style="background:#111;border:1px solid #222;border-radius:12px;overflow:hidden">
            <img src="/static/uploads/{f['filename']}" style="width:100%">
            <div style="padding:10px"><b>{f['titulo']}</b> - {f['categoria']}<br>
            <small>{f['data']} - ❤️ {f['likes']}</small><br>
            <a href="/like/{f['id']}" style="color:#d4af37">Curtir</a>
            {" <a href='/delete/"+str(f['id'])+"' style='color:red;margin-left:10px'>Apagar</a>" if admin else ""}
            </div>
        </div>
        """
    if not html_fotos:
        html_fotos = "<p style='color:#888'>Nenhuma foto ainda. Loga como admin e posta!</p>"

    admin_bar = f"""
    <div style="background:#d4af37;color:#000;padding:10px;text-align:center">MODO ADMIN - <a href="/admin/logout">Sair</a>
    <form action="/upload" method="post" enctype="multipart/form-data" style="background:#111;padding:15px;border-radius:10px;margin:10px auto;max-width:400px;color:white">
        <h3>Postar Foto</h3>
        <input type="file" name="foto" required style="width:100%;margin:5px 0"><br>
        <input name="titulo" placeholder="Titulo" required style="width:100%;padding:8px;margin:5px 0"><br>
        <select name="categoria" style="width:100%;padding:8px"><option>Ensaio</option><option>Casamento</option><option>Evento</option><option>Retrato</option></select><br>
        <button style="background:#d4af37;padding:10px;width:100%;border:none;border-radius:5px;margin-top:5px;font-weight:bold">POSTAR</button>
    </form>
    </div>
    """ if admin else ""

    login_form = "" if admin else """
    <div style="text-align:center;margin:20px">
    <form action="/admin/login" method="post" style="display:inline-block;background:#111;padding:15px;border-radius:10px;border:1px solid #222">
        <input type="password" name="senha" placeholder="Senha admin (666777)" style="padding:8px"><button style="padding:8px;background:#d4af37;border:none;margin-left:5px">Entrar Admin</button>
    </form></div>
    """

    return f"""
    <html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>{NOME}</title></head>
    <body style="background:#0a0a0a;color:white;font-family:Arial;margin:0">
    <header style="padding:20px;text-align:center;border-bottom:1px solid #222"><h1 style="color:#d4af37;margin:0">{NOME}</h1><p style="color:#888">Jumirim, Cerquilho e regiao</p></header>
    {admin_bar}
    {login_form}
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:15px;padding:20px;max-width:1100px;margin:auto">
    {html_fotos}
    </div>
    <div style="text-align:center;padding:30px">
        <a href="https://wa.me/{WHATSAPP}" style="background:#25D366;color:white;padding:12px 25px;border-radius:30px;text-decoration:none">Falar no WhatsApp</a>
    </div>
    </body></html>
    """

@app.route("/admin/login", methods=["POST"])
def login():
    if request.form.get("senha") == SENHA:
        session["admin"] = True
    return redirect(url_for("index"))

@app.route("/admin/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("index"))

@app.route("/upload", methods=["POST"])
def upload():
    if not session.get("admin"):
        return "Sem permissao", 403
    file = request.files.get("foto")
    if file:
        filename = datetime.now().strftime("%Y%m%d%H%M%S_") + secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        con = sqlite3.connect(DB_PATH)
        con.execute("INSERT INTO fotos (filename,titulo,categoria,data,likes) VALUES (?,?,?,?,0)", (filename, request.form.get("titulo","Foto"), request.form.get("categoria","Ensaio"), datetime.now().strftime("%d/%m/%Y")))
        con.commit()
        con.close()
    return redirect(url_for("index"))

@app.route("/delete/<int:foto_id>")
def delete_foto(foto_id):
    if not session.get("admin"):
        return "Sem permissao", 403
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT filename FROM fotos WHERE id=?", (foto_id,)).fetchone()
    if row:
        try: os.remove(os.path.join(UPLOAD_FOLDER, row[0]))
        except: pass
        con.execute("DELETE FROM fotos WHERE id=?", (foto_id,))
        con.commit()
    con.close()
    return redirect(url_for("index"))

@app.route("/like/<int:foto_id>")
def like(foto_id):
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE fotos SET likes=likes+1 WHERE id=?", (foto_id,))
    con.commit()
    con.close()
    return redirect(url_for("index"))

app = app
