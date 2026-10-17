# -*- coding: utf-8 -*-
"""逐条验证 ChatGPT 独立复核提出的 5 项 P0-2 事实主张"""
import csv
import os
from collections import Counter

ROOT = r"D:\筑工杯数据获取"
P2 = os.path.join(ROOT, "广州市AI养老研究_第二阶段_本地实证_20261017")
DET = os.path.join(P2, "海珠坐标多证据批量核验明细.csv")
LAY = os.path.join(P2, "海珠坐标结论分层_街道可用vs点位可用.csv")

det = list(csv.DictReader(open(DET, encoding="utf-8-sig")))
lay = {r["place_id"]: r for r in csv.DictReader(open(LAY, encoding="utf-8-sig"))}
print("明细:", len(det), "| 分层:", len(lay))

print()
print("=" * 104)
print("### 主张2验证：n_candidates>1 到底是多少条？")
n_gt1 = [r for r in det if int(r["原n_candidates"] or 0) > 1]
print("  n_candidates > 1 总数:", len(n_gt1))
print("  按 verdict 分布:", dict(Counter(r["原verdict"] for r in n_gt1)))
print("  按 n 分布:", dict(Counter(int(r["原n_candidates"]) for r in n_gt1)))
print()
print("  其中 verdict != needs_review 的记录:")
odd = [r for r in n_gt1 if r["原verdict"] != "needs_review"]
for r in odd:
    print("    %-14s verdict=%-14s n=%-2s level=%-8s lng=%r lat=%r  addr=%s" % (
        r["place_id"], r["原verdict"], r["原n_candidates"], r["原level"],
        r.get("lng_wgs84", ""), r.get("lat_wgs84", ""), r["canonical_address"][:44]))
print("  复核方点名的两条是否在此:")
for pid in ("P-0bb41fec", "P-2f0f7abf"):
    hit = [r for r in det if r["place_id"] == pid]
    if hit:
        r = hit[0]
        print("    %-14s verdict=%-12s n=%-2s addr=%s" % (
            pid, r["原verdict"], r["原n_candidates"], r["canonical_address"][:50]))
    else:
        print("    %-14s **不在明细中**" % pid)

print()
print("=" * 104)
print("### 主张2验证续：needs_review 且 n>1 的分解")
nr = [r for r in det if r["原verdict"] == "needs_review" and int(r["原n_candidates"] or 0) > 1]
print("  needs_review 且 n>1:", len(nr))
print("  其状态分布:", dict(Counter(r["修订后状态"] for r in nr)))
print()
print("  125 = 123(needs_review) + 2(failed) ? →", len(n_gt1) == len(nr) + len(odd))
print("  123 = 91 + 17 + 15 ? →", len(nr) == 91 + 17 + 15)

print()
print("=" * 104)
print("### 主张3验证：两条 verified=Y 但 level=兴趣点 的记录")
ver = [r for r in det if r["原verified"] == "Y"]
print("  verified=Y 总数:", len(ver))
print("  其 level 分布:", dict(Counter(r["原level"] for r in ver)))
weak_ver = [r for r in ver if r["原level"] not in ("门址", "门牌号")]
print()
print("  非门址/门牌号的 verified 记录（应为 2 条）:", len(weak_ver))
for r in weak_ver:
    print("    %-14s level=%-8s 分层=%s" % (r["place_id"], r["原level"],
                                          lay[r["place_id"]]["结论层级"]))
    print("      addr=%s" % r["canonical_address"][:70])
print()
print("  复核方点名的两条:")
for pid in ("P-2db0b22d", "P-d227f901"):
    hit = [r for r in det if r["place_id"] == pid]
    if hit:
        r = hit[0]
        print("    %-14s verified=%s level=%-8s addr=%s" % (
            pid, r["原verified"], r["原level"], r["canonical_address"][:50]))
    else:
        print("    %-14s **不在明细中**" % pid)

print()
print("=" * 104)
print("### 主张4验证：门牌粒度 209 的构成")
door_ver = [r for r in ver if r["原level"] in ("门址", "门牌号")]
b116 = [r for r in det if lay[r["place_id"]]["结论层级"] ==
        "R1 街道可归属 + R2 门牌级（未现场确认）"]
all_door = [r for r in det if r["原level"] in ("门址", "门牌号")]
print("  全部 level∈{门址,门牌号} 记录:", len(all_door))
print("  其中 verified=Y:", len(door_ver))
print("  其中 116 类:", len([r for r in b116 if r["原level"] in ("门址", "门牌号")]))
print("  93 + 116 =", len(door_ver) + len(b116), "（应等于 209）")
print("  验证: all_door =", len(all_door))

print()
print("=" * 104)
print("### 主张1验证：REPRODUCE.md 中的 91/283 表述")
RP = os.path.join(P2, "REPRODUCE.md")
t = open(RP, encoding="utf-8").read()
import re
print("  REPRODUCE.md 中关于街道级的行:")
for L in t.split("\n"):
    if "街道" in L or "门牌" in L or "坐标总记录" in L or "verif" in L.lower():
        print("   ", L.strip()[:150])

print()
print("=" * 104)
print("=" * 104)
print("### 结论：复核方 5 项主张的验证结果")
ok2 = (len(n_gt1) == 125 and len(nr) == 123 and len(odd) == 2
       and set(r["place_id"] for r in odd) == {"P-0bb41fec", "P-2f0f7abf"})
print("  主张2 (125 = 123 + 2)：", "**成立**" if ok2 else "**不成立**")
ok3 = (len(weak_ver) == 2
       and set(r["place_id"] for r in weak_ver) == {"P-2db0b22d", "P-d227f901"})
print("  主张3 (2条兴趣点verified)：", "**成立**" if ok3 else "**不成立**")
ok4 = (len(door_ver) + len(b116) == 209 == len(all_door))
print("  主张4 (209 = 93 + 116)：", "**成立**" if ok4 else "**不成立**")
