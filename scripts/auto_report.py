#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股每日自动复盘 + 周末消息面精复盘
- 周一至周五 15:30：收盘复盘 + 次日预判
- 周六 15:30：周末消息汇总 + 下周展望
- 周日 15:30：精细化策略 + 下周交易计划
输出：Markdown 格式复盘报告 + 微信推送
"""

import os
import json
from datetime import datetime
from pathlib import Path

# ============================================================
# 配置（从 GitHub Secrets 读取）
# ============================================================
LLM_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN", "")

OUTPUT_DIR = Path(__file__).parent.parent / "reports"

# ============================================================
# 提示词
# ============================================================

SYSTEM_PROMPT = """你是A股短线复盘助手，风格对标「开盘啦一图复盘 + 同花顺涨停聚焦」。

铁律：
1. 只给结论，不给废话。每个板块不超过3句话。
2. 数据先行、逻辑直给。不写"可能""或许""关注"这类废话。
3. 涨停梯队、最强风口、情绪周期是核心，大盘点位是背景。
4. 输出长度为200-400字（手机一屏看完），精炼不啰嗦。
5. 拒绝长篇大论，拒绝四维分析框架，拒绝大段理论阐述。"""

USER_PROMPT = """## 任务：收盘极简复盘

日期：{date_str}（{weekday}）

请按以下5段格式输出，每段1-3句话，总字数200-400：

【涨停数据】
涨停X家（昨X家）| 跌停X家 | 炸板率X% | 封板率X% | 连板最高X板

【最强风口】
🔥 风口1：XX板块（X家涨停，龙头XX）
🔥 风口2：XX板块（X家涨停，龙头XX）
🔥 风口3：XX板块（X家涨停，龙头XX）
一句话：资金集中在XX方向，XX方向在退潮。

【涨停梯队】
X板：XX股（题材）| X板：XX股
X板：XX股、XX股
首板核心：XX、XX、XX
梯队判断：完整/断层，高位接力意愿强/弱

【情绪周期】
当前阶段：冰点/修复/主升/高潮/退潮/混沌
判断依据：连板高度X板，涨停X家，炸板率X%，昨日涨停今日表现
一句话：明天情绪看修复/看分歧/看退潮

【明日重点】
盯盘信号：XX板块集合竞价强弱
机会方向：1-2个具体方向+个股类型
风险提示：1个致命风险
仓位：X成（进攻X成/防守X成）"""

# ============================================================
# 周末提示词（周六：消息面快评）
# ============================================================

WEEKEND_SATURDAY_PROMPT = """## 任务：周末消息快评

日期：{date_str}（周六）| 本周最后交易日：{friday_str}

请按以下5段极简格式输出，总字数250-400：

【节前收官】
涨停X家 | 跌停X家 | 连板最高X板（XX股）| 炸板率X%
最强方向：XX（X家涨停），退潮方向：XX
一句话定性：X市X情绪，资金在XX抱团/出逃

【周末重磅】
🟢 利好①：一句话说清事件 → 利好哪个板块（1-2个标的类型）
🟢 利好②：同上
🔴 利空①：一句话说清 → 影响什么
只列有官方来源的，瞎编的直接跳过

【发酵题材】
题材①：XX（发酵程度：充分/正在/尚未）→ 周一预期：高开兑现/继续接力
题材②：同上
预期差方向：有什么利好还没被讨论到？

【下周一预判】
竞价看点：XX板块集合竞价量能，XX股的封单
情景①强势：什么信号 → 怎么做
情景②弱势：什么信号 → 怎么做
仓位建议：X成 | 止损线：上证破XX点

【一句话】
"周末消息面偏X，核心变量是XX，下周一预计X开后X，盯紧XX。" """

# ============================================================
# 周末提示词（周日：下周交易计划）
# ============================================================

WEEKEND_SUNDAY_PROMPT = """## 任务：下周作战计划

日期：{date_str}（周日）| 上个交易日：{friday_str}

请按以下5段极简格式输出，总字数250-400：

【周末舆情终判】
舆情温度：🔥X星（五星最热）
一致性预期：一致看多/多空分歧大/普遍观望
周末发酵最狠的方向：XX（一致性预期太强，周一大概率高开低走）
被低估的方向：XX（周末没怎么讨论，但逻辑硬）

【节前结构复盘】
涨停梯队：最高X板（XX股），梯队完整/断层
主线：XX（龙头XX，涨停X家，持续X天）
暗线：XX（悄悄在涨，散户还没发现）
退潮信号：XX方向开始坑人/还没退潮迹象
资金态度：游资积极/游资佛系/机构主导

【下周剧本推演】
情景①（概率X%）：什么信号 → 指数到哪 → 核心策略
情景②（概率X%）：什么信号 → 指数到哪 → 核心策略
情景③（概率X%）：什么信号 → 指数到哪 → 核心策略

【核心股票池】
列3-5个方向，每个方向给1-2个具体标的+关注逻辑（一句话）：

| 方向 | 标的参考 | 逻辑 | 买点区间 | 止损 |
|------|---------|------|---------|------|
（表内每列一句话）

【交易纪律】
仓位上限：X成 | 单票上限：X成 | 单日亏损上限：X%
无条件撤退信号：
1. XX
2. XX

【一句话】
"下周看X，周初X，核心变量是XX，策略：XX。" """

# ============================================================
# 核心函数
# ============================================================

def call_deepseek(system_prompt: str, user_prompt: str) -> str:
    """调用 DeepSeek API 生成复盘报告"""
    try:
        import openai
        
        client = openai.OpenAI(
            api_key=LLM_API_KEY,
            base_url="https://api.deepseek.com/v1",
        )
        
        print("📡 正在调用 DeepSeek API 生成报告...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=1500,
        )
        
        content = response.choices[0].message.content
        print("✅ DeepSeek API 调用成功")
        return content
    
    except Exception as e:
        error_msg = f"# 报告生成失败\n\n错误：{str(e)}\n\n请检查 DEEPSEEK_API_KEY 是否正确。"
        print(f"❌ API 调用失败：{e}")
        return error_msg


def format_for_wechat(md_content: str) -> str:
    """将 Markdown 格式转换为微信可读的纯文本格式"""
    import re
    
    text = md_content
    
    # 1. 去掉代码块
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    # 2. 表格转为缩进列表
    lines = text.split('\n')
    result = []
    in_table = False
    table_header = []
    table_rows = []
    last_was_table = False
    
    for line in lines:
        stripped = line.strip()
        
        # 检测表格行
        if stripped.startswith('|') and stripped.endswith('|'):
            if not in_table:
                in_table = True
                table_header = []
                table_rows = []
            
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            
            # 跳过分隔行
            if all(re.match(r'^[-: ]+$', c) for c in cells):
                continue
            
            if not table_header:
                table_header = cells
            else:
                table_rows.append(cells)
            continue
        
        # 表格结束，输出格式化表格
        if in_table and not stripped.startswith('|'):
            in_table = False
            if table_header and table_rows:
                for row in table_rows:
                    row_text = ' · '.join(
                        f"{table_header[i] if i < len(table_header) else ''}：{row[i] if i < len(row) else ''}"
                        for i in range(min(len(table_header), len(row)))
                    )
                    result.append('  ' + row_text)
            result.append('')
            table_header = []
            table_rows = []
            last_was_table = True
        
        # 3. 标题：### → 【】, ## → ▎, # → 去掉
        if stripped.startswith('#### '):
            result.append('')
            result.append('▸ ' + stripped[5:])
            result.append('')
        elif stripped.startswith('### '):
            result.append('')
            result.append('【' + stripped[4:] + '】')
            result.append('')
        elif stripped.startswith('## '):
            result.append('')
            result.append('━━━ ' + stripped[3:] + ' ━━━')
            result.append('')
        elif stripped.startswith('# '):
            result.append('')
            result.append('◆ ' + stripped[2:] + ' ◆')
            result.append('')
        
        # 4. 分隔线跳过
        elif stripped in ('---', '--- ', '***', '---'):
            result.append('')
        
        # 5. 引用块
        elif stripped.startswith('> '):
            result.append('  「' + stripped[2:] + '」')
        
        # 6. 列表项
        elif re.match(r'^[\-\*]\s', stripped):
            result.append('  • ' + re.sub(r'^[\-\*]\s+', '', stripped))
        
        # 7. 数字列表
        elif re.match(r'^\d+\.\s', stripped):
            result.append('  ' + stripped)
        
        # 8. 粗体：去掉 ** 标记
        else:
            line_text = re.sub(r'\*\*(.*?)\*\*', r'【\1】', stripped)
            # 斜体：去掉
            line_text = re.sub(r'\*(.*?)\*', r'\1', line_text)
            # 行内代码
            line_text = re.sub(r'`(.*?)`', r'\1', line_text)
            if line_text.strip():
                result.append(line_text)
            else:
                result.append('')
    
    # 9. 清理多余空行
    clean = []
    prev_empty = False
    for line in result:
        is_empty = not line.strip()
        if is_empty and prev_empty:
            continue
        clean.append(line)
        prev_empty = is_empty
    
    return '\n'.join(clean)


def push_wechat(title: str, content: str) -> bool:
    """通过 PushPlus 推送到微信"""
    if not PUSHPLUS_TOKEN:
        print("⚠️ 未配置 PUSHPLUS_TOKEN，跳过推送")
        return False
    
    try:
        import requests
        
        # 格式化 Markdown 为微信可读格式
        formatted = format_for_wechat(content)
        
        # 截取（微信限制约4000字符）
        if len(formatted) > 3800:
            send_content = formatted[:3800] + "\n\n…（完整报告见 GitHub）"
        else:
            send_content = formatted
        
        url = "https://www.pushplus.plus/send"
        data = {
            "token": PUSHPLUS_TOKEN,
            "title": title,
            "content": send_content,
            "channel": "wechat"
        }
        
        resp = requests.post(url, json=data, timeout=15)
        result = resp.json()
        
        if result.get("code") == 200:
            print("✅ 微信推送成功")
            return True
        else:
            print(f"⚠️ 微信推送失败：{result}")
            return False
    
    except Exception as e:
        print(f"⚠️ 微信推送异常：{e}")
        return False


def save_report(content: str, date_str: str) -> Path:
    """保存报告到文件"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"report_{date_str}.md"
    filepath = OUTPUT_DIR / filename
    
    now = datetime.now()
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# A 股收盘复盘报告\n")
        f.write(f"> 生成时间：{now.strftime('%Y-%m-%d %H:%M:%S')}（GitHub Actions 自动生成）\n\n")
        f.write(content)
    
    print(f"✅ 报告已保存：{filepath}")
    return filepath


def main():
    now = datetime.now()
    weekday = now.weekday()  # 0=周一 ... 5=周六 6=周日
    
    date_str = now.strftime("%Y%m%d")
    date_cn = now.strftime("%Y年%m月%d日")
    weekdays_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday_cn = weekdays_cn[weekday]
    
    # 检查配置
    if not LLM_API_KEY:
        print("❌ 未配置 DEEPSEEK_API_KEY，请在 GitHub Secrets 中设置")
        return
    
    # 选择提示词：周六/周日用周末模板，周一到周五用日常模板
    if weekday == 5:  # 周六
        print(f"📅 {date_cn} 周六 — 周末消息面精复盘")
        # 计算本周五的日期
        friday = now
        # weekday=5 是周六，往前推1天就是周五
        from datetime import timedelta
        friday = now - timedelta(days=1)
        friday_str = friday.strftime("%Y年%m月%d日")
        user_prompt = WEEKEND_SATURDAY_PROMPT.format(
            date_str=date_cn, weekday=weekday_cn, friday_str=friday_str
        )
        title = f"📡 周末消息精复盘 {date_cn}"
        
    elif weekday == 6:  # 周日
        print(f"📅 {date_cn} 周日 — 下周交易计划精复盘")
        from datetime import timedelta
        friday = now - timedelta(days=2)
        friday_str = friday.strftime("%Y年%m月%d日")
        user_prompt = WEEKEND_SUNDAY_PROMPT.format(
            date_str=date_cn, weekday=weekday_cn, friday_str=friday_str
        )
        title = f"🎯 下周交易计划 {date_cn}"
        
    else:  # 周一至周五
        print(f"🚀 {date_cn} {weekday_cn} — 收盘复盘 + 次日预判")
        user_prompt = USER_PROMPT.format(date_str=date_cn, weekday=weekday_cn)
        title = f"📈 A股复盘 {date_cn} {weekday_cn}"
    
    # 生成报告
    report = call_deepseek(SYSTEM_PROMPT, user_prompt)
    
    # 保存报告
    filepath = save_report(report, date_str)
    
    # 推送到微信
    push_wechat(title, report)
    
    print(f"🎉 全部完成！报告路径：{filepath}")


if __name__ == "__main__":
    main()
