
from flask import Flask, request, redirect, session, send_from_directory, render_template_string
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3, os, urllib.parse
app = Flask(__name__)
app.secret_key = "foto-jumirim-2026"
UPLOAD_FOLDER = "/tmp/static/uploads"
DB_PATH = "/tmp/fotos.db"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
SENHA = "666777"
WHATSAPP = "5515996216025"
def init_db():
    try:
        con = sqlite3.connect(DB_PATH)
        con.execute("CREATE TABLE IF NOT EXISTS fotos (id INTEGER PRIMARY KEY, filename TEXT, titulo TEXT, categoria TEXT, data TEXT, likes INTEGER DEFAULT 0)")
        con.execute("CREATE TABLE IF NOT EXISTS agendamentos (id INTEGER PRIMARY KEY, nome TEXT, whatsapp TEXT, tipo TEXT, data_evento TEXT, horario TEXT, local TEXT, mensagem TEXT, status TEXT, criado TEXT)")
        con.commit()
        con.close()
    except: pass
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
def get_ag():
    try:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        ag = con.execute("SELECT * FROM agendamentos ORDER BY id DESC").fetchall()
        con.close()
        return ag
    except:
        return []
@app.route('/static/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)
@app.route("/")
def index():
    fotos = get_fotos()
    html = ""
    for f in fotos:
        html+=f'<div style="background:#111;border:1px solid #222;border-radius:12px;overflow:hidden"><img src="/static/uploads/{f[1]}" style="width:100%;height:200px;object-fit:cover"><div style="padding:10px"><b>{f[2]}</b> - {f[3]}<br><small>{f[4]}</small></div></div>'
    if not html:
        html='<p style="color:#888;text-align:center;grid-column:1/-1">Nenhuma foto ainda - vai no /admin e posta!</p>'
    return f'<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Alice Fotos</title></head><body style="background:#0a0a0a;color:#fff;font-family:Arial;margin:0"><header style="padding:20px;text-align:center;border-bottom:1px solid #222"><h1 style="color:#d4af37">Alice - Fotos Jumirim</h1><a href="#agendar" style="background:#d4af37;color:#000;padding:10px 20px;border-radius:20px;text-decoration:none">Agendar</a> <a href="https://wa.me/{WHATSAPP}" style="background:#25D366;color:#fff;padding:10px 20px;border-radius:20px;text-decoration:none">WhatsApp</a></header><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:15px;padding:20px;max-width:1100px;margin:auto">{html}</div><div id="agendar" style="background:#111;padding:30px"><div style="max-width:500px;margin:auto"><h2 style="color:#d4af37;text-align:center">Agendar Ensaio</h2><form action="/agendar" method="post"><input name="nome" placeholder="Seu nome" required style="width:100%;padding:10px;margin:5px 0;background:#1a1a1a;border:1px solid #222;color:#fff;border-radius:6px"><input name="whatsapp" placeholder="WhatsApp" required style="width:100%;padding:10px;margin:5px 0;background:#1a1a1a;border:1px solid #222;color:#fff;border-radius:6px"><select name="tipo" style="width:100%;padding:10px;margin:5px 0;background:#1a1a1a;border:1px solid #222;color:#fff"><option>Ensaio</option><option>Casamento</option><option>Evento</option></select><input name="data_evento" type="date" style="width:100%;padding:10px;margin:5px 0;background:#1a1a1a;border:1px solid #222;color:#fff"><input name="local" placeholder="Local" style="width:100%;padding:10px;margin:5px 0;background:#1a1a1a;border:1px solid #222;color:#fff"><textarea name="mensagem" placeholder="Mensagem" style="width:100%;padding:10px;margin:5px 0;background:#1a1a1a;border:1px solid #222;color:#fff"></textarea><button style="width:100%;background:#d4af37;padding:12px;border:none;border-radius:6px;font-weight:bold">Enviar pro WhatsApp</button></form></div></div></body></html>'

@app.route("/agendar", methods=["POST"])
def agendar():
    init_db()
    d = {k: request.form.get(k) for k in ["nome","whatsapp","tipo","data_evento","local","mensagem"]}
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO agendamentos (nome,whatsapp,tipo,data_evento,horario,local,mensagem,status,criado) VALUES (?,?,?,?,?,?,?, 'Pendente',?)", (d["nome"],d["whatsapp"],d["tipo"],d["data_evento"],"",d["local"],d["mensagem"],datetime.now().strftime("%d/%m/%Y %H:%M")))
    con.commit()
    con.close()
    msg = f"Ola! Sou {d['nome']}, quero agendar {d['tipo']} dia {d['data_evento']} em {d['local']}. {d['mensagem']} Meu Whats: {d['whatsapp']}"
    return redirect(f"https://wa.me/{WHATSAPP}?text={urllib.parse.quote(msg)}")

@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method=="POST":
        if request.form.get("senha")==SENHA:
            session["admin"]=True
            return redirect("/admin")
    if not session.get("admin"):
        return '<html><body style="background:#0a0a0a;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh"><form method="post" style="background:#111;padding:20px;border-radius:10px"><h3>Admin Alice</h3><input type="password" name="senha" placeholder="666777"><button>Entrar</button></form></body></html>'
    fotos=get_fotos()
    ags=get_ag()
    lista=""
    for ag in ags:
        lista+=f'<div style="background:#0a0a0a;border:1px solid #222;padding:10px;margin:5px 0;border-radius:6px"><b>{ag[1]}</b> - {ag[3]} dia {ag[4]}<br>{ag[2]} - {ag[6]}<br>{ag[7]}</div>'
    fotos_html=""
    for f in fotos:
        fotos_html+=f'<div style="background:#111;border:1px solid #222;border-radius:8px;overflow:hidden"><img src="/static/uploads/{f[1]}" style="width:100%;height:120px;object-fit:cover"><div style="padding:5px"><small>{f[2]}</small><br><a href="/delete/{f[0]}" style="color:red">Apagar</a></div></div>'
    return f'<html><body style="background:#0a0a0a;color:#fff;font-family:Arial;margin:0"><header style="background:#d4af37;color:#000;padding:10px;display:flex;justify-content:space-between"><b>ADMIN</b><a href="/admin/logout" style="color:#000">Sair</a></header><div style="padding:20px;max-width:1000px;margin:auto"><div style="display:grid;grid-template-columns:1fr 1fr;gap:20px"><div style="background:#111;padding:15px;border-radius:10px"><h3>Postar Foto</h3><form action="/upload" method="post" enctype="multipart/form-data"><input type="file" name="foto" required style="width:100%"><input name="titulo" placeholder="Titulo" required style="width:100%;padding:8px;margin:5px 0;background:#1a1a1a;border:1px solid #222;color:#fff"><select name="categoria" style="width:100%;padding:8px;background:#1a1a1a;color:#fff"><option>Ensaio</option><option>Casamento</option><option>Evento</option></select><button style="width:100%;background:#d4af37;padding:10px;border:none;border-radius:6px;margin-top:10px;font-weight:bold">POSTAR</button></form></div><div style="background:#111;padding:15px;border-radius:10px"><h3>Agendamentos ({len(ags)})</h3><div style="max-height:400px;overflow:auto">{lista if lista else "Nenhum ainda"}</div></div></div><h3 style="margin-top:20px">Fotos ({len(fotos)})</h3><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px">{fotos_html}</div></div></body></html>'

@app.route("/admin/logout")
def logout():
    session.pop("admin",None)
    return redirect("/admin")

@app.route("/upload", methods=["POST"])
def upload():
    if not session.get("admin"):
        return redirect("/admin")
    file=request.files.get("foto")
    if file and file.filename:
        filename=datetime.now().strftime("%Y%m%d%H%M%S_")+secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        con=sqlite3.connect(DB_PATH)
        con.execute("INSERT INTO fotos (filename,titulo,categoria,data,likes) VALUES (?,?,?,?,0)", (filename, request.form.get("titulo","Foto"), request.form.get("categoria","Ensaio"), datetime.now().strftime("%d/%m/%Y")))
        con.commit()
        con.close()
    return redirect("/admin")

@app.route("/delete/<int:foto_id>")
def delete_foto(foto_id):
    con=sqlite3.connect(DB_PATH)
    row=con.execute("SELECT filename FROM fotos WHERE id=?", (foto_id,)).fetchone()
    if row:
        try: os.remove(os.path.join(UPLOAD_FOLDER, row[0]))
        except: pass
        con.execute("DELETE FROM fotos WHERE id=?", (foto_id,))
        con.commit()
    con.close()
    return redirect("/admin")

app=app
