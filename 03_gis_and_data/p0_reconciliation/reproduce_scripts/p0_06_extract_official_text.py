# -*- coding: utf-8 -*-
"""精确重抽官方正文（id=zoomcon）+ 与第三方镜像交叉核对 + 生成证据清单"""
import hashlib
import json
import os
import re

ROOT = r"D:\筑工杯数据获取"
D = os.path.join(ROOT, "_work_probe", "p0", "_evidence_try")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest().upper()


def clean(s):
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?is)<br\s*/?>", "\n", s)
    s = re.sub(r"(?is)</(p|div|tr|td|h\d|li)>", "\n", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    s = s.replace("&ldquo;", "“").replace("&rdquo;", "”")
    s = re.sub(r"[ \t\u3000]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return "\n".join(x.strip() for x in s.split("\n") if x.strip())


print("=" * 104)
print("### 1 官方承接主体变更公告 —— 正文精确抽取")
p = os.path.join(D, "mzj_11045014_subject_change.html")
raw = open(p, "rb").read().decode("utf-8", "ignore")
m = re.search(r'(?is)<div class="content_article" id="zoomcon"[^>]*>(.*?)</div>', raw)
body_html = m.group(1) if m else ""
print("  正文容器命中:", bool(m), "| 原始HTML长度:", len(body_html))
text = clean(body_html)
print()
print("  --- 官方正文（逐行） ---")
for L in text.split("\n"):
    print("   ", L)
open(os.path.join(D, "mzj_11045014_官方正文.txt"), "w", encoding="utf-8").write(text)

# 标题与发布时间
mt = re.search(r'(?is)<h1 class="content_title"[^>]*>(.*?)</h1>', raw)
md = re.search(r'发布时间：<b>([^<]+)</b>', raw)
print()
print("  标题:", clean(mt.group(1)) if mt else "(未取)")
print("  发布时间:", md.group(1) if md else "(未取)")
print("  落款日期:", [L for L in text.split("\n") if "2026年10月" in L])

print()
print("=" * 104)
print("### 2 与第三方镜像交叉核对（关键事实）")
mirror = open(os.path.join(D, "p03_yfbzb_mirror.html"), "rb").read().decode("utf-8", "ignore")
mtxt = clean(mirror)
FACTS = [
    ("承接主体", "广州珠江家园健康养老服务有限公司"),
    ("起始日期", "2026年10月1日"),
    ("咨询电话", "020-62886288"),
    ("指导中心电话", "020-86088931"),
]
for lab, kw in FACTS:
    in_official = kw in text
    in_mirror = kw in mtxt
    print("  %-12s %-32s 官方正文:%-5s 第三方镜像:%s" % (
        lab, kw, "有" if in_official else "无", "有" if in_mirror else "无"))

print()
print("=" * 104)
print("### 3 P03 / 预算 / 变更公告 全部已获取原件清单")
FILES = [
    ("P03结果公告_中国政府采购网", "p03_ccgp_result.html", "A", "官方原文HTML（含预算、中标折扣、服务期、得分表）"),
    ("P03分项报价表_官方附件2", "att_p03_报价附件.pdf", "A", "官方附件：单价/数量/折扣/总价"),
    ("民政局2026部门预算", "mzj_2026_budget.pdf", "A", "官方PDF：1,795万元绩效项目预算数"),
    ("民政局2026部门预算_文本抽取", "mzj_2026_budget.txt", "派生", "由PDF提取，非来源原件"),
    ("承接主体变更公告_官方正文", "mzj_11045014_subject_change.html", "A", "官方页面原文（含正文）"),
    ("承接主体变更公告_正文抽取", "mzj_11045014_官方正文.txt", "派生", "由HTML提取"),
    ("承接主体变更公告_动态列表页", "mzj_dt_list.html", "A", "列表页，证明公告存在与日期"),
    ("P03结果公告_第三方镜像", "p03_yfbzb_mirror.html", "C", "第三方镜像，仅交叉核对，不替代官方"),
    ("P03结果公告_费用标准通知PDF", "att_8a7edc70a075148901a0be0fbae71943.pdf", "A", "广州市政采中心代理费收费标准通知"),
]
rows = []
for lab, fn, lvl, note in FILES:
    p2 = os.path.join(D, fn)
    if os.path.exists(p2):
        rows.append({"名称": lab, "文件": fn, "字节": os.path.getsize(p2),
                     "SHA256": sha(p2), "证据等级": lvl, "说明": note})
        print("  [%s] %11d B  %s  %s" % (lvl, os.path.getsize(p2), sha(p2)[:24], lab))
    else:
        print("  [缺失] %s" % lab)

json.dump(rows, open(os.path.join(D, "_evidence_manifest.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print()
print("已保存 _evidence_manifest.json")
