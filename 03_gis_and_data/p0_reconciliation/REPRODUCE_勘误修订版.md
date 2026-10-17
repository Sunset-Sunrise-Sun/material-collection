# REPRODUCE 勘误修订版（P0-2）

**日期**：2026-10-17
**取代范围**：仅取代阶段二 `REPRODUCE.md` 中「四、复现结果核对点」表的相关行。
**原文件**：`03_gis_and_data/phase2_local_gis/REPRODUCE.md`（保留不改，作历史版本）

---

## 一、被更正的行

| 核对项 | 原 REPRODUCE.md | 更正为 | 说明 |
|---|---|---|---|
| 街道级可归属合计（R1+R2） | ~~91~~ | **283** | 91 是「新增多候选计数」，不是街道级总数 |
| 其中门牌级（R2） | ~~68~~ | 见下方两行 | 68 只是 91 子集中的门牌级部分 |
| 门牌粒度可用（含未确认候选） | — | **209** | = 93（verified 门址级）+ 116（未确认门牌候选） |
| 严格点位分析资格 | — | **93** | = 95 原始 verified − 2 条兴趣点层级（待核） |
| 新增多候选计数 | — | **91** | = 123 原多候选中通过一致性者 |

## 二、更正后的完整核对点

| 核对项 | 期望值 | 来源 |
|---|---|---|
| 坐标总记录 | **340** | `_p02_assert_v2.json` → counts.total |
| 原始 `verified=Y` 状态数 | **95** | counts.ver95 |
| 严格点位分析资格 | **93** | counts.strict93 |
| 其中不具严格资格（兴趣点层级） | **2**（P-2db0b22d、P-d227f901） | weak_verified_ids |
| **街道级可用总数** | **283** | counts.street283 |
| 门牌粒度可用（含未确认候选） | **209** | counts.door209 |
| 新增多候选计数 | **91** | counts.in91 |
| 原始 `n_candidates>1` | **125** | counts.n_gt1 |
| 其中有多候选且编码可用 | **123** | counts.n_gt1_ok |
| 其中多候选但编码不可用（落区外） | **2**（P-0bb41fec→白云、P-2f0f7abf→南沙） | counts.n_gt1_bad + bad_multi_detail |
| `verdict=failed` 总数 | **3**（含 P-45b4cccd：API 错误 30001、无坐标） | counts.failed |
| 六类互斥合计 | **340** | 95+116+72+30+24+3 |

## 三、关键关系（复现时须同时满足）

```text
283（街道级可用总数） ≠ 91（新增多候选计数）
 95（原始verified状态） ≠ 93（严格点位分析资格）
209（门牌粒度记录，含未确认） ≠ 209 个已核实服务点
125 = 123 + 2;   123 = 91 + 17 + 15
95 + 116 + 72 + 30 + 24 + 3 = 340
```

## 四、复现命令

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$py = '<python with openpyxl/shapely>'
& $py reproduce_scripts\p0_08_coordinate_cross_table_v2.py
& $py reproduce_scripts\p0_09_verify_review_claims.py
```

所需输入：`out/geocode_results.csv`、阶段二 `海珠坐标多证据批量核验明细.csv`、
`海珠坐标结论分层_街道可用vs点位可用.csv`。

## 五、注意

- 本次仅修订**定义与字段**，**未改变任何一条记录的分类**（0 条重新分类）。
- 原始 `verified=Y` 状态**未被修改**，95 条计数保持不变；
  「严格点位分析资格 93」是**新增的分析资格字段**，不是把 95 降级为 93。
- 仅街道级记录**不得**用于点位距离、缓冲区与米级结论。
