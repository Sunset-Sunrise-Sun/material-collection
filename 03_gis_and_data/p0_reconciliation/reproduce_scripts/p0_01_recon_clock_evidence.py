# -*- coding: utf-8 -*-
"""P0-1 侦察：日期矛盾性质的取证式核查
关键问题：报告日期 2026-10-30 / 2026-11-01 晚于审查基准日 2026-10-17。
需要判定属于：A) 误标  B) 项目时钟不同  C) 材料确属未来版本
判据（尽量用不能人为编造的证据）：
  1 系统时钟
  2 文件系统 CreationTime / LastWriteTime（可被复制操作改写，仅作辅助）
  3 git commit 时间戳（由提交机器写入）
  4 geocode_cache.json 内的 API 调用时间戳 called_at（外部调用时写入，难伪造）
  5 仓库首次提交时间（GitHub 侧）
"""
import json
import os
import subprocess
from datetime import datetime, timezone

ROOT = r"D:\筑工杯数据获取"

print("=" * 104)
print("### 1 系统时钟")
now = datetime.now()
print("  本地时间:", now.strftime("%Y-%m-%d %H:%M:%S"))
print("  UTC     :", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"))
print("  时区偏移:", now.astimezone().strftime("%z"))
print("  时间戳源: Windows 系统时钟（Get-Date / Python datetime.now）")

print()
print("=" * 104)
print("### 2 geocode_cache.json 内的 API 调用时间戳（外部调用时写入）")
CACHE = os.path.join(ROOT, "out", "geocode_cache.json")
cache = json.load(open(CACHE, encoding="utf-8"))
times = [v.get("called_at") for v in cache.values() if v.get("called_at")]
print("  条目数:", len(cache), "| 有 called_at:", len(times))
print("  最早:", min(times))
print("  最晚:", max(times))
from collections import Counter
dates = Counter(t[:10] for t in times)
print("  按日期分布:")
for d, n in sorted(dates.items()):
    print("    %s  %d 条" % (d, n))

print()
print("=" * 104)
print("### 3 关键目录/文件的文件系统时间戳")
TARGETS = [
    ("阶段2输出目录", os.path.join(ROOT, "广州市AI养老研究_第二阶段_本地实证_20261017")),
    ("阶段1增量复核目录(10-30)", os.path.join(ROOT, "广州市AI养老研究_官方取证与GIS衔接_增量复核_20261030")),
    ("阶段1衔接目录(10-29)", os.path.join(ROOT, "广州市AI养老研究_官方取证与GIS衔接_20261029")),
    ("封版包zip", os.path.join(ROOT, "广州市AI养老研究_最终成果包_20261020.zip")),
    ("geocode_cache.json", CACHE),
    ("geocode_results.csv", os.path.join(ROOT, "out", "geocode_results.csv")),
    ("冻结框架xlsx", os.path.join(ROOT, "_work_probe", "_report_stage",
                                  "广州市AI养老研究_最终成果包_20261020", "02_前序轮次成果",
                                  "16项指标操作化表_最终版.xlsx")),
]
for lab, p in TARGETS:
    if not os.path.exists(p):
        print("  [缺失] %-28s %s" % (lab, p))
        continue
    st = os.stat(p)
    print("  %-28s" % lab)
    print("      创建: %s | 修改: %s" % (
        datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
        datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")))
    print("      路径: %s" % os.path.relpath(p, ROOT))

print()
print("=" * 104)
print("### 4 阶段2 每个文件的文件系统时间戳（用于判断是否本轮生成）")
P2 = os.path.join(ROOT, "广州市AI养老研究_第二阶段_本地实证_20261017")
for fn in sorted(os.listdir(P2)):
    p = os.path.join(P2, fn)
    if not os.path.isfile(p):
        continue
    st = os.stat(p)
    print("  %-46s 创建 %s  修改 %s" % (
        fn, datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M"),
        datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")))

print()
print("=" * 104)
print("### 5 阶段1(10-30) 目录文件时间戳")
P1 = os.path.join(ROOT, "广州市AI养老研究_官方取证与GIS衔接_增量复核_20261030")
if os.path.isdir(P1):
    for fn in sorted(os.listdir(P1)):
        p = os.path.join(P1, fn)
        if not os.path.isfile(p):
            continue
        st = os.stat(p)
        print("  %-46s 创建 %s  修改 %s" % (
            fn, datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M"),
            datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")))
else:
    print("  **目录不存在**")

print()
print("=" * 104)
print("### 6 外部下载文件的真实下载时间（webDownload）")
WD = r"D:\webDownload"
if os.path.isdir(WD):
    fs = sorted(os.listdir(WD), key=lambda f: os.stat(os.path.join(WD, f)).st_mtime, reverse=True)[:10]
    for f in fs:
        st = os.stat(os.path.join(WD, f))
        print("  %-72s 修改 %s" % (f[:72],
              datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")))
else:
    print("  无")

print()
print("=" * 104)
print("### 7 git 提交时间戳（仓库侧，由提交机器写入）")
GIT = r"C:\Program Files\Git\cmd\git.exe"
REPO = os.path.join(ROOT, "_work_probe", "stage2repo")
if os.path.isdir(REPO):
    r = subprocess.run([GIT, "-c", "core.quotepath=false", "log", "--all",
                        "--format=%h|%cI|%aI|%d|%s", "-n", "12"],
                       cwd=REPO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print(r.stdout.strip() or r.stderr[:300])
else:
    print("  本地 clone 不存在:", REPO)
