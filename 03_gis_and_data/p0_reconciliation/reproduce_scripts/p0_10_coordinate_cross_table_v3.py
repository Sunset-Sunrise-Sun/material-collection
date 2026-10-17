# -*- coding: utf-8 -*-
"""P0-2 v3：审计加固版
必修1 已修复（脚本 except 分支继承上一行）；本脚本产出 v3 逐行表/汇总表/断言JSON/审计抽取
必修2 断言改用真实数据统计，输出 name/actual/expected/passed 数组
必修3 记录级点位资格(93) 与 最终米级分析(待坐标系验证) 分离
必修4 门牌粒度记录数_含未确认候选
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
V2 = os.path.join(OUT, "P0-2_海珠坐标逐行分类交叉表_v2.csv")
V2SUM = os.path.join(OUT, "P0-2_分层互斥汇总表_v2.csv")


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
print("明细(修复后):", len(det), "| 分层:", len(lay), "| geocode原始:", len(go))

ROWS = []
for d in det:
    pid = d["place_id"]
    g = go[pid]
    layer = lay[pid]["结论层级"]
    st = d["修订后状态"]
    # 原始 API 字段（一律取原始 geocode，不取归一化值）
    n_api = (g.get("n_candidates") or "").strip()
    lvl_api = (g.get("level") or "").strip()
    ver_api = (g.get("verified") or "").strip()
    lng = (g.get("lng_wgs84") or "").strip()
    lat = (g.get("lat_wgs84") or "").strip()
    n_num = int(n_api) if n_api.isdigit() else 0
    is_ver = (ver_api == "Y")
    is_door = lvl_api in DOOR
    coord_ok = (lng != "" and lat != "")

    street_ok = layer in (LAY[0], LAY[1], LAY[2])
    door_rec = is_door and street_ok
    rec_level_point = is_ver and is_door and coord_ok      # 记录级点位资格
    in91 = (st == "多候选但空间-文本一致（待现场确认）")

    unc = []
    if is_ver and not is_door:
        unc.append("原始verified=Y但层级=%r：不具记录级点位资格，待核；"
                   "**不改变原始verified状态、不把95降为93**" % lvl_api)
    if is_ver and is_door:
        unc.append("记录级点位资格具备；但**11区边界坐标系待验证，故最终米级分析仍待授权**")
    if in91:
        unc.append("多候选(n=%s)，仅证街道归属，未证点位唯一" % (n_api or "缺失"))
    if g.get("verdict") == "failed":
        if coord_ok:
            unc.append("地理编码判failed：返回坐标落于%s（adcode=%s）**非海珠区**；"
                       "坐标存在但不可用，**并非坐标为空**"
                       % ((g.get("district") or "区外"), (g.get("adcode") or "?")))
        else:
            unc.append("地理编码API失败（infocode=%s），无候选、无坐标；"
                       "原始 n_candidates 缺失，**不得归一化为1**"
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
        # --- 原始 API 字段（不归一化）---
        "原始verdict_API": (g.get("verdict") or ""),
        "原始verified_API": ver_api,
        "原始n_candidates_API": n_api,
        "原始level_API": lvl_api,
        "经纬度是否非空_API": "是" if coord_ok else "否",
        "geocode返回district": (g.get("district") or ""),
        "geocode返回adcode": (g.get("adcode") or ""),
        "geocode_status": (g.get("status") or ""),
        "geocode_infocode": (g.get("infocode") or ""),
        # --- 衍生字段 ---
        "n_candidates_数值化": n_num,
        "原始n_candidates是否>1": "是" if n_num > 1 else "否",
        "当前判定等级": layer,
        "当前修订后状态": st,
        "街道级是否可用": "是" if street_ok else "否",
        "门牌粒度记录数_含未确认候选": "是" if door_rec else "否",
        "记录级点位资格": "是" if rec_level_point else "否",
        "最终米级分析资格": ("待坐标系验证" if rec_level_point else "否"),
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
    c["coord_ok"] += (x["经纬度是否非空_API"] == "是")
    c["ver95"] += (x["是否属于原始95条verified"] == "是")
    c["rec93"] += (x["记录级点位资格"] == "是")
    c["door209"] += (x["门牌粒度记录数_含未确认候选"] == "是")
    c["street283"] += (x["街道级是否可用"] == "是")
    c["in91"] += (x["是否计入新增91条"] == "是")
    c["failed"] += (x["原始verdict_API"] == "failed")

print()
print("=" * 104)
print("### 1 v3 关键口径")
for k, lab in (("total", "总记录"), ("n_gt1", "原始 n_candidates>1"),
               ("coord_ok", "经纬度非空"), ("failed", "verdict=failed"),
               ("ver95", "原始 verified=Y"), ("rec93", "记录级点位资格"),
               ("door209", "门牌粒度记录数(含未确认)"), ("street283", "街道级可用"),
               ("in91", "计入新增91条")):
    print("  %-30s %d" % (lab, c[k]))

# ---------- 必修2：断言数组 ----------
AS = []


def A(name, actual, expected):
    passed = (actual == expected)
    AS.append({"name": name, "actual": actual, "expected": expected, "passed": passed})
    print("  [%s] %-54s actual=%s expected=%s"
          % ("PASS" if passed else "FAIL", name, actual, expected))
    return passed


print()
print("=" * 104)
print("### 2 断言 v3（必修2：真实数据统计 + 结构化数组）")
print("-- 必修1 回归：脚本修复后计数不变")
A("H1 原始 n_candidates>1 仍为 125（修复后重算）", c["n_gt1"], 125)
A("H2 P-45b4cccd 原始 n_candidates 保持缺失",
  [x["原始n_candidates_API"] for x in ROWS if x["place_id"] == "P-45b4cccd"], [""])
A("H3 P-45b4cccd 原始 level 保持缺失",
  [x["原始level_API"] for x in ROWS if x["place_id"] == "P-45b4cccd"], [""])
A("H4 受影响记录仅 1 条（坐标为空）",
  len([x for x in ROWS if x["经纬度是否非空_API"] == "否"]), 1)

print()
print("-- 必修2：G3c / G4 按真实数据统计")
bad = [x for x in ROWS if x["原始n_candidates是否>1"] == "是"
       and x["原始verdict_API"] == "failed"]
print("     多候选且 failed 的记录:", [x["place_id"] for x in bad])
# G3c：直接检查原始经纬度是否非空（不用 adcode 代替）
A("G3c 两条落区外记录原始经纬度均非空",
  [x["经纬度是否非空_API"] for x in bad], ["是", "是"])
A("G3c2 两条落区外记录 adcode 均非海珠(440105)",
  [x["geocode返回adcode"] != "440105" for x in bad], [True, True])
print("       坐标与区名明细:")
for x in bad:
    print("         %s lng=" % x["place_id"], end="")
    g = go[x["place_id"]]
    print("%r lat=%r district=%s adcode=%s" % (
        g["lng_wgs84"], g["lat_wgs84"], x["geocode返回district"], x["geocode返回adcode"]))
# G4：从实际行分别统计四个分组
g_91 = len([x for x in ROWS if x["当前修订后状态"] == "多候选但空间-文本一致（待现场确认）"])
g_17 = len([x for x in ROWS if x["当前修订后状态"] == "多候选（仍需人工逐条决议）"])
g_15 = len([x for x in ROWS if x["当前修订后状态"] == "坐标与地址街道冲突（待核）"
            and x["原始n_candidates是否>1"] == "是"])
g_2 = len(bad)
print("     四分组实际统计: 91=%d 17=%d 15=%d 2=%d 合计=%d"
      % (g_91, g_17, g_15, g_2, g_91 + g_17 + g_15 + g_2))
A("G4 四分组实际合计 = 原始多候选总数",
  g_91 + g_17 + g_15 + g_2, c["n_gt1"])
A("G4a 分组1 空间-文本一致", g_91, 91)
A("G4b 分组2 仍需人工", g_17, 17)
A("G4c 分组3 冲突(多候选)", g_15, 15)
A("G4d 分组4 failed落区外", g_2, 2)

print()
print("-- 必修3：记录级资格 vs 最终米级分析")
A("G8a 记录级点位资格 = 93", c["rec93"], 93)
A("G8b 原始 verified=Y = 95", c["ver95"], 95)
A("G8c 最终米级分析资格全部为'待坐标系验证'",
  sorted({x["最终米级分析资格"] for x in ROWS if x["记录级点位资格"] == "是"}),
  ["待坐标系验证"])
A("G8d 无任一条被标为最终米级可用",
  len([x for x in ROWS if x["最终米级分析资格"] == "是"]), 0)

print()
print("-- 必修4：门牌粒度标签与计数")
A("G9 门牌粒度记录数(含未确认) = 209", c["door209"], 209)
A("G9b 209 = 93记录级资格 + 116未确认候选",
  (len([x for x in ROWS if x["门牌粒度记录数_含未确认候选"] == "是"
        and x["记录级点位资格"] == "是"]),
   len([x for x in ROWS if x["门牌粒度记录数_含未确认候选"] == "是"
        and x["当前判定等级"] == LAY[1]])), (93, 116))

print()
print("-- 其余口径")
A("G1 原始 n_candidates>1 = 125", c["n_gt1"], 125)
A("G5 91 条全部为多候选", all(
    x["原始n_candidates是否>1"] == "是" for x in ROWS if x["是否计入新增91条"] == "是"), True)
A("G6 283=街道级总数; 91=新增多候选", (c["street283"], c["in91"]), (283, 91))
weak = [x for x in ROWS if x["是否属于原始95条verified"] == "是"
        and x["记录级点位资格"] == "否"]
A("G7 两条兴趣点 verified 无记录级点位资格",
  (len(weak), sorted(x["place_id"] for x in weak)), (2, ["P-2db0b22d", "P-d227f901"]))
A("G10 六类合计 = 340", c["total"], 340)
A("G11 verdict=failed 共 3 条", c["failed"], 3)

print()
print("-- 回归断言")
layc = Counter(x["当前判定等级"] for x in ROWS)
b116 = {x["place_id"] for x in ROWS if x["当前判定等级"] == LAY[1]}
b95 = {x["place_id"] for x in ROWS if x["是否属于原始95条verified"] == "是"}
b91 = {x["place_id"] for x in ROWS if x["是否计入新增91条"] == "是"}
b72 = {x["place_id"] for x in ROWS if x["当前判定等级"] == LAY[2]}
A("C2 门牌级层=116", layc[LAY[1]], 116)
A("C3 仅街道层=72", layc[LAY[2]], 72)
A("C5 116∩95=0", len(b116 & b95), 0)
A("C6 91⊂(116∪72)", len(b91 & (b116 | b72)), 91)
A("C7 91=68+23", [len(b91 & b116), len(b91 & b72)], [68, 23])
A("C8 188∩95=0", len((b116 | b72) & b95), 0)
A("A1 place_id 唯一", len({x["place_id"] for x in ROWS}), 340)

allok = all(a["passed"] for a in AS)
print()
print("  断言总数:", len(AS), "| 通过:", sum(1 for a in AS if a["passed"]),
      "| 失败:", sum(1 for a in AS if not a["passed"]))
print("  assert_all:", allok)

# ---------- 输出 v3 ----------
p_v3 = os.path.join(OUT, "P0-2_海珠坐标逐行分类交叉表_v3.csv")
with open(p_v3, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(ROWS[0].keys()))
    w.writeheader()
    w.writerows(ROWS)

DEF = {LAY[0]: "原始verified=Y；2 条层级兴趣点→无记录级点位资格（待核）",
       LAY[1]: "门牌粒度但未现场确认；可街道汇总，点位为候选",
       LAY[2]: "仅能定街道；禁止点位/距离/缓冲区/米级",
       LAY[3]: "无一致指向，保留待核",
       LAY[4]: "坐标与文本矛盾，不得采信单侧",
       LAY[5]: "空坐标或编码失败（3 条 failed：1 条 API 错误无坐标、2 条落区外有坐标）"}
SUM = []
for i, k in enumerate(LAY):
    sub = [x for x in ROWS if x["当前判定等级"] == k]
    SUM.append({
        "类别编号": "①②③④⑤⑥"[i], "当前判定等级": k, "条数": len(sub),
        "其中原始verified=Y": sum(x["是否属于原始95条verified"] == "是" for x in sub),
        "其中记录级点位资格": sum(x["记录级点位资格"] == "是" for x in sub),
        "最终米级分析资格": ("待坐标系验证" if k == LAY[0] else "否"),
        "其中门牌粒度记录数_含未确认": sum(
            x["门牌粒度记录数_含未确认候选"] == "是" for x in sub),
        "其中街道级可用": sum(x["街道级是否可用"] == "是" for x in sub),
        "其中计入新增91条": sum(x["是否计入新增91条"] == "是" for x in sub),
        "说明": DEF[k]})
SUM.append({
    "类别编号": "合计", "当前判定等级": "合计", "条数": sum(x["条数"] for x in SUM),
    "其中原始verified=Y": sum(x["其中原始verified=Y"] for x in SUM),
    "其中记录级点位资格": sum(x["其中记录级点位资格"] for x in SUM),
    "最终米级分析资格": "待坐标系验证（0 条被授权）",
    "其中门牌粒度记录数_含未确认": sum(x["其中门牌粒度记录数_含未确认"] for x in SUM),
    "其中街道级可用": sum(x["其中街道级可用"] for x in SUM),
    "其中计入新增91条": sum(x["其中计入新增91条"] for x in SUM),
    "说明": "283=街道级可用总数；91=新增多候选计数（125子集）；"
            "93=记录级点位资格，**最终米级分析须待坐标系验证**；"
            "209=门牌粒度记录数（93+116），非209个已核实点位"})
p_sum3 = os.path.join(OUT, "P0-2_分层互斥汇总表_v3.csv")
with open(p_sum3, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(SUM[0].keys()))
    w.writeheader()
    w.writerows(SUM)

# ---------- 最小化审计抽取表 ----------
AUD = []
for x in ROWS:
    AUD.append({
        "place_id": x["place_id"],
        "原始n_candidates_API": x["原始n_candidates_API"],
        "原始level_API": x["原始level_API"],
        "原始verified_API": x["原始verified_API"],
        "原始verdict_API": x["原始verdict_API"],
        "经纬度是否非空": x["经纬度是否非空_API"],
        "geocode返回district": x["geocode返回district"],
        "geocode返回adcode": x["geocode返回adcode"],
        "geocode_status": x["geocode_status"],
        "geocode_infocode": x["geocode_infocode"],
        "当前判定等级": x["当前判定等级"],
        "记录级点位资格": x["记录级点位资格"],
    })
p_aud = os.path.join(OUT, "P0-2_geocode审计抽取.csv")
with open(p_aud, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(AUD[0].keys()))
    w.writeheader()
    w.writerows(AUD)

# ---------- 与 v2 逐 ID 差异 ----------
v2 = list(csv.DictReader(open(V2, encoding="utf-8-sig")))
v2map = {r["place_id"]: r for r in v2}
v3map = {x["place_id"]: x for x in ROWS}
iddiff = []
for pid in v2map:
    a, b = v2map[pid], v3map[pid]
    if a["当前判定等级"] != b["当前判定等级"]:
        iddiff.append({"place_id": pid, "v2": a["当前判定等级"], "v3": b["当前判定等级"]})
print()
print("=" * 104)
print("### 3 与 v2 对比")
print("  v2 行数/列数: %d / %d" % (len(v2), len(list(v2[0].keys()))))
print("  v3 行数/列数: %d / %d" % (len(ROWS), len(list(ROWS[0].keys()))))
print("  place_id 集合一致:", set(v2map) == set(v3map))
print("  **所属类别变化记录数: %d**" % len(iddiff))
print("  v2 标的点位级可用(95) → v3 拆为 记录级点位资格(93) + 2条待核")
print()
for lab, p in (("v2 逐行", V2), ("v3 逐行", p_v3), ("v2 汇总", V2SUM), ("v3 汇总", p_sum3)):
    print("  %-10s %9d B  %s" % (lab, os.path.getsize(p), sha(p)))

json.dump({
    "assert_all": allok,
    "assertions": AS,
    "counts": dict(c),
    "groups": {"g91": g_91, "g17": g_17, "g15": g_15, "g2": g_2,
               "sum": g_91 + g_17 + g_15 + g_2},
    "bad_multi_detail": [{"place_id": x["place_id"],
                          "adcode": x["geocode返回adcode"],
                          "district": x["geocode返回district"],
                          "lng": go[x["place_id"]]["lng_wgs84"],
                          "lat": go[x["place_id"]]["lat_wgs84"]} for x in bad],
    "weak_verified_ids": sorted(x["place_id"] for x in weak),
    "files": {
        "v2_rows": {"bytes": os.path.getsize(V2), "sha256": sha(V2)},
        "v3_rows": {"bytes": os.path.getsize(p_v3), "sha256": sha(p_v3)},
        "v2_sum": {"bytes": os.path.getsize(V2SUM), "sha256": sha(V2SUM)},
        "v3_sum": {"bytes": os.path.getsize(p_sum3), "sha256": sha(p_sum3)},
        "audit": {"bytes": os.path.getsize(p_aud), "sha256": sha(p_aud)},
    },
    "id_level_category_changes": len(iddiff),
}, open(os.path.join(OUT, "_p02_assert_v3.json"), "w", encoding="utf-8"),
    ensure_ascii=False, indent=1)
print()
print("已保存 _p02_assert_v3.json")
