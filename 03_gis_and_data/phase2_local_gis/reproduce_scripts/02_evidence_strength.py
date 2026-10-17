# -*- coding: utf-8 -*-
"""任务B-1b：核验"多候选但空间-文本一致"的实际证据强度
关键问题：91 条中，证据是否足以确定"点"？还是只能确定"街道"？
必须区分两个不同结论：
  R1 街道级可归属（用于街道级汇总）—— 只需坐标与文本同属一街道
  R2 坐标准确（用于点位分析）—— 需要门牌级或唯一候选
"""
import csv
import json
import os
from collections import Counter

OUT = r"D:\筑工杯数据获取\广州市AI养老研究_第二阶段_本地实证_20261017"
P = os.path.join(OUT, "海珠坐标多证据批量核验明细.csv")
rows = list(csv.DictReader(open(P, encoding="utf-8-sig")))

ok = [r for r in rows if r["修订后状态"] == "多候选但空间-文本一致（待现场确认）"]
print("=" * 104)
print("### '多候选但空间-文本一致' 的 %d 条：证据强度分析" % len(ok))
print()
print("-- 按 level 分层（level 越高说明 geocode 定位越细）")
for k, v in Counter(r["原level"] for r in ok).most_common():
    print("   %-14s %d" % (k, v))
print()
print("-- 按 n_candidates 分层")
for k, v in sorted(Counter(int(r["原n_candidates"]) for r in ok).items()):
    print("   n=%-2d  %d" % (k, v))
print()
print("-- 证据组合分布")
combos = Counter()
for r in ok:
    tags = []
    if r["E1_坐标落面_WGS"]:
        tags.append("E1")
    if r["E2_GCJ列转WGS后落面"] and r["E2_GCJ列转WGS后落面"] == r["E1_坐标落面_WGS"]:
        tags.append("E2同")
    if r["E3_地址文本街道"]:
        tags.append("E3")
    if r["E5_名录街道归属"]:
        tags.append("E5")
    combos["+".join(tags)] += 1
for k, v in combos.most_common():
    print("   %-24s %d" % (k, v))

print()
print("-- 关键判断：E3（地址含街道名）是否存在的两条子集")
with_e3 = [r for r in ok if r["E3_地址文本街道"]]
without_e3 = [r for r in ok if not r["E3_地址文本街道"]]
print("   含 E3（地址文本明写街道名）: %d 条 —— 街道归属可交叉验证" % len(with_e3))
print("   不含 E3（仅靠坐标+名录）    : %d 条 —— 街道归属仅靠 E1+E5" % len(without_e3))
print()
print("   不含 E3 的记录，其 level 分布:")
for k, v in Counter(r["原level"] for r in without_e3).most_common():
    print("      %-14s %d" % (k, v))
print()
print("   不含 E3 且 level 较弱（小巷/住宅区/道路/区县/未知/村庄）的记录 —— **坐标不能视为可用**:")
weak = [r for r in without_e3 if r["原level"] in
        ("小巷", "住宅区", "道路", "区县", "未知", "村庄", "")]
print("      %d 条" % len(weak))
for r in weak[:10]:
    print("        %s  level=%-8s  addr=%s" % (r["place_id"], r["原level"],
                                                r["canonical_address"][:46]))

print()
print("=" * 104)
print("### 结论：必须拆分两个不同结论层级")
r1 = [r for r in ok if r["E1_坐标落面_WGS"]]  # 街道可归属
r2 = [r for r in ok if r["原level"] in ("门址", "门牌号")]  # 定位到门牌级
print("  R1 街道级可归属（坐标与名录/文本同属一街道）: %d 条" % len(r1))
print("  R2 定位到门牌级（level=门址/门牌号）        : %d 条" % len(r2))
print()
print("  ✅ 可用于【街道级汇总】但【不可用于点位/米级分析】: %d 条" % len(r1))
print("  ⚠️ 其中 level 较弱（小巷/住宅区/道路等）      : %d 条 → 街道归属可用，但坐标精度不可信" %
      (len(r1) - len(r2)))

export = []
for r in rows:
    st = r["修订后状态"]
    if st == "已核实（沿用原判定）":
        lvl_R = "R2 坐标准确（原始verified=Y）"
        usable = "点位分析 + 街道汇总"
    elif st in ("多候选但空间-文本一致（待现场确认）", "单候选-空间文本一致（待现场确认）"):
        if r["原level"] in ("门址", "门牌号"):
            lvl_R = "R1 街道可归属 + R2 门牌级（未现场确认）"
            usable = "街道汇总（已用）；点位需现场确认"
        else:
            lvl_R = "R1 仅街道可归属（坐标精度不足）"
            usable = "仅街道汇总；**不可用于点位/距离分析**"
    elif st == "坐标与地址街道冲突（待核）":
        lvl_R = "冲突（不可用）"
        usable = "不可用，待人工"
    elif st in ("多候选（仍需人工逐条决议）", "单候选但证据不足（待核）"):
        lvl_R = "证据不足（不可用）"
        usable = "不可用，待人工"
    else:
        lvl_R = "无坐标/失败"
        usable = "不可用"
    export.append({**r, "结论层级": lvl_R, "可用范围": usable})

p2 = os.path.join(OUT, "海珠坐标结论分层_街道可用vs点位可用.csv")
with open(p2, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(export[0].keys()))
    w.writeheader()
    w.writerows(export)
print()
print("已导出分层结果:", p2, len(export), "行")
for k, v in Counter(e["结论层级"] for e in export).most_common():
    print("   %-42s %d" % (k, v))

json.dump({"resolved_total": len(ok), "with_e3": len(with_e3),
           "without_e3": len(without_e3), "weak_level_n": len(weak),
           "R1_street_usable": len(r1), "R2_point_level": len(r2),
           "layers": dict(Counter(e["结论层级"] for e in export))},
          open(os.path.join(OUT, "_evidence_strength.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
