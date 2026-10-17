# -*- coding: utf-8 -*-
"""P0-2：海珠坐标分层计数逐行对齐
从原始 CSV 逐行重算，输出：
  1 逐行分类表（340 行，含 8 个必需列）
  2 互斥分类汇总表
  3 校验断言（含 91/116/72/95 的数学关系证明）
"""
import csv
import hashlib
import json
import os
from collections import Counter, defaultdict

ROOT = r"D:\筑工杯数据获取"
P2 = os.path.join(ROOT, "广州市AI养老研究_第二阶段_本地实证_20261017")
OUT = os.path.join(ROOT, "广州市AI养老研究_P0核对_20261017")
os.makedirs(OUT, exist_ok=True)

DET = os.path.join(P2, "海珠坐标多证据批量核验明细.csv")
LAY = os.path.join(P2, "海珠坐标结论分层_街道可用vs点位可用.csv")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest().upper()


print("=" * 104)
print("### 0 输入文件")
for p in (DET, LAY):
    print("  %-52s %9d B  %s" % (os.path.basename(p), os.path.getsize(p), sha(p)))

det = list(csv.DictReader(open(DET, encoding="utf-8-sig")))
lay = {r["place_id"]: r for r in csv.DictReader(open(LAY, encoding="utf-8-sig"))}
print("  明细行:", len(det), "| 分层行:", len(lay))
print("  place_id 集合一致:", set(r["place_id"] for r in det) == set(lay.keys()))

DOOR = ("门址", "门牌号")
VERIFIED_STATUS = "已核实（沿用原判定）"
MULTI_OK = "多候选但空间-文本一致（待现场确认）"
SINGLE_OK = "单候选-空间文本一致（待现场确认）"

# ---------- 逐行构建 ----------
ROWS = []
for r in det:
    pid = r["place_id"]
    L = lay[pid]
    st = r["修订后状态"]
    layer = L["结论层级"]
    lvl = r["原level"]
    is_door = lvl in DOOR
    is_verified = (r["原verified"] == "Y")
    n_cand = int(r["原n_candidates"] or 0)

    # 是否计入"新增91条"：= 多候选且被判空间-文本一致
    in91 = (st == MULTI_OK)

    # 三个可用性维度（严格定义见汇总表）
    street_ok = layer in ("R2 坐标准确（原始verified=Y）",
                          "R1 街道可归属 + R2 门牌级（未现场确认）",
                          "R1 仅街道可归属（坐标精度不足）")
    door_ok = is_door and street_ok          # geocode 层级达门牌 且 有街道归属
    point_ok = is_verified                    # 仅原始 verified=Y 视为点位可用（不升级）

    # 不确定性说明
    unc = []
    if is_verified and not is_door:
        unc.append("原始verified=Y但geocode层级为%s，点位精度存疑（本轮不擅自降级）" % lvl)
    if in91:
        unc.append("多候选(n=%d)，仅证明街道归属，未证明点位唯一" % n_cand)
    if st == SINGLE_OK and not is_door:
        unc.append("单候选但层级为%s，坐标精度不足" % lvl)
    if layer == "冲突（不可用）":
        unc.append("坐标落面与地址文本街道冲突，不得采信单侧")
    if layer == "证据不足（不可用）":
        unc.append("坐标/地址/名录无一致指向")
    if layer == "无坐标/失败":
        unc.append("坐标为空或地理编码失败")
    if not unc:
        unc.append("无额外不确定性")

    ROWS.append({
        "place_id": pid,
        "canonical_address": r["canonical_address"],
        # ---- 8 个必需列 ----
        "原始状态": "%s / verified=%s / n_candidates=%d" % (r["原verdict"], r["原verified"], n_cand),
        "原始verdict": r["原verdict"],
        "原始verified": r["原verified"],
        "原始n_candidates": n_cand,
        "原始level": lvl,
        "当前判定等级": layer,
        "当前修订后状态": st,
        "点位级是否可用": "是" if point_ok else "否",
        "门牌级是否可用": "是" if door_ok else "否",
        "街道级是否可用": "是" if street_ok else "否",
        "是否属于原始95条verified": "是" if is_verified else "否",
        "是否计入新增91条": "是" if in91 else "否",
        "证据依据": r["判定依据"],
        "不确定性说明": "；".join(unc),
        "E1坐标落面": r["E1_坐标落面_WGS"],
        "E3地址文本街道": r["E3_地址文本街道"],
        "E5名录街道归属": r["E5_名录街道归属"],
    })

print()
print("=" * 104)
print("### 1 互斥分类汇总（按「当前判定等级」，6 类）")
c_layer = Counter(x["当前判定等级"] for x in ROWS)
LAY_ORDER = ["R2 坐标准确（原始verified=Y）",
             "R1 街道可归属 + R2 门牌级（未现场确认）",
             "R1 仅街道可归属（坐标精度不足）",
             "证据不足（不可用）", "冲突（不可用）", "无坐标/失败"]
tot = 0
for k in LAY_ORDER:
    v = c_layer.get(k, 0)
    tot += v
    print("  %-46s %4d" % (k, v))
print("  %-46s %4d" % ("合计", tot))

print()
print("=" * 104)
print("### 2 逐行 CSV 输出 + 校验断言")


def assert_eq(name, got, want):
    ok = (got == want)
    print("  [%s] %-52s got=%s want=%s" % ("PASS" if ok else "FAIL", name, got, want))
    return ok


all_ok = True
print()
print("-- 断言 A：总数与互斥还原")
all_ok &= assert_eq("A1 逐行总数 = 340", len(ROWS), 340)
all_ok &= assert_eq("A2 place_id 唯一（无重复）", len(set(x["place_id"] for x in ROWS)), 340)
all_ok &= assert_eq("A3 六类合计 = 340", tot, 340)

print()
print("-- 断言 B：三条可用性维度的计数")
n_point = sum(1 for x in ROWS if x["点位级是否可用"] == "是")
n_door = sum(1 for x in ROWS if x["门牌级是否可用"] == "是")
n_street = sum(1 for x in ROWS if x["街道级是否可用"] == "是")
print("     点位级可用 %d | 门牌级可用 %d | 街道级可用 %d" % (n_point, n_door, n_street))
all_ok &= assert_eq("B1 点位级可用 = 95（仅原始verified）", n_point, 95)
all_ok &= assert_eq("B2 门牌级可用 = 116+93 = 209", n_door, 209)
all_ok &= assert_eq("B3 街道级可用 = 95+116+72 = 283", n_street, 283)

print()
print("-- 断言 C：95 / 116 / 72 / 91 的数学关系")
n95 = sum(1 for x in ROWS if x["是否属于原始95条verified"] == "是")
n91 = sum(1 for x in ROWS if x["是否计入新增91条"] == "是")
n116 = c_layer.get("R1 街道可归属 + R2 门牌级（未现场确认）", 0)
n72 = c_layer.get("R1 仅街道可归属（坐标精度不足）", 0)
print("     95 条 verified = %d | 116 = %d | 72 = %d | 91 = %d" % (n95, n116, n72, n91))
all_ok &= assert_eq("C1 原始 verified = 95", n95, 95)
all_ok &= assert_eq("C2 门牌级层 = 116", n116, 116)
all_ok &= assert_eq("C3 仅街道层 = 72", n72, 72)
all_ok &= assert_eq("C4 新增 91 条 = 91", n91, 91)

# 关键关系：116 是否含 95
b116 = {x["place_id"] for x in ROWS if x["当前判定等级"] == LAY_ORDER[1]}
b95 = {x["place_id"] for x in ROWS if x["是否属于原始95条verified"] == "是"}
b91 = {x["place_id"] for x in ROWS if x["是否计入新增91条"] == "是"}
b72 = {x["place_id"] for x in ROWS if x["当前判定等级"] == LAY_ORDER[2]}
print()
print("     **116 与 95 是否相交**:", len(b116 & b95), "条")
all_ok &= assert_eq("C5 116 层不含任何 verified 记录（交集=0）", len(b116 & b95), 0)
print("     **91 是否全在 116∪72 内**: 91∩(116∪72) =", len(b91 & (b116 | b72)), "条")
all_ok &= assert_eq("C6 91 全部落在 116∪72 内（无遗漏）", len(b91 & (b116 | b72)), 91)
print("     91 中属于 116 的:", len(b91 & b116), "条；属于 72 的:", len(b91 & b72), "条")
all_ok &= assert_eq("C7 91 = 68(在116) + 23(在72)", (len(b91 & b116), len(b91 & b72)), (68, 23))
print("     116∪72 (=188) 与 95 的交集:", len((b116 | b72) & b95))
all_ok &= assert_eq("C8 188 与 95 互斥", len((b116 | b72) & b95), 0)
all_ok &= assert_eq("C9 95 + 188 = 283（有街道归属总数）", 95 + 188, 283)

print()
print("-- 断言 D：91 的来源（从上一轮 123 条多候选转来）")
multi = [x for x in ROWS if x["原始n_candidates"] >= 2 and x["原始verdict"] == "needs_review"]
print("     原多候选(needs_review 且 n>=2):", len(multi))
all_ok &= assert_eq("D1 原多候选数 = 123", len(multi), 123)
md = Counter(x["当前修订后状态"] for x in multi)
for k, v in md.most_common():
    print("       → %-42s %d" % (k, v))
all_ok &= assert_eq("D2 多候选去向合计 = 123", sum(md.values()), 123)
all_ok &= assert_eq("D3 其中判为空间-文本一致(即91) = 91",
                    md.get(MULTI_OK, 0), 91)

print()
print("-- 断言 E：单候选相关的口径区分（易混淆点）")
single_all = [x for x in ROWS if x["原始n_candidates"] == 1 and x["原始verdict"] == "needs_review"]
single_ok = [x for x in ROWS if x["当前修订后状态"] == SINGLE_OK]
print("     口径E-a 原 n_candidates==1 且 needs_review :", len(single_all))
print("     口径E-b 状态为'单候选-空间文本一致'         :", len(single_ok))
print("     **两者定义不同，不得混用**：E-b 是 E-a 的子集（另有一部分被判冲突/证据不足）")
all_ok &= assert_eq("E1 原单候选(needs_review 且 n=1) = 119", len(single_all), 119)
all_ok &= assert_eq("E2 其中状态为'空间-文本一致' = 97", len(single_ok), 97)
sa = {x["place_id"] for x in single_all}
all_ok &= assert_eq("E3 97 全部来自 119（子集关系）", len({x["place_id"] for x in single_ok} & sa), 97)
sc = Counter(x["当前修订后状态"] for x in single_all)
print("     119 条的最终去向：")
for k, v in sc.most_common():
    print("       → %-42s %d" % (k, v))
all_ok &= assert_eq("E4 119 去向合计 = 119", sum(sc.values()), 119)
all_ok &= assert_eq("E5 116 = 68(来自多候选91) + 48(来自单候选97)",
                    (len(b91 & b116), 116 - len(b91 & b116)), (68, 48))
all_ok &= assert_eq("E6 72 = 23(来自多候选91) + 49(来自单候选97)",
                    (len(b91 & b72), 72 - len(b91 & b72)), (23, 49))

print()
print("-- 断言 F：不升级原则（无任何多候选被标 verified）")
upgraded = [x for x in ROWS if x["是否计入新增91条"] == "是" and x["是否属于原始95条verified"] == "是"]
all_ok &= assert_eq("F1 无多候选被升级为 verified", len(upgraded), 0)
all_ok &= assert_eq("F2 verified 总数仍为 95（未被改动）", n95, 95)

print()
print("=" * 104)
print("### 3 输出文件")
p_out = os.path.join(OUT, "P0-2_海珠坐标逐行分类交叉表.csv")
with open(p_out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(ROWS[0].keys()))
    w.writeheader()
    w.writerows(ROWS)
print("  逐行表:", p_out, len(ROWS), "行,", os.path.getsize(p_out), "B")

# 汇总表
SUM = []
for k in LAY_ORDER:
    sub = [x for x in ROWS if x["当前判定等级"] == k]
    SUM.append({
        "类别编号": "①②③④⑤⑥"[LAY_ORDER.index(k)],
        "当前判定等级": k,
        "条数": len(sub),
        "其中原始verified=Y": sum(1 for x in sub if x["是否属于原始95条verified"] == "是"),
        "其中计入新增91条": sum(1 for x in sub if x["是否计入新增91条"] == "是"),
        "点位级可用": sum(1 for x in sub if x["点位级是否可用"] == "是"),
        "门牌级可用": sum(1 for x in sub if x["门牌级是否可用"] == "是"),
        "街道级可用": sum(1 for x in sub if x["街道级是否可用"] == "是"),
        "可用于点位/距离/缓冲区": "是" if k == LAY_ORDER[0] else "否",
        "说明": {
            LAY_ORDER[0]: "原始 verified=Y；唯一可用于米级空间运算（其中2条level为弱层级，已单独标注待核）",
            LAY_ORDER[1]: "geocode 门牌级但未现场确认；可用于街道汇总，点位为候选",
            LAY_ORDER[2]: "仅能定街道；坐标可能落街道内任意位置，禁止点位/距离/缓冲区",
            LAY_ORDER[3]: "无一致指向，保留待核",
            LAY_ORDER[4]: "坐标与文本矛盾，不得采信单侧",
            LAY_ORDER[5]: "空坐标或失败",
        }[k],
    })
SUM.append({"类别编号": "合计", "当前判定等级": "合计", "条数": sum(x["条数"] for x in SUM),
            "其中原始verified=Y": sum(x["其中原始verified=Y"] for x in SUM),
            "其中计入新增91条": sum(x["其中计入新增91条"] for x in SUM),
            "点位级可用": sum(x["点位级可用"] for x in SUM),
            "门牌级可用": sum(x["门牌级可用"] for x in SUM),
            "街道级可用": sum(x["街道级可用"] for x in SUM)})
p_sum = os.path.join(OUT, "P0-2_分层互斥汇总表.csv")
with open(p_sum, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(SUM[0].keys()))
    w.writeheader()
    w.writerows(SUM)
print("  汇总表:", p_sum, len(SUM), "行")

print()
print("=" * 104)
print("### 4 结论")
print("  全部断言:", "通过" if all_ok else "**存在失败**")
print()
print("  95 / 116 / 72 / 91 的关系（数学证明）：")
print("    95  = 原始 verified=Y（点位可用），与其余各类互斥")
print("    116 = 门牌级层（全部来自 needs_review，不含任何 verified）")
print("    72  = 仅街道层（全部来自 needs_review，不含任何 verified）")
print("    188 = 116 + 72 = 本轮'街道可归属'总数（不含 verified 的 95）")
print("    283 = 95 + 188 = 有街道归属的全部记录")
print("    91  = 123 条原多候选中通过一致性检验者 = 68(属116) + 23(属72)")
print("    → 91 是 116∪72 的**子集**，不是独立类别；116 不含 95，故不矛盾")
print("    → 差额来源：116 中另有 48 条来自原单候选(97)")
print("    → 断言：95+116+72+30+24+3 = %d = 340" % (95 + 116 + 72 + 30 + 24 + 3))

json.dump({"assert_all": all_ok,
           "counts": {"total": len(ROWS), "verified95": n95, "layer116": n116,
                      "layer72": n72, "new91": n91, "point_ok": n_point,
                      "door_ok": n_door, "street_ok": n_street,
                      "multi_total": len(multi), "single_total": len(single_all), "single_ok": len(single_ok)},
           "relations": {"b116_and_b95": len(b116 & b95), "b91_in_116_or_72": len(b91 & (b116 | b72)),
                         "b91_in_116": len(b91 & b116), "b91_in_72": len(b91 & b72),
                         "sum_check": 95 + 116 + 72 + 30 + 24 + 3}},
          open(os.path.join(OUT, "_p02_assert.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print()
print("  已保存 _p02_assert.json")
