"""本机 AI 客户端会话读取器（只读，不修改任何应用文件）。
来源：
  - Claude Code / Claude 桌面版 Code 标签：~/.claude/projects/**/*.jsonl
    （按 model 字段区分：deepseek-* → deepseek，其余 → claude；标题取自 Claude 桌面版 claude-code-sessions/*.json）
  - ChatGPT/Codex 桌面版：~/.codex/sessions/**/rollout-*.jsonl(.zst)，标题取自 ~/.codex/session_index.jsonl
每个读取器 yield (源文件路径, 平台, conv)。conv 格式同 converters：dict(id,title,created,updated,messages=[(role,text,time)])。
"""
import glob, io, json, os, re, shutil, tempfile

HOME = os.path.expanduser("~")
LOCAL = os.environ.get("LOCALAPPDATA", "")
CLAUDE_PKG = glob.glob(os.path.join(LOCAL, "Packages", "Claude_*", "LocalCache", "Roaming", "Claude"))
SECRET = re.compile(r"(s[k]-[A-Za-z0-9_\-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9\-]{10,}|eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})")
NOISE = re.compile(r"^\s*(<[a-z_\-]+[ >]|# AGENTS\.md|Caveat: The messages below)", re.I)
SKIPPED = []  # 无法读取的文件说明

def redact(s): return SECRET.sub("[REDACTED]", s or "")

def _copy_read(path):
    """先复制到临时目录再读，避免占用/修改原文件。"""
    fd, tmp = tempfile.mkstemp(suffix=os.path.basename(path)[-12:]); os.close(fd)
    try:
        shutil.copyfile(path, tmp)
        with open(tmp, "rb") as f: data = f.read()
    finally:
        try: os.remove(tmp)
        except OSError: pass
    if path.endswith(".zst"):
        try: import zstandard
        except ImportError:
            SKIPPED.append(path); return None
        data = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(data)).read()
    return data.decode("utf-8", "replace")

def _lines(path):
    t = _copy_read(path)
    if t is None: return
    for line in t.splitlines():
        try: yield json.loads(line)
        except ValueError: pass

def _texts(content, kinds):
    if isinstance(content, str): return [content]
    out = []
    for c in content or []:
        if isinstance(c, dict) and c.get("type") in kinds and c.get("text"): out.append(c["text"])
    return out

def _push(msgs, role, text, t):
    text = redact(text).strip()
    if not text or NOISE.match(text): return
    if msgs and msgs[-1][0] == role: msgs[-1] = (role, msgs[-1][1] + "\n\n" + text, msgs[-1][2])
    else: msgs.append((role, text, t))

# ---------- Claude Code（含 DeepSeek 后端） ----------
def claude_titles():
    titles = {}
    for base in CLAUDE_PKG + [os.path.join(os.environ.get("APPDATA", ""), "Claude")]:
        for p in glob.glob(os.path.join(base, "claude-code-sessions", "**", "*.json"), recursive=True):
            try:
                d = json.loads(_copy_read(p))
                if d.get("cliSessionId") and d.get("title"): titles[d["cliSessionId"]] = d["title"]
            except Exception: pass
    return titles

def claude_code_files():
    return [p for p in glob.glob(os.path.join(HOME, ".claude", "projects", "**", "*.jsonl"), recursive=True)
            if os.sep + "subagents" + os.sep not in p]

def read_claude_code(path, titles):
    msgs, models, sid, title, first, last = [], set(), os.path.basename(path)[:-6], "", "", ""
    for o in _lines(path):
        if o.get("type") == "summary" and o.get("summary") and not title: title = o["summary"]
        if o.get("type") not in ("user", "assistant") or o.get("isSidechain") or o.get("isMeta"): continue
        m = o.get("message") or {}; t = o.get("timestamp", "")
        first = first or t; last = t or last
        if o["type"] == "assistant":
            if m.get("model") and not m["model"].startswith("<"): models.add(m["model"])
            for x in _texts(m.get("content"), ("text",)): _push(msgs, "assistant", x, t)
        else:
            for x in _texts(m.get("content"), ("text",)): _push(msgs, "user", x, t)
    plat = "deepseek" if any(x.startswith("deepseek") for x in models) else "claude"
    title = titles.get(sid) or title or (msgs[0][1].splitlines()[0][:50] if msgs else "")
    return plat, {"id": "local-" + sid, "title": title, "created": first, "updated": last, "messages": msgs,
                  "model": ",".join(sorted(models))}

# ---------- ChatGPT / Codex 桌面版 ----------
def codex_files():
    return sorted(glob.glob(os.path.join(HOME, ".codex", "sessions", "**", "rollout-*.jsonl*"), recursive=True))

def codex_titles():
    t = {}
    p = os.path.join(HOME, ".codex", "session_index.jsonl")
    if os.path.exists(p):
        for o in _lines(p):
            if o.get("id"): t[o["id"]] = o.get("thread_name", "")
    return t

def read_codex(path, titles):
    msgs, sid, first, last = [], "", "", ""
    for o in _lines(path):
        p = o.get("payload") or {}; t = o.get("timestamp", "")
        if o.get("type") == "session_meta": sid = p.get("id") or p.get("session_id") or ""; first = p.get("timestamp", t)
        if o.get("type") != "response_item" or p.get("type") != "message": continue
        role = p.get("role")
        if role not in ("user", "assistant"): continue
        last = t or last
        for x in _texts(p.get("content"), ("input_text", "output_text", "text")): _push(msgs, role, x, t)
    sid = sid or os.path.basename(path).split(".")[0][-36:]
    title = titles.get(sid) or (msgs[0][1].splitlines()[0][:50] if msgs else "")
    return "chatgpt", {"id": "codex-" + sid, "title": title, "created": first, "updated": last or first, "messages": msgs}

def iter_local():
    """yield (path, reader)；reader() 返回 (platform, conv)。"""
    ct = claude_titles()
    for p in claude_code_files(): yield p, (lambda p=p: read_claude_code(p, ct))
    xt = codex_titles()
    for p in codex_files(): yield p, (lambda p=p: read_codex(p, xt))

# 已调研、目前不支持的来源（说明见 README）
UNSUPPORTED = {
    "Claude 桌面版 聊天标签": "会话保存在 claude.ai 服务器；本地 IndexedDB 只有少量缓存元数据，没有完整消息",
    "Grok": "本机未安装 Grok 桌面客户端（网页版数据在服务器）",
    "VS Code DeepSeek 插件": "未安装独立 DeepSeek 插件；DeepSeek 实际通过 Claude Code（ANTHROPIC_BASE_URL=api.deepseek.com）使用，已由 Claude Code 读取器覆盖",
}
