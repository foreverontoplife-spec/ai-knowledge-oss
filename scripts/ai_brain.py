#!/usr/bin/env python3
"""ai_brain：扫描文件夹里的 AI 聊天导出（zip/json），转成 Obsidian 兼容 Markdown，存到 sources/<平台>/<年>/<年-月>/。
仅用标准库。示例：
  python scripts/ai_brain.py                      # 扫描 ~/Downloads
  python scripts/ai_brain.py --src D:/exports --push
  python scripts/ai_brain.py --file x.json --platform claude
  python scripts/ai_brain.py --local --push          # 读取本机 Claude Code/DeepSeek、ChatGPT(Codex) 桌面版会话
"""
import argparse, hashlib, json, os, re, subprocess, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from converters import REGISTRY, detect

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(REPO, ".ai_brain", "processed.json")

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def load_jsons(path):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.lower().endswith(".json"):
                    try: yield os.path.basename(n), json.loads(z.read(n).decode("utf-8-sig"))
                    except Exception: pass
    else:
        try:
            with open(path, encoding="utf-8-sig") as f: yield os.path.basename(path), json.load(f)
        except Exception: pass

def slug(s):
    s = re.sub(r"[\\/:*?\"<>|#^\[\]\s]+", "-", (s or "untitled").strip()).strip("-.")
    return s[:60] or "untitled"

def q(s): return json.dumps(s or "", ensure_ascii=False)

def index(root):
    ids = {}
    for dp, _, fs in os.walk(root):
        for f in fs:
            if f.endswith(".md"):
                p = os.path.join(dp, f)
                with open(p, encoding="utf-8") as fh:
                    for i, line in enumerate(fh):
                        if line.startswith("id: "): ids[json.loads(line[4:])] = p; break
                        if i > 15: break
    return ids

def render(conv, platform, cid):
    lines = ["---", f"title: {q(conv['title'] or '无标题')}", f"platform: {platform}", f"id: {q(cid)}",
             f"created: {q(conv['created'])}", f"updated: {q(conv['updated'])}", f"messages: {len(conv['messages'])}",
             "tags:", "  - ai-chat", f"  - {platform}", "---", "", f"# {conv['title'] or '无标题'}", ""]
    for role, text, t in conv["messages"]:
        lines += [f"## {'🧑 用户' if role == 'user' else '🤖 AI'}" + (f" · {t[:19].replace('T', ' ')}" if t else ""), "", text.strip(), ""]
    return "\n".join(lines)

def write(conv, platform, root, ids):
    cid = f"{platform}:{conv['id']}"
    date = (conv["created"] or "1970-01-01")[:10]
    old = ids.get(cid)
    path = old or os.path.join(root, platform, date[:4], date[:7], f"{date}-{slug(conv['title'])}.md")
    if not old:
        base, n = path[:-3], 2
        while os.path.exists(path): path, n = f"{base}-{n}.md", n + 1
    new = render(conv, platform, cid)
    if old:
        with open(old, encoding="utf-8") as f:
            if f.read() == new: return "same"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f: f.write(new)
    ids[cid] = path
    return "updated" if old else "new"

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=os.path.join(os.path.expanduser("~"), "Downloads"), help="要扫描的文件夹（默认 ~/Downloads）")
    ap.add_argument("--file", action="append", default=[], help="只处理指定文件（可多次）")
    ap.add_argument("--platform", default="auto", choices=["auto"] + sorted(REGISTRY))
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--force", action="store_true", help="忽略已处理记录，重新处理")
    ap.add_argument("--local", action="store_true", help="读取本机客户端会话（不扫描导出文件）")
    ap.add_argument("--commit", action="store_true"); ap.add_argument("--push", action="store_true", help="commit 并 push")
    a = ap.parse_args()
    root = os.path.join(a.repo, "sources"); log_path = os.path.join(a.repo, ".ai_brain", "processed.json")
    log = json.load(open(log_path, encoding="utf-8")) if os.path.exists(log_path) else {}
    files = [] if a.local else (a.file or [os.path.join(a.src, f) for f in sorted(os.listdir(a.src)) if f.lower().endswith((".zip", ".json"))])
    ids = index(root); st = {"new": 0, "updated": 0, "same": 0}; plats = set(); skipped = 0
    if a.local:
        import local_sources as L
        per = {}
        for p, reader in L.iter_local():
            try: stt = os.stat(p); sig = [int(stt.st_mtime), stt.st_size]
            except OSError: continue
            key = "local:" + p
            if log.get(key) == sig and not a.force: skipped += 1; continue
            try: plat, conv = reader()
            except Exception as e: print("读取失败", p, type(e).__name__); continue
            if p in L.SKIPPED: continue
            if conv.get("id") and conv["messages"]:
                r = write(conv, plat, root, ids); st[r] += 1; plats.add(plat)
                per[plat] = per.get(plat, 0) + 1
            log[key] = sig
        print("本机来源（本次处理会话数）:", per or "无变化")
        if L.SKIPPED: print(f"跳过 {len(L.SKIPPED)} 个 .zst 压缩会话（缺少 zstandard，请用 run_local_import.ps1 通过 uv 运行）")
    for p in files:
        h = sha(p)
        if h in log and not a.force: skipped += 1; continue
        found = []
        for name, data in load_jsons(p):
            plat = a.platform if a.platform != "auto" else detect(name, data)
            if not plat: continue
            found.append(plat); plats.add(plat)
            for conv in REGISTRY[plat].convert(data):
                if conv.get("id") and conv["messages"]: st[write(conv, plat, root, ids)] += 1
        if found: log[h] = {"file": os.path.basename(p), "platforms": sorted(set(found))}
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f: json.dump(log, f, ensure_ascii=False, indent=1)
    print(f"平台: {', '.join(sorted(plats)) or '无'} | 新增 {st['new']} | 更新 {st['updated']} | 未变 {st['same']} | 已处理过跳过 {skipped} 个文件")
    if (a.commit or a.push) and st["new"] + st["updated"]:
        g = lambda *x: subprocess.run(["git", "-C", a.repo, *x], check=True)
        g("add", "sources", ".ai_brain"); g("commit", "-m", f"import {'/'.join(sorted(plats))}: +{st['new']} ~{st['updated']}")
        if a.push: g("push")

if __name__ == "__main__": main()
