from flask import Flask, request, redirect, session, send_from_directory
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
INSTAGRAM = "https://www.instagram.com/alicefotosjumirim"
GOOGLE_REVIEW = "/avaliar"

CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")
USE_CLOUDINARY = bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)

if USE_CLOUDINARY:
    try:
        import cloudinary, cloudinary.uploader, cloudinary.api
        cloudinary.config(cloud_name=CLOUDINARY_CLOUD_NAME, api_key=CLOUDINARY_API_KEY, api_secret=CLOUDINARY_API_SECRET, secure=True)
    except:
        USE_CLOUDINARY=False

def init_db():
    try:
        con=sqlite3.connect(DB_PATH)
        con.execute("CREATE TABLE IF NOT EXISTS fotos (id INTEGER PRIMARY KEY, filename TEXT, titulo TEXT, categoria TEXT, album TEXT, data TEXT, likes INTEGER DEFAULT 0, url TEXT, public_id TEXT)")
        con.execute("CREATE TABLE IF NOT EXISTS agendamentos (id INTEGER PRIMARY KEY, nome TEXT, whatsapp TEXT, tipo TEXT, data_evento TEXT, horario TEXT, local TEXT, mensagem TEXT, status TEXT, criado TEXT)")
        for sql in ["ALTER TABLE fotos ADD COLUMN url TEXT","ALTER TABLE fotos ADD COLUMN public_id TEXT","ALTER TABLE fotos ADD COLUMN album TEXT"]:
            try: con.execute(sql)
            except: pass
        con.commit(); con.close()
    except: pass

def get_fotos(album=None):
    try:
        init_db()
        con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row
        if album: fotos=con.execute("SELECT * FROM fotos WHERE album=? ORDER BY id DESC",(album,)).fetchall()
        else: fotos=con.execute("SELECT * FROM fotos ORDER BY id DESC").fetchall()
        con.close()
        if USE_CLOUDINARY and len(fotos)==0:
            try:
                import cloudinary.api
                result=cloudinary.api.resources(type="upload", prefix="alice-fotos-jumirim", max_results=200)
                out=[]
                for r in result.get('resources',[]):
                    pid=r['public_id']; parts=pid.split('/'); an=parts[1] if len(parts)>1 else "Sem pasta"
                    if album and album!=an: continue
                    out.append({'id':pid,'titulo':parts[-1],'album':an,'data':r['created_at'][:10],'url':r['secure_url'],'public_id':pid})
                return out
            except: return []
        return fotos
    except: return []

def get_albuns():
    try:
        init_db(); con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row
        albuns=con.execute("SELECT album, COUNT(*) as qtd FROM fotos WHERE album IS NOT NULL AND album!='' GROUP BY album ORDER BY MAX(id) DESC").fetchall(); con.close()
        if USE_CLOUDINARY and len(albuns)==0:
            try:
                import cloudinary.api; folders=cloudinary.api.subfolders("alice-fotos-jumirim")
                res=[]
                for f in folders.get('folders',[]):
                    name=f['name']
                    try: cnt=cloudinary.api.resources(type="upload", prefix=f"alice-fotos-jumirim/{name}", max_results=1).get('total_count',0)
                    except: cnt=0
                    if cnt>0: res.append({'album':name,'qtd':cnt})
                return res
            except: pass
        return albuns
    except: return []

@app.route('/debug')
def debug():
    fotos=get_fotos()
    return f"<html><body style='background:#000;color:#0f0;padding:20px'><h1>DEBUG</h1><p>NUVEM: {'ATIVADA' if USE_CLOUDINARY else 'DESATIVADA'}</p><p>Total fotos: {len(fotos)}</p><a href='/admin'>Admin</a></body></html>"


@app.route('/avaliar', methods=["GET","POST"])
def avaliar():
    init_db()
    if request.method=="POST":
        nome=request.form.get("nome","Anônimo")[:50]
        estrelas=request.form.get("estrelas","5")
        comentario=request.form.get("comentario","")[:500]
        # Salva como agendamento tipo Avaliação pra você ver no admin
        try:
            con=sqlite3.connect(DB_PATH)
            con.execute("INSERT INTO agendamentos (nome,whatsapp,tipo,data_evento,horario,local,mensagem,status,criado) VALUES (?,?,?,?,?,?,?, 'Avaliação',?)",
                (nome, "", f"Avaliação {estrelas} estrelas", "", "", "", comentario, datetime.now().strftime("%d/%m/%Y %H:%M")))
            con.commit(); con.close()
        except: pass
        # Manda pro WhatsApp também
        msg=f"Olá Alice! ⭐ Nova avaliação no site!\n\nNome: {nome}\nEstrelas: {estrelas}/5\nComentário: {comentario}"
        return redirect(f"https://wa.me/{WHATSAPP}?text="+urllib.parse.quote(msg))
    # Página de avaliação
    return f"""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Avaliar Alice Fotos</title></head>
    <body style="background:#0a0a0a;color:#fff;font-family:Arial;margin:0">
    <header style="padding:20px;text-align:center;border-bottom:1px solid #222"><h1 style="color:#d4af37">⭐ Avalie Alice Fotos Jumirim</h1><a href="/" style="color:#d4af37">Voltar ao site</a></header>
    <div style="max-width:600px;margin:30px auto;padding:20px">
        <div style="background:#111;border:1px solid #222;border-radius:16px;padding:25px">
            <h2 style="color:#d4af37;text-align:center">Deixe sua avaliação!</h2>
            <p style="color:#888;text-align:center">Sua opinião é muito importante!</p>
            <form method="post">
                <input name="nome" placeholder="Seu nome" required style="width:100%;padding:12px;margin:8px 0;background:#1a1a1a;border:1px solid #333;color:#fff;border-radius:8px;box-sizing:border-box">
                <label style="color:#d4af37">Quantas estrelas?</label>
                <select name="estrelas" style="width:100%;padding:12px;margin:8px 0;background:#1a1a1a;border:1px solid #333;color:#fff;border-radius:8px">
                    <option value="5">⭐⭐⭐⭐⭐ - 5 estrelas - Amei!</option>
                    <option value="4">⭐⭐⭐⭐ - 4 estrelas - Muito bom!</option>
                    <option value="3">⭐⭐⭐ - 3 estrelas - Bom</option>
                    <option value="2">⭐⭐ - 2 estrelas</option>
                    <option value="1">⭐ - 1 estrela</option>
                </select>
                <textarea name="comentario" placeholder="Conta como foi seu ensaio, o que mais gostou... *" required rows="4" style="width:100%;padding:12px;margin:8px 0;background:#1a1a1a;border:1px solid #333;color:#fff;border-radius:8px;box-sizing:border-box"></textarea>
                <button style="width:100%;background:#d4af37;color:#000;padding:14px;border:none;border-radius:8px;font-weight:bold;font-size:16px;cursor:pointer">⭐ Enviar Avaliação</button>
            </form>
            <div style="margin-top:25px;text-align:center;border-top:1px solid #222;padding-top:20px">
                <p style="color:#888">Ou avalie direto no Google:</p>
                <a href="{GOOGLE_REVIEW}" target="_blank" style="background:#fff;color:#000;padding:12px 24px;border-radius:25px;text-decoration:none;font-weight:bold;display:inline-block">⭐ Avaliar no Google Maps</a>
                <p style="color:#666;font-size:12px;margin-top:10px">Se não tiver Google Meu Negócio ainda, as avaliações vão pro seu WhatsApp e aparecem no seu admin!</p>
            </div>
        </div>
    </div>
    </body></html>"""

@app.route('/static/uploads/<path:filename>')

def serve_upload(filename): return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/")
def index():
    album_filtro=request.args.get("album")
    fotos=get_fotos(album_filtro)
    albuns=get_albuns()
    filtros=""
    for a in albuns:
        nome=a['album'] if isinstance(a,dict) else a[0]
        filtros+=f'<a href="/?album={nome}" style="background:#1a1a1a;border:1px solid #333;color:#fff;padding:6px 14px;border-radius:20px;text-decoration:none;margin:4px;display:inline-block">📁 {nome}</a>'
    filtros+=f'<a href="/" style="background:#d4af37;color:#000;padding:6px 14px;border-radius:20px;text-decoration:none;margin:4px;display:inline-block">Todas</a>'
    html_fotos=""
    for f in fotos:
        img=f['url'] if isinstance(f,dict) else (f[7] if len(f)>7 and f[7] else '/static/uploads/'+f[1])
        title=f['titulo'] if isinstance(f,dict) else f[2]; alb=f['album'] if isinstance(f,dict) else f[4]; data=f['data'] if isinstance(f,dict) else (f[5] if len(f)>5 else "")
        msg=urllib.parse.quote(f"Olá Alice! Gostei da foto {title}")
        html_fotos+=f'<div style="background:#111;border:1px solid #222;border-radius:12px;overflow:hidden"><img src="{img}" loading="lazy" style="width:100%;height:260px;object-fit:cover"><div style="padding:12px"><b style="color:#d4af37">{title}</b><br><small style="color:#888">📁 {alb} • {data}</small><br><a href="https://wa.me/{WHATSAPP}?text={msg}" target="_blank" style="background:#25D366;color:#fff;padding:6px 12px;border-radius:20px;text-decoration:none;font-size:12px;display:inline-block;margin-top:8px">💬 Falar sobre essa foto</a></div></div>'
    if not html_fotos:
        html_fotos=f'<p style="color:#888;text-align:center;grid-column:1/-1;padding:40px">Nenhuma foto ainda em {album_filtro if album_filtro else "galeria"}</p>'
    return f'<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Alice Fotos Jumirim</title></head><body style="background:#0a0a0a;color:#fff;font-family:Arial;margin:0"><header style="padding:25px;text-align:center;border-bottom:1px solid #222"><h1 style="color:#d4af37;margin:0 0 8px 0;font-size:28px">Alice Fotos Jumirim</h1><p style="color:#888;margin:0 0 15px 0">Ensaios • Casamentos • Eventos</p><div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin:15px 0"><a href="#agendar" style="background:#d4af37;color:#000;padding:10px 22px;border-radius:25px;text-decoration:none;font-weight:bold">📅 Agendar Ensaio</a><a href="{GOOGLE_REVIEW}" target="_blank" style="background:#fff;color:#000;padding:10px 22px;border-radius:25px;text-decoration:none;font-weight:bold">⭐ Avalie no Google!</a><a href="https://wa.me/{WHATSAPP}" target="_blank" style="background:#25D366;color:#fff;padding:10px 22px;border-radius:25px;text-decoration:none;font-weight:bold">WhatsApp</a></div><div style="margin-top:15px">{filtros}</div></header><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:18px;padding:25px;max-width:1300px;margin:auto">{html_fotos}</div><div style="background:linear-gradient(135deg,#1a1a1a,#111);padding:50px 20px;text-align:center;border-top:1px solid #222"><h2 style="color:#d4af37">Avalie no Google! ⭐⭐⭐⭐⭐</h2><p style="color:#ccc;max-width:600px;margin:15px auto">Sua avaliação me ajuda muito!</p><a href="{GOOGLE_REVIEW}" target="_blank" style="background:#fff;color:#000;padding:14px 30px;border-radius:30px;text-decoration:none;font-weight:bold;display:inline-block">⭐ Avaliar no Google</a></div><div id="agendar" style="background:#0f0f0f;padding:50px 20px"><div style="max-width:600px;margin:auto;background:#111;border:1px solid #222;border-radius:16px;padding:30px"><h2 style="color:#d4af37;text-align:center">📩 Agendar Ensaio / Mandar Mensagem</h2><p style="color:#888;text-align:center;font-size:14px">Sua mensagem vai direto pro meu WhatsApp!</p><form action="/agendar" method="post"><input name="nome" placeholder="Seu nome *" required style="width:100%;padding:12px;margin:8px 0;background:#1a1a1a;border:1px solid #333;color:#fff;border-radius:8px;box-sizing:border-box"><input name="whatsapp" placeholder="Seu WhatsApp *" required style="width:100%;padding:12px;margin:8px 0;background:#1a1a1a;border:1px solid #333;color:#fff;border-radius:8px;box-sizing:border-box"><select name="tipo" style="width:100%;padding:12px;margin:8px 0;background:#1a1a1a;border:1px solid #333;color:#fff;border-radius:8px"><option>Ensaio Fotográfico</option><option>Casamento</option><option>Aniversário</option><option>Outro</option></select><div style="display:grid;grid-template-columns:1fr 1fr;gap:10px"><input name="data_evento" type="date" style="padding:12px;background:#1a1a1a;border:1px solid #333;color:#fff;border-radius:8px"><input name="local" placeholder="Local" style="padding:12px;background:#1a1a1a;border:1px solid #333;color:#fff;border-radius:8px"></div><textarea name="mensagem" placeholder="Me conta o que precisa... *" required rows="4" style="width:100%;padding:12px;margin:8px 0;background:#1a1a1a;border:1px solid #333;color:#fff;border-radius:8px;box-sizing:border-box"></textarea><button style="width:100%;background:#25D366;color:#fff;padding:14px;border:none;border-radius:8px;font-weight:bold;font-size:16px">💬 Enviar no WhatsApp</button></form></div></div><footer style="background:#000;padding:30px;text-align:center;border-top:1px solid #222"><p style="color:#d4af37">Alice Fotos Jumirim</p><p style="color:#888;font-size:13px">WhatsApp: (15) 99621-6025</p><div style="margin-top:15px"><a href="{INSTAGRAM}" target="_blank" style="color:#d4af37;margin:0 10px;text-decoration:none">Instagram</a><a href="https://wa.me/{WHATSAPP}" target="_blank" style="color:#25D366;margin:0 10px;text-decoration:none">WhatsApp</a><a href="{GOOGLE_REVIEW}" target="_blank" style="color:#fff;margin:0 10px;text-decoration:none">Avaliar</a></div></footer></body></html>'

@app.route("/agendar", methods=["POST"])
def agendar():
    init_db()
    d = {k: request.form.get(k,"").strip() for k in ["nome","whatsapp","tipo","data_evento","local","mensagem"]}
    con=sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO agendamentos (nome,whatsapp,tipo,data_evento,horario,local,mensagem,status,criado) VALUES (?,?,?,?,?,?,?, 'Pendente',?)", (d["nome"],d["whatsapp"],d["tipo"],d["data_evento"],"",d["local"],d["mensagem"],datetime.now().strftime("%d/%m/%Y %H:%M")))
    con.commit(); con.close()
    msg = f"Olá Alice! Sou {d['nome']} - Quero agendar: {d['tipo']} Data: {d['data_evento']} Local: {d['local']} Mensagem: {d['mensagem']} Meu Whats: {d['whatsapp']}"
    return redirect(f"https://wa.me/{WHATSAPP}?text={urllib.parse.quote(msg)}")

@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method=="POST":
        if request.form.get("senha")==SENHA: session["admin"]=True; return redirect("/admin")
    if not session.get("admin"):
        return '<html><body style="background:#0a0a0a;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;font-family:Arial"><form method="post" style="background:#111;padding:30px;border-radius:12px;text-align:center"><h3 style="color:#d4af37">Admin Alice Fotos</h3><input type="password" name="senha" placeholder="666777" style="padding:10px;width:100%;background:#1a1a1a;border:1px solid #333;color:#fff;border-radius:6px"><br><br><button style="background:#d4af37;color:#000;padding:10px 20px;border:none;border-radius:20px;font-weight:bold">Entrar</button></form></body></html>'
    album_filtro=request.args.get("album"); fotos=get_fotos(album_filtro)
    try: con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row; ags=con.execute("SELECT * FROM agendamentos ORDER BY id DESC").fetchall(); con.close()
    except: ags=[]
    albuns=get_albuns()
    lista=""
    for ag in ags:
        try:
            nome=ag[1]; whats=ag[2]; tipo=ag[3]; data_e=ag[4]; local=ag[6]; mens=ag[7]; criado=ag[9]
            lista+=f'<div style="background:#0a0a0a;border:1px solid #333;padding:12px;margin:8px 0;border-radius:8px"><b>{nome}</b> <small>{criado}</small><br><b style="color:#d4af37">{tipo}</b> - {data_e} em {local}<br><small>{whats}</small><br><div style="background:#111;padding:8px;border-radius:6px;margin:6px 0">{mens}</div></div>'
        except: continue
    fotos_html=""
    for f in fotos[:100]:
        img=f['url'] if isinstance(f,dict) else (f[7] if len(f)>7 and f[7] else '/static/uploads/'+f[1])
        fid=f['public_id'] if isinstance(f,dict) else f[0]
        title=f['titulo'] if isinstance(f,dict) else f[2]
        fotos_html+=f'<div style="background:#111;border-radius:8px;overflow:hidden"><img src="{img}" style="width:100%;height:120px;object-fit:cover"><div style="padding:6px"><small>{title}</small><br><a href="/delete/{fid}" style="color:red;font-size:12px">Apagar</a></div></div>'
    albuns_html=""
    for a in albuns:
        nome=a['album'] if isinstance(a,dict) else a[0]; qtd=a['qtd'] if isinstance(a,dict) else a[1]
        albuns_html+=f'<div style="display:flex;justify-content:space-between;background:#0a0a0a;padding:10px;border-radius:8px;margin:6px 0"><span>📁 {nome} ({qtd})</span><span><a href="/?album={nome}" target="_blank" style="color:#d4af37;margin-right:8px">Ver</a><a href="/delete_album/{nome}" style="color:red">Apagar</a></span></div>'
    return f'<html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="background:#0a0a0a;color:#fff;font-family:Arial;margin:0"><header style="background:#00aa00;color:#fff;padding:12px 20px;display:flex;justify-content:space-between"><b>☁️ NUVEM ATIVA - {len(fotos)} fotos!</b><a href="/admin/logout" style="color:#fff">Sair</a></header><div style="padding:20px;max-width:1200px;margin:auto"><div style="display:grid;grid-template-columns:1fr 1fr;gap:20px"><div style="background:#111;padding:20px;border-radius:12px"><h3 style="color:#d4af37">📸 Postar Foto</h3><form action="/upload" method="post" enctype="multipart/form-data"><input name="album" placeholder="Ex: Casamento Ana" required style="width:100%;padding:12px;margin:6px 0;background:#1a1a1a;border:1px solid #333;color:#fff;border-radius:8px"><input name="titulo" placeholder="Título" required style="width:100%;padding:12px;margin:6px 0;background:#1a1a1a;border:1px solid #333;color:#fff;border-radius:8px"><input type="file" name="foto" accept="image/*" required style="width:100%;padding:10px;margin:10px 0;color:#fff"><button style="width:100%;background:#d4af37;color:#000;padding:14px;border:none;border-radius:8px;font-weight:bold">☁️ POSTAR NA NUVEM</button></form></div><div style="background:#111;padding:20px;border-radius:12px"><h3>📁 Pastas ({len(albuns)})</h3><div style="max-height:350px;overflow:auto">{albuns_html if albuns_html else "Nenhuma pasta"}</div></div></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:20px"><div><h3>Fotos ({len(fotos)})</h3><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;max-height:600px;overflow:auto;padding:10px;background:#0f0f0f;border-radius:10px">{fotos_html if fotos_html else "Nenhuma foto"}</div></div><div style="background:#111;padding:20px;border-radius:12px"><h3 style="color:#25D366">💬 Mensagens ({len(ags)})</h3><div style="max-height:600px;overflow:auto">{lista if lista else "Nenhuma mensagem ainda - quando cliente preencher formulário vai aparecer aqui!"}</div></div></div></div></body></html>'

@app.route("/admin/logout")
def logout(): session.pop("admin",None); return redirect("/admin")

@app.route("/upload", methods=["POST"])
def upload():
    if not session.get("admin"): return redirect("/admin")
    file=request.files.get("foto"); album=request.form.get("album","Sem pasta").strip(); titulo=request.form.get("titulo","Foto")
    if file and file.filename:
        init_db()
        if USE_CLOUDINARY:
            try:
                import cloudinary.uploader
                result=cloudinary.uploader.upload(file, folder=f"alice-fotos-jumirim/{album}", public_id=datetime.now().strftime("%Y%m%d%H%M%S_")+secure_filename(file.filename).rsplit('.',1)[0], overwrite=True)
                url=result['secure_url']; public_id=result['public_id']
                con=sqlite3.connect(DB_PATH); con.execute("INSERT INTO fotos (filename,titulo,categoria,album,data,likes,url,public_id) VALUES (?,?,?,?,?,?,?,?)",(url,titulo,"Ensaio",album,datetime.now().strftime("%d/%m/%Y"),0,url,public_id)); con.commit(); con.close()
            except Exception as e:
                filename=datetime.now().strftime("%Y%m%d%H%M%S_")+secure_filename(file.filename); file.save(os.path.join(UPLOAD_FOLDER, filename))
                con=sqlite3.connect(DB_PATH); con.execute("INSERT INTO fotos (filename,titulo,categoria,album,data,likes,url,public_id) VALUES (?,?,?,?,?,?,?,?)",(filename,titulo,"Ensaio",album,datetime.now().strftime("%d/%m/%Y"),0,filename,f"local_{filename}")); con.commit(); con.close()
        else:
            filename=datetime.now().strftime("%Y%m%d%H%M%S_")+secure_filename(file.filename); file.save(os.path.join(UPLOAD_FOLDER, filename))
            con=sqlite3.connect(DB_PATH); con.execute("INSERT INTO fotos (filename,titulo,categoria,album,data,likes) VALUES (?,?,?,?,?,0)",(filename,titulo,"Ensaio",album,datetime.now().strftime("%d/%m/%Y"))); con.commit(); con.close()
    return redirect("/admin")

@app.route("/delete/<path:foto_id>")
def delete_foto(foto_id):
    try:
        if USE_CLOUDINARY and "/" in str(foto_id):
            try: import cloudinary.uploader; cloudinary.uploader.destroy(foto_id)
            except: pass
            try: con=sqlite3.connect(DB_PATH); con.execute("DELETE FROM fotos WHERE public_id=?",(foto_id,)); con.commit(); con.close()
            except: pass
        else:
            con=sqlite3.connect(DB_PATH); row=con.execute("SELECT filename FROM fotos WHERE id=?",(foto_id,)).fetchone()
            if row:
                try: os.remove(os.path.join(UPLOAD_FOLDER, row[0]))
                except: pass
                con.execute("DELETE FROM fotos WHERE id=?",(foto_id,)); con.commit()
            con.close()
    except: pass
    return redirect("/admin")

@app.route("/delete_album/<path:album_name>")
def delete_album(album_name):
    try:
        if USE_CLOUDINARY:
            try:
                import cloudinary.api, cloudinary.uploader
                resources=cloudinary.api.resources(type="upload", prefix=f"alice-fotos-jumirim/{album_name}", max_results=200)
                for r in resources.get('resources',[]): cloudinary.uploader.destroy(r['public_id'])
                try: cloudinary.api.delete_folder(f"alice-fotos-jumirim/{album_name}")
                except: pass
            except: pass
        con=sqlite3.connect(DB_PATH); con.execute("DELETE FROM fotos WHERE album=?",(album_name,)); con.commit(); con.close()
    except: pass
    return redirect("/admin")

app=app
