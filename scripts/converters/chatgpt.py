"""ChatGPT: conversations.json，树形 mapping（含分支，按 current_node 取最终分支）。"""
from .common import ts, text_of
NAME = "chatgpt"

def detect(filename, data):
    return isinstance(data, list) and bool(data) and isinstance(data[0], dict) and "mapping" in data[0] \
        and not any("fragments" in (n.get("message") or {}) for n in data[0]["mapping"].values())

def _chain(mapping, current):
    if not current or current not in mapping:  # 没有 current_node：从根沿最后一个子节点走
        roots = [k for k, n in mapping.items() if not n.get("parent")]
        node, seq = (roots[0] if roots else None), []
        while node:
            seq.append(mapping[node]); kids = mapping[node].get("children") or []
            node = kids[-1] if kids and kids[-1] in mapping else None
        return seq
    seq, seen = [], set()
    while current and current in mapping and current not in seen:
        seen.add(current); seq.append(mapping[current]); current = mapping[current].get("parent")
    return list(reversed(seq))

def convert(data):
    for c in data:
        msgs = []
        for n in _chain(c.get("mapping") or {}, c.get("current_node")):
            m = n.get("message") or {}
            role = (m.get("author") or {}).get("role")
            if (m.get("metadata") or {}).get("is_visually_hidden_from_conversation"): continue
            t = text_of(m.get("content"))
            if role in ("user", "assistant") and t.strip(): msgs.append((role, t, ts(m.get("create_time"))))
        yield dict(id=c.get("conversation_id") or c.get("id"), title=c.get("title"),
                   created=ts(c.get("create_time")), updated=ts(c.get("update_time")), messages=msgs)
