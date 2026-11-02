"""转换器公用工具。每个转换器返回 dict(id,title,created,updated,messages=[(role,text,time)])。"""
import datetime as dt

def ts(v):
    if v in (None, ""): return ""
    if isinstance(v, dict):
        v = v.get("$date", "")
        if isinstance(v, dict): v = v.get("$numberLong", "")
    try:
        f = float(v)
        if f > 1e12: f /= 1000
        return dt.datetime.fromtimestamp(f, dt.timezone.utc).isoformat()
    except (TypeError, ValueError):
        s = str(v)
        try: return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).isoformat()
        except ValueError: return s

def text_of(c):
    if isinstance(c, str): return c
    if isinstance(c, list): return "\n".join(t for t in (text_of(x) for x in c) if t)
    if isinstance(c, dict):
        for k in ("text", "parts", "content", "message"):
            if k in c: return text_of(c[k])
    return ""
