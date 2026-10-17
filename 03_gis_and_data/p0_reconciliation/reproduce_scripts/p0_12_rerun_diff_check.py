# -*- coding: utf-8 -*-
"""重跑受影响的明细与分层，逐行对比新旧差异"""
import csv
import hashlib
import json
import os

ROOT = r"D:\筑工杯数据获取"
P2 = os.path.join(ROOT, "广州市AI养老研究_第二阶段_本地实证_20261017")
OUT = os.path.join(ROOT, "广州市AI养老研究_P0核对_20261017")
BK = os.path.join(OUT, "_pre_v3_backup")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


print("=" * 104)
print("### 重跑后文件对比")
pairs = [
    ("海珠坐标多证据批量核验明细.csv", "逐行明细"),
    ("海珠坐标结论分层_街道可用vs点位可用.csv", "结论分层"),
    ("_resolve_stats.json", "resolve统计"),
    ("_evidence_strength.json", "强度统计"),
]
for fn, lab in pairs:
    old = os.path.join(BK, fn)
    new = os.path.join(P2, fn)
    if not (os.path.exists(old) and os.path.exists(new)):
        print("  [缺失] %s" % fn)
        continue
    ho, hn = sha(old), sha(new)
    print()
    print("  --- %s ---" % lab)
    print("    旧: %9d B  %s" % (os.path.getsize(old), ho))
    print("    新: %9d B  %s" % (os.path.getsize(new), hn))
    print("    字节是否相同:", ho == hn)

print()
print("=" * 104)
print("### 逐行差异（明细 CSV）")
oldr = list(csv.DictReader(open(os.path.join(BK, "海珠坐标多证据批量核验明细.csv"),
                                encoding="utf-8-sig")))
newr = list(csv.DictReader(open(os.path.join(P2, "海珠坐标多证据批量核验明细.csv"),
                                encoding="utf-8-sig")))
print("  行数 旧/新:", len(oldr), "/", len(newr))
print("  place_id 顺序一致:", [r["place_id"] for r in oldr] == [r["place_id"] for r in newr])
diffs = []
for a, b in zip(oldr, newr):
    for k in a.keys():
        if a[k] != b.get(k):
            diffs.append({"place_id": a["place_id"], "field": k,
                          "old": a[k], "new": b.get(k)})
print("  字段级差异条目:", len(diffs))
for d in diffs:
    print("    %-14s %-18s %r → %r" % (d["place_id"], d["field"], d["old"], d["new"]))

print()
print("=" * 104)
print("### 逐行差异（分层 CSV）")
oldo = list(csv.DictReader(open(os.path.join(BK, "海珠坐标结论分层_街道可用vs点位可用.csv"),
                                encoding="utf-8-sig")))
newo = list(csv.DictReader(open(os.path.join(P2, "海珠坐标结论分层_街道可用vs点位可用.csv"),
                                encoding="utf-8-sig")))
ldiff = []
for a, b in zip(oldo, newo):
    for k in a.keys():
        if a[k] != b.get(k):
            ldiff.append((a["place_id"], k, a[k], b.get(k)))
print("  字段级差异条目:", len(ldiff))
for x in ldiff[:20]:
    print("    %-14s %-18s %r → %r" % x)
print("  **结论层级是否有任何变化**:",
      "无" if not any(x[1] == "结论层级" for x in ldiff) else "**有**")

# 关键计数复核
from collections import Counter
n_gt1 = [r for r in newr if str(r["原n_candidates"]).strip().isdigit()
         and int(r["原n_candidates"]) > 1]
print()
print("=" * 104)
print("### 关键计数（修复后，基于明细 CSV）")
print("  原始 n_candidates>1:", len(n_gt1))
print("  状态分布:", dict(Counter(r["修订后状态"] for r in newr)))
print("  P-45b4cccd 修复后:", [dict(r) for r in newr if r["place_id"] == "P-45b4cccd"])

json.dump({"diffs": diffs, "layer_diffs": [{"place_id": x[0], "field": x[1],
                                            "old": x[2], "new": x[3]} for x in ldiff],
           "n_gt1": len(n_gt1)},
          open(os.path.join(OUT, "_v3_rerun_diff.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print()
print("已保存 _v3_rerun_diff.json")
