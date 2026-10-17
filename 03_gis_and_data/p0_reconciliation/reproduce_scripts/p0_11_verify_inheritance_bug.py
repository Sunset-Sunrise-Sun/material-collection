# -*- coding: utf-8 -*-
"""必修1 核验：确认 except 分支继承上一行元数据，并核实 P-45b4cccd 的原始字段"""
import csv
import os

ROOT = r"D:\筑工杯数据获取"
GO = os.path.join(ROOT, "out", "geocode_results.csv")
DET = os.path.join(ROOT, "广州市AI养老研究_第二阶段_本地实证_20261017",
                   "海珠坐标多证据批量核验明细.csv")

go = list(csv.DictReader(open(GO, encoding="utf-8-sig")))
det = list(csv.DictReader(open(DET, encoding="utf-8-sig")))
print("geocode 行数:", len(go), "| 明细行数:", len(det))

print()
print("=" * 104)
print("### 1 定位 P-45b4cccd 在 geocode_results.csv 中的位置与相邻行")
idx = next(i for i, r in enumerate(go) if r["place_id"] == "P-45b4cccd")
print("  索引:", idx, "（0-based）")
for k in (idx - 1, idx, idx + 1):
    if 0 <= k < len(go):
        r = go[k]
        print("  [%3d] %-14s verdict=%-12s verified=%-4r n=%-4r level=%-8r lng=%-12r" % (
            k, r["place_id"], r["verdict"], r.get("verified"),
            r.get("n_candidates"), r.get("level"), r.get("lng_wgs84")))
        print("        district=%r adcode=%r status=%r infocode=%r" % (
            r.get("district"), r.get("adcode"), r.get("status"), r.get("infocode")))
        print("        addr=%s" % r["canonical_address"][:60])

print()
print("=" * 104)
print("### 2 明细 CSV 中 P-45b4cccd 与上一行的值（检验是否继承）")
di = next(i for i, r in enumerate(det) if r["place_id"] == "P-45b4cccd")
for k in (di - 1, di):
    if 0 <= k < len(det):
        r = det[k]
        print("  [%3d] %-14s 原verdict=%-12r 原verified=%-4r 原n_candidates=%-4r 原level=%-8r 状态=%r" % (
            k, r["place_id"], r["原verdict"], r["原verified"],
            r["原n_candidates"], r["原level"], r["修订后状态"]))

print()
print("=" * 104)
print("### 3 判定：是否继承")
d_prev = det[di - 1] if di > 0 else None
d_cur = det[di]
if d_prev:
    same = all(d_prev[f] == d_cur[f] for f in ("原verified", "原n_candidates", "原level"))
    print("  上一行:", d_prev["place_id"], "| 当前行:", d_cur["place_id"])
    print("  原verified   : prev=%r cur=%r 相同=%s" % (
        d_prev["原verified"], d_cur["原verified"],
        d_prev["原verified"] == d_cur["原verified"]))
    print("  原n_candidates: prev=%r cur=%r 相同=%s" % (
        d_prev["原n_candidates"], d_cur["原n_candidates"],
        d_prev["原n_candidates"] == d_cur["原n_candidates"]))
    print("  原level      : prev=%r cur=%r 相同=%s" % (
        d_prev["原level"], d_cur["原level"],
        d_prev["原level"] == d_cur["原level"]))
    print()
    print("  **三者全部相同 → 确认继承缺陷成立:", same, "**")
    print("  复核方指出上一行为 P-68e159ad:", d_prev["place_id"] == "P-68e159ad")

print()
print("=" * 104)
print("### 4 P-45b4cccd 的**正确**原始值（来自 geocode_results.csv）")
r = go[idx]
print("  原verdict      :", repr(r["verdict"]))
print("  原verified     :", repr(r.get("verified")))
print("  原n_candidates :", repr(r.get("n_candidates")), "← 缺失（空）")
print("  原level        :", repr(r.get("level")), "← 缺失（空）")
print("  longitude      :", repr(r.get("lng_wgs84")), "← 空")
print("  latitude       :", repr(r.get("lat_wgs84")), "← 空")
print("  status/infocode:", repr(r.get("status")), "/", repr(r.get("infocode")))

print()
print("=" * 104)
print("### 5 影响评估：修复后是否有任何计数变化")
# 受影响记录数：明细中坐标为空的行
empty = [r for r in go if not (r.get("lng_wgs84") or "").strip()
         or not (r.get("lat_wgs84") or "").strip()]
print("  geocode 中坐标为空的行数:", len(empty))
for r in empty:
    print("    -", r["place_id"], "| n=%r level=%r verified=%r" % (
        r.get("n_candidates"), r.get("level"), r.get("verified")))

print()
print("  修复后 P-45b4cccd 字段将变为: 原verified='' 原n_candidates='' 原level=''")
print("  其 is_door 仍为 False（'住宅区' 与 '' 均不在门址/门牌号内）")
print("  其 n>1 仍为 False（1 与 0 均不大于 1）")
print("  → **分类与计数预期不变，但须重跑证明**")
