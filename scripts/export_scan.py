"""export_scan：在 ~/Downloads 和 ai-knowledge/.inbox 里找官方导出文件（ChatGPT / Claude / Grok / DeepSeek 的 zip/json）。
每个文件按 (修改时间, 大小) 记一次，没变化就不再打开；只有像聊天导出的文件才交给转换器（之后再按 sha256 去重）。"""
import os, zipfile

def _is_name(n):
    b = os.path.basename(n).lower()
    return b.endswith(".json") and ("conversation" in b or "grok" in b)

def looks_like_export(p, trust=False):
    try:
        if zipfile.is_zipfile(p):
            with zipfile.ZipFile(p) as z:
                names = z.namelist()
                return any(_is_name(n) for n in names) or (trust and any(n.lower().endswith(".json") for n in names))
        if not p.lower().endswith(".json") or os.path.getsize(p) > (500 << 20): return False
        if trust: return True
        with open(p, "rb") as f: head = f.read(65536)
        return head.lstrip(b"\xef\xbb\xbf \r\n\t")[:1] in (b"[", b"{") and \
            any(k in head for k in (b'"mapping"', b'"chat_messages"', b'"conversations"', b'"responses"'))
    except Exception:
        return False

def candidates(dirs, log, force=False):
    """dirs: [(文件夹, 是否信任)]；.inbox 里的文件一律尝试，Downloads 里只取像导出的。"""
    for d, trust in dirs:
        if not os.path.isdir(d): continue
        for f in sorted(os.listdir(d)):
            p = os.path.join(d, f)
            if not os.path.isfile(p) or not f.lower().endswith((".zip", ".json")): continue
            try: st = os.stat(p)
            except OSError: continue
            key, sig = "scan:" + p, [int(st.st_mtime), st.st_size]
            if log.get(key) == sig and not force: continue
            log[key] = sig
            if looks_like_export(p, trust): yield p