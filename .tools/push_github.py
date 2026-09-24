# -*- coding: utf-8 -*-
"""把 cet4-word-miner 通过 GitHub REST API 推送到 klb299/cet4-word-miner。

用法：
    python .tools/push_github.py <TOKEN> [--dry]

行为：
  1. 校验 token / 取用户名
  2. 仓库不存在则创建（public）
  3. 逐个文件建/更新 blob -> 建 tree -> 建 commit -> 更新 ref
  4. 输出仓库地址与 Pages 地址
不依赖 git，只走 api.github.com。
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = r"D:\项目\4级\cet4-word-miner"
API = "https://api.github.com"
REPO = "cet4-word-miner"

# 不进仓库的东西
SKIP_DIRS = {".shots", "__pycache__", ".git", ".workbuddy", "node_modules"}
SKIP_FILES = {".DS_Store", "Thumbs.db"}
SKIP_EXT = {".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".zip", ".exe"}
# 截图/临时目录不传；输出产物要传（网页就是成品）
MAX_BYTES = 45 * 1024 * 1024


def req(method, path, token, body=None, raw=False, tries=4):
    """发一次 API 请求。网络抖动（连接被对端关掉 / 超时）自动重试，
       否则 51 个文件传到一半断一次就整个白跑。HTTP 4xx/5xx 不重试，那不是抖动。"""
    url = path if path.startswith("http") else API + path
    data = json.dumps(body).encode() if body is not None else None
    last = None
    for attempt in range(tries):
        r = urllib.request.Request(url, data=data, method=method)
        r.add_header("Authorization", "Bearer " + token)
        r.add_header("Accept", "application/vnd.github+json")
        r.add_header("User-Agent", "cet4-word-miner-push")
        r.add_header("X-GitHub-Api-Version", "2022-11-28")
        if data:
            r.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                txt = resp.read().decode()
                return resp.status, (txt if raw else (json.loads(txt) if txt else {}))
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:400]
            return e.code, detail
        except (urllib.error.URLError, OSError) as e:
            last = e
            if attempt < tries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
    return 0, f"network error: {type(last).__name__}: {last}"


def collect():
    """收集要上传的文件，返回 [(仓库内路径, 字节), ...]"""
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn in SKIP_FILES or os.path.splitext(fn)[1].lower() in SKIP_EXT:
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT).replace("\\", "/")
            try:
                with open(full, "rb") as f:
                    b = f.read()
            except OSError:
                continue
            if len(b) > MAX_BYTES:
                print(f"  跳过（超过 45MB）：{rel}")
                continue
            out.append((rel, b))
    out.sort(key=lambda x: x[0])
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    token = sys.argv[1].strip()
    dry = "--dry" in sys.argv

    st, me = req("GET", "/user", token)
    if st != 200:
        print(f"token 校验失败 [{st}]：{me}")
        return 1
    user = me["login"]
    print(f"已认证：{user}")

    files = collect()
    total = sum(len(b) for _, b in files)
    print(f"待上传 {len(files)} 个文件，共 {total/1024/1024:.2f} MB")
    for rel, b in files[:200]:
        print(f"    {rel}  {len(b)/1024:.1f} KB")
    if len(files) > 200:
        print(f"    … 另有 {len(files)-200} 个")
    if dry:
        print("\n--dry：只列清单，未上传。")
        return 0

    # 建仓库（已存在则忽略 422）
    st, r = req("GET", f"/repos/{user}/{REPO}", token)
    if st == 404:
        st, r = req("POST", "/user/repos", token, {
            "name": REPO,
            "description": "CET-4 历年真题重点词提取工具：每个词都带真题原句、题目情境与中文译文，"
                           "按年份题型归类，导出可交互学习网页 / Markdown / Anki。",
            "homepage": f"https://{user}.github.io/{REPO}/output/index.html",
            "private": False,
            "has_issues": True, "has_wiki": False, "auto_init": False,
        })
        if st not in (200, 201):
            print(f"建仓库失败 [{st}]：{r}")
            return 1
        print(f"已创建仓库 {user}/{REPO}")
    else:
        print(f"仓库已存在 {user}/{REPO}，将覆盖更新")

    # 取默认分支当前 commit
    st, info = req("GET", f"/repos/{user}/{REPO}", token)
    branch = info.get("default_branch") or "main"
    parent = None
    st, ref = req("GET", f"/repos/{user}/{REPO}/git/ref/heads/{branch}", token)
    if st == 200:
        parent = ref["object"]["sha"]
        print(f"当前 {branch} = {parent[:8]}")
    else:
        # 空仓库上 git/trees、git/blobs 一律 409（Git Repository is empty），
        # 只有 contents API 的 PUT 能落下第一个提交，用它把分支建出来。
        print(f"{branch} 还不存在，先创建初始提交")
        st, seed = req("PUT", f"/repos/{user}/{REPO}/contents/.gitkeep", token, {
            "message": "chore: 初始化仓库",
            "content": base64.b64encode(b"").decode(),
            "branch": branch,
        })
        if st not in (200, 201):
            print(f"初始化失败 [{st}]：{seed}")
            return 1
        parent = seed["commit"]["sha"]
        print(f"已初始化 {branch} = {parent[:8]}")

    # 上传 blob
    tree = []
    for i, (rel, b) in enumerate(files, 1):
        st, blob = req("POST", f"/repos/{user}/{REPO}/git/blobs", token, {
            "content": base64.b64encode(b).decode(),
            "encoding": "base64",
        })
        if st not in (200, 201):
            print(f"  上传失败 {rel} [{st}]：{blob}")
            return 1
        tree.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        if i % 25 == 0 or i == len(files):
            print(f"  已上传 {i}/{len(files)}")

    st, nt = req("POST", f"/repos/{user}/{REPO}/git/trees", token,
                 {"tree": tree})
    if st not in (200, 201):
        print(f"建 tree 失败 [{st}]：{nt}")
        return 1

    payload = {"message": "CET-4 真题词汇工具：手机端适配 + 全面数据修复",
               "tree": nt["sha"]}
    if parent:
        payload["parents"] = [parent]
    st, cm = req("POST", f"/repos/{user}/{REPO}/git/commits", token, payload)
    if st not in (200, 201):
        print(f"建 commit 失败 [{st}]：{cm}")
        return 1
    print(f"已建 commit {cm['sha'][:8]}")

    if parent:
        st, rr = req("PATCH", f"/repos/{user}/{REPO}/git/refs/heads/{branch}",
                     token, {"sha": cm["sha"], "force": False})
    else:
        st, rr = req("POST", f"/repos/{user}/{REPO}/git/refs", token,
                     {"ref": f"refs/heads/{branch}", "sha": cm["sha"]})
    if st not in (200, 201):
        print(f"更新分支失败 [{st}]：{rr}")
        return 1
    print(f"已更新 {branch}")

    print()
    print("完成：")
    print(f"  仓库  https://github.com/{user}/{REPO}")
    print(f"  网页  https://{user}.github.io/{REPO}/output/index.html")
    print()
    print("提示：GitHub Pages 需要在仓库 Settings -> Pages 里把 Source 设为")
    print(f"      Deploy from a branch -> {branch} -> / (root) 才会生效。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
