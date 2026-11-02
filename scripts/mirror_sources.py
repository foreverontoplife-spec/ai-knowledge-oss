#!/usr/bin/env python3
"""mirror_sources：把 sources/ 复制一份到仓库外的镜像文件夹，给 basic-memory 的 ai-sources 项目做语义搜索。
原因：basic-memory 同步时会改写 Markdown 的 frontmatter（加 permalink、改引号），直接指向 sources/ 会破坏去重并造成
git 改动。镜像只在原文内容变化时才重新复制，原文删除时镜像也删除；sources/ 本身永远不被改动。
默认镜像位置：%LOCALAPPDATA%\\ai-knowledge\\sources-index（可用 --dest 修改）。"""
import argparse, hashlib, json, os, shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "ai-knowledge", "sources-index")

def sha(p):
    with open(p, "rb") as f: return hashlib.sha256(f.read()).hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("--dest", default=DEFAULT); a = ap.parse_args()
    src = os.path.join(REPO, "sources"); state_p = os.path.join(a.dest, ".mirror_state.json")
    os.makedirs(a.dest, exist_ok=True)
    state = json.load(open(state_p, encoding="utf-8")) if os.path.exists(state_p) else {}
    seen, n_new = set(), 0
    for dp, _, fs in os.walk(src):
        for f in fs:
            if not f.endswith(".md"): continue
            p = os.path.join(dp, f); rel = os.path.relpath(p, src); seen.add(rel); h = sha(p)
            if state.get(rel) == h and os.path.exists(os.path.join(a.dest, rel)): continue
            os.makedirs(os.path.dirname(os.path.join(a.dest, rel)), exist_ok=True)
            shutil.copyfile(p, os.path.join(a.dest, rel)); state[rel] = h; n_new += 1
    gone = [r for r in state if r not in seen]
    for r in gone:
        try: os.remove(os.path.join(a.dest, r))
        except OSError: pass
        del state[r]
    with open(state_p, "w", encoding="utf-8") as f: json.dump(state, f, ensure_ascii=False, indent=1)
    print(f"搜索镜像: 复制 {n_new} 个，删除 {len(gone)} 个 -> {a.dest}")

if __name__ == "__main__": main()