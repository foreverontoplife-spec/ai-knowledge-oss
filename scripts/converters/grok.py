"""Grok: accounts.x.ai 导出，{"conversations":[{"conversation":{},"responses":[{"response":{}}]}]}（尽力兼容）。"""
from .common import ts
NAME = "grok"
def detect(filename, data):
    if isinstance(data, dict) and "conversations" in data: return True
    return isinstance(data, list) and bool(data) and isinstance(data[0], dict) and "responses" in data[0]
def convert(data):
    for item in (data.get("conversations", []) if isinstance(data, dict) else data):
        c = item.get("conversation", item); msgs = []
        for r in item.get("responses", []):
            r = r.get("response", r)
            if (r.get("message") or "").strip():
                msgs.append(("user" if str(r.get("sender", "")).lower() in ("human", "user") else "assistant", r["message"], ts(r.get("create_time"))))
        yield dict(id=c.get("id") or c.get("conversation_id"), title=c.get("title"),
                   created=ts(c.get("create_time")), updated=ts(c.get("modify_time") or c.get("update_time")), messages=msgs)
