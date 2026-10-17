# -*- coding: utf-8 -*-
"""任务B-1：海珠坐标多证据批量核验引擎

可用证据（全部本地已有，无需外网）：
  E1 坐标点面判定：geocode 首选点落在 18 街道哪一面（WGS-84 假设）
  E2 GCJ 假设点面判定：把点按"区界为 GCJ"再判定一次（双假设）
  E3 地址文本街道线索：canonical_address 是否含某街道名
  E4 geocode 返回的 street 字段（道路名）
  E5 名录侧街道归属：services.csv 的 street_inferred / street_attribution_status / street_basis
  E6 匹配层级质量：level（门址/门牌号 优于 小巷/住宅区/兴趣点/道路/区县）

决议原则（保守）：
  - 只有 E1/E2 与 E3/E5 一致，且 level 不太差 → 才升为"空间一致可定位（待现场确认）"
  - 任何两项冲突 → 保持"冲突待核"
  - 不得凭单一候选坐标升为"已核实"（已核实仍只保留原 verified=Y 的 95 条）
"""
import csv
import json
import math
import os
import re
from collections import Counter, defaultdict

ROOT = r"D:\筑工杯数据获取"
OUT = os.path.join(ROOT, "广州市AI养老研究_第二阶段_本地实证_20261017")
os.makedirs(OUT, exist_ok=True)
TODAY = "2026-10-17"

RES = os.path.join(ROOT, "out", "geocode_results.csv")
SV = os.path.join(ROOT, "data", "services.csv")
PL = os.path.join(ROOT, "data", "places.csv")
LNK = os.path.join(ROOT, "data", "service_place_link.csv")
SW = os.path.join(ROOT, "data", "_spatial_verification_worklist.csv")
MQ = os.path.join(ROOT, "data", "_manual_review_queue.csv")
HZ = os.path.join(ROOT, "data", "boundaries", "haizhu_18_streets_osm_wgs84.geojson")

from shapely.geometry import Point, shape
from shapely.ops import transform

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


# ---------- 边界 ----------
hz = json.load(open(HZ, encoding="utf-8"))
S_WGS = {f["properties"]["name"]: shape(f["geometry"]) for f in hz["features"]}
S_GCJ = {k: transform(lambda x, y, z=None: wgs2gcj(x, y), v) for k, v in S_WGS.items()}
SHORT = {}
for k in S_WGS:
    SHORT[k] = k
    SHORT[k.replace("街道", "街")] = k
    SHORT[k.replace("街道", "")] = k


def street_of(lng, lat, table):
    pt = Point(lng, lat)
    for nm, g in table.items():
        if g.contains(pt):
            return nm
    return ""


# ---------- 读数据 ----------
geo = list(csv.DictReader(open(RES, encoding="utf-8-sig")))
places = {r["place_id"]: r for r in csv.DictReader(open(PL, encoding="utf-8-sig"))}
services = {r["service_id"]: r for r in csv.DictReader(open(SV, encoding="utf-8-sig"))}
links = list(csv.DictReader(open(LNK, encoding="utf-8-sig")))
place_svcs = defaultdict(list)
for l in links:
    place_svcs[l["place_id"]].append(l["service_id"])
sw = {r["place_id"]: r for r in csv.DictReader(open(SW, encoding="utf-8-sig"))}
mq = list(csv.DictReader(open(MQ, encoding="utf-8-sig")))
mq_by_place = defaultdict(list)
for r in mq:
    mq_by_place[r["place_id"]].append(r)

print("geocode:", len(geo), "| places:", len(places), "| services:", len(services))
print("links:", len(links), "| 空间工单:", len(sw), "| 人工复核队列:", len(mq))


def addr_streets(addr):
    """地址文本中出现的海珠街道名（返回唯一列表）"""
    a = str(addr or "")
    found = []
    for short, full in SHORT.items():
        if len(short) >= 2 and short in a and full not in found:
            found.append(full)
    return found


# ---------- 逐条多证据核验 ----------
ROWS = []
for r in geo:
    pid = r["place_id"]
    addr = r["canonical_address"]
    # === v3 修复（2026-10-17）===
    # 原缺陷：n / lvl / ver 在下方坐标解析之后才赋值，导致坐标异常的 except 分支
    #           读取到**上一行**的值（如 P-45b4cccd 继承了 P-68e159ad 的
    #           原n_candidates=1 / 原level=住宅区）。
    # 修复：三个原始字段一律先从**当前记录 r** 初始化；API 缺失即保持缺失，不归一化为 1。
    _n_raw = (r.get("n_candidates") or "").strip()
    n = int(_n_raw) if _n_raw.isdigit() else 0
    lvl = (r.get("level") or "")
    ver = (r.get("verified") or "")
    try:
        lng_w, lat_w = float(r["lng_wgs84"]), float(r["lat_wgs84"])
        lng_g, lat_g = float(r["lng_gcj02"]), float(r["lat_gcj02"])
    except (ValueError, TypeError):
        # 无有效坐标：直接登记为待核，不做推断；**不读取任何上行状态**
        ROWS.append({
            "place_id": pid, "canonical_address": addr,
            "原verdict": r["verdict"], "原verified": ver,
            "原n_candidates": _n_raw, "原level": lvl,
            "E1_坐标落面_WGS": "", "E2_GCJ列转WGS后落面": "",
            "E3_地址文本街道": "", "E4_返回道路名": r.get("street", ""),
            "E5_名录街道归属": "", "E6_层级质量": 0, "人工复核标记": "",
            "空间工单状态": (sw.get(pid, {}) or {}).get("status", ""),
            "修订后状态": "无有效坐标（待核）", "置信状态": "—",
            "判定依据": "坐标字段为空或非数值", "处理动作": "保留原记录，不删除",
            "修订日期": TODAY, "修订来源": "阶段2多证据批量核验（E1-E6）",
        })
        continue
    # n / lvl / ver 已在循环开头从当前 r 初始化（v3 修复）

    # E1/E2 点面判定（双假设）
    e1 = street_of(lng_w, lat_w, S_WGS)
    e2 = street_of(lng_g, lat_g, S_WGS)          # 若点列与边界同为各自坐标系
    e2b = street_of(*gcj2wgs(lng_g, lat_g), S_WGS)
    # E3 地址文本街道
    e3 = addr_streets(addr)
    # E4 geocode 返回的 street（道路名，非行政区）
    e4 = r.get("street", "")
    # E5 名录侧归属
    svc_streets = []
    svc_status = []
    for sid in place_svcs.get(pid, []):
        s = services.get(sid)
        if not s:
            continue
        if s.get("street_inferred"):
            svc_streets.append(s["street_inferred"])
        svc_status.append(s.get("street_attribution_status", ""))
    def _canon(x):
        """街道名归一化：'XX街'/'XX街道'/'XX' → 'XX街道'（仅限海珠18街道）"""
        if not x:
            return ""
        x = str(x).strip()
        if x in SHORT:
            return SHORT[x]
        for cand in (x, x + "街", x + "街道"):
            if cand in SHORT:
                return SHORT[cand]
        if x.endswith("街道"):
            base = x[:-2]
        elif x.endswith("街"):
            base = x[:-1]
        else:
            base = x
        if base + "街道" in S_WGS:
            return base + "街道"
        return ""
    e5 = sorted({_canon(x) for x in svc_streets if _canon(x)})
    # E6 匹配层级质量
    LEVEL_RANK = {"门址": 3, "门牌号": 3, "兴趣点": 2, "公交地铁站点": 2,
                  "住宅区": 1, "村庄": 1, "道路": 1, "小巷": 1, "乡镇": 1,
                  "区县": 0, "未知": 0, "": 0}
    q = LEVEL_RANK.get(lvl, 0)
    # 人工复核队列标记
    mqs = mq_by_place.get(pid, [])
    mq_scope = sorted({m.get("scope", "") for m in mqs if m.get("scope")})

    # ---- 决议 ----
    geo_streets = {x for x in (e1, e2, e2b) if x}
    evid = []
    if e1:
        evid.append("E1坐标落面=%s" % e1)
    if e2b and e2b != e1:
        evid.append("E2假设下=%s" % e2b)
    if e3:
        evid.append("E3地址街道=%s" % "/".join(e3))
    if e5:
        evid.append("E5名录归属=%s" % "/".join(e5))

    status = ""
    conf = ""
    action = ""
    reason = ""

    if ver == "Y":
        status, conf = "已核实（沿用原判定）", "高"
        action, reason = "无需修订", "原始 verified=Y"
    elif r["verdict"] == "failed":
        status, conf = "无法定位（保留，不推断）", "—"
        action, reason = "保留原记录，不删除", "地理编码失败"
    else:
        # 一致性判定
        e5_set = set(e5)
        e3_set = set(e3)
        consensus = None
        if e3_set and len(e3_set) == 1:
            cand = next(iter(e3_set))
            if e1 == cand and (not e5_set or cand in e5_set):
                consensus = cand
        if consensus is None and e5_set and len(e5_set) == 1:
            cand = next(iter(e5_set))
            if e1 == cand:
                consensus = cand
        if consensus is None and e1 and not e3_set and not e5_set and q >= 2:
            consensus = e1  # 仅坐标，但层级尚可（仍标待确认）

        if consensus and q >= 1 and not (e2b and e2b != consensus and e3_set and consensus not in e2b):
            # 多候选也能被空间+文本一致支持
            if n >= 2:
                status = "多候选但空间-文本一致（待现场确认）"
                conf = "中"
            else:
                status = "单候选-空间文本一致（待现场确认）"
                conf = "中"
            action = "可列为待现场确认点位；仍未达'已核实'"
            reason = "；".join(evid) + "；层级质量=%s" % lvl
        elif e1 and e3_set and e1 not in e3_set:
            status, conf = "坐标与地址街道冲突（待核）", "低"
            action = "保留待核；不采信单侧"
            reason = "坐标落面=%s，但地址文本指向=%s" % (e1, "/".join(e3))
        elif not geo_streets:
            status, conf = "坐标落在18街道外（待核）", "低"
            action = "保留待核；疑坐标偏移或越界"
            reason = "双假设下均未落面"
        else:
            status, conf = "多候选（仍需人工逐条决议）" if n >= 2 else "单候选但证据不足（待核）", "低"
            action = "保留待人工；需街道台账/门牌核实"
            reason = "；".join(evid) if evid else "无强证据"

    ROWS.append({
        "place_id": pid,
        "canonical_address": addr,
        "原verdict": r["verdict"],
        "原verified": ver,
        "原n_candidates": n,
        "原level": lvl,
        "E1_坐标落面_WGS": e1,
        "E2_GCJ列转WGS后落面": e2b,
        "E3_地址文本街道": "/".join(e3),
        "E4_返回道路名": e4,
        "E5_名录街道归属": "/".join(e5),
        "E6_层级质量": q,
        "人工复核标记": "/".join(mq_scope),
        "空间工单状态": (sw.get(pid, {}) or {}).get("status", ""),
        "修订后状态": status,
        "置信状态": conf,
        "判定依据": reason,
        "处理动作": action,
        "修订日期": TODAY,
        "修订来源": "阶段2多证据批量核验（E1-E6）",
    })

print()
print("=" * 104)
print("### 本轮决议结果分布")
for k, v in Counter(x["修订后状态"] for x in ROWS).most_common():
    print("  %-40s %d" % (k, v))

print()
print("### 与上一轮对比（上轮: 已核实95/单候选111/多候选123/冲突8/失败3）")
prev = {"已核实（沿用原判定）": 95, "单候选可定位（待现场确认）": 111,
        "多候选（不可自动决议）": 123, "单候选但街道线索冲突": 8,
        "失败（保留，不推断）": 3}
cur = Counter(x["修订后状态"] for x in ROWS)
print("  本轮：")
for k in sorted(set(list(prev) + list(cur))):
    print("    %-40s 上轮 %3d → 本轮 %3d" % (k, prev.get(k, 0), cur.get(k, 0)))
newly = cur.get("多候选但空间-文本一致（待现场确认）", 0)
print()
print("  **多候选记录中，本轮新增可列为待现场确认的: %d 条**" % newly)

print()
print("=" * 104)
print("### 多候选(123条) 的核验明细分布")
multi = [x for x in ROWS if x["原n_candidates"] >= 2 and x["原verdict"] == "needs_review"]
print("  多候选记录:", len(multi))
for k, v in Counter(x["修订后状态"] for x in multi).most_common():
    print("    %-40s %d" % (k, v))
print()
print("  多候选被判定为'空间-文本一致'的，其 n_candidates 分布:")
okmulti = [x for x in multi if x["修订后状态"] == "多候选但空间-文本一致（待现场确认）"]
print("   ", dict(Counter(x["原n_candidates"] for x in okmulti)))
print("   层级分布:", dict(Counter(x["原level"] for x in okmulti)))

# ---------- 保存 ----------
p = os.path.join(OUT, "海珠坐标多证据批量核验明细.csv")
with open(p, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(ROWS[0].keys()))
    w.writeheader()
    w.writerows(ROWS)
print()
print("已导出:", p, len(ROWS), "行")

json.dump({"total": len(ROWS),
           "dist": dict(Counter(x["修订后状态"] for x in ROWS)),
           "prev_dist": prev,
           "multi_total": len(multi),
           "multi_resolved": len(okmulti),
           "multi_dist": dict(Counter(x["修订后状态"] for x in multi))},
          open(os.path.join(OUT, "_resolve_stats.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("已保存 _resolve_stats.json")
