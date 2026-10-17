# -*- coding: utf-8 -*-
"""任务1-G：米级分析的双假设稳健性检验
区界坐标系待验证 → 凡涉及"点是否落入面"的判断，须在 H_WGS 与 H_GCJ 两种假设下各算一次，
报告结果差异；若差异小，则结论稳健；若差异大，则标注"受坐标系不确定性影响"。
"""
import json
import math
import os
import csv
from collections import Counter

from shapely.geometry import Point, shape
from shapely.ops import transform

ROOT = r"D:\筑工杯数据获取"
B = os.path.join(ROOT, "筑工杯_旧数据_2026前期", "_baseline_current")
OUT = r"D:\筑工杯数据获取\广州市AI养老研究_GIS实证分析_第一轮_20261028"

_A = 6378245.0
_EE = 0.00669342162296594323


def _tlat(x, y):
    r = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    r += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    r += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    r += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return r


def _tlng(x, y):
    r = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    r += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    r += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    r += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return r


def wgs2gcj(lng, lat):
    if not (73.66 < lng < 135.05 and 3.86 < lat < 53.55):
        return lng, lat
    dl = _tlat(lng - 105.0, lat - 35.0)
    dg = _tlng(lng - 105.0, lat - 35.0)
    rl = lat / 180.0 * math.pi
    m = 1 - _EE * math.sin(rl) ** 2
    sm = math.sqrt(m)
    dl = (dl * 180.0) / ((_A * (1 - _EE)) / (m * sm) * math.pi)
    dg = (dg * 180.0) / (_A / sm * math.cos(rl) * math.pi)
    return lng + dg, lat + dl


def gcj2wgs(lng, lat):
    wl, wa = lng, lat
    for _ in range(10):
        gl, ga = wgs2gcj(wl, wa)
        wl += lng - gl
        wa += lat - ga
    return wl, wa


dv = json.load(open(os.path.join(B, "raw", "city_districts_datav.json"), encoding="utf-8"))
G_RAW = {f["properties"]["name"]: shape(f["geometry"]) for f in dv["features"]}
G_WGS = {k: transform(lambda x, y, z=None: gcj2wgs(x, y), v) for k, v in G_RAW.items()}


def district_wgs(lng, lat):
    pt = Point(lng, lat)
    for nm, g in G_WGS.items():
        if g.contains(pt):
            return nm
    return None


def district_gcj(lng, lat):
    pt = Point(lng, lat)
    for nm, g in G_RAW.items():
        if g.contains(pt):
            return nm
    return None


# ---------- 海珠街道边界（WGS-84，已核对）与设施点 ----------
hz = json.load(open(os.path.join(ROOT, "data", "boundaries",
                                 "haizhu_18_streets_osm_wgs84.geojson"), encoding="utf-8"))
STREETS = {f["properties"]["name"]: shape(f["geometry"]) for f in hz["features"]}


def street_of(lng, lat):
    pt = Point(lng, lat)
    for nm, g in STREETS.items():
        if g.contains(pt):
            return nm
    return None


geo = list(csv.DictReader(open(os.path.join(ROOT, "out", "geocode_results.csv"),
                               encoding="utf-8-sig")))
pts = []
for r in geo:
    if r.get("district") != "海珠区":
        continue
    try:
        pts.append({"place_id": r["place_id"], "verified": r.get("verified", ""),
                    "street_field": r.get("street_inferred", ""),
                    "lng": float(r["lng_wgs84"]), "lat": float(r["lat_wgs84"])})
    except Exception:
        pass
print("海珠设施点(WGS列):", len(pts))

# ---------- 双假设：点落在哪个区 ----------
print()
print("=" * 100)
print("### 1 设施点 → 区 归属（双假设对照）")
agree = disagree = 0
dis_rows = []
for p in pts:
    dw = district_wgs(p["lng"], p["lat"])
    dg = district_gcj(*wgs2gcj(p["lng"], p["lat"]))   # 若区界为GCJ，需把WGS转GCJ再判
    if dw == dg:
        agree += 1
    else:
        disagree += 1
        dis_rows.append((p["place_id"], dw, dg))
print("  两假设判定一致: %d/%d (%.2f%%)" % (agree, len(pts), 100 * agree / len(pts)))
print("  判定不一致: %d" % disagree)
for pid, a, b in dis_rows[:10]:
    print("     %s  H_WGS判=%-8s H_GCJ判=%-8s" % (pid, a, b))

# ---------- 街道归属稳健性 ----------
print()
print("=" * 100)
print("### 2 设施点 → 海珠街道 归属稳健性")
# 街道边界为WGS；H_WGS 下直接用点；H_GCJ 下需把点按"区界为GCJ"换算
sa = sd = 0
sdis = []
for p in pts:
    s_w = street_of(p["lng"], p["lat"])
    # 若区界/整体为GCJ，则点的WGS坐标需转GCJ后与WGS街道比对（保持相对一致）
    lg, la = wgs2gcj(p["lng"], p["lat"])
    s_g = street_of(lg, la)
    if s_w == s_g:
        sa += 1
    else:
        sd += 1
        sdis.append((p["place_id"], s_w, s_g))
print("  两假设街道判定一致: %d/%d (%.2f%%)" % (sa, len(pts), 100 * sa / len(pts)))
print("  不一致: %d" % sd)
for pid, a, b in sdis[:10]:
    print("     %s  H_WGS=%-8s H_GCJ=%-8s" % (pid, a, b))

# ---------- 区名对照：高德返回的 district 字段 vs 双假设 ----------
print()
print("=" * 100)
print("### 3 高德返回 district 字段 vs 几何判定（独立标签）")
# geocode_results 里有 district 字段（高德返回），可作标签
tags = []
for r in geo:
    try:
        tags.append({"pid": r["place_id"], "dist_field": r.get("district", ""),
                     "lng": float(r["lng_wgs84"]), "lat": float(r["lat_wgs84"])})
    except Exception:
        pass
ok_w = ok_g = 0
n = 0
for t in tags:
    if not t["dist_field"]:
        continue
    n += 1
    if district_wgs(t["lng"], t["lat"]) == t["dist_field"]:
        ok_w += 1
    if district_gcj(*wgs2gcj(t["lng"], t["lat"])) == t["dist_field"]:
        ok_g += 1
print("  有效标签:", n)
print("  H_WGS 一致率: %d/%d (%.2f%%)" % (ok_w, n, 100 * ok_w / n if n else 0))
print("  H_GCJ 一致率: %d/%d (%.2f%%)" % (ok_g, n, 100 * ok_g / n if n else 0))
print("  注：高德 district 字段与高德坐标同属商业体系，**不是独立标签**，仅作一致性参考。")

# ---------- 结论 ----------
print()
print("=" * 100)
print("### 4 稳健性结论")
ratio = min(agree, disagree) / len(pts) if pts else 0
print("  区归属两假设一致率: %.2f%%" % (100 * agree / len(pts)))
print("  街道归属两假设一致率: %.2f%%" % (100 * sa / len(pts)))
print()
if agree / len(pts) > 0.95 and sa / len(pts) > 0.95:
    print("  => 在'设施点归属'这一用途上，坐标系不确定性**影响很小**（一致率>95%），")
    print("     因此区级/街道级计数与密度结论**稳健**，可以在报告中按 H_WGS 主口径给出，")
    print("     并注明已做双假设交叉检验。")
else:
    print("  => 一致率不足95%，相关空间判定须并列报告两种假设结果。")
print()
print("  但必须同时声明：**距离类指标（直线距离、缓冲区半径）对坐标系敏感**，")
print("  在坐标系未独立验证前，不给出米级精确距离结论，只给出量级与相对排序。")

json.dump({"district_agree": agree, "district_disagree": disagree, "n": len(pts),
           "street_agree": sa, "street_disagree": sd,
           "tag_n": n, "tag_hit_wgs": ok_w, "tag_hit_gcj": ok_g},
          open(os.path.join(OUT, "_crs_dual_hypothesis.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print()
print("已保存 _crs_dual_hypothesis.json")
