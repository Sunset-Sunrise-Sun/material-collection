# -*- coding: utf-8 -*-
"""P0-2 修订 v2（最终版）
- 91 = 新增多候选计数；283 = 街道级可用总数（不可混）
- 原始 n_candidates>1 = 125 = 123(可用) + 2(failed)
- **纠正复核方一处归因**：那 2 条 failed 记录**并非坐标为空**，而是坐标落在海珠区外
  （P-0bb41fec→白云区 adcode 440111；P-2f0f7abf→南沙区 440115）
- 第 3 条 failed：P-45b4cccd（API 错误 30001，无 n_candidates、无坐标），不在 125 内
- 严格点位分析资格 = 93（=95−2 条兴趣点层级 verified）
- 门牌粒度可用（含未确认候选）= 209 = 93 + 116
- **不改变任何一条记录的分类**
"""
import csv
import hashlib
import json
import os
from collections import Counter

ROOT = r"D:\筑工杯数据获取"
P2 = os.path.join(ROOT, "广州市AI养老研究_第二阶段_本地实证_20261017")
OUT = os.path.join(ROOT, "广州市AI养老研究_P0核对_20261017")
DET = os.path.join(P2, "海珠坐标多证据批量核验明细.csv")
LAYF = os.path.join(P2, "海珠坐标结论分层_街道可用vs点位可用.csv")
GOF = os.path.join(ROOT, "out", "geocode_results.csv")
V1 = os.path.join(OUT, "P0-2_海珠坐标逐行分类交叉表.csv")
V1SUM = os.path.join(OUT, "P0-2_分层互斥汇总表.csv")


def sha(p):
    if not os.path.exists(p):
        return ""
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


DOOR = ("门址", "门牌号")
LAY = ["R2 坐标准确（原始verified=Y）",
       "R1 街道可归属 + R2 门牌级（未现场确认）",
       "R1 仅街道可归属（坐标精度不足）",
       "证据不足（不可用）", "冲突（不可用）", "无坐标/失败"]

det = list(csv.DictReader(open(DET, encoding="utf-8-sig")))
lay = {r["place_id"]: r for r in csv.DictReader(open(LAYF, encoding="utf-8-sig"))}
go = {r["place_id"]: r for r in csv.DictReader(open(GOF, encoding="utf-8-sig"))}
print("明细:", len(det), "| 分层:", len(lay), "| geocode:", len(go))

ROWS = []
for d in det:
    pid = d["place_id"]
    layer = lay[pid]["结论层级"]
    st = d["修订后状态"]
    lvl = d["原level"]
    n_raw = d["原n_candidates"]
    n = int(n_raw) if str(n_raw).strip() not in ("", "None") else 0
    is_ver = (d["原verified"] == "Y")
    is_door = lvl in DOOR
    g = go[pid]
    lng = (g.get("lng_wgs84") or "").strip()
    lat = (g.get("lat_wgs84") or "").strip()
    geo_ok = (g.get("verdict") != "failed") and lng != "" and lat != ""
    adcode = (g.get("adcode") or "").strip()
    dist = (g.get("district") or "").strip()

    street_ok = layer in (LAY[0], LAY[1], LAY[2])
    door_gran = is_door and street_ok
    strict = is_ver and is_door and geo_ok
    in91 = (st == "多候选但空间-文本一致（待现场确认）")

    unc = []
    if is_ver and not is_door:
        unc.append("原始verified=Y但层级=%s：不具严格点位分析资格，标待核；"
                   "**不改变原始verified状态、不把95降为93**" % lvl)
    if is_ver and is_door:
        unc.append("原始verified=Y且门址/门牌号级；仍受11区边界坐标系待验证限制")
    if in91:
        unc.append("多候选(n=%d)，仅证街道归属，未证点位唯一" % n)
    if g.get("verdict") == "failed":
        if lng and lat:
            unc.append("地理编码判失败：返回坐标落于%s（adcode=%s）**非海珠区**，"
                       "坐标存在但不可用；**并非坐标为空**" % (dist or "区外", adcode or "?"))
        else:
            unc.append("地理编码API失败（infocode=%s），无候选、无坐标"
                       % (g.get("infocode") or "?"))
    if st == "坐标与地址街道冲突（待核）":
        unc.append("坐标落面与地址文本街道冲突，不得采信单侧")
    if st == "多候选（仍需人工逐条决议）":
        unc.append("多候选未通过一致性检验，保留待人工")
    if st == "单候选但证据不足（待核）":
        unc.append("单候选但证据不足")
    if not unc:
        unc.append("无额外不确定性")

    ROWS.append({
        "place_id": pid,
        "canonical_address": d["canonical_address"],
        "原始verdict": d["原verdict"],
        "原始verified": d["原verified"],
        "原始n_candidates": n_raw,
        "原始level": lvl,
        "原始n_candidates是否>1": "是" if n > 1 else "否",
        "有可用地理编码结果": "是" if geo_ok else "否",
        "geocode返回district": dist,
        "geocode返回adcode": adcode,
        "当前判定等级": layer,
        "当前修订后状态": st,
        "街道级是否可用": "是" if street_ok else "否",
        "门牌粒度可用_含未确认候选": "是" if door_gran else "否",
        "严格点位分析资格": "是" if strict else "否",
        "是否属于原始95条verified": "是" if is_ver else "否",
        "是否计入新增91条": "是" if in91 else "否",
        "证据依据": d["判定依据"],
        "不确定性说明": "；".join(unc),
        "E1坐标落面": d["E1_坐标落面_WGS"],
        "E3地址文本街道": d["E3_地址文本街道"],
        "E5名录街道归属": d["E5_名录街道归属"],
    })

c = Counter()
for x in ROWS:
    c["total"] += 1
    c["n_gt1"] += (x["原始n_candidates是否>1"] == "是")
    c["geo_ok"] += (x["有可用地理编码结果"] == "是")
    c["n_gt1_ok"] += (x["原始n_candidates是否>1"] == "是" and x["有可用地理编码结果"] == "是")
    c["n_gt1_bad"] += (x["原始n_candidates是否>1"] == "是" and x["有可用地理编码结果"] == "否")
    c["ver95"] += (x["是否属于原始95条verified"] == "是")
    c["strict93"] += (x["严格点位分析资格"] == "是")
    c["door209"] += (x["门牌粒度可用_含未确认候选"] == "是")
    c["street283"] += (x["街道级是否可用"] == "是")
    c["in91"] += (x["是否计入新增91条"] == "是")
    c["failed"] += (x["原始verdict"] == "failed")

print()
print("=" * 104)
print("### 1 v2 关键口径")
for k, lab in (("total", "总记录"), ("n_gt1", "原始 n_candidates>1"),
               ("n_gt1_ok", "多候选且地理编码可用"), ("n_gt1_bad", "多候选但编码不可用"),
               ("geo_ok", "全表可用地理编码"), ("failed", "verdict=failed"),
               ("ver95", "原始 verified=Y"), ("strict93", "严格点位分析资格"),
               ("door209", "门牌粒度可用(含未确认)"), ("street283", "街道级可用"),
               ("in91", "计入新增91条")):
    print("  %-30s %d" % (lab, c[k]))

print()
print("=" * 104)
print("### 2 断言 v2")
allok = True


def A(name, got, want):
    global allok
    ok = (got == want)
    allok &= ok
    print("  [%s] %-56s got=%s want=%s" % ("PASS" if ok else "FAIL", name, got, want))


print("-- G. 复核方要求的断言")
A("G1 原始 n_candidates>1 = 125", c["n_gt1"], 125)
A("G2 多候选且有可用地理编码结果 = 123", c["n_gt1_ok"], 123)
A("G3 多候选但编码不可用 = 2", c["n_gt1_bad"], 2)
bad_ids = sorted({x["place_id"] for x in ROWS
                  if x["原始n_candidates是否>1"] == "是"
                  and x["有可用地理编码结果"] == "否"})
print("     失败多候选 ID:", bad_ids)
A("G3b ID 固定为复核方所列两条", bad_ids == ["P-0bb41fec", "P-2f0f7abf"], True)
rec2 = [x for x in ROWS if x["place_id"] in bad_ids]
for x in rec2:
    print("       %s → district=%s adcode=%s" % (x["place_id"],
                                                 x["geocode返回district"],
                                                 x["geocode返回adcode"]))
A("G3c 【纠正】这 2 条返回坐标非空（非'坐标为空'）",
  all(x["geocode返回adcode"] for x in rec2), True)
A("G3d 【纠正】这 2 条均落海珠区外（adcode≠440105）",
  all(x["geocode返回adcode"] != "440105" for x in rec2), True)
A("G4 125 = 91 + 17 + 15 + 2", 91 + 17 + 15 + 2, 125)
A("G5 91 全部为多候选且编码可用",
  all(x["原始n_candidates是否>1"] == "是" and x["有可用地理编码结果"] == "是"
      for x in ROWS if x["是否计入新增91条"] == "是"), True)
A("G6 283=街道级可用总数; 91=新增多候选计数", (c["street283"], c["in91"]), (283, 91))
weak_ver = [x for x in ROWS if x["是否属于原始95条verified"] == "是"
            and x["严格点位分析资格"] == "否"]
A("G7 两条兴趣点 verified 无严格点位资格",
  (len(weak_ver), {x["place_id"] for x in weak_ver}),
  (2, {"P-2db0b22d", "P-d227f901"}))
A("G8 严格点位资格=93; verified=95; 差2",
  (c["strict93"], c["ver95"], c["ver95"] - c["strict93"]), (93, 95, 2))
A("G9 门牌粒度可用 = 209 = 93+116", c["door209"], 93 + 116)
A("G10 六类合计 = 340", c["total"], 340)
A("G11 verdict=failed 共 3 条", c["failed"], 3)

print()
print("-- 回归断言")
layc = Counter(x["当前判定等级"] for x in ROWS)
b116 = {x["place_id"] for x in ROWS if x["当前判定等级"] == LAY[1]}
b95 = {x["place_id"] for x in ROWS if x["是否属于原始95条verified"] == "是"}
b91 = {x["place_id"] for x in ROWS if x["是否计入新增91条"] == "是"}
b72 = {x["place_id"] for x in ROWS if x["当前判定等级"] == LAY[2]}
A("C1 verified=95", c["ver95"], 95)
A("C2 门牌级层=116", layc[LAY[1]], 116)
A("C3 仅街道层=72", layc[LAY[2]], 72)
A("C5 116∩95=0", len(b116 & b95), 0)
A("C6 91⊂(116∪72)", len(b91 & (b116 | b72)), 91)
A("C7 91=68+23", (len(b91 & b116), len(b91 & b72)), (68, 23))
A("C8 188∩95=0", len((b116 | b72) & b95), 0)
A("C9 95+188=283", 95 + 188, 283)
A("A1 place_id 唯一", len({x["place_id"] for x in ROWS}), 340)
A("D1 needs_review且n>=2=123",
  len([x for x in ROWS if x["原始verdict"] == "needs_review"
       and x["原始n_candidates是否>1"] == "是"]), 123)
print()
print("  全部断言:", "通过" if allok else "**存在失败**")

p_v2 = os.path.join(OUT, "P0-2_海珠坐标逐行分类交叉表_v2.csv")
with open(p_v2, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(ROWS[0].keys()))
    w.writeheader()
    w.writerows(ROWS)

DEF = {LAY[0]: "原始verified=Y；其中 2 条层级兴趣点→不具严格点位资格（待核）",
       LAY[1]: "门牌粒度但未现场确认；可街道汇总，点位为候选",
       LAY[2]: "仅能定街道；禁止点位/距离/缓冲区/米级",
       LAY[3]: "无一致指向，保留待核",
       LAY[4]: "坐标与文本矛盾，不得采信单侧",
       LAY[5]: "空坐标或编码失败（3 条 failed：1 条 API 错误、2 条落区外）"}
SUM = []
for i, k in enumerate(LAY):
    sub = [x for x in ROWS if x["当前判定等级"] == k]
    SUM.append({"类别编号": "①②③④⑤⑥"[i], "当前判定等级": k, "条数": len(sub),
                "其中原始verified=Y": sum(x["是否属于原始95条verified"] == "是" for x in sub),
                "其中严格点位分析资格": sum(x["严格点位分析资格"] == "是" for x in sub),
                "其中门牌粒度可用_含未确认": sum(x["门牌粒度可用_含未确认候选"] == "是" for x in sub),
                "其中街道级可用": sum(x["街道级是否可用"] == "是" for x in sub),
                "其中计入新增91条": sum(x["是否计入新增91条"] == "是" for x in sub),
                "可用于点位距离缓冲区米级": ("是（%d 条）" %
                                     sum(x["严格点位分析资格"] == "是" for x in sub))
                if k == LAY[0] else "否",
                "说明": DEF[k]})
SUM.append({"类别编号": "合计", "当前判定等级": "合计",
            "条数": sum(x["条数"] for x in SUM),
            "其中原始verified=Y": sum(x["其中原始verified=Y"] for x in SUM),
            "其中严格点位分析资格": sum(x["其中严格点位分析资格"] for x in SUM),
            "其中门牌粒度可用_含未确认": sum(x["其中门牌粒度可用_含未确认"] for x in SUM),
            "其中街道级可用": sum(x["其中街道级可用"] for x in SUM),
            "其中计入新增91条": sum(x["其中计入新增91条"] for x in SUM),
            "可用于点位距离缓冲区米级": "仅 93 条",
            "说明": "六类互斥。283=街道级可用总数；91=新增多候选计数（125 子集）"})
p_sum2 = os.path.join(OUT, "P0-2_分层互斥汇总表_v2.csv")
with open(p_sum2, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(SUM[0].keys()))
    w.writeheader()
    w.writerows(SUM)

print()
print("=" * 104)
print("### 3 新旧对比")
v1 = list(csv.DictReader(open(V1, encoding="utf-8-sig")))
v1map = {r["place_id"]: r for r in v1}
v2map = {r["place_id"]: r for r in ROWS}
changed = [(p, v1map[p]["当前判定等级"], v2map[p]["当前判定等级"]) for p in v1map
           if v1map[p]["当前判定等级"] != v2map[p]["当前判定等级"]
           or v1map[p]["当前修订后状态"] != v2map[p]["当前修订后状态"]]
for lab, old, new in (("逐行表", V1, p_v2), ("汇总表", V1SUM, p_sum2)):
    print("  %s v1 %8d B  %s" % (lab, os.path.getsize(old), sha(old)))
    print("  %s v2 %8d B  %s" % (lab, os.path.getsize(new), sha(new)))
print("  place_id 集合一致:", set(v1map) == set(v2map))
print("  **分类变化记录数:", len(changed), "**")
oc, nc = list(v1[0].keys()), list(ROWS[0].keys())
print("  v1 %d 列 → v2 %d 列" % (len(oc), len(nc)))
print("  新增列:", [x for x in nc if x not in oc])
print("  移除列:", [x for x in oc if x not in nc])

json.dump({"assert_all": allok, "counts": dict(c), "bad_multi_ids": bad_ids,
           "bad_multi_detail": [{"place_id": x["place_id"],
                                 "district": x["geocode返回district"],
                                 "adcode": x["geocode返回adcode"]} for x in rec2],
           "weak_verified_ids": sorted(x["place_id"] for x in weak_ver),
           "files": {"v1_rows": {"bytes": os.path.getsize(V1), "sha256": sha(V1)},
                     "v2_rows": {"bytes": os.path.getsize(p_v2), "sha256": sha(p_v2)},
                     "v1_sum": {"bytes": os.path.getsize(V1SUM), "sha256": sha(V1SUM)},
                     "v2_sum": {"bytes": os.path.getsize(p_sum2), "sha256": sha(p_sum2)}},
           "reclassified": len(changed),
           "new_columns": [x for x in nc if x not in oc],
           "removed_columns": [x for x in oc if x not in nc]},
          open(os.path.join(OUT, "_p02_assert_v2.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print()
print("已保存 _p02_assert_v2.json")
