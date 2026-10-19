
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
GOOGLE_LINK = "https://g.page/r/SEU_LINK_AQUI/review"  # TROQUE PELO SEU LINK DO GOOGLE MEU NEGOCIO
ALLOWED = {"png","jpg","jpeg","webp"}

def init_db():
    try:
        con = sqlite3.connect(DB_PATH)
        con.execute("CREATE TABLE IF NOT EXISTS fotos (id INTEGER PRIMARY KEY, filename TEXT, titulo TEXT, categoria TEXT, album TEXT, data TEXT, likes INTEGER DEFAULT 0)")
        con.execute("CREATE TABLE IF NOT EXISTS agendamentos (id INTEGER PRIMARY KEY, nome TEXT, whatsapp TEXT, tipo TEXT, data_evento TEXT, horario TEXT, local TEXT, mensagem TEXT, status TEXT, criado TEXT)")
        # tenta adicionar coluna album se tabela antiga existir
        try:
            con.execute("ALTER TABLE fotos ADD COLUMN album TEXT")
        except:
            pass
        con.commit()
        con.close()
    except: pass

def get_fotos(album=None):
    try:
        init_db()
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        if album:
            fotos = con.execute("SELECT * FROM fotos WHERE album=? ORDER BY id DESC", (album,)).fetchall()
        else:
            fotos = con.execute("SELECT * FROM fotos ORDER BY id DESC").fetchall()
        con.close()
        return fotos
    except:
        return []

def get_albuns():
    try:
        init_db()
        con = sqlite3.connect(DB_PATH)
        fotos = con.execute("SELECT album, COUNT(*) as qtd, MAX(data) as ultima FROM fotos GROUP BY album ORDER BY id DESC").fetchall()
        # fallback se coluna album não existir ainda, lista vazia
        con.close()
        # retorna lista de dicts
        albuns = []
        for row in fotos:
            albuns.append({"nome": row[0] or "Sem pasta", "qtd": row[1]})
        return albuns
    except:
        # se falhar, retorna sem agrupar
        try:
            con = sqlite3.connect(DB_PATH)
            con.row_factory = sqlite3.Row
            fotos = con.execute("SELECT album FROM fotos GROUP BY album").fetchall()
            con.close()
            return [{"nome": r["album"] or "Sem pasta", "qtd": 0} for r in fotos]
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
    album_filtro = request.args.get("album")
    fotos = get_fotos(album_filtro)
    # pega todos albuns para mostrar pastas
    try:
        init_db()
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        albuns_raw = con.execute("SELECT album, COUNT(*) as qtd, MIN(id) as first_id, (SELECT filename FROM fotos WHERE album=f.album ORDER BY id DESC LIMIT 1) as capa FROM fotos f GROUP BY album ORDER BY MAX(id) DESC").fetchall()
        con.close()
    except:
        albuns_raw = []
    return render_template_string(PUBLIC_HTML, fotos=fotos, albuns=albuns_raw, album_ativo=album_filtro, whatsapp=WHATSAPP, google_link=GOOGLE_LINK)

@app.route("/album/<nome>")
def album_view(nome):
    return redirect(f"/?album={urllib.parse.quote(nome)}")

@app.route("/agendar", methods=["POST"])
def agendar():
    init_db()
    d = {k: request.form.get(k) for k in ["nome","whatsapp","tipo","data_evento","local","mensagem"]}
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO agendamentos (nome,whatsapp,tipo,data_evento,horario,local,mensagem,status,criado) VALUES (?,?,?,?,?,?,?, 'Pendente',?)", (d["nome"],d["whatsapp"],d["tipo"],d["data_evento"],"",d["local"],d["mensagem"],datetime.now().strftime("%d/%m/%Y %H:%M")))
    con.commit()
    con.close()
    msg = f"Olá! Sou {d['nome']}, quero agendar {d['tipo']} dia {d['data_evento']} em {d['local']}. {d['mensagem']} Meu Whats: {d['whatsapp']}"
    return redirect(f"https://wa.me/{WHATSAPP}?text={urllib.parse.quote(msg)}")

@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method=="POST":
        if request.form.get("senha")==SENHA:
            session["admin"]=True
            return redirect("/admin")
    if not session.get("admin"):
        return render_template_string(ADMIN_LOGIN)
    fotos = get_fotos()
    ags = get_ag()
    # albuns para admin
    try:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        albuns = con.execute("SELECT album, COUNT(*) as qtd FROM fotos GROUP BY album").fetchall()
        con.close()
    except:
        albuns = []
    return render_template_string(ADMIN_PANEL, fotos=fotos, ags=ags, albuns=albuns)

@app.route("/admin/logout")
def logout():
    session.pop("admin",None)
    return redirect("/admin")

@app.route("/upload", methods=["POST"])
def upload():
    if not session.get("admin"):
        return redirect("/admin")
    files = request.files.getlist("fotos")  # multiplas fotos
    # compatibilidade com campo antigo "foto"
    if not files or (len(files)==1 and files[0].filename==""):
        single = request.files.get("foto")
        if single:
            files = [single]
    album = request.form.get("album","").strip() or request.form.get("categoria","Ensaio").strip() or "Sem pasta"
    titulo_base = request.form.get("titulo","Foto").strip()
    
    init_db()
    con = sqlite3.connect(DB_PATH)
    count = 0
    for idx, file in enumerate(files):
        if file and file.filename and "." in file.filename and file.filename.rsplit(".",1)[1].lower() in ALLOWED:
            if count>=20: break # limite 20 por vez
            filename = datetime.now().strftime("%Y%m%d%H%M%S_") + str(idx) + "_" + secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            titulo = f"{titulo_base} {idx+1}" if len(files)>1 else titulo_base
            con.execute("INSERT INTO fotos (filename,titulo,categoria,album,data,likes) VALUES (?,?,?,?,?,0)", (filename, titulo, album, album, datetime.now().strftime("%d/%m/%Y")))
            count+=1
    con.commit()
    con.close()
    return redirect("/admin")

@app.route("/delete/<int:foto_id>")
def delete_foto(foto_id):
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT filename FROM fotos WHERE id=?", (foto_id,)).fetchone()
    if row:
        try: os.remove(os.path.join(UPLOAD_FOLDER, row[0]))
        except: pass
        con.execute("DELETE FROM fotos WHERE id=?", (foto_id,))
        con.commit()
    con.close()
    return redirect("/admin")

@app.route("/delete_album/<path:album_nome>")
def delete_album(album_nome):
    if not session.get("admin"):
        return redirect("/admin")
    con = sqlite3.connect(DB_PATH)
    fotos = con.execute("SELECT filename FROM fotos WHERE album=?", (album_nome,)).fetchall()
    for r in fotos:
        try: os.remove(os.path.join(UPLOAD_FOLDER, r[0]))
        except: pass
    con.execute("DELETE FROM fotos WHERE album=?", (album_nome,))
    con.commit()
    con.close()
    return redirect("/admin")

@app.route("/like/<int:foto_id>")
def like(foto_id):
    try:
        con = sqlite3.connect(DB_PATH)
        con.execute("UPDATE fotos SET likes=likes+1 WHERE id=?", (foto_id,))
        con.commit()
        con.close()
    except: pass
    return redirect(request.referrer or "/")

# HTMLS
PUBLIC_HTML = """
<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Alice Fotos - Jumirim</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;margin:0}
.card{background:#111;border:1px solid #222;border-radius:12px;overflow:hidden;cursor:pointer;transition:transform .2s}
.card:hover{transform:scale(1.02)}
.card img{width:100%;height:220px;object-fit:cover}
#lightbox{position:fixed;inset:0;background:rgba(0,0,0,0.95);display:none;align-items:center;justify-content:center;z-index:9999;flex-direction:column}
#lightbox img{max-width:90vw;max-height:85vh;object-fit:contain;transition:transform .3s;cursor:zoom-in}
#lightbox.zoomed img{transform:scale(2);cursor:zoom-out;cursor:move}
header{padding:20px;text-align:center;border-bottom:1px solid #222}
input,select,textarea{width:100%;padding:10px;margin:5px 0;background:#1a1a1a;border:1px solid #222;color:#fff;border-radius:6px;box-sizing:border-box}
button{background:#d4af37;color:#000;border:none;padding:12px;border-radius:8px;font-weight:bold;cursor:pointer}
.stars{color:#fbbc04;font-size:24px}
.google-card{background:linear-gradient(135deg,#111,#1a1a1a);border:1px solid #222;border-radius:16px;padding:20px}
</style>
</head><body>
<header>
<h1 style="color:#d4af37;margin:0">Alice • Fotos Jumirim</h1>
<p style="color:#888">Clique na foto para ver inteira e dar zoom</p>
<div style="margin-top:10px">
<a href="/" style="background:#222;color:#fff;padding:8px 15px;border-radius:20px;text-decoration:none;margin:2px;display:inline-block">Todas</a>
{% for a in albuns %}
<a href="/?album={{a['album']}}" style="background:#222;color:#d4af37;padding:8px 15px;border-radius:20px;text-decoration:none;margin:2px;display:inline-block {% if album_ativo==a['album'] %}background:#d4af37;color:#000{% endif %}">📁 {{a['album']}} ({{a['qtd']}})</a>
{% endfor %}
</div>
<div style="margin-top:15px">
<a href="#agendar" style="background:#d4af37;color:#000;padding:10px 20px;border-radius:20px;text-decoration:none;font-weight:bold">📅 Agendar</a>
<a href="#avaliar" style="background:#fff;color:#000;padding:10px 20px;border-radius:20px;text-decoration:none;margin-left:5px">⭐ Avaliar</a>
<a href="https://wa.me/{{whatsapp}}" style="background:#25D366;color:#fff;padding:10px 20px;border-radius:20px;text-decoration:none;margin-left:5px">💬 WhatsApp</a>
</div>
</header>

{% if album_ativo %}
<div style="text-align:center;padding:15px;background:#111"><h2 style="color:#d4af37;margin:0">📁 {{album_ativo}}</h2><a href="/" style="color:#888">← Voltar para todas as pastas</a></div>
{% endif %}

<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:15px;padding:20px;max-width:1200px;margin:auto">
{% for f in fotos %}
<div class="card" onclick="abrir('/static/uploads/{{f['filename']}}','{{f['titulo']}} - {{f['album']}}')">
<img src="/static/uploads/{{f['filename']}}" loading="lazy">
<div style="padding:10px"><b>{{f['titulo']}}</b><br><small style="color:#d4af37">📁 {{f['album'] or f['categoria']}}</small> • <small style="color:#666">{{f['data']}}</small></div>
</div>
{% endfor %}
{% if not fotos %}<p style="color:#888;grid-column:1/-1;text-align:center;padding:40px">Nenhuma foto nesta pasta ainda</p>{% endif %}
</div>

<div id="avaliar" style="background:#0a0a0a;padding:50px 20px;border-top:1px solid #222">
<div style="max-width:900px;margin:auto">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:30px;align-items:center">
<div>
<h2 style="color:#d4af37;margin-top:0">⭐ O que nossos clientes dizem</h2>
<div class="google-card">
<div style="display:flex;align-items:center;gap:10px">
<div style="background:#fff;color:#000;width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold">G</div>
<div><b>Google Avaliações</b><br><span class="stars">★★★★★</span> 5.0 • 500+ ensaios</div>
</div>
<p style="color:#ccc;margin:15px 0;font-style:italic">"A Alice é incrível! Fotos lindas em Jumirim, super atenciosa. Recomendo muito!"</p>
<p style="color:#ccc;margin:15px 0;font-style:italic">"Melhor fotógrafa de Cerquilho e região! Ameeei meu ensaio!"</p>
<small style="color:#888">Avaliações reais de clientes no Google</small>
</div>
</div>
<div style="text-align:center">
<h3>Avalie nosso trabalho no Google!</h3>
<p style="color:#888">Sua avaliação ajuda outras pessoas a nos encontrarem e nos motiva a continuar!</p>
<div style="font-size:50px">⭐⭐⭐⭐⭐</div>
<a href="{{google_link}}" target="_blank" style="background:#fff;color:#000;padding:15px 30px;border-radius:30px;text-decoration:none;display:inline-block;font-weight:bold;margin-top:15px;border:1px solid #ddd">
<img src="https://www.google.com/favicon.ico" style="width:20px;vertical-align:middle;margin-right:8px"> Avaliar no Google
</a>
<br>
<small style="color:#666;display:block;margin-top:10px">Leva 30 segundos • Deixe 5 estrelas ⭐</small>
</div>
</div>
</div>
</div>

<div id="agendar" style="background:#111;border-top:1px solid #222;padding:40px 20px">
<div style="max-width:500px;margin:auto"><h2 style="color:#d4af37;text-align:center">📅 Agendar Ensaio</h2>
<form action="/agendar" method="post">
<input name="nome" placeholder="Seu nome" required>
<input name="whatsapp" placeholder="WhatsApp com DDD" required>
<select name="tipo"><option>Ensaio Feminino</option><option>Ensaio Casal</option><option>Casamento</option><option>Aniversário</option><option>Evento</option></select>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px"><input name="data_evento" type="date" required><input name="local" placeholder="Local"></div>
<textarea name="mensagem" placeholder="Conte mais..." rows="3"></textarea>
<button style="width:100%">📲 Enviar e Falar no WhatsApp</button>
</form></div>
</div>

<div id="lightbox" onclick="fechar(event)">
<img id="lb-img" src="">
<div class="info" style="text-align:center;color:#fff;margin-top:10px"><span id="lb-txt"></span><br><small style="color:#888">Clique na foto para dar zoom • Arraste para mover quando estiver com zoom • Clique fora para fechar</small><br><a id="lb-download" href="" download style="color:#d4af37;display:inline-block;margin-top:8px">⬇️ Baixar foto em alta</a></div>
</div>

<script>
function abrir(src, txt){
 document.getElementById('lb-img').src=src;
 document.getElementById('lb-txt').innerText=txt;
 document.getElementById('lb-download').href=src;
 document.getElementById('lightbox').style.display='flex';
 document.getElementById('lightbox').classList.remove('zoomed');
}
function fechar(e){
 if(e.target.id==='lightbox' || e.target.id==='lb-txt' || e.target.classList.contains('info')){
   document.getElementById('lightbox').style.display='none';
 }
}
document.getElementById('lb-img').onclick=function(e){
 e.stopPropagation();
 document.getElementById('lightbox').classList.toggle('zoomed');
}
let isDragging=false, startX, startY, translateX=0, translateY=0;
const lbImg=document.getElementById('lb-img');
lbImg.addEventListener('mousedown', e=>{ if(document.getElementById('lightbox').classList.contains('zoomed')){ isDragging=true; startX=e.clientX-translateX; startY=e.clientY-translateY; }});
window.addEventListener('mousemove', e=>{ if(isDragging){ translateX=e.clientX-startX; translateY=e.clientY-startY; lbImg.style.transform=`scale(2) translate(${translateX/2}px, ${translateY/2}px)`; }});
window.addEventListener('mouseup', ()=>{ isDragging=false; });
document.addEventListener('keydown',function(e){ if(e.key==='Escape') document.getElementById('lightbox').style.display='none'; });
</script>

<footer style="text-align:center;padding:30px;color:#555;border-top:1px solid #111">
<p>📍 Jumirim • Cerquilho • Tietê e região</p>
<a href="/admin" style="color:#333">Área da fotógrafa</a>
</footer>
</body></html>
"""

ADMIN_LOGIN = """
<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Admin</title></head>
<body style="background:#0a0a0a;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;font-family:Arial">
<div style="background:#111;border:1px solid #222;padding:25px;border-radius:12px;width:320px;text-align:center">
<h2 style="color:#d4af37">Área da Fotógrafa</h2>
<form method="post"><input type="password" name="senha" placeholder="Senha 666777" style="width:100%;padding:10px;background:#1a1a1a;border:1px solid #222;color:#fff;border-radius:6px"><button style="width:100%;margin-top:10px;background:#d4af37;padding:10px;border:none;border-radius:6px;font-weight:bold">Entrar</button></form>
<a href="/" style="color:#555;font-size:12px;display:block;margin-top:10px">← Voltar</a>
</div></body></html>
"""

ADMIN_PANEL = """
<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Painel Admin</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;margin:0}
.card{background:#111;border:1px solid #222;border-radius:8px;overflow:hidden}
.card img{width:100%;height:120px;object-fit:cover}
input,select{padding:10px;background:#1a1a1a;border:1px solid #222;color:#fff;border-radius:6px;width:100%;box-sizing:border-box;margin:4px 0}
#drop-zone{border:2px dashed #d4af37;border-radius:12px;padding:30px;text-align:center;background:#0a0a0a;margin:10px 0;transition:all .2s}
#drop-zone.dragover{background:#1a1a1a;border-color:#fff}
#preview{display:grid;grid-template-columns:repeat(auto-fill,minmax(80px,1fr));gap:8px;margin:10px 0}
#preview img{width:100%;height:80px;object-fit:cover;border-radius:6px;border:1px solid #222}
</style>
</head><body>
<header style="background:#d4af37;color:#000;padding:12px;display:flex;justify-content:space-between"><b>ADMIN - Alice</b><div><a href="/" style="color:#000;margin-right:10px">Ver site</a><a href="/admin/logout" style="color:#000;font-weight:bold">Sair</a></div></header>
<div style="max-width:1100px;margin:auto;padding:20px">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
<div style="background:#111;border:1px solid #222;padding:15px;border-radius:10px">
<h3 style="color:#d4af37;margin-top:0">📁 Criar Pasta e Postar Fotos</h3>
<form action="/upload" method="post" enctype="multipart/form-data" id="upload-form">
<label style="color:#888;font-size:12px">Nome da pasta:</label>
<input name="album" placeholder="Ex: Casamento Ana e João - 12/10" required style="border:1px solid #d4af37">
<label style="color:#888;font-size:12px">Título base:</label>
<input name="titulo" placeholder="Ex: Casamento Ana" required>

<div id="drop-zone">
<div style="font-size:40px">📸</div>
<b>Arraste 10 fotos aqui</b><br>
<small style="color:#888">ou clique para escolher da galeria</small><br>
<small style="color:#d4af37">Pode escolher várias de uma vez no celular, sem precisar CTRL!</small>
<input type="file" name="fotos" id="fotos-input" multiple accept="image/*" style="display:none">
<button type="button" onclick="document.getElementById('fotos-input').click()" style="margin-top:10px;background:#222;color:#d4af37;border:1px solid #d4af37;padding:8px 15px;border-radius:20px">📂 Escolher Fotos da Galeria</button>
</div>

<div id="preview"></div>
<p id="contador" style="color:#d4af37;font-weight:bold;text-align:center"></p>

<button type="submit" id="btn-postar" style="width:100%;background:#d4af37;padding:12px;border:none;border-radius:6px;font-weight:bold;margin-top:10px;display:none">📁 POSTAR <span id="qtd-btn">0</span> FOTOS NA PASTA</button>
</form>
</div>

<div style="background:#111;border:1px solid #222;padding:15px;border-radius:10px">
<h3 style="color:#d4af37;margin-top:0">📁 Pastas criadas</h3>
{% for a in albuns %}
<div style="display:flex;justify-content:space-between;background:#0a0a0a;padding:8px;border-radius:6px;margin:5px 0"><span>📁 {{a['album']}} ({{a['qtd']}})</span><span><a href="/?album={{a['album']}}" style="color:#d4af37;font-size:12px">Ver</a> <a href="/delete_album/{{a['album']}}" style="color:#ff6666;font-size:12px;margin-left:5px" onclick="return confirm('Apagar pasta inteira?')">Apagar</a></span></div>
{% endfor %}
{% if not albuns %}<p style="color:#888">Nenhuma pasta ainda</p>{% endif %}

<h3 style="color:#d4af37;margin-top:20px">📅 Agendamentos ({{ags|length}})</h3>
<div style="max-height:250px;overflow:auto">
{% for ag in ags %}
<div style="background:#0a0a0a;border:1px solid #222;padding:8px;border-radius:6px;margin:5px 0;font-size:12px"><b>{{ag[1]}}</b> - {{ag[3]}} {{ag[4]}}<br>{{ag[2]}} - {{ag[6]}}</div>
{% endfor %}
</div>

<h3 style="color:#d4af37;margin-top:20px">⭐ Avaliação Google</h3>
<p style="color:#888;font-size:12px">Coloque seu link do Google Meu Negócio aqui no código (GOOGLE_LINK) e os clientes vão avaliar!</p>
</div>
</div>

<h3 style="margin-top:30px">Fotos recentes</h3>
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px">
{% for f in fotos[:50] %}
<div class="card"><img src="/static/uploads/{{f['filename']}}"><div style="padding:6px"><small>{{f['album']}}<br>{{f['titulo']}}</small><br><a href="/delete/{{f[0]}}" style="color:#ff6666;font-size:11px" onclick="return confirm('Apagar?')">Apagar</a></div></div>
{% endfor %}
</div>
</div>

<script>
let allFiles = [];
let compressedFiles = [];
const input = document.getElementById('fotos-input');
const dropZone = document.getElementById('drop-zone');
const preview = document.getElementById('preview');
const contador = document.getElementById('contador');
const btn = document.getElementById('btn-postar');
const qtdBtn = document.getElementById('qtd-btn');
const form = document.getElementById('upload-form');

function compressImage(file, maxWidth=1600, quality=0.7){
  return new Promise((resolve)=>{
    const reader = new FileReader();
    reader.onload = e=>{
      const img = new Image();
      img.onload = ()=>{
        let w = img.width, h = img.height;
        if(w > maxWidth){ h = h * maxWidth / w; w = maxWidth; }
        const canvas = document.createElement('canvas');
        canvas.width = w; canvas.height = h;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, w, h);
        canvas.toBlob(blob=>{
          const newFile = new File([blob], file.name.replace(/\.\w+$/, '.jpg'), {type:'image/jpeg'});
          resolve(newFile);
        }, 'image/jpeg', quality);
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  });
}

async function handleFiles(novos){
  contador.innerText = 'Comprimindo fotos... aguarde';
  for(const file of novos){
    if(allFiles.length >= 10) break;
    if(!file.type.startsWith('image/')) continue;
    const compressed = await compressImage(file);
    allFiles.push(compressed);
  }
  updatePreview();
}

function updatePreview(){
  preview.innerHTML='';
  allFiles.forEach((file,i)=>{
    const reader = new FileReader();
    reader.onload = e=>{
      const div = document.createElement('div');
      div.style.position='relative';
      div.innerHTML=`<img src="${e.target.result}"><small style="font-size:9px;display:block;text-align:center">${(file.size/1024).toFixed(0)}KB</small><a style="color:red;font-size:10px;cursor:pointer;display:block;text-align:center" onclick="remover(${i})">X remover</a>`;
      preview.appendChild(div);
    }
    reader.readAsDataURL(file);
  });
  contador.innerText = allFiles.length>0 ? `${allFiles.length} fotos prontas para postar (já comprimidas!)` : '';
  qtdBtn.innerText = allFiles.length;
  btn.style.display = allFiles.length>0 ? 'block' : 'none';
  const dt = new DataTransfer();
  allFiles.forEach(f=>dt.items.add(f));
  input.files = dt.files;
}

function remover(i){
  allFiles.splice(i,1);
  updatePreview();
}

input.addEventListener('change', async e=>{
  const novos = Array.from(e.target.files);
  await handleFiles(novos);
  input.value='';
});

dropZone.addEventListener('dragover', e=>{ e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', e=>{ dropZone.classList.remove('dragover'); });
dropZone.addEventListener('drop', async e=>{
  e.preventDefault();
  dropZone.classList.remove('dragover');
  const novos = Array.from(e.dataTransfer.files).filter(f=>f.type.startsWith('image/'));
  await handleFiles(novos);
});
dropZone.addEventListener('click', e=>{
  if(e.target.tagName!=='BUTTON' && e.target.tagName!=='A') document.getElementById('fotos-input').click();
});

form.addEventListener('submit', e=>{
  if(allFiles.length===0){ e.preventDefault(); alert('Escolha pelo menos 1 foto!'); return; }
  if(allFiles.length>10){ e.preventDefault(); alert('Máximo 10 fotos por vez! No Vercel free só aguenta 10 pequenas. Poste 10, depois mais 10.'); return; }
  btn.innerText='Enviando... aguarde';
  btn.disabled=true;
});
</script>
</body></html>
"""

app=app
