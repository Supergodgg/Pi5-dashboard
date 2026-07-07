#!/usr/bin/env python3
import json, os, re, sqlite3, sys
from datetime import datetime, timezone

DB = os.path.expanduser('~/.hermes/state.db')
OUT = '/tmp/dashboard-comm.js'
MAX = 8

PLAT = {
    'weixin': {'a':'微','l':'WeChat','p':'weixin'},
    'telegram': {'a':'✈','l':'Telegram','p':'telegram'},
    'discord': {'a':'💬','l':'Discord','p':'discord'},
    'cli': {'a':'⬛','l':'Terminal','p':'cli'},
}

def clean(t):
    if not t: return ''
    t = re.sub(r'<thinking>.*?</thinking>', '', t, flags=re.DOTALL)
    t = re.sub(r'<.*?>', '', t)
    t = t.strip()
    return t[:150] if t else '(tool use)'

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT m.role,m.content,m.timestamp,s.source FROM messages m JOIN sessions s ON m.session_id=s.id WHERE m.content IS NOT NULL AND m.content!='' ORDER BY m.timestamp DESC LIMIT ?", (MAX*4,)).fetchall()
conn.close()

msgs = []
seen = set()
for r in rows:
    if len(msgs) >= MAX: break
    role = r['role']; src = r['source'] or 'cli'
    ts = datetime.fromtimestamp(r['timestamp'], tz=timezone.utc).astimezone()
    key = (role, (r['content'] or '')[:30])
    if key in seen: continue
    seen.add(key)
    pi = PLAT.get(src, {'a':'?','l':src,'p':'hermes'})
    if role == 'user':
        msgs.append({'platform':pi['p'],'avatar':pi['a'],'role':'user','label':pi['l'],'time':ts.strftime('%H:%M'),'text':clean(r['content'])})
    elif role == 'assistant' and len(msgs) > 0:
        m = re.search(r'<thinking>(.*?)</thinking>', r['content'] or '', re.DOTALL)
        think = None
        if m:
            lines = [l.strip() for l in m.group(1).strip().split('\n') if l.strip()]
            think = ' '.join(lines[:6])[:250]
        msgs.append({'platform':'hermes','avatar':'🤖','role':'agent','label':'Hermes','time':ts.strftime('%H:%M'),'text':clean(r['content']),'thinking':think})

with open(OUT,'w') as f:
    f.write('window.__DASHBOARD_COMM__ = '+json.dumps(msgs,ensure_ascii=False)+';\n')
