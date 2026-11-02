#!/usr/bin/env python3
"""仓库体检：每个 .md 有 front matter（title/platform/id/created），id 不重复，无 zip、无疑似密钥。只读。"""
import os, re, sys, collections
ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
REQ = ("title", "platform", "id", "created")
SECRET = re.compile(r"(gh[p]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{40,}|s[k]-[A-Za-z0-9_-]{32,}|AKIA[0-9A-Z]{16}|xox[bpa]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
errs, ids, counts = [], collections.defaultdict(list), collections.Counter()
for dp, dns, fs in os.walk(ROOT):
    dns[:] = [d for d in dns if d != ".git"]
    for f in fs:
        p = os.path.join(dp, f); rel = os.path.relpath(p, ROOT)
        if f.lower().endswith((".zip", ".7z", ".rar")): errs.append(f"压缩包不应提交: {rel}"); continue
        try: txt = open(p, encoding="utf-8").read()
        except Exception: continue
        if SECRET.search(txt): errs.append(f"疑似密钥: {rel}")
        if not (f.endswith(".md") and rel.startswith("sources" + os.sep)): continue
        m = re.match(r"---\n(.*?)\n---\n", txt, re.S)
        if not m: errs.append(f"缺少 front matter: {rel}"); continue
        fm = dict(l.split(": ", 1) for l in m.group(1).splitlines() if ": " in l and not l.startswith(" "))
        miss = [k for k in REQ if not fm.get(k, "").strip('" ')]
        if miss: errs.append(f"缺少字段 {miss}: {rel}")
        ids[fm.get("id")].append(rel); counts[fm.get("platform", "?")] += 1
for i, ps in ids.items():
    if i and len(ps) > 1: errs.append(f"重复 id {i}: {ps}")
print("对话数量:", dict(counts), "合计", sum(counts.values()))
for e in errs: print("❌", e)
print("✅ 检查通过" if not errs else f"共 {len(errs)} 个问题"); sys.exit(1 if errs else 0)
