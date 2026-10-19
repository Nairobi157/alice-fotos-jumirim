
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

# DEBUG - mostra se variaveis existem
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")
USE_CLOUDINARY = bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)

print(f"=== DEBUG CLOUDINARY ===")
print(f"CLOUD_NAME: {'OK - '+CLOUDINARY_CLOUD_NAME if CLOUDINARY_CLOUD_NAME else 'VAZIO!'}")
print(f"API_KEY: {'OK - '+CLOUDINARY_API_KEY[:4]+'...' if CLOUDINARY_API_KEY else 'VAZIO!'}")
print(f"API_SECRET: {'OK - '+CLOUDINARY_API_SECRET[:4]+'...' if CLOUDINARY_API_SECRET else 'VAZIO!'}")
print(f"USE_CLOUDINARY: {USE_CLOUDINARY}")

if USE_CLOUDINARY:
    try:
        import cloudinary
        import cloudinary.uploader
        import cloudinary.api
        cloudinary.config(cloud_name=CLOUDINARY_CLOUD_NAME, api_key=CLOUDINARY_API_KEY, api_secret=CLOUDINARY_API_SECRET, secure=True)
        print("Cloudinary CONFIGURADO COM SUCESSO!")
    except Exception as e:
        print(f"Erro config cloudinary: {e}")
        USE_CLOUDINARY=False
else:
    print("Cloudinary DESATIVADO - variaveis vazias!")

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
                result=cloudinary.api.resources(type="upload", prefix="alice-fotos-jumirim", max_results=100)
                out=[]
                for r in result.get('resources',[]):
                    pid=r['public_id']; parts=pid.split('/'); an=parts[1] if len(parts)>1 else "Sem pasta"
                    if album and album!=an: continue
                    out.append({'id':pid,'filename':r['secure_url'],'titulo':'Foto','album':an,'data':r['created_at'][:10],'url':r['secure_url'],'public_id':pid})
                return out
            except Exception as e:
                print(f"Erro listar cloudinary: {e}")
                return []
        return fotos
    except Exception as e:
        print(f"Erro get_fotos: {e}")
        return []

def get_albuns():
    try:
        init_db(); con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row
        albuns=con.execute("SELECT album, COUNT(*) as qtd FROM fotos GROUP BY album ORDER BY MAX(id) DESC").fetchall(); con.close()
        if USE_CLOUDINARY and len(albuns)==0:
            try:
                import cloudinary.api; folders=cloudinary.api.subfolders("alice-fotos-jumirim")
                res=[]
                for f in folders.get('folders',[]):
                    name=f['name']
                    try: cnt=cloudinary.api.resources(type="upload", prefix=f"alice-fotos-jumirim/{name}", max_results=1).get('total_count',0)
                    except: cnt=0
                    res.append({'album':name,'qtd':cnt})
                return res
            except: pass
        return albuns
    except: return []

def get_ag():
    try: con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row; ag=con.execute("SELECT * FROM agendamentos ORDER BY id DESC").fetchall(); con.close(); return ag
    except: return []

@app.route('/debug')
def debug():
    return f"""
    <html><body style="background:#000;color:#0f0;font-family:monospace;padding:20px">
    <h1>DEBUG CLOUDINARY</h1>
    <p>CLOUD_NAME: {'✅ '+CLOUDINARY_CLOUD_NAME if CLOUDINARY_CLOUD_NAME else '❌ VAZIO - NÃO CONFIGURADO!'}</p>
    <p>API_KEY: {'✅ '+CLOUDINARY_API_KEY[:6]+'...' if CLOUDINARY_API_KEY else '❌ VAZIO!'}</p>
    <p>API_SECRET: {'✅ '+CLOUDINARY_API_SECRET[:6]+'...' if CLOUDINARY_API_SECRET else '❌ VAZIO!'}</p>
    <p>USE_CLOUDINARY: {'✅ ATIVADO' if USE_CLOUDINARY else '❌ DESATIVADO'}</p>
    <hr>
    <p>Se algum estiver VAZIO, vai no Vercel > Settings > Environment Variables e confere!</p>
    <p>Tem que ter EXATAMENTE esses 3 nomes:</p>
    <ul>
    <li>CLOUDINARY_CLOUD_NAME = ecffkd3p</li>
    <li>CLOUDINARY_API_KEY = 478583531779143</li>
    <li>CLOUDINARY_API_SECRET = seu secret</li>
    </ul>
    <p>Marca Production e faz Redeploy!</p>
    <a href="/admin" style="color:#d4af37">Voltar pro admin</a>
    </body></html>
    """

@app.route('/static/uploads/<path:filename>')
def serve_upload(filename): return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/")
def index():
    album_filtro=request.args.get("album"); fotos=get_fotos(album_filtro)
    try: init_db(); con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row; albuns_raw=con.execute("SELECT album, COUNT(*) as qtd FROM fotos GROUP BY album ORDER BY MAX(id) DESC").fetchall(); con.close()
    except: albuns_raw=[]
    if len(albuns_raw)==0 and USE_CLOUDINARY: albuns_raw=get_albuns()
    html_fotos=""
    for f in fotos:
        img=f['url'] if isinstance(f,dict) else (f[7] if len(f)>7 and f[7] else '/static/uploads/'+f[1])
        title=f['titulo'] if isinstance(f,dict) else f[2]; alb=f['album'] if isinstance(f,dict) else f[4]
        html_fotos+=f'<div style="background:#111;border:1px solid #222;border-radius:12px;overflow:hidden"><img src="{img}" style="width:100%;height:200px;object-fit:cover"><div style="padding:10px"><b>{title}</b> - {alb}</div></div>'
    if not html_fotos: html_fotos='<p style="color:#888;text-align:center;grid-column:1/-1">Nenhuma foto ainda - /admin</p>'
    return f'<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Alice Fotos</title></head><body style="background:#0a0a0a;color:#fff;font-family:Arial;margin:0"><header style="padding:20px;text-align:center;border-bottom:1px solid #222"><h1 style="color:#d4af37">Alice - Fotos Jumirim</h1><a href="/admin" style="background:#d4af37;color:#000;padding:10px 20px;border-radius:20px;text-decoration:none">Admin</a> | <a href="/debug" style="color:#888">Debug</a></header><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:15px;padding:20px;max-width:1100px;margin:auto">{html_fotos}</div></body></html>'

@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method=="POST":
        if request.form.get("senha")==SENHA: session["admin"]=True; return redirect("/admin")
    if not session.get("admin"): return '<html><body style="background:#0a0a0a;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh"><form method="post" style="background:#111;padding:20px;border-radius:10px"><h3>Admin Alice - senha 666777</h3><input type="password" name="senha" placeholder="666777"><button>Entrar</button></form></body></html>'
    album_filtro=request.args.get("album"); fotos=get_fotos(album_filtro); ags=get_ag(); albuns=get_albuns()
    status = "☁️ NUVEM ATIVA - fotos nunca somem! ✅" if USE_CLOUDINARY else "⚠️ CLOUDINARY DESATIVADO - veja /debug ❌"
    html=f'<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{{background:#0a0a0a;color:#fff;font-family:Arial;margin:0}}input{{width:100%;padding:10px;margin:5px 0;background:#1a1a1a;border:1px solid #222;color:#fff;border-radius:6px}}</style></head><body><header style="background:{"#00aa00" if USE_CLOUDINARY else "#aa0000"};color:#fff;padding:15px;display:flex;justify-content:space-between"><b>{status}</b><span><a href="/debug" style="color:#fff;margin-right:15px">Debug</a><a href="/admin/logout" style="color:#fff">Sair</a></span></header><div style="padding:20px;max-width:1000px;margin:auto">'
    if not USE_CLOUDINARY:
        html+='<div style="background:#442200;border:2px solid #ffaa00;padding:15px;border-radius:10px;margin-bottom:20px"><h3>❌ Cloudinary não ativou!</h3><p>Vai no Vercel > Settings > Environment Variables</p><p>Confere se tem EXATAMENTE:</p><p>CLOUDINARY_CLOUD_NAME = ecffkd3p<br>CLOUDINARY_API_KEY = 478583531779143<br>CLOUDINARY_API_SECRET = (seu secret)</p><p>Marca Production e faz Redeploy! Depois clica em <a href="/debug" style="color:#d4af37">/debug</a> pra ver!</p></div>'
    html+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px"><div style="background:#111;padding:15px;border-radius:10px"><h3>Postar Foto</h3><form action="/upload" method="post" enctype="multipart/form-data"><input name="album" placeholder="Nome da pasta: Ex: Casamento Ana" required><input name="titulo" placeholder="Titulo da foto" required><input type="file" name="foto" accept="image/*" required style="color:#fff"><button style="width:100%;background:#d4af37;padding:12px;border:none;border-radius:6px;font-weight:bold;margin-top:10px">POSTAR NA NUVEM</button></form></div><div style="background:#111;padding:15px;border-radius:10px"><h3>Pastas</h3>'
    for a in albuns:
        nome=a['album'] if isinstance(a,dict) else a[0]; qtd=a['qtd'] if isinstance(a,dict) else a[1]
        html+=f'<div style="display:flex;justify-content:space-between;background:#0a0a0a;padding:8px;border-radius:6px;margin:5px 0"><span>📁 {nome} ({qtd})</span><span><a href="/?album={nome}" style="color:#d4af37">Ver</a> <a href="/delete_album/{nome}" style="color:red;margin-left:5px">Apagar</a></span></div>'
    html+=f'</div></div><h3>Fotos ({len(fotos)})</h3><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px">'
    for f in fotos[:60]:
        img=f['url'] if isinstance(f,dict) else (f[7] if len(f)>7 and f[7] else '/static/uploads/'+f[1]); fid=f['public_id'] if isinstance(f,dict) else f[0]
        title=f['titulo'] if isinstance(f,dict) else f[2]
        html+=f'<div style="background:#111;border-radius:8px;overflow:hidden"><img src="{img}" style="width:100%;height:120px;object-fit:cover"><div style="padding:5px"><small>{title}</small><br><a href="/delete/{fid}" style="color:red">Apagar</a></div></div>'
    html+='</div></div></body></html>'; return html

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
                print(f"Upload Cloudinary OK: {public_id}")
            except Exception as e:
                print(f"Erro upload cloudinary: {e}")
                filename=datetime.now().strftime("%Y%m%d%H%M%S_")+secure_filename(file.filename); file.save(os.path.join(UPLOAD_FOLDER, filename))
                con=sqlite3.connect(DB_PATH); con.execute("INSERT INTO fotos (filename,titulo,categoria,album,data,likes) VALUES (?,?,?,?,?,0)",(filename,titulo,"Ensaio",album,datetime.now().strftime("%d/%m/%Y"))); con.commit(); con.close()
        else:
            filename=datetime.now().strftime("%Y%m%d%H%M%S_")+secure_filename(file.filename); file.save(os.path.join(UPLOAD_FOLDER, filename))
            con=sqlite3.connect(DB_PATH); con.execute("INSERT INTO fotos (filename,titulo,categoria,album,data,likes) VALUES (?,?,?,?,?,0)",(filename,titulo,"Ensaio",album,datetime.now().strftime("%d/%m/%Y"))); con.commit(); con.close()
    return redirect("/admin")

@app.route("/delete/<path:foto_id>")
def delete_foto(foto_id):
    try:
        if USE_CLOUDINARY and "/" in str(foto_id):
            try:
                import cloudinary.uploader; cloudinary.uploader.destroy(foto_id)
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
                resources=cloudinary.api.resources(type="upload", prefix=f"alice-fotos-jumirim/{album_name}", max_results=100)
                for r in resources.get('resources',[]): cloudinary.uploader.destroy(r['public_id'])
                try: cloudinary.api.delete_folder(f"alice-fotos-jumirim/{album_name}")
                except: pass
            except: pass
        con=sqlite3.connect(DB_PATH); con.execute("DELETE FROM fotos WHERE album=?",(album_name,)); con.commit(); con.close()
    except: pass
    return redirect("/admin")

app=app
