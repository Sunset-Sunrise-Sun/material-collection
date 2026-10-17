# -*- coding: utf-8 -*-
"""P0-1 外部门钟锚定：区分"本机时钟错误" vs "文件名日期误标"
外部权威来源（不受本机时钟影响）：
  A GitHub API 的 created_at / pushed_at —— 由 GitHub 服务器生成
  B 找回 ZIP 内成员的 mtime —— 由打包方机器写入
  C 文档内部自称日期
"""
import json
import os
import ssl
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime

ROOT = r"D:\筑工杯数据获取"
OWNER, REPO = "Sunset-Sunrise-Sun", "material-collection"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def api(u):
    req = urllib.request.Request(u, headers={"User-Agent": "dsh-agent"})
    with urllib.request.urlopen(req, timeout=40, context=CTX) as r:
        return json.loads(r.read())


print("=" * 104)
print("### A. GitHub 仓库元数据（GitHub 服务器生成，不受本机时钟影响）")
meta = api("https://api.github.com/repos/%s/%s" % (OWNER, REPO))
for k in ("created_at", "updated_at", "pushed_at"):
    print("  %-12s %s" % (k, meta.get(k)))
print("  说明：created_at = 仓库创建时间；pushed_at = 最近推送时间")

print()
print("-- 各 commit 的 GitHub 侧 author/committer 时间（前 6 条）")
commits = api("https://api.github.com/repos/%s/%s/commits?per_page=6" % (OWNER, REPO))
for c in commits:
    print("  %s  author=%s  committer=%s" % (
        c["sha"][:12], c["commit"]["author"]["date"], c["commit"]["committer"]["date"]))

print()
print("-- 分支 review/phase2-local-gis 的 GitHub 侧提交")
try:
    br = api("https://api.github.com/repos/%s/%s/branches/review%%2Fphase2-local-gis"
             % (OWNER, REPO))
    c = br["commit"]["commit"]
    print("  %s  author=%s  committer=%s" % (
        br["commit"]["sha"][:12], c["author"]["date"], c["committer"]["date"]))
except Exception as e:
    print("  查询失败:", str(e)[:120])

print()
print("=" * 104)
print("### B. 找回 ZIP 内成员的原始时间戳（打包方机器写入）")
ZIPS = [
    ("缺失官方取证输入包", os.path.join(
        r"D:\webDownload",
        "%E5%B9%BF%E5%B7%9E%E5%B8%82AI%E8%80%81_%E7%BC%BA%E5%A4%B1"
        "%E5%AE%98%E6%96%B9%E5%8F%96%E8%AF%81%E8%BE%93%E5%85%A5%E6%96%87%E4%BB%B6_20261017.zip")),
    ("官方证据包", os.path.join(
        r"D:\webDownload",
        "%E5%B9%BF%E5%B7%9EAI%E5%85%BB%E8%80%81_%E5%AE%98%E6%96%B9%E8%AF%81%E6%8D%AE.zip")),
]
for lab, p in ZIPS:
    print()
    if not os.path.exists(p):
        # 尝试通配
        import glob
        pat = os.path.join(r"D:\webDownload", "*%E5%AE%98%E6%96%B9%E8%AF%81%E6%8D%AE*")
        alts = glob.glob(pat)
        if alts:
            p = alts[0]
        else:
            print("  [缺失] %s" % lab)
            continue
    print("  %s (%d B)" % (lab, os.path.getsize(p)))
    try:
        with zipfile.ZipFile(p) as z:
            for i in z.infolist():
                if i.filename.endswith("/"):
                    continue
                raw = i.filename
                if not (i.flag_bits & 0x800):
                    try:
                        raw = i.filename.encode("cp437").decode("utf-8")
                    except Exception:
                        pass
                print("    mtime=%s  %8d B  %s" % (i.date_time, i.file_size, raw))
    except Exception as e:
        print("    读取失败:", str(e)[:100])

print()
print("=" * 104)
print("### C. 文档内部自称日期 vs 文件名日期")
DOCS = [
    ("阶段1(10-30)增量复核报告",
     os.path.join(ROOT, "广州市AI养老研究_官方取证与GIS衔接_增量复核_20261030",
                  "增量复核报告_找回输入后补全_20261030.md")),
    ("阶段1(10-30)变更日志",
     os.path.join(ROOT, "广州市AI养老研究_官方取证与GIS衔接_增量复核_20261030",
                  "本轮变更日志与失败待核清单.md")),
    ("阶段2验收报告",
     os.path.join(ROOT, "广州市AI养老研究_第二阶段_本地实证_20261017",
                  "给ChatGPT验收用简明报告.md")),
    ("阶段2归档说明",
     os.path.join(ROOT, "广州市AI养老研究_第二阶段_本地实证_20261017",
                  "归档说明_独立验收用.md")),
]
import re
for lab, p in DOCS:
    print()
    print("  --- %s ---" % lab)
    if not os.path.exists(p):
        print("      [缺失]")
        continue
    t = open(p, encoding="utf-8").read()
    dates = Counter(re.findall(r"20\d{2}-\d{2}-\d{2}", t))
    print("      文件名日期片段:", re.findall(r"20\d{6}", os.path.basename(p)) or "无")
    print("      文内日期出现次数（前10）:")
    for d, n in dates.most_common(10):
        print("        %s  ×%d" % (d, n))
