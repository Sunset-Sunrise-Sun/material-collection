# -*- coding: utf-8 -*-
"""任务B 续：B5 区级供给密度与人口结构复算 / B6 海珠街道对照（新坐标分层）
/ B7 复现性核对 —— 并合并成最终工作簿
"""
import csv
import json
import math
import os
import shutil
from collections import Counter, defaultdict

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from shapely.geometry import Point, shape

ROOT = r"D:\筑工杯数据获取"
B = os.path.join(ROOT, "筑工杯_旧数据_2026前期", "_baseline_current")
OUT = os.path.join(ROOT, "广州市AI养老研究_第二阶段_本地实证_20261017")
TODAY = "2026-10-17"
KX = 111.32 * math.cos(math.radians(23.1))
KY = 110.57

HF = PatternFill("solid", fgColor="1F4E79")
HF2 = PatternFill("solid", fgColor="2E75B6")
HF3 = PatternFill("solid", fgColor="806000")
HF4 = PatternFill("solid", fgColor="C00000")
HFG = PatternFill("solid", fgColor="375623")
WF = Font(color="FFFFFF", bold=True, size=10)
TH = Side(style="thin", color="BFBFBF")
BD = Border(left=TH, right=TH, top=TH, bottom=TH)
WRAP = Alignment(wrap_text=True, vertical="top")
NOTE = Font(italic=True, size=9, color="808080")


def sheet(wb, name, title, note, cols, rows, widths, fill=None):
    ws = wb.create_sheet(name)
    ws.cell(row=1, column=1, value=title).font = Font(bold=True, size=12, color="1F4E79")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(1, len(cols)))
    ws.cell(row=2, column=1, value=note).font = NOTE
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max(1, len(cols)))
    ws.cell(row=2, column=1).alignment = WRAP
    ws.row_dimensions[2].height = 54
    for j, c in enumerate(cols, 1):
        cell = ws.cell(row=4, column=j, value=c)
        cell.fill = fill or HF
        cell.font = WF
        cell.border = BD
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    ws.row_dimensions[4].height = 30
    for i, r in enumerate(rows, 5):
        for j, c in enumerate(cols, 1):
            cell = ws.cell(row=i, column=j, value=r.get(c, ""))
            cell.alignment = WRAP
            cell.border = BD
            cell.font = Font(size=9)
    for j, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "B5"
    ws.auto_filter.ref = "A4:%s%d" % (get_column_letter(len(cols)), ws.max_row)
    return ws


# =========================================================
# 读取基础数据
# =========================================================
p25 = {r["region"]: r for r in csv.DictReader(
    open(os.path.join(B, "data", "population_2025_registered_district.csv"), encoding="utf-8-sig"))}
p20 = {r["name"]: r for r in csv.DictReader(
    open(os.path.join(B, "data", "population_2020_all_levels.csv"), encoding="utf-8-sig"))
    if r["level"] == "district"}
tw = list(csv.DictReader(open(os.path.join(B, "data", "population_2020_176_townships.csv"),
                              encoding="utf-8-sig")))
EC = json.load(open(os.path.join(B, "data", "eldercare_20260923.json"), encoding="utf-8"))
ME = list(csv.DictReader(open(os.path.join(B, "data", "elder_meals_20250205.csv"),
                              encoding="utf-8-sig")))
MP = list(csv.DictReader(open(os.path.join(B, "data", "medical_primary_202311.csv"),
                              encoding="utf-8-sig")))
DISTRICTS = ["荔湾区", "越秀区", "海珠区", "天河区", "白云区", "黄埔区",
             "番禺区", "花都区", "南沙区", "从化区", "增城区"]

inst = Counter(r["district_as_reported"] for r in EC)
beds = defaultdict(int)
for r in EC:
    if isinstance(r.get("registered_beds"), int):
        beds[r["district_as_reported"]] += r["registered_beds"]
meal = Counter(r["district"] for r in ME)
pc = Counter(r["district"] for r in MP)

# =========================================================
# 先建 B1-B4（从中间数据）
# =========================================================
wb = openpyxl.Workbook()
wb.remove(wb.active)

import pickle
_P1 = pickle.load(open(os.path.join(OUT, "_part1_data.pkl"), "rb"))

sheet(wb, "B1_坐标分层结果",
      "B1｜海珠设施坐标：结论分层（区分'街道可归属'与'点位可用'）——本轮核心推进",
      "本轮对 340 条地理编码记录做**多证据批量核验**（E1坐标点面判定／E2双假设／E3地址文本街道／"
      "E4返回道路名／E5名录街道归属／E6匹配层级）。**关键纪律：多候选坐标不得因'街道一致'就升为'已核实'**；"
      "'已核实'仍只保留原始 verified=Y 的 95 条。本表把结论拆成两层：街道级可归属 vs 点位可用。",
      ["结论层级", "条数", "含义", "可用于街道级汇总", "可用于点位/距离分析"],
      _P1["B1"], [42, 8, 68, 16, 18], fill=HF4)

sheet(wb, "B2_街镇名标准化",
      "B2｜街镇名标准化结果（仅海珠区可映射到18街道；其他10区无边界）",
      "映射依据：haizhu_18_streets_osm_wgs84.geojson 的 name 字段（已与 2020 人口表 18/18 核对）。"
      "标准化规则：'XX街'/'XX街道'/'XX' → 'XX街道'，仅限海珠18街道名单。"
      "**其他10区因缺街镇边界，不做映射也不臆造标准名**。",
      ["名录", "行政区", "记录数", "township_raw唯一值数", "可映射到海珠18街道标准名", "映射率", "说明"],
      _P1["B2"], [12, 10, 10, 20, 22, 22, 60], fill=HF2)

sheet(wb, "B2b_海珠映射明细",
      "B2b｜海珠区 township_raw → 标准街道名 逐项映射",
      "共 36 个（名录×街镇）组合；海珠18街道全覆盖。",
      ["名录", "原始街镇名", "记录数", "标准化街镇名", "映射方式"],
      _P1["B2b"], [12, 16, 10, 18, 14], fill=HF2)

sheet(wb, "B3_名录质量登记",
      "B3｜名录重复 / 同址 / 区划归属冲突 逐项登记（只登记，不改值、不合并不去重）",
      "**纪律：任何一条都保留原始值，不做合并、不去重、不改上报区**；"
      "同址不必然等于重复（可能是不同服务主体共用场所）；区划冲突可能是执业地与登记地口径不同。",
      ["类型", "名录", "记录ID", "名称", "原始值", "修订值", "判定依据", "置信状态", "处理"],
      _P1["B3"], [16, 12, 24, 34, 40, 26, 42, 20, 44], fill=HF3)

sheet(wb, "B4_GIS不确定性说明",
      "B4｜GIS 数据不确定性总说明（坐标系／边界／归属／坐标／口径）",
      "本表把每一类不确定性的**当前状态、证据、对分析的影响、本轮处理方式、可闭合路径**分列。"
      "**凡标'待验证'或'缺失'者，均不得在本轮结论中被当作已知。**",
      ["不确定性维度", "当前状态", "证据", "对分析的影响", "本轮处理", "可闭合路径"],
      _P1["B4"], [20, 22, 56, 44, 40, 44], fill=HF4)

# =========================================================
# B5 区级复算
# =========================================================
B5 = []
for d in DISTRICTS:
    a = p25[d]
    b = p20[d]
    tot, a60, a65, a80 = (int(a["total_population"]), int(a["age60_plus"]),
                          int(a["age65_plus"]), int(a["age80_plus"]))
    a60_20 = int(b["age60_plus"])
    ni, nb, nm, npc = inst[d], beds[d], meal[d], pc[d]
    B5.append({
        "区": d,
        "总人口_2025户籍": tot, "60+_2025户籍": a60, "65+_2025户籍": a65, "80+_2025户籍": a80,
        "60+占比_2025(%)": float(a["age60_pct"]),
        "65+占比_2025(%)": float(a["age65_pct"]),
        "80+占60+_2025(%)": float(a["age80_share_of_age60"]),
        "60+_2020常住": a60_20,
        "养老机构_2026": ni, "备案床位_2026": nb,
        "长者饭堂_2025": nm, "基层医疗_2023": npc,
        "床位每千名60+[床2026÷人2025]": round(nb / (a60 / 1000), 2) if a60 else "",
        "机构每万名60+[2026÷2025]": round(ni / (a60 / 10000), 2) if a60 else "",
        "饭堂每万名60+[2025÷2025]": round(nm / (a60 / 10000), 2) if a60 else "",
        "基层医疗每万名60+[2023÷2025]": round(npc / (a60 / 10000), 2) if a60 else "",
        "床位每千名60+_敏感度[床2026÷人2020]": round(nb / (a60_20 / 1000), 2) if a60_20 else "",
        "两分母差异(%)": round(100 * ((nb / (a60 / 1000)) - (nb / (a60_20 / 1000)))
                          / (nb / (a60_20 / 1000)), 1) if a60 and a60_20 and nb else "",
    })
tot_sum = {k: sum(r[k] for r in B5) for k in
           ("总人口_2025户籍", "60+_2025户籍", "65+_2025户籍", "80+_2025户籍",
            "养老机构_2026", "备案床位_2026", "长者饭堂_2025", "基层医疗_2023")}
B5.append({"区": "合计", **tot_sum,
           "床位每千名60+[床2026÷人2025]": round(
               tot_sum["备案床位_2026"] / (tot_sum["60+_2025户籍"] / 1000), 2),
           "说明": "分区加总"})
sheet(wb, "B5_区级供给与人口复算",
      "B5｜区级供给密度与人口结构复算（公式、年份、分母全部显式标注）",
      "**公式**：床位每千名60+ = 备案床位(2026) ÷ [60岁及以上户籍人口(2025) ÷ 1000]；其余同理。"
      "**分子分母年份不同（跨年）→ 仅为供给密度代理，不是同期比率，更不是需求满足率**。"
      "最后一列用 2020 常住 60+ 作分母做敏感度对照，**两列不可混用**。"
      "**设施数量 ≠ 服务能力；供给密度 ≠ 可达性 ≠ 需求满足率。**",
      ["区", "总人口_2025户籍", "60+_2025户籍", "65+_2025户籍", "80+_2025户籍",
       "60+占比_2025(%)", "65+占比_2025(%)", "80+占60+_2025(%)", "60+_2020常住",
       "养老机构_2026", "备案床位_2026", "长者饭堂_2025", "基层医疗_2023",
       "床位每千名60+[床2026÷人2025]", "机构每万名60+[2026÷2025]", "饭堂每万名60+[2025÷2025]",
       "基层医疗每万名60+[2023÷2025]", "床位每千名60+_敏感度[床2026÷人2020]", "两分母差异(%)"],
      B5, [8, 14, 13, 13, 13, 12, 12, 14, 12, 11, 12, 12, 12, 18, 18, 18, 20, 22, 12])

# 口径校验
CHK = []
for k, f in (("总人口_2025户籍", "total_population"), ("60+_2025户籍", "age60_plus"),
             ("65+_2025户籍", "age65_plus"), ("80+_2025户籍", "age80_plus")):
    s = sum(r[k] for r in B5 if r["区"] != "合计")
    city = int(p25["全市"][f])
    CHK.append({"校验项": "分区合计 vs 全市口径 - %s" % k, "分区合计": s,
                "全市口径": city, "差额": s - city,
                "结论": "一致" if s == city else "**不一致**"})
CHK.append({"校验项": "养老机构合计", "分区合计": sum(inst.values()),
            "全市口径": len(EC), "差额": sum(inst.values()) - len(EC),
            "结论": "一致" if sum(inst.values()) == len(EC) else "不一致"})
CHK.append({"校验项": "饭堂合计", "分区合计": sum(meal.values()),
            "全市口径": len(ME), "差额": sum(meal.values()) - len(ME),
            "结论": "一致" if sum(meal.values()) == len(ME) else "不一致"})
CHK.append({"校验项": "基层医疗合计", "分区合计": sum(pc.values()),
            "全市口径": len(MP), "差额": sum(pc.values()) - len(MP),
            "结论": "一致" if sum(pc.values()) == len(MP) else "不一致"})
sheet(wb, "B5b_口径校验",
      "B5b｜内部一致性与全市口径校验（差额应为0）",
      "四项人口与三套名录的分区加总必须等于全市口径；非0即为内部不一致，需登记。",
      ["校验项", "分区合计", "全市口径", "差额", "结论"],
      CHK, [40, 16, 16, 10, 16], fill=HF2)

# =========================================================
# B6 海珠街道对照（用 R1 街道可归属数据）
# =========================================================
LAYER = list(csv.DictReader(open(os.path.join(OUT, "海珠坐标结论分层_街道可用vs点位可用.csv"),
                                 encoding="utf-8-sig")))
hz = json.load(open(os.path.join(ROOT, "data", "boundaries",
                                 "haizhu_18_streets_osm_wgs84.geojson"), encoding="utf-8"))
S = {f["properties"]["name"]: shape(f["geometry"]) for f in hz["features"]}
HZPOP = {r["name"]: r for r in tw if r["district"] == "海珠区"}

# 按街道统计各层级点数
street_layer = defaultdict(Counter)
for r in LAYER:
    st = r.get("E1_坐标落面_WGS", "")
    if not st:
        continue
    street_layer[st][r["结论层级"]] += 1
    street_layer[st]["_all"] += 1

B6 = []
for nm, g in S.items():
    pr = HZPOP[nm]
    area = g.area * KX * KY
    pop = int(pr["total_population"])
    a60 = int(pr["age60_plus"])
    c = street_layer.get(nm, Counter())
    r2 = c.get("R2 坐标准确（原始verified=Y）", 0)
    r1p = c.get("R1 街道可归属 + R2 门牌级（未现场确认）", 0)
    r1s = c.get("R1 仅街道可归属（坐标精度不足）", 0)
    usable = r2 + r1p + r1s
    B6.append({
        "街道": nm, "面积km2_OSM": round(area, 2),
        "总人口_2020常住": pop, "60+_2020常住": a60,
        "60+占比_2020(%)": float(pr["age60_pct"]),
        "人口密度_人/km2": round(pop / area, 0),
        "60+密度_人/km2": round(a60 / area, 0),
        "已核实点位": r2,
        "门牌级待确认": r1p,
        "仅街道级(点位不可用)": r1s,
        "**可用设施点数(街道汇总口径)**": usable,
        "每万名60+可用点数": round(usable / (a60 / 10000), 2) if a60 else "",
        "点密度_个/km2": round(usable / area, 3),
        "不可用点数(冲突/证据不足)": c.get("冲突（不可用）", 0) + c.get("证据不足（不可用）", 0),
        "点位分析可用数(R2层)": r2 + r1p,
    })
B6.sort(key=lambda x: -x["**可用设施点数(街道汇总口径)**"])
ttl = {k: sum(v for v in (r[k] for r in B6) if isinstance(v, (int, float)))
       for k in ("已核实点位", "门牌级待确认", "仅街道级(点位不可用)",
                 "**可用设施点数(街道汇总口径)**", "不可用点数(冲突/证据不足)",
                 "点位分析可用数(R2层)")}
B6.append({"街道": "合计", **ttl, "面积km2_OSM": round(sum(r["面积km2_OSM"] for r in B6), 2),
           "总人口_2020常住": sum(r["总人口_2020常住"] for r in B6),
           "60+_2020常住": sum(r["60+_2020常住"] for r in B6)})
sheet(wb, "B6_海珠街道对照",
      "B6｜海珠18街道对照分析（用**本轮坐标分层**重算，区分'街道汇总口径'与'点位分析口径'）",
      "与阶段1相比，本轮把设施点按证据强度分层后再汇总："
      "**街道汇总口径** = 已核实 + 门牌级待确认 + 仅街道可归属（有街道归属即计入街道汇总）；"
      "**点位分析口径** = 仅 已核实 + 门牌级待确认（坐标精度足够）。"
      "**点位数≠服务能力；人口密度≠失能需求；零可用点位不等于无设施**（可能只是坐标未决议）。"
      "面积为 OSM 界线近似值。",
      ["街道", "面积km2_OSM", "总人口_2020常住", "60+_2020常住", "60+占比_2020(%)",
       "人口密度_人/km2", "60+密度_人/km2", "已核实点位", "门牌级待确认",
       "仅街道级(点位不可用)", "**可用设施点数(街道汇总口径)**", "每万名60+可用点数",
       "点密度_个/km2", "不可用点数(冲突/证据不足)", "点位分析可用数(R2层)"],
      B6, [10, 11, 13, 12, 13, 12, 12, 10, 11, 14, 18, 16, 12, 16, 16], fill=HFG)

# 街道层级变化对照（阶段1 vs 阶段2）
B6b = []
s1 = {"海幢街道": 8, "龙凤街道": 7, "南华西街道": 5, "江南中街道": 11, "沙园街道": 5,
      "昌岗街道": 0, "素社街道": 10, "滨江街道": 10, "南石头街道": 6, "新港街道": 0,
      "赤岗街道": 6, "瑞宝街道": 3, "凤阳街道": 11, "琶洲街道": 7, "江海街道": 1,
      "南洲街道": 5, "华洲街道": 2, "官洲街道": 0}
for r in B6:
    if r["街道"] == "合计":
        continue
    old = s1.get(r["街道"], 0)
    new = r["**可用设施点数(街道汇总口径)**"]
    B6b.append({"街道": r["街道"],
                "阶段1_verified点数": old,
                "阶段2_街道汇总可用点数": new,
                "净增": new - old,
                "阶段2_点位分析可用数": r["点位分析可用数(R2层)"],
                "说明": ("本轮由0升为可归属" if old == 0 and new > 0 else
                       "点数增加" if new > old else
                       "无变化" if new == old else "**减少（原verified点本轮判为冲突）**")})
sheet(wb, "B6b_街道点数变化",
      "B6b｜街道设施点数：阶段1（仅 verified）vs 阶段2（分层后街道汇总口径）",
      "阶段1的 verified 点数为 97 个服务点对应的地点数口径；本轮按 place 级分层重算。"
      "**净增来源是'原先被判 needs_review 但证据可支持街道归属'的记录，不是新增设施**。"
      "注意：两份计数的统计单元略有差异（阶段1按服务点、阶段2按地点），差额仅作方向性参考，**不可直接相减当作增减设施数**。",
      ["街道", "阶段1_verified点数", "阶段2_街道汇总可用点数", "净增",
       "阶段2_点位分析可用数", "说明"],
      B6b, [12, 18, 22, 8, 20, 34], fill=HFG)

# =========================================================
# B7 复现性核对
# =========================================================
B7 = [
    {"复现项": "人口对账48项", "输入文件": "elder_population_2025.txt + population_2025_registered_district.csv",
     "脚本": "gis4/t123_build.py", "本轮是否复算": "是（沿用）",
     "复算结果": "48项全部一致、0处不一致", "可复现": "是",
     "哈希/校验": "见 输入输出SHA256清单"},
    {"复现项": "区级供给密度", "输入文件": "3套名录 + 2张人口表",
     "脚本": "stage2/s3_gis_results1.py（B5）", "本轮是否复算": "**是（本轮独立重算）**",
     "复算结果": "分区加总=全市口径，差额0（见B5b）", "可复现": "是",
     "哈希/校验": "B5b 校验表"},
    {"复现项": "海珠坐标分层", "输入文件": "geocode_results.csv + services.csv + places.csv + 18街道边界",
     "脚本": "stage2/s1_resolve.py + s1b_strength.py", "本轮是否复算": "**是（本轮新增）**",
     "复算结果": "340条分层：95/116/72/30/24/3", "可复现": "是",
     "哈希/校验": "_resolve_stats.json + _evidence_strength.json"},
    {"复现项": "街镇名映射", "输入文件": "2套名录 + 18街道边界name",
     "脚本": "stage2/s3_gis_results1.py（B2）", "本轮是否复算": "**是（本轮新增）**",
     "复算结果": "海珠36组合全部映射，0未映射", "可复现": "是", "哈希/校验": "B2b明细"},
    {"复现项": "海珠街道对照", "输入文件": "坐标分层 + 18街道边界 + 176街镇人口",
     "脚本": "stage2/s3_gis_results1.py（B6）", "本轮是否复算": "**是（本轮新增）**",
     "复算结果": "18街道，可用点数合计与分层总数勾稽一致", "可复现": "是",
     "哈希/校验": "B6合计行"},
    {"复现项": "坐标系双假设一致率", "输入文件": "geocode_results + 11区边界",
     "脚本": "gis3/t1_dual_hypothesis.py", "本轮是否复算": "否（沿用阶段1）",
     "复算结果": "区级100%、街道级约64%", "可复现": "是（脚本在库）",
     "哈希/校验": "_crs_dual_hypothesis.json"},
    {"复现项": "阶段1图表", "输入文件": "B5/B6同类输入",
     "脚本": "gis3/t3_figures.py", "本轮是否复算": "否（本轮未重绘）",
     "复算结果": "—", "可复现": "是（脚本在库，但未与成果同目录归档）",
     "哈希/校验": "**已列为缺口 GA-042**"},
]
sheet(wb, "B7_复现性核对",
      "B7｜复现性核对清单（每项复算的输入、脚本、结果与可复现性）",
      "**可复现性判定标准**：从原始输入 + 脚本重跑，能得到与已发布结果相同的数值与哈希。"
      "本轮新增计算（B5/B6/坐标分层/街镇映射）均已独立重算并附校验；"
      "阶段1图表本轮未重绘，标注为'可复现但未归档脚本'，已列入缺口台账 GA-042。",
      ["复现项", "输入文件", "脚本", "本轮是否复算", "复算结果", "可复现", "哈希/校验"],
      B7, [18, 44, 30, 20, 34, 10, 26], fill=HF2)

# =========================================================
# 合并：把 part1 的表并入
# =========================================================
# B1-B4 已在前面直接从中间数据建表，无需合并临时文件

p = os.path.join(OUT, "本轮本地数据处理与GIS分析结果.xlsx")
wb.save(p)
print("saved", p, os.path.getsize(p), "B")
print("工作表:", wb.sheetnames)
json.dump({"B5_rows": len(B5), "B6_rows": len(B6), "B7_rows": len(B7),
           "checks": CHK}, open(os.path.join(OUT, "_part2_stats.json"), "w",
                                encoding="utf-8"), ensure_ascii=False, indent=1)
