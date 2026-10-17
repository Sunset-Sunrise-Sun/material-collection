# -*- coding: utf-8 -*-
"""P0-3 尝试获取官方原文（结果公告 + 部门预算PDF + 承接主体变更公告）
成功则落盘并记 SHA-256；失败则如实记为"未取得"并记录失败原因与尝试时间。
注意：仅针对本任务点名的 URL 做定向获取，不做泛化搜索。
"""
import hashlib
import json
import os
import ssl
import time
import urllib.error
import urllib.request

ROOT = r"D:\筑工杯数据获取"
OUTP = os.path.join(ROOT, "_work_probe", "p0", "_evidence_try")
os.makedirs(OUTP, exist_ok=True)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
PROXY = "http://127.0.0.1:7890"
opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
    urllib.request.HTTPSHandler(context=CTX),
)
HDR = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

TARGETS = [
    ("P03_结果公告_中国政府采购网",
     "http://www.ccgp.gov.cn/cggg/dfgg/zbgg/202609/t20260920_27366941.htm",
     "p03_ccgp_result.html"),
    ("部门预算PDF_民政局2026",
     "https://mzj.gz.gov.cn/attachment/7/7971/7971615/10684047.pdf",
     "mzj_2026_budget.pdf"),
    ("P03_第三方镜像_yfbzb",
     "https://www.yfbzb.com/winbid/detail/20260920_632960196.html",
     "p03_yfbzb_mirror.html"),
    ("平安通承接主体变更_民政局动态列表",
     "https://mzj.gz.gov.cn/dt/index.html",
     "mzj_dt_list.html"),
]

RESULT = []
for lab, url, fn in TARGETS:
    print("=" * 100)
    print("### %s" % lab)
    print("  URL:", url)
    t0 = time.time()
    rec = {"label": lab, "url": url, "saved_name": fn, "ok": False,
           "attempted_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    try:
        req = urllib.request.Request(url, headers=HDR)
        with opener.open(req, timeout=45) as r:
            data = r.read()
            code = r.status
            ctype = r.headers.get("Content-Type", "")
            clen = r.headers.get("Content-Length", "")
        print("  HTTP:", code, "| Content-Type:", ctype, "| 声明长度:", clen)
        print("  实际字节:", len(data))
        h = hashlib.sha256(data).hexdigest().upper()
        p = os.path.join(OUTP, fn)
        with open(p, "wb") as f:
            f.write(data)
        rec.update({"ok": True, "http": code, "content_type": ctype,
                    "bytes": len(data), "sha256": h,
                    "saved_path": os.path.relpath(p, ROOT),
                    "elapsed_s": round(time.time() - t0, 2)})
        print("  SHA256:", h)
        # 内容抽查
        head = data[:1200]
        try:
            txt = head.decode("utf-8", "ignore")
        except Exception:
            txt = ""
        if "html" in ctype.lower() or b"<html" in data[:500].lower():
            import re
            # 提取 title
            m = re.search(r"<title>(.*?)</title>", data.decode("utf-8", "ignore"),
                          re.S | re.I)
            title = m.group(1).strip() if m else "(无 title)"
            print("  页面标题:", title[:120])
            for kw in ("平安通", "CZ2026-1278", "珠江家园", "83", "10,017,000",
                       "30,051,000", "中标", "折扣"):
                if kw in data.decode("utf-8", "ignore"):
                    print("    命中关键词:", kw)
        elif data[:4] == b"%PDF":
            print("  → 有效 PDF（文件头 %PDF）")
        rec["preview"] = txt[:200].replace("\n", " ")
    except urllib.error.HTTPError as e:
        print("  **HTTP 错误:", e.code, e.reason)
        rec.update({"error": "HTTPError %s %s" % (e.code, e.reason),
                    "elapsed_s": round(time.time() - t0, 2)})
    except Exception as e:
        print("  **获取失败:", type(e).__name__, str(e)[:200])
        rec.update({"error": "%s: %s" % (type(e).__name__, str(e)[:200]),
                    "elapsed_s": round(time.time() - t0, 2)})
    RESULT.append(rec)

print()
print("=" * 100)
print("### 汇总")
for r in RESULT:
    print("  [%s] %-34s %s" % ("OK " if r["ok"] else "FAIL", r["label"],
                               ("%d B  %s" % (r["bytes"], r["sha256"][:24]))
                               if r["ok"] else r.get("error", "")[:80]))

json.dump(RESULT, open(os.path.join(OUTP, "_fetch_result.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print()
print("已保存:", os.path.join(OUTP, "_fetch_result.json"))
