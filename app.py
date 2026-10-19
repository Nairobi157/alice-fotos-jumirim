import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3
app = Flask(__name__)
app.secret_key = "foto-jumirim-2026"
UPLOAD_FOLDER = "/tmp/static/uploads"
ALLOWED = {"png","jpg","jpeg","webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("/tmp", exist_ok=True)
WHATSAPP = "5515996216025"
INSTAGRAM = "seu.instagram"
GOOGLE_REVIEW_LINK = "https://g.page/r/SEU_LINK/review"
NOME_FOTOGRAFO = "Alice - Fotos"
ADMIN_SENHA = "666777"
def init_db():
    con = sqlite3.connect("/tmp/fotos.db")
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS fotos (id INTEGER PRIMARY KEY, filename TEXT, titulo TEXT, categoria TEXT, descricao TEXT, data TEXT, likes INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS comentarios (id INTEGER PRIMARY KEY, foto_id INTEGER, nome TEXT, texto TEXT, data TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS agendamentos (id INTEGER PRIMARY KEY, nome TEXT, whatsapp TEXT, tipo TEXT, data_evento TEXT, horario TEXT, local TEXT, mensagem TEXT, status TEXT, criado TEXT)")
    con.commit()
    con.close()
init_db()
def allowed_file(f):
    return "." in f and f.rsplit(".",1)[1].lower() in ALLOWED
@app.route("/")
def index():
    con = sqlite3.connect("/tmp/fotos.db")
    con.row_factory = sqlite3.Row
    fotos = con.execute("SELECT * FROM fotos ORDER BY id DESC").fetchall()
    comentarios = {}
    for row in con.execute("SELECT * FROM comentarios ORDER BY id DESC").fetchall():
        comentarios.setdefault(row["foto_id"], []).append(dict(row))
    con.close()
    return render_template("index.html", fotos=fotos, comentarios=comentarios, whatsapp=WHATSAPP, instagram=INSTAGRAM, google_link=GOOGLE_REVIEW_LINK, nome=NOME_FOTOGRAFO)
@app.route("/admin/login", methods=["POST"])
def admin_login():
    if request.form.get("senha") == ADMIN_SENHA:
        session["admin"] = True
    return redirect(url_for("index"))
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("index"))
@app.route("/upload", methods=["POST"])
def upload():
    if not session.get("admin"):
        return "Sem permissao", 403
    file = request.files.get("foto")
    titulo = request.form.get("titulo","Sem titulo")
    categoria = request.form.get("categoria","Ensaio")
    descricao = request.form.get("descricao","")
    if file and allowed_file(file.filename):
        filename = datetime.now().strftime("%Y%m%d%H%M%S_") + secure_filename(file.filename)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        con = sqlite3.connect("/tmp/fotos.db")
        con.execute("INSERT INTO fotos (filename,titulo,categoria,descricao,data,likes) VALUES (?,?,?,?,?,0)", (filename,titulo,categoria,descricao,datetime.now().strftime("%d/%m/%Y")))
        con.commit()
        con.close()
    return redirect(url_for("index"))
@app.route("/delete/<int:foto_id>")
def delete_foto(foto_id):
    if not session.get("admin"):
        return "Sem permissao", 403
    con = sqlite3.connect("/tmp/fotos.db")
    row = con.execute("SELECT filename FROM fotos WHERE id=?", (foto_id,)).fetchone()
    if row:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, row[0]))
        except:
            pass
        con.execute("DELETE FROM fotos WHERE id=?", (foto_id,))
        con.execute("DELETE FROM comentarios WHERE foto_id=?", (foto_id,))
        con.commit()
    con.close()
    return redirect(url_for("index"))
@app.route("/like/<int:foto_id>")
def like(foto_id):
    con = sqlite3.connect("/tmp/fotos.db")
    con.execute("UPDATE fotos SET likes=likes+1 WHERE id=?", (foto_id,))
    con.commit()
    con.close()
    return jsonify({"ok":True})
@app.route("/comentar", methods=["POST"])
def comentar():
    foto_id = request.form.get("foto_id")
    nome = request.form.get("nome")[:50]
    texto = request.form.get("texto")[:300]
    if nome and texto:
        con = sqlite3.connect("/tmp/fotos.db")
        con.execute("INSERT INTO comentarios (foto_id,nome,texto,data) VALUES (?,?,?,?)", (foto_id,nome,texto,datetime.now().strftime("%d/%m %H:%M")))
        con.commit()
        con.close()
    return redirect(url_for("index"))
@app.route("/agendar", methods=["POST"])
def agendar():
    data = {k: request.form.get(k) for k in ["nome","whatsapp","tipo","data_evento","horario","local","mensagem"]}
    con = sqlite3.connect("/tmp/fotos.db")
    con.execute("INSERT INTO agendamentos (nome,whatsapp,tipo,data_evento,horario,local,mensagem,status,criado) VALUES (?,?,?,?,?,?,?, 'Pendente',?)", (data["nome"],data["whatsapp"],data["tipo"],data["data_evento"],data["horario"],data["local"],data["mensagem"],datetime.now().strftime("%d/%m/%Y %H:%M")))
    con.commit()
    con.close()
    import urllib.parse
    msg = f"Ola! Sou {data['nome']}, quero contratar para {data['tipo']} no dia {data['data_evento']} em {data['local']}. {data['mensagem']} Meu Whats: {data['whatsapp']}"
    link = f"https://wa.me/{WHATSAPP}?text={urllib.parse.quote(msg)}"
    return redirect(link)
@app.route("/admin/agendamentos")
def lista_agendamentos():
    if not session.get("admin"):
        return redirect(url_for("index"))
    con = sqlite3.connect("/tmp/fotos.db")
    con.row_factory = sqlite3.Row
    ag = con.execute("SELECT * FROM agendamentos ORDER BY id DESC").fetchall()
    con.close()
    return render_template("agendamentos.html", agendamentos=ag, whatsapp=WHATSAPP)
if __name__ == "__main__":
    app.run(debug=True, port=5000)
