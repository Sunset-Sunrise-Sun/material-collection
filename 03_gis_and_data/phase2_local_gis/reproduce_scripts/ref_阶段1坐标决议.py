# -*- coding: utf-8 -*-
"""任务5：海珠坐标人工决议 + 街镇名标准化 + 名录区划冲突/同址复核
人工修订一律记录：原值 / 修订值 / 依据 / 来源 / 日期 / 置信状态。
不删除任何记录；不擅自把"多候选"判为已确定。
"""
import csv
import json
import math
import os
import re
from collections import Counter, defaultdict

ROOT = r"D:\筑工杯数据获取"
B = os.path.join(ROOT, "筑工杯_旧数据_2026前期", "_baseline_current")
OUT = r"D:\筑工杯数据获取\广州市AI养老研究_官方取证与GIS衔接_20261029"
os.makedirs(OUT, exist_ok=True)
TODAY = "2026-10-29"

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


def gcj2wgs(lng, lat):
    wl, wa = lng, lat
    for _ in range(10):
        x, y = wl - 105.0, wa - 35.0
        r1 = (-100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
              + (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
              + (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
              + (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0)
        r2 = (300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
              + (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
              + (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
              + (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0)
        rl = wa / 180.0 * math.pi
        m = 1 - _EE * math.sin(rl) ** 2
        sm = math.sqrt(m)
        dl = (r1 * 180.0) / ((_A * (1 - _EE)) / (m * sm) * math.pi)
        dg = (r2 * 180.0) / (_A / sm * math.cos(rl) * math.pi)
        wl += lng - (wl + dg)
        wa += lat - (wa + dl)
    return wl, wa


# ---------------- 读入 ----------------
geo = list(csv.DictReader(open(os.path.join(ROOT, "out", "geocode_results.csv"),
                               encoding="utf-8-sig")))
hz = json.load(open(os.path.join(ROOT, "data", "boundaries",
                                 "haizhu_18_streets_osm_wgs84.geojson"), encoding="utf-8"))
from shapely.geometry import Point, shape
STREETS = {f["properties"]["name"]: shape(f["geometry"]) for f in hz["features"]}
STREET_SHORT = {k.replace("街道", "街"): k for k in STREETS}
print("geocode 记录:", len(geo), "| 海珠街道:", len(STREETS))

# ---------------- 1) 坐标人工决议 ----------------
print()
print("=" * 104)
print("### 1 海珠坐标人工决议（242条 needs_review）")
RES = []
for r in geo:
    verdict = r["verdict"]
    n = int(r["n_candidates"] or 0)
    lvl = r["level"]
    reason = r["verdict_reason"]
    # 原值（一律原样保留）
    orig = {"place_id": r["place_id"], "canonical_address": r["canonical_address"],
            "原verdict": verdict, "原verified": r.get("verified", ""),
            "原level": lvl, "原镇/街道字段": r.get("township", ""),
            "原street字段": r.get("street", ""), "原n_candidates": n,
            "原lng_gcj02": r.get("lng_gcj02", ""), "原lat_gcj02": r.get("lat_gcj02", ""),
            "原lng_wgs84": r.get("lng_wgs84", ""), "原lat_wgs84": r.get("lat_wgs84", "")}

    # 决议规则（保守，逐条记录依据）
    if verdict == "success" and r.get("verified") == "Y":
        new_status = "已核实（沿用原判定）"
        basis = "原始 verified=Y"
        conf = "高"
        action = "无需修订"
    elif verdict == "failed":
        new_status = "失败（保留，不推断）"
        basis = "地理编码返回失败"
        conf = "—"
        action = "保留原记录，不删除"
    elif n == 1:
        # 唯一候选：可判为"单候选可定位"，但仍须空间+文本双校验
        try:
            wl, wa = float(r["lng_wgs84"]), float(r["lat_wgs84"])
        except Exception:
            new_status = "保留待核"
            basis = "缺有效坐标"
            conf = "低"
            action = "保留"
            RES.append({**orig, "修订后状态": new_status, "修订值": "无",
                        "判定依据": basis, "置信状态": conf, "处理动作": action,
                        "修订日期": TODAY, "修订来源": "本轮规则化决议"})
            continue
        inside = next((nm for nm, g in STREETS.items() if g.contains(Point(wl, wa))), None)
        # 地址文本里的街道线索
        addr = r["canonical_address"]
        addr_street = None
        for short, full in STREET_SHORT.items():
            if short in addr:
                addr_street = full
                break
        if inside and (addr_street is None or addr_street == inside):
            new_status = "单候选可定位（待现场确认）"
            basis = "n_candidates=1 且坐标落在海珠街道内；地址无街道线索或与坐标一致"
            conf = "中"
            action = "建议纳入可用点（须标注未现场验证）"
        elif inside:
            new_status = "单候选但街道线索冲突"
            basis = "n_candidates=1，坐标落入%s，但地址文本指向%s" % (inside, addr_street)
            conf = "低"
            action = "保留待人工复核"
        else:
            new_status = "坐标落在街道外"
            basis = "n_candidates=1 但坐标不落在海珠18街道任一内"
            conf = "低"
            action = "保留待核（疑坐标偏移或越界）"
    else:
        new_status = "多候选（不可自动决议）"
        basis = "n_candidates=%d（≥2），无唯一性依据" % n
        conf = "低"
        action = "保留待人工逐条决议（需街道台账/门牌核实）"

    RES.append({**orig, "修订后状态": new_status, "修订值": new_status,
                "判定依据": basis, "置信状态": conf, "处理动作": action,
                "修订日期": TODAY, "修订来源": "本轮规则化决议（保守规则，不推断）"})

print("决议后状态分布:")
for k, v in Counter(r["修订后状态"] for r in RES).most_common():
    print("  %-30s %d" % (k, v))
print()
print("按原判定 × 新状态:")
for k, v in Counter((r["原verdict"], r["修订后状态"]) for r in RES).most_common():
    print("  %-14s -> %-30s %d" % (k[0], k[1], v))

# ---------------- 2) 街镇名标准化 ----------------
print()
print("=" * 104)
print("### 2 街镇名标准化")
CANON = {}
for nm in STREETS:
    CANON[nm] = nm
    CANON[nm.replace("街道", "街")] = nm
    CANON[nm.replace("街道", "")] = nm
    CANON[nm.replace("街道", "") + "街道"] = nm

def norm_street(s):
    if s is None:
        return ""
    t = str(s).strip()
    t = t.replace("办事处", "").replace(" ", "").replace("　", "")
    if t in CANON:
        return CANON[t]
    # 尝试补"街"/"街道"
    for cand in (t, t + "街", t + "街道", t.replace("街", "街道")):
        if cand in CANON:
            return CANON[cand]
    return ""

# 统计各名录街镇名
me = list(csv.DictReader(open(os.path.join(B, "data", "elder_meals_20250205.csv"),
                              encoding="utf-8-sig")))
mp = list(csv.DictReader(open(os.path.join(B, "data", "medical_primary_202311.csv"),
                              encoding="utf-8-sig")))
for tag, recs, key, dist in (("长者饭堂", me, "township_raw", "district"),
                             ("基层医疗", mp, "township_raw", "district")):
    uniq = sorted({r[key] for r in recs if r.get(key)})
    print()
    print("-- %s: township_raw 唯一值 %d 个" % (tag, len(uniq)))
    if tag == "长者饭堂":
        hz_uniq = sorted({r[key] for r in recs if r.get("district") == "海珠区"})
        print("   其中海珠区 township_raw: %d 个" % len(hz_uniq))
        ok = sum(1 for x in hz_uniq if norm_street(x))
        print("   可映射到海珠18街道标准名: %d/%d" % (ok, len(hz_uniq)))
        for x in hz_uniq:
            print("      %-12s -> %s" % (x, norm_street(x) or "**未映射**"))
    else:
        hz_uniq = sorted({r[key] for r in recs if r.get("district") == "海珠区"})
        print("   其中海珠区 township_raw: %d 个" % len(hz_uniq))
        ok = sum(1 for x in hz_uniq if norm_street(x))
        print("   可映射: %d/%d" % (ok, len(hz_uniq)))

# 全量映射表（全部11区，仅记录映射关系，供后续扩展）
MAP_ROWS = []
for tag, recs, key, dist in (("长者饭堂", me, "township_raw", "district"),
                             ("基层医疗", mp, "township_raw", "district")):
    seen = set()
    for r in recs:
        raw = (r.get(key) or "").strip()
        d = r.get(dist, "")
        if not raw or (d, raw) in seen:
            continue
        seen.add((d, raw))
        std = norm_street(raw)
        MAP_ROWS.append({
            "名录": tag, "行政区": d, "原始街镇名": raw,
            "标准化街镇名": std if std else "",
            "映射状态": ("已映射（海珠18街道）" if std else
                       "未映射（非海珠区或名称无法对应）"),
            "映射依据": ("海珠18街道边界name字段（OSM，已与人口表18/18核对）" if std else "—"),
            "修订日期": TODAY,
        })
print()
print("全量映射表行数:", len(MAP_ROWS))
print("已映射:", sum(1 for x in MAP_ROWS if x["标准化街镇名"]))

# ---------------- 3) 区划冲突与同址复核 ----------------
print()
print("=" * 104)
print("### 3 名录区划冲突与同址记录复核")
EC = json.load(open(os.path.join(B, "data", "eldercare_20260923.json"), encoding="utf-8"))
ALIAS = {"荔湾": "荔湾区", "越秀": "越秀区", "海珠": "海珠区", "天河": "天河区",
         "白云": "白云区", "黄埔": "黄埔区", "番禺": "番禺区", "花都": "花都区",
         "南沙": "南沙区", "从化": "从化区", "增城": "增城区", "萝岗": "黄埔区"}
def infer_dist(a):
    f = sorted({v for k, v in ALIAS.items() if v in str(a)})
    return f[0] if len(f) == 1 else ("多区" if len(f) > 1 else "未识别")

QA = []
for r in EC:
    rep, inf = r.get("district_as_reported", ""), infer_dist(r.get("address_raw", ""))
    if rep and inf not in ("未识别", "多区") and rep != inf:
        QA.append({"类型": "区划归属冲突", "名录": "养老机构", "记录ID": "YLJG-%03d" % r["source_id"],
                   "名称": r["name"], "原始值": "上报区=%s；地址推定区=%s" % (rep, inf),
                   "修订值": "**不修订**（无权威依据，登记待核）",
                   "判定依据": "地址文本含其他区名，但机构上报区为登记区；二者口径可能不同（执业地 vs 登记地）",
                   "置信状态": "待核", "处理动作": "保留原值并登记；建议向区民政局核实",
                   "修订日期": TODAY, "修订来源": "本轮自动比对 + 人工规则"})
# 同址复核
def norm_addr(a):
    return "".join(str(a or "").replace("（", "(").replace("）", ")").split())
for tag, recs, namek, addrk in (("长者饭堂", me, "name", "address_raw"),
                                ("养老机构", EC, "name", "address_raw"),
                                ("基层医疗", mp, "name", "address_raw")):
    g = defaultdict(list)
    for r in recs:
        a = norm_addr(r.get(addrk))
        if a and len(a) >= 8:
            g[a].append(r)
    for a, lst in g.items():
        if len(lst) > 1:
            QA.append({"类型": "同址多记录", "名录": tag, "记录ID": "/".join(
                (("FANT-%04d" % int(x["source_id"])) if tag == "长者饭堂" else
                 ("YLJG-%03d" % x["source_id"]) if tag == "养老机构" else
                 ("JCYL-%03d" % int(x["source_id"]))) for x in lst),
                "名称": "；".join(x.get(namek, "")[:26] for x in lst),
                "原始值": "地址=%s（%d条记录同址）" % (a[:60], len(lst)),
                "修订值": "**不合并、不去重**（可能是不同服务主体共用场所）",
                "判定依据": "标准化地址完全一致；但服务主体名称不同，无法据地址判定为重复",
                "置信状态": "待核", "处理动作": "保留全部记录；建议现场核实是否同一场所多主体",
                "修订日期": TODAY, "修订来源": "本轮地址规范化比对"})
print("冲突/同址登记条数:", len(QA))
for q in QA:
    print("  [%s|%s] %s | %s" % (q["类型"], q["名录"], q["名称"][:36], q["原始值"][:70]))

# ---------------- 保存 ----------------
MJSON = {
    "生成日期": TODAY,
    "坐标决议": {
        "总记录": len(RES),
        "状态分布": dict(Counter(r["修订后状态"] for r in RES)),
        "原判定分布": dict(Counter(r["原verdict"] for r in RES)),
        "可纳入可用点候选（单候选可定位）": sum(
            1 for r in RES if r["修订后状态"] == "单候选可定位（待现场确认）"),
        "仍需人工逐条决议（多候选）": sum(
            1 for r in RES if r["修订后状态"] == "多候选（不可自动决议）"),
    },
    "街镇名映射": {"映射表行数": len(MAP_ROWS),
                   "已映射": sum(1 for x in MAP_ROWS if x["标准化街镇名"])},
    "冲突与同址": {"条数": len(QA),
                   "按类型": dict(Counter(q["类型"] for q in QA))},
}
json.dump(MJSON, open(os.path.join(OUT, "_task5_manual_resolution.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# CSV 导出
def dump_csv(rows, name):
    if not rows:
        return
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("导出:", name, len(rows), "行")

dump_csv(RES, "海珠坐标人工决议记录.csv")
dump_csv(MAP_ROWS, "街镇名标准化映射表.csv")
dump_csv(QA, "名录区划冲突与同址复核记录.csv")
print()
print(json.dumps(MJSON, ensure_ascii=False, indent=1))
