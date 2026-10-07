#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
个股利好/利空提取器（对标「个股利好提取器 v1.3」核心逻辑）
- 抓取财经快讯（东方财富 / 同花顺 / 新浪财经）
- 用全量 A 股代码表做名称匹配（含常见简称别名）
- 按利好五级（L5-L1）/ 利空三级（N3-N1）关键词规则评级
- 输出精简的「个股利好/利空」清单文本，供盘前简报注入

本模块可独立运行：python scripts/fetch_stock_news.py
"""
import os
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

# ============================================================
# 评级关键词（利好五级 / 利空三级）
# ============================================================

# 利好五级（红，越高级越硬）
BENEFIT_KEYWORDS = {
    "L5": [  # 硬利好：订单落地 / 已实施增持回购 / 确定分红
        "中标", "签订合同", "签署协议", "订单", "已回购", "已增持", "回购完成", "增持完成",
        "确定分红", "派发现金红利", "分红方案", "获得订单", "重大项目签约", "中标公示",
    ],
    "L4": [  # 准硬利好：量产 / 交付 / 获批 / 投产
        "量产", "交付", "获批", "投产", "获得批文", "通过认证", "上市销售", "取得注册证",
        "首台套", "完成交付", "开始量产", "商业化",
    ],
    "L3": [  # 强催化：扩产投资 / 定增合资 / 拟回购拟增持
        "扩产", "投资建设", "定增", "增资", "合资", "拟回购", "拟增持", "回购计划", "增持计划",
        "新建产线", "产能扩建", "战略投资", "增资扩股", "回购股份", "增持股份",
    ],
    "L2": [  # 软利好：合作融资 / 经营改善 / 产品发布上线
        "合作", "融资", "签约", "战略合作", "产品发布", "上线", "业绩预增", "扭亏", "经营改善",
        "新品", "达成合作", "签署合作", "发布新品", "预增", "业绩增长",
    ],
    "L1": [  # 传闻预期：传闻 / 据悉 / 有望 / 拟 / 计划
        "传闻", "据悉", "有望", "拟", "计划", "或将", "预计", "考虑",
    ],
}

# 利空三级（暗红，越深越严重）
RISK_KEYWORDS = {
    "N3": [  # 重大利空：立案调查 / 退市风险 / 股权冻结 / 实控人被查
        "立案调查", "退市风险", "股权冻结", "实控人被查", "被立案", "强制退市", "重大违法",
        "被证监会立案", "涉嫌", "实控人",
    ],
    "N2": [  # 实质利空：减持 / 警示函 / 处罚 / 业绩暴雷 / 合作终止
        "减持", "警示函", "处罚", "业绩暴雷", "预亏", "亏损", "终止合作", "终止协议", "商誉减值",
        "违约", "下调评级", "业绩下滑", "被警示", "责令改正",
    ],
    "N1": [  # 软利空：小比例减持 / 常规问询函
        "问询函", "关注函", "小比例减持", "监管函",
    ],
}

# 常见简称别名（快讯里常写简称，代码表里是全称）
ALIAS_MAP = {
    "茅台": "贵州茅台", "宁德": "宁德时代", "中石油": "中国石油", "中石化": "中国石化",
    "比亚迪": "比亚迪", "隆基": "隆基绿能", "通威": "通威股份", "阳光电源": "阳光电源",
    "中信证券": "中信证券", "万科": "万科A", "保利": "保利发展", "招商银行": "招商银行",
    "中国平安": "中国平安", "平安": "中国平安", "招行": "招商银行", "工行": "工商银行",
    "建行": "建设银行", "农行": "农业银行", "中行": "中国银行", "交行": "交通银行",
    "五粮液": "五粮液", "泸州老窖": "泸州老窖", "山西汾酒": "山西汾酒",
    "中芯国际": "中芯国际", "中芯": "中芯国际", "海光": "海光信息", "寒武纪": "寒武纪",
    "长电": "长电科技", "三安": "三安光电", "北方华创": "北方华创", "中微": "中微公司",
    "药明": "药明康德", "恒瑞": "恒瑞医药", "迈瑞": "迈瑞医疗",
    "立讯": "立讯精密", "歌尔": "歌尔股份", "蓝思": "蓝思科技",
    "三一": "三一重工", "徐工": "徐工机械", "中联": "中联重科",
    "潍柴": "潍柴动力", "中国神华": "中国神华", "陕西煤业": "陕西煤业",
    "中远海控": "中远海控", "上港": "上港集团", "宁波港": "宁波港",
    "中国建筑": "中国建筑", "中国中铁": "中国中铁", "中国铁建": "中国铁建",
    "中国交建": "中国交建", "中国电建": "中国电建", "中国能建": "中国能建",
    "中国中免": "中国中免", "伊利": "伊利股份", "蒙牛": "蒙牛乳业",
    "海尔": "海尔智家", "美的": "美的集团", "格力": "格力电器",
    "万科A": "万科A", "金地": "金地集团", "招商蛇口": "招商蛇口",
    "中国船舶": "中国船舶", "中国重工": "中国重工", "中船": "中国船舶",
}


# ============================================================
# 快讯抓取
# ============================================================

def _fetch_eastmoney_news():
    """东方财富快讯（web_724 财经快讯）"""
    items = []
    try:
        url = ("https://np-listapi.eastmoney.com/comm/web/getFastNewsList"
               "?client=web&biz=web_724&fastColumn=102&sortEnd=&pageSize=50&req_trace=1")
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json().get("data", {})
        lst = data.get("fastNewsList", []) or []
        for it in lst:
            title = (it.get("title") or "").strip()
            summary = (it.get("summary") or "").strip()
            if title:
                items.append(title + ("。" + summary if summary else ""))
    except Exception:
        pass
    return items


def _fetch_10jqka_news():
    """同花顺快讯"""
    items = []
    try:
        r = requests.get(
            "https://news.10jqka.com.cn/tapp/news/push/stock/?page=1",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=10,
        )
        data = json.loads(r.text)
        lst = data.get("data", {}).get("list", []) or data.get("data", [])
        if isinstance(lst, list):
            for it in lst[:30]:
                title = (it.get("title", "") or it.get("digest", "") or "").strip()
                if title:
                    items.append(title)
    except Exception:
        pass
    return items


def _fetch_sina_news():
    """新浪财经快讯"""
    items = []
    try:
        r = requests.get(
            "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&k=&num=30&page=1",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=10,
        )
        lst = r.json().get("result", {}).get("data", []) or []
        if isinstance(lst, list):
            for it in lst:
                title = (it.get("title", "") or it.get("intro", "") or "").strip()
                if title:
                    items.append(title)
    except Exception:
        pass
    return items


# ============================================================
# 代码表加载 + 名称匹配
# ============================================================

_CODE_TABLE = None  # 缓存


def _load_code_table():
    """加载全量 A 股代码表 {名称: 代码}"""
    global _CODE_TABLE
    if _CODE_TABLE is not None:
        return _CODE_TABLE

    mapping = {}

    # 1. 优先用 akshare 拉全量
    try:
        import akshare as ak
        df = ak.stock_info_a_code_name()
        for _, row in df.iterrows():
            name = str(row.get("name", "")).strip()
            code = str(row.get("code", "")).strip()
            # 清洗：去空格、全角转半角
            name_clean = name.replace(" ", "").replace("\u3000", "")
            name_clean = name_clean.replace("Ａ", "A").replace("Ｂ", "B").replace("Ｈ", "H")
            if name_clean and code:
                mapping[name_clean] = code
                # 去掉"股份"等后缀再补一个键，便于快讯简称匹配
                # 剩余长度须 >= 3，避免"开发"、"日上"等短词误匹配
                for suf in ["有限公司", "股份", "集团", "科技", "控股"]:
                    if name_clean.endswith(suf) and len(name_clean) - len(suf) >= 3:
                        mapping[name_clean[: -len(suf)]] = code
    except Exception:
        pass

    # 2. 合并常见别名
    for alias, full in ALIAS_MAP.items():
        if full in mapping:
            mapping[alias] = mapping[full]

    _CODE_TABLE = mapping
    return mapping


def _match_stock(text, mapping):
    """返回文本中命中的 [(名称, 代码)]，按名称长度降序（优先长名精确匹配）。

    规则：长度 >= 3 的名称正常匹配；长度 == 2 的仅匹配 ALIAS_MAP 精选别名，
    避免短词（"开发"/"日上"等）误命中。
    """
    hits = []
    alias_keys = set(ALIAS_MAP.keys())
    # 名称按长度降序，避免"平安"误吞"中国平安"
    names = sorted(mapping.keys(), key=len, reverse=True)
    for name in names:
        if len(name) < 2:
            continue
        if len(name) == 2 and name not in alias_keys:
            continue
        if name in text:
            hits.append((name, mapping[name]))
    # 去重（同一代码只保留一次，保留最长名称）
    seen = {}
    for name, code in hits:
        if code not in seen:
            seen[code] = name
    return [(name, code) for code, name in seen.items()]


# ============================================================
# 评级
# ============================================================

def _rate(text):
    """对单条快讯文本评级，返回 (type, level) 或 None；type ∈ {利好, 利空}"""
    # 先判利空（严重优先）
    for level in ["N3", "N2", "N1"]:
        for kw in RISK_KEYWORDS[level]:
            if kw in text:
                return ("利空", level)
    # 再判利好（硬优先）
    for level in ["L5", "L4", "L3", "L2", "L1"]:
        for kw in BENEFIT_KEYWORDS[level]:
            if kw in text:
                return ("利好", level)
    return None


# ============================================================
# 主入口
# ============================================================

def fetch_stock_news(max_items: int = 30) -> str:
    """
    提取个股利好/利空，返回精简文本清单。
    失败时返回空字符串（调用方据此静默降级）。
    """
    # 1. 抓快讯
    news = []
    news += _fetch_eastmoney_news()
    news += _fetch_10jqka_news()
    news += _fetch_sina_news()
    # 去重保序
    seen = set()
    uniq = []
    for n in news:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    if not uniq:
        return ""

    # 2. 加载代码表
    mapping = _load_code_table()
    if not mapping:
        return ""

    # 3. 逐条匹配 + 评级
    benefit = {}   # code -> {name, level, sample}
    risk = {}      # code -> {name, level, sample}
    for text in uniq:
        r = _rate(text)
        if not r:
            continue
        typ, level = r
        hits = _match_stock(text, mapping)
        if not hits:
            continue
        for name, code in hits:
            # 排除 ST / 退市
            if "ST" in name or "退" in name:
                continue
            sample = text if len(text) <= 60 else text[:60] + "…"
            if typ == "利好":
                # 同股取更高优先级（L5 > L4 > ...）
                if code not in benefit or BENEFIT_LEVEL_ORDER[level] < BENEFIT_LEVEL_ORDER[benefit[code]["level"]]:
                    benefit[code] = {"name": name, "level": level, "sample": sample}
            else:
                if code not in risk or RISK_LEVEL_ORDER[level] < RISK_LEVEL_ORDER[risk[code]["level"]]:
                    risk[code] = {"name": name, "level": level, "sample": sample}

    # 利好利空互斥：命中利空的股票，从利好里剔除
    for code in list(benefit.keys()):
        if code in risk:
            del benefit[code]

    if not benefit and not risk:
        return ""

    # 4. 组装输出
    lines = []
    lines.append("【个股利好/利空提取】（规则抓取，仅供信息参考）")

    if benefit:
        # 按级别排序
        order = {"L5": 0, "L4": 1, "L3": 2, "L2": 3, "L1": 4}
        items = sorted(benefit.values(), key=lambda x: order.get(x["level"], 9))
        lines.append(f"利好 {len(items)} 条：")
        for it in items:
            lines.append(f"  {it['level']} {it['name']}({it['sample']})")
    if risk:
        order = {"N3": 0, "N2": 1, "N1": 2}
        items = sorted(risk.values(), key=lambda x: order.get(x["level"], 9))
        lines.append(f"利空 {len(items)} 条：")
        for it in items:
            lines.append(f"  {it['level']} {it['name']}({it['sample']})")

    return "\n".join(lines)


# 级别顺序常量（用于优先级比较）
BENEFIT_LEVEL_ORDER = {"L5": 0, "L4": 1, "L3": 2, "L2": 3, "L1": 4}
RISK_LEVEL_ORDER = {"N3": 0, "N2": 1, "N1": 2}


if __name__ == "__main__":
    print("=" * 50)
    print("个股利好/利空提取器（本地测试）")
    print("=" * 50)
    out = fetch_stock_news()
    if out:
        print(out)
    else:
        print("（无输出：快讯抓取失败或无个股命中）")
