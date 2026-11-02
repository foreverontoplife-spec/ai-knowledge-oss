"""Claude: conversations.json，chat_messages 列表（尽力兼容）。"""
from .common import ts, text_of
NAME = "claude"
def detect(filename, data):
    return isinstance(data, list) and bool(data) and isinstance(data[0], dict) and "chat_messages" in data[0]
def convert(data):
    for c in data:
        msgs = []
        for m in c.get("chat_messages", []):
            t = m.get("text") or text_of(m.get("content"))
            if t.strip(): msgs.append(("user" if m.get("sender") == "human" else "assistant", t, ts(m.get("created_at"))))
        yield dict(id=c.get("uuid"), title=c.get("name"), created=ts(c.get("created_at")), updated=ts(c.get("updated_at")), messages=msgs)
