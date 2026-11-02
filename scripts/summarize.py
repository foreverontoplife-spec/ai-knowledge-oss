#!/usr/bin/env python3
"""summarize：把 sources/ 里新增或改过的对话，用 DeepSeek（OpenAI 兼容接口）提炼成摘要笔记，
写到 brain/0-Inbox/summaries/<日期>-<标题>.md（决策 / 待办 / 问题 / 要点 + 原文链接）。
已处理记录：.ai_brain/summarized.json（按文件 sha256，内容变了才重做）。
会花钱，默认关闭：ai_brain_config.json 里 "enable_summarize": true 才会在定时任务里运行（--auto）。
密钥只在运行时读取：环境变量 DEEPSEEK_API_KEY，或 ~/.claude/settings.json 的 env（BASE_URL 指向 deepseek 时的
ANTHROPIC_AUTH_TOKEN / ANTHROPIC_API_KEY）。不会打印或写入仓库。
示例：
  python scripts/summarize.py --dry-run          # 只列出待摘要的对话
  python scripts/summarize.py --max 2            # 手动摘要最多 2 个
  python scripts/summarize.py --auto             # 定时任务用：配置未开启则直接退出
"""
import argparse, hashlib, json, os, re, sys, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(REPO, "ai_brain_config.json")
DEFAULT_CFG = {"enable_summarize": False, "summarize_model": "deepseek-flash", "summarize_base_url": "https://api.deepseek.com",
               "summarize_max_per_run": 10, "summarize_max_chars": 24000, "summarize_min_chars": 300}
PROMPT = ("你是个人知识库助手。阅读下面这段用户与 AI 的对话，用中文输出 Markdown，严格只包含以下四个二级标题：\n"
          "## 决策\n## 待办\n## 问题\n## 要点\n"
          "每节用简短的 - 列表；待办用 - [ ] 开头；没有内容的写「- 无」。不要编造对话里没有的内容，不要复述密钥、密码。")

def cfg():
    c = dict(DEFAULT_CFG)
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH, encoding="utf-8") as f: c.update(json.load(f))
    return c

def api_key():
    k = os.environ.get("DEEPSEEK_API_KEY")
    if k: return k
    p = os.path.join(os.path.expanduser("~"), ".claude", "settings.json")
    try:
        with open(p, encoding="utf-8") as f: env = json.load(f).get("env", {})
    except Exception: return None
    if "deepseek" in str(env.get("ANTHROPIC_BASE_URL", "")).lower():
        return env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_API_KEY")
    return None

def sha(p):
    with open(p, "rb") as f: return hashlib.sha256(f.read()).hexdigest()

def meta(text):
    m = {}
    if text.startswith("---"):
        for line in text.split("\n")[1:30]:
            if line.startswith("---"): break
            if ": " in line:
                k, v = line.split(": ", 1)
                try: m[k] = json.loads(v)
                except Exception: m[k] = v
    return m

def body(text):
    if text.startswith("---"):
        i = text.find("\n---", 3)
        if i > 0: return text[i + 4:].strip()
    return text

def slug(s):
    s = re.sub(r"[\\/:*?\"<>|#^\[\]\s]+", "-", (s or "untitled").strip()).strip("-.")
    return s[:60] or "untitled"

def call(c, key, content):
    req = urllib.request.Request(c["summarize_base_url"].rstrip("/") + "/chat/completions", method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        data=json.dumps({"model": c["summarize_model"], "temperature": 0.2, "max_tokens": 1200,
                         "messages": [{"role": "system", "content": PROMPT}, {"role": "user", "content": content}]}).encode())
    with urllib.request.urlopen(req, timeout=120) as r: d = json.load(r)
    return d["choices"][0]["message"]["content"].strip(), d.get("usage", {})

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auto", action="store_true", help="定时任务模式：enable_summarize 不是 true 就退出")
    ap.add_argument("--max", type=int, help="本次最多摘要几个")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--file", action="append", default=[], help="只摘要指定的 sources md")
    a = ap.parse_args(); c = cfg()
    if a.auto and not c.get("enable_summarize"):
        print("AI 摘要未开启（ai_brain_config.json enable_summarize=false），跳过"); return
    state_p = os.path.join(REPO, ".ai_brain", "summarized.json")
    state = json.load(open(state_p, encoding="utf-8")) if os.path.exists(state_p) else {}
    src = os.path.join(REPO, "sources"); todo = []
    files = [os.path.abspath(f) for f in a.file] or sorted(os.path.join(dp, f) for dp, _, fs in os.walk(src) for f in fs if f.endswith(".md"))
    for p in files:
        rel = os.path.relpath(p, REPO).replace("\\", "/"); h = sha(p)
        if state.get(rel, {}).get("sha") == h: continue
        todo.append((p, rel, h))
    print(f"待摘要 {len(todo)} 个")
    todo = todo[: a.max if a.max is not None else c["summarize_max_per_run"]]
    if a.dry_run:
        for _, rel, _ in todo: print(" ", rel)
        return
    key = api_key()
    if not key: print("找不到 DeepSeek 密钥（DEEPSEEK_API_KEY 或 ~/.claude/settings.json），跳过"); return
    out_dir = os.path.join(REPO, "brain", "0-Inbox", "summaries"); os.makedirs(out_dir, exist_ok=True)
    tot = {"prompt_tokens": 0, "completion_tokens": 0}; n = 0
    for p, rel, h in todo:
        text = open(p, encoding="utf-8").read(); m = meta(text); b = body(text)
        old = state.get(rel, {}).get("summary")
        if len(b) < c["summarize_min_chars"]:
            state[rel] = {"sha": h, "summary": old, "skipped": "too short"}; continue
        if len(b) > c["summarize_max_chars"]:
            half = c["summarize_max_chars"] // 2; b = b[:half] + "\n\n……（中间省略）……\n\n" + b[-half:]
        try: summ, usage = call(c, key, f"标题：{m.get('title', '')}\n平台：{m.get('platform', '')}\n\n{b}")
        except Exception as e:
            print("摘要失败", rel, type(e).__name__, getattr(e, "code", "")); continue
        for k in tot: tot[k] += int(usage.get(k, 0) or 0)
        date = str(m.get("created") or "")[:10] or "1970-01-01"
        name = old or f"{date}-{slug(m.get('title'))}.md"
        if not old:
            base, i = name[:-3], 2
            while os.path.exists(os.path.join(out_dir, name)): name, i = f"{base}-{i}.md", i + 1
        link = os.path.relpath(p, out_dir).replace("\\", "/")
        note = "\n".join(["---", f"title: {json.dumps('摘要：' + str(m.get('title') or '无标题'), ensure_ascii=False)}",
            "type: summary", f"platform: {m.get('platform', '')}", f"source: {json.dumps(rel, ensure_ascii=False)}",
            f"created: {json.dumps(str(m.get('created', '')))}", "tags:", "  - ai-summary", f"  - {m.get('platform', 'ai')}", "---", "",
            f"# 摘要：{m.get('title') or '无标题'}", "", f"原文：[{os.path.basename(p)}]({link.replace(' ', '%20')})", "", summ, ""])
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="\n") as f: f.write(note)
        state[rel] = {"sha": h, "summary": name, "usage": usage}; n += 1
        print("已摘要", rel, "->", name, "tokens", usage.get("prompt_tokens"), "/", usage.get("completion_tokens"))
        with open(state_p, "w", encoding="utf-8") as f: json.dump(state, f, ensure_ascii=False, indent=1)
    with open(state_p, "w", encoding="utf-8") as f: json.dump(state, f, ensure_ascii=False, indent=1)
    print(f"完成 {n} 个，输入 {tot['prompt_tokens']} tokens，输出 {tot['completion_tokens']} tokens")

if __name__ == "__main__": main()