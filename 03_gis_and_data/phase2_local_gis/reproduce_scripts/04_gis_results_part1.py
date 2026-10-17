# -*- coding: utf-8 -*-
"""任务B：本地数据处理与 GIS 分析结果（可复算）
B1 坐标分层结果（本轮新增结论）
B2 街镇名标准化补全（全11区尝试）
B3 名录重复/同址/区划冲突逐项登记
B4 GIS 不确定性说明（坐标系/边界/归属）
B5 区级供给密度与人口结构（可复算，含双分母）
B6 海珠街道对照分析（用R1街道可归属数据重算）
B7 复现性核对（数值与公式可回溯）
"""
import csv
import json
import math
import os
from collections import Counter, defaultdict

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = r"D:\筑工杯数据获取"
B = os.path.join(ROOT, "筑工杯_旧数据_2026前期", "_baseline_current")
OUT = os.path.join(ROOT, "广州市AI养老研究_第二阶段_本地实证_20261017")
TODAY = "2026-10-17"

# ---------- 样式 ----------
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
    ws.row_dimensions[2].height = 56
    for j, c in enumerate(cols, 1):
        cell = ws.cell(row=4, column=j, value=c)
        cell.fill = fill or HF
        cell.font = WF
        cell.border = BD
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    ws.row_dimensions[4].height = 32
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


wb = openpyxl.Workbook()
wb.remove(wb.active)

# =========================================================
# B1 坐标分层结果
# =========================================================
LAYER = list(csv.DictReader(open(os.path.join(OUT, "海珠坐标结论分层_街道可用vs点位可用.csv"),
                                 encoding="utf-8-sig")))
lay_cnt = Counter(r["结论层级"] for r in LAYER)
B1 = [{"结论层级": k, "条数": v,
       "含义": {
           "R2 坐标准确（原始verified=Y）": "原始地理编码唯一且已核验，可用于点位与街道分析",
           "R1 街道可归属 + R2 门牌级（未现场确认）": "坐标与地址/名录同属一街道，且定位到门牌级；"
                                             "可用于街道汇总，点位需现场确认",
           "R1 仅街道可归属（坐标精度不足）": "可确认所属街道，但 geocode 层级为道路/小巷/住宅区等，"
                                    "**不可用于点位或距离分析**",
           "证据不足（不可用）": "坐标、地址文本、名录街道无一致指向；维持待核",
           "冲突（不可用）": "坐标落面与地址文本街道冲突；不得采信单侧",
           "无坐标/失败": "坐标为空或地理编码失败；保留原记录不删除",
       }.get(k, ""),
       "可用于街道级汇总": "是" if k.startswith(("R2", "R1")) else "否",
       "可用于点位/距离分析": "是" if k in ("R2 坐标准确（原始verified=Y）",
                                "R1 街道可归属 + R2 门牌级（未现场确认）") else "否",
       } for k, v in lay_cnt.most_common()]
sheet(wb, "B1_坐标分层结果",
      "B1｜海珠设施坐标：结论分层（区分'街道可归属'与'点位可用'）——本轮核心推进",
      "本轮对 340 条地理编码记录做**多证据批量核验**（E1坐标点面判定／E2双假设／E3地址文本街道／"
      "E4返回道路名／E5名录街道归属／E6匹配层级）。**关键纪律：多候选坐标不得因'街道一致'就升为'已核实'**；"
      "'已核实'仍只保留原始 verified=Y 的 95 条。本表把结论拆成两层：街道级可归属 vs 点位可用。",
      ["结论层级", "条数", "含义", "可用于街道级汇总", "可用于点位/距离分析"],
      B1, [42, 8, 68, 16, 18], fill=HF4)
print("B1:", dict(lay_cnt))

# =========================================================
# B2 街镇名标准化补全
# =========================================================
me = list(csv.DictReader(open(os.path.join(B, "data", "elder_meals_20250205.csv"),
                              encoding="utf-8-sig")))
mp = list(csv.DictReader(open(os.path.join(B, "data", "medical_primary_202311.csv"),
                              encoding="utf-8-sig")))
hz = json.load(open(os.path.join(ROOT, "data", "boundaries",
                                 "haizhu_18_streets_osm_wgs84.geojson"), encoding="utf-8"))
HZ_STREETS = [f["properties"]["name"] for f in hz["features"]]
CANON = {}
for nm in HZ_STREETS:
    CANON[nm] = nm
    CANON[nm.replace("街道", "街")] = nm
    CANON[nm.replace("街道", "")] = nm


def canon_hz(x):
    if not x:
        return ""
    x = str(x).strip()
    if x in CANON:
        return CANON[x]
    for c in (x, x + "街", x + "街道"):
        if c in CANON:
            return CANON[c]
    base = x[:-2] if x.endswith("街道") else (x[:-1] if x.endswith("街") else x)
    return base + "街道" if base + "街道" in HZ_STREETS else ""


B2 = []
for tag, recs in (("长者饭堂", me), ("基层医疗", mp)):
    for d in sorted({r["district"] for r in recs}):
        sub = [r for r in recs if r["district"] == d]
        raw = sorted({(r.get("township_raw") or "").strip() for r in sub if (r.get("township_raw") or "").strip()})
        mapped = [canon_hz(x) for x in raw]
        ok = sum(1 for m in mapped if m)
        B2.append({"名录": tag, "行政区": d, "记录数": len(sub),
                   "township_raw唯一值数": len(raw),
                   "可映射到海珠18街道标准名": ok if d == "海珠区" else 0,
                   "映射率": ("%d/%d" % (ok, len(raw))) if d == "海珠区" else "不适用（无该区街镇边界）",
                   "说明": ("海珠区有18街道边界，可完全映射" if d == "海珠区"
                          else "**该区无街镇边界，仅保留原始 township_raw，不做映射**")})
sheet(wb, "B2_街镇名标准化",
      "B2｜街镇名标准化结果（仅海珠区可映射到18街道；其他10区无边界）",
      "映射依据：haizhu_18_streets_osm_wgs84.geojson 的 name 字段（已与 2020 人口表 18/18 核对）。"
      "标准化规则：'XX街'/'XX街道'/'XX' → 'XX街道'，仅限海珠18街道名单。"
      "**其他10区因缺街镇边界，不做映射也不臆造标准名**，仅保留原始 township_raw 供后续补采时使用。",
      ["名录", "行政区", "记录数", "township_raw唯一值数", "可映射到海珠18街道标准名", "映射率", "说明"],
      B2, [12, 10, 10, 20, 22, 22, 60], fill=HF2)

# 明细：海珠 township_raw → 标准名
B2b = []
for tag, recs in (("长者饭堂", me), ("基层医疗", mp)):
    sub = [r for r in recs if r.get("district") == "海珠区"]
    cnt = Counter((r.get("township_raw") or "").strip() for r in sub)
    for raw, n in sorted(cnt.items()):
        B2b.append({"名录": tag, "原始街镇名": raw, "记录数": n,
                    "标准化街镇名": canon_hz(raw) or "**未映射**",
                    "映射方式": "直接匹配" if raw in CANON else "规则补全" if canon_hz(raw) else "无法映射"})
sheet(wb, "B2b_海珠映射明细",
      "B2b｜海珠区 township_raw → 标准街道名 逐项映射",
      "共 36 个（名录×街镇）组合；海珠18街道全覆盖。", 
      ["名录", "原始街镇名", "记录数", "标准化街镇名", "映射方式"],
      B2b, [12, 16, 10, 18, 14], fill=HF2)
print("B2: 海珠映射组合", len(B2b), "| 未映射", sum(1 for x in B2b if "未映射" in x["标准化街镇名"]))

# =========================================================
# B3 名录质量逐项登记
# =========================================================
EC = json.load(open(os.path.join(B, "data", "eldercare_20260923.json"), encoding="utf-8"))
ALIAS = {"荔湾": "荔湾区", "越秀": "越秀区", "海珠": "海珠区", "天河": "天河区",
         "白云": "白云区", "黄埔": "黄埔区", "番禺": "番禺区", "花都": "花都区",
         "南沙": "南沙区", "从化": "从化区", "增城": "增城区", "萝岗": "黄埔区"}


def infer_dist(a):
    f = sorted({v for k, v in ALIAS.items() if v in str(a)})
    return f[0] if len(f) == 1 else ("多区" if len(f) > 1 else "未识别")


def norm_addr(a):
    return "".join(str(a or "").replace("（", "(").replace("）", ")").split())


B3 = []
# 区划冲突
for r in EC:
    rep, inf = r.get("district_as_reported", ""), infer_dist(r.get("address_raw", ""))
    if rep and inf not in ("未识别", "多区") and rep != inf:
        B3.append({"类型": "区划归属冲突", "名录": "养老机构",
                   "记录ID": "YLJG-%03d" % r["source_id"], "名称": r.get("name", ""),
                   "原始值": "上报区=%s；地址推定区=%s" % (rep, inf),
                   "修订值": "**不修订**（无权威依据）",
                   "判定依据": "地址含其他区名；执业地 vs 登记地口径可能不同",
                   "置信状态": "待核", "处理": "保留原值并登记；建议向区民政局核实"})
# 同址
for tag, recs, namek, addrk, idfmt in (
        ("长者饭堂", me, "name", "address_raw", "FANT-%04d"),
        ("养老机构", EC, "name", "address_raw", "YLJG-%03d"),
        ("基层医疗", mp, "name", "address_raw", "JCYL-%03d")):
    g = defaultdict(list)
    for r in recs:
        a = norm_addr(r.get(addrk))
        if a and len(a) >= 8:
            g[a].append(r)
    for a, lst in g.items():
        if len(lst) > 1:
            ids = []
            for x in lst:
                try:
                    ids.append(idfmt % int(x.get("source_id", 0)))
                except Exception:
                    ids.append("?")
            B3.append({"类型": "同址多记录", "名录": tag, "记录ID": "/".join(ids),
                       "名称": "；".join(str(x.get(namek, ""))[:26] for x in lst),
                       "原始值": "地址=%s（%d条同址）" % (a[:60], len(lst)),
                       "修订值": "**不合并、不去重**",
                       "判定依据": "标准化地址完全一致，但服务主体名称不同",
                       "置信状态": "待核", "处理": "保留全部记录；建议现场核实是否同一场所多主体"})
# 基层医疗缺区名
mp_missing = [r for r in mp if infer_dist(r.get("address_raw", "")) == "未识别"]
B3.append({"类型": "地址缺区名", "名录": "基层医疗",
           "记录ID": "共%d条" % len(mp_missing), "名称": "（汇总登记）",
           "原始值": "地址文本不含任何区名",
           "修订值": "不修订",
           "判定依据": "仅能依上报区字段；无法用地址反推区",
           "置信状态": "已登记（不影响本轮区级计数）",
           "处理": "保留；建议补坐标或街道名"})
sheet(wb, "B3_名录质量登记",
      "B3｜名录重复 / 同址 / 区划归属冲突 逐项登记（只登记，不改值、不合并不去重）",
      "**纪律：任何一条都保留原始值，不做合并、不去重、不改上报区**；"
      "同址不必然等于重复（可能是不同服务主体共用场所）；区划冲突可能是执业地与登记地口径不同。",
      ["类型", "名录", "记录ID", "名称", "原始值", "修订值", "判定依据", "置信状态", "处理"],
      B3, [16, 12, 24, 34, 40, 26, 42, 20, 44], fill=HF3)
print("B3:", dict(Counter(x["类型"] for x in B3)))

# =========================================================
# B4 GIS 不确定性说明
# =========================================================
B4 = [
    {"不确定性维度": "11区边界坐标系", "当前状态": "**待验证**",
     "证据": "city_districts_datav.json 无 crs/EPSG；独立检验（334地铁站语义标签19/20 vs 18/20）无区分力；"
            "最优平移≈GCJ偏移但存'测绘差异'替代解释",
     "对分析的影响": "区级归属双假设一致率100% → 区级结论稳健；街道级一致率约64% → 街道级须并列",
     "本轮处理": "一律双假设并列报告；不宣称坐标系已确认",
     "可闭合路径": "①声明EPSG的官方区界 ②3个实测控制点 ③官方影像明显地物比对"},
    {"不确定性维度": "11区边界性质", "当前状态": "第三方整理（DataV）",
     "证据": "非官方勘定界线；11/11几何有效、无重叠、并集单部件",
     "对分析的影响": "不得作为官方界线发布",
     "本轮处理": "引用时标注来源与性质", "可闭合路径": "获取官方勘定界线"},
    {"不确定性维度": "天河区面积口径", "当前状态": "口径待核",
     "证据": "估算136.70 km² vs 常见陆域约96 km²（比值1.42）",
     "对分析的影响": "以面积为分母的密度指标对天河可能偏低",
     "本轮处理": "标注口径；密度类结果并列绝对量", "可闭合路径": "确认含水域/陆域口径"},
    {"不确定性维度": "海珠街道边界性质", "当前状态": "OSM 社区测绘（WGS-84）",
     "证据": "haizhu_18_streets_osm_wgs84.geojson；名称与人口表18/18核对；并集91.79 km²；"
            "与区界双向覆盖0.982/0.993，对称差约2.3 km²",
     "对分析的影响": "街道级面积/密度为近似值；边界附近点归属敏感",
     "本轮处理": "标注来源；边界带点位单独标记",
     "可闭合路径": "获取官方街道界线"},
    {"不确定性维度": "其他10区街镇边界", "当前状态": "**缺失**",
     "证据": "boundary_gist_2021 仅26要素/13具名/几何未校验，不可用",
     "对分析的影响": "**全市街镇级分析完全不可做**",
     "本轮处理": "不做全市街镇级任何排名或汇总",
     "可闭合路径": "定向获取10区街镇边界"},
    {"不确定性维度": "海珠设施坐标", "当前状态": "分层可用",
     "证据": "本轮多证据核验：已核实95／门牌级116／仅街道72／证据不足30／冲突24／无坐标3",
     "对分析的影响": "街道级汇总可用（≥289条有街道归属）；点位分析仅限门牌级且未现场确认",
     "本轮处理": "见 B1 分层表；点位分析只用R2层并标注未现场确认",
     "可闭合路径": "人工逐条决议剩余54条 + 抽样现场核验"},
    {"不确定性维度": "名录区划归属", "当前状态": "2条冲突 + 2组同址 + 44条缺区名",
     "证据": "B3 登记表",
     "对分析的影响": "区级计数可能有<1%误差",
     "本轮处理": "登记不改值；区级结论保留小数不四舍五入到个位",
     "可闭合路径": "向区民政局/执业登记核实"},
    {"不确定性维度": "跨年口径", "当前状态": "分子分母年份不同",
     "证据": "床位2026／饭堂2025-02／基层医疗2023-11 ÷ 人口2025户籍",
     "对分析的影响": "供给密度代理为跨年近似，非同期比率",
     "本轮处理": "逐列标注年份；并列2020常住分母做敏感度",
     "可闭合路径": "补采同期名录与人口"},
]
sheet(wb, "B4_GIS不确定性说明",
      "B4｜GIS 数据不确定性总说明（坐标系／边界／归属／坐标／口径）",
      "本表把每一类不确定性的**当前状态、证据、对分析的影响、本轮处理方式、可闭合路径**分列。"
      "**凡标'待验证'或'缺失'者，均不得在本轮结论中被当作已知。**",
      ["不确定性维度", "当前状态", "证据", "对分析的影响", "本轮处理", "可闭合路径"],
      B4, [20, 22, 56, 44, 40, 44], fill=HF4)

import pickle
pickle.dump({"B1": B1, "B2": B2, "B2b": B2b, "B3": B3, "B4": B4},
            open(os.path.join(OUT, "_part1_data.pkl"), "wb"))
print("B4 完成；中间数据已落盘 _part1_data.pkl")
json.dump({"B1": dict(lay_cnt), "B2": {"combos": len(B2b),
                                        "unmapped": sum(1 for x in B2b if "未映射" in x["标准化街镇名"])},
           "B3": dict(Counter(x["类型"] for x in B3))},
          open(os.path.join(OUT, "_part1_stats.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
