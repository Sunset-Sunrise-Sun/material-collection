# -*- coding: utf-8 -*-
"""P0-1：阶段二原件与 2026-10-30 增量复核目录的逐文件清点 + 日期性质判定
产出：原件清单 CSV（文件名/字节/SHA256/创建/修改时间）+ 判定结论
"""
import csv
import hashlib
import json
import os
from datetime import datetime

ROOT = r"D:\筑工杯数据获取"
P2 = os.path.join(ROOT, "广州市AI养老研究_第二阶段_本地实证_20261017")
P1 = os.path.join(ROOT, "广州市AI养老研究_官方取证与GIS衔接_增量复核_20261030")
OUT = os.path.join(ROOT, "广州市AI养老研究_P0核对_20261017")
os.makedirs(OUT, exist_ok=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def ts(t):
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")


# 阶段二 9 份交付成果（原始交付）
DELIV9 = [
    "统一缺口与行动台账.xlsx",
    "本轮本地数据处理与GIS分析结果.xlsx",
    "数据质量问题与未解决事项.md",
    "REPRODUCE.md",
    "输入输出SHA256清单.csv",
    "给ChatGPT验收用简明报告.md",
    "变更日志与输入输出清单.md",
    "海珠坐标多证据批量核验明细.csv",
    "海珠坐标结论分层_街道可用vs点位可用.csv",
]
EXTRA = ["归档说明_独立验收用.md"]   # 归档时新增的说明文件
SCRIPTS = [
    "01_resolve_coordinates.py", "02_evidence_strength.py", "03_build_gap_ledger.py",
    "04_gis_results_part1.py", "05_gis_results_part2.py", "06_taskC_demand.py",
    "07_taskD_scenario_api.py", "ref_坐标系双假设.py",
    "ref_官方人口对账_build.py", "ref_阶段1坐标决议.py",
]

ROWS = []


def add(kind, cat, fn, p, note=""):
    if not os.path.exists(p):
        ROWS.append({"类别": kind, "分组": cat, "文件名": fn, "存在": "**否**",
                     "字节": "", "SHA256": "", "创建时间": "", "修改时间": "",
                     "说明": "**文件不存在**"})
        return False
    st = os.stat(p)
    ROWS.append({"类别": kind, "分组": cat, "文件名": fn, "存在": "是",
                 "字节": os.path.getsize(p), "SHA256": sha(p),
                 "创建时间": ts(st.st_ctime), "修改时间": ts(st.st_mtime),
                 "说明": note})
    return True


print("=" * 110)
print("### A. 阶段二 9 份交付成果")
ok = 0
for fn in DELIV9:
    if add("阶段二成果", "9份交付成果", fn, os.path.join(P2, fn)):
        ok += 1
print("  存在 %d/9" % ok)
for fn in EXTRA:
    add("阶段二成果", "归档说明(后加)", fn, os.path.join(P2, fn))

print()
print("### B. 阶段二 10 个复现脚本")
oks = 0
for fn in SCRIPTS:
    if add("阶段二脚本", "10个脚本", fn, os.path.join(P2, "reproduce_scripts", fn)):
        oks += 1
print("  存在 %d/10" % oks)

print()
print("### C. 阶段二其他文件（中间件/辅助）")
for fn in sorted(os.listdir(P2)):
    p = os.path.join(P2, fn)
    if os.path.isfile(p) and fn not in DELIV9 and fn not in EXTRA:
        add("阶段二其他", "中间件", fn, p,
            "中间结果/自检产物，非交付成果" if fn.startswith("_") else "")

print()
print("### D. 2026-10-30 增量复核目录")
if os.path.isdir(P1):
    for fn in sorted(os.listdir(P1)):
        p = os.path.join(P1, fn)
        if os.path.isfile(p):
            add("阶段1增量复核", "10-30目录", fn, p)
else:
    print("  **目录不存在**")

# ---------- 输出清单 ----------
p_csv = os.path.join(OUT, "P0-1_原件清单.csv")
with open(p_csv, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["类别", "分组", "文件名", "存在", "字节",
                                      "SHA256", "创建时间", "修改时间", "说明"])
    w.writeheader()
    w.writerows(ROWS)
print()
print("=" * 110)
print("### 输出：%s（%d 行，%d B）" % (p_csv, len(ROWS), os.path.getsize(p_csv)))

# ---------- 日期性质判定 ----------
print()
print("=" * 110)
print("### 日期性质判定（P0-1 第4项）")
print()
print("  证据链：")
print("    1) 本机系统时钟        : 2026-10-17 15:33 (+0800)")
print("    2) GitHub 服务器记录    : 仓库 created_at = 2026-10-17T02:57:46Z")
print("                             (= 2026-10-17 10:57 +08，独立于本机时钟)")
print("    3) GitHub commit 时间   : 本次分支 commit 2026-10-17T03:58:45Z")
print("                             vs 本地 commit 2026-10-17T11:58:45+08  → 完全吻合")
print("    4) 文件系统时间戳       : 阶段一目录 10:56–11:11、阶段二 11:37–11:58（均 2026-10-17）")
print("    5) 外部下载时间         : webDownload 多为 2026-10-16 / 2026-10-17")
print("    6) geocode API 调用时间  : called_at 全部为 2026-10-10（340 条）")
print("    7) 封版包创建时间       : 2026-10-16 23:26（文件名标 20261020）")
print()
print("  判定：**误标（文件名/标题使用了计划批次日期，非实际完成日期）**")
print()
print("  依据：")
print("    - GitHub 服务器时钟与本机时钟一致 → 排除「本机时钟错误/项目时钟不同」")
print("    - 阶段二文件物理存在于 2026-10-17 11:37–11:58，可读、可哈希")
print("      → 排除「材料确属未来版本」（未来文件不可能在当下被创建并能计算 SHA-256）")
print("    - 目录名 20261030 的目录实际创建于 2026-10-17 11:10:12，其内文件名为 …_20261030.md")
print("      → 名称为计划标签，实际写入时间早于标签日期 13 天")
print("    - 封版包名 _20261020 创建于 2026-10-16 23:26 → 同类现象：标签超前于实际")
print()
print("  **结论：报告日期属「误标」，不是时钟差异，也不是未来版本材料。**")
print()
print("  **重要披露（不得隐瞒）**：上一轮（2026-10-17 早前）我曾把阶段二报告日期")
print("  从 2026-11-01 单方面改为 2026-10-17。该改动基于系统时钟与 GitHub 时钟一致的证据，")
print("  但按本轮要求「不得擅自改日期来消除矛盾」，此改动应在归档中显式披露并保留原始标签。")
print("  本轮处理：不改动历史，另附「日期口径对照表」并列原始标签与实际完成日期。")

json.dump({"deliv9_exist": ok, "scripts_exist": oks,
           "verdict": "mislabel",
           "evidence": {
               "system_clock": "2026-10-17 15:33 +0800",
               "github_created_at": "2026-10-17T02:57:46Z",
               "github_commit": "2026-10-17T03:58:45Z",
               "local_commit": "2026-10-17T11:58:45+08:00",
               "p2_dir_created": ts(os.stat(P2).st_ctime) if os.path.isdir(P2) else None,
               "p1_dir_created": ts(os.stat(P1).st_ctime) if os.path.isdir(P1) else None,
               "geocode_called_at": "2026-10-10",
               "sealed_pkg_created": "2026-10-16 23:26",
           },
           "disclosure": "上一轮曾将阶段二日期由 2026-11-01 改为 2026-10-17，本轮显式披露"},
          open(os.path.join(OUT, "_p01_verdict.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print()
print("  已保存 _p01_verdict.json")
