"""DeepSeek: conversations.json，mapping 节点里 message.fragments（REQUEST/RESPONSE）（尽力兼容）。"""
from .common import ts
NAME = "deepseek"
def detect(filename, data):
    return isinstance(data, list) and bool(data) and isinstance(data[0], dict) and "mapping" in data[0] \
        and any("fragments" in (n.get("message") or {}) for n in data[0]["mapping"].values())
def convert(data):
    for c in data:
        msgs = []
        for n in (c.get("mapping") or {}).values():
            m = n.get("message") or {}
            for f in m.get("fragments", []):
                role = {"REQUEST": "user", "RESPONSE": "assistant"}.get(str(f.get("type", "")).upper())
                if role and f.get("content"): msgs.append((role, f["content"], ts(m.get("inserted_at"))))
        yield dict(id=c.get("id"), title=c.get("title"), created=ts(c.get("inserted_at")), updated=ts(c.get("updated_at")), messages=msgs)
