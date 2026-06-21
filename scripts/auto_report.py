#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股收盘后自动复盘 + 次日预判
每日 15:30（ GitHub Actions UTC 07:30 ）自动执行
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

SYSTEM_PROMPT = """你是一位拥有 15 年 A 股实战经验的量化交易分析师，擅长从量能、资金、技术面、情绪面四个维度进行短线条复盘分析。

风格要求：
- 数据驱动，每个结论有依据
- 短线条思维，关注 1-3 个交易日
- 理性冷静，不盲目乐观也不过度恐慌
- 可操作，给出明确次日策略

输出格式：Markdown，1500-2500 字，数据用表格，关键结论加粗。"""

USER_PROMPT = """## 任务：A 股收盘复盘 + 次日预判

**日期**：{date_str}（{weekday}）

---

### 一、今日大盘数据

请基于你的知识库和训练数据，对{date_str}的 A 股市场进行复盘分析。

若无法获取实时数据，请基于近期市场趋势和典型量价关系进行合理分析和预判。

#### 核心指数表现
请分析上证指数、深证成指、创业板指、科创50 的收盘表现和量能变化。

#### 市场情绪
请分析涨跌家数、涨停跌停数量、市场赚钱效应。

#### 资金流向
请分析北向资金动向、主力资金流向、热点板块资金进出。

#### 热点板块
请分析当日领涨板块和领跌板块，判断主线题材和发酵阶段。

---

### 二、四维量化分析

#### 量能分析
- 今日量能水平（放量/缩量/平量）
- 量价配合关系
- 与近 5 日均量对比
- **量能结论**

#### 技术面分析
- 主要指数是否站上 5/10/20 日线
- MACD / KDJ / RSI 状态
- 支撑位与压力位
- **技术结论**

#### 资金面分析
- 北向资金趋势
- 主力资金动向
- **资金结论**

#### 情绪面分析
- 市场温度（涨跌比、涨停跌停）
- 投机热度（连板、炸板率）
- 恐慌或贪婪程度
- **情绪结论**

---

### 三、次日预判（核心输出）

#### 🟢 次日机会方向（最多 3 个）
每个方向包含：具体方向 — 逻辑依据 — 关注标的类型 — 触发条件

#### 🔴 次日风险预警（至少 2 个）
每个风险包含：具体风险点 — 应对策略

#### 📋 次日操作策略
- 整体仓位建议（X 成，进攻/防守/观望）
- 开盘前 30 分钟观察要点
- 盘中关键时间节点
- 止损纪律

---

### 四、一句话总结
不超过 50 字，格式：
> "明日预计 [震荡偏多/震荡偏空/窄幅震荡]，核心变量是 XXX，建议 [积极做多/谨慎防守/空仓观望]。"
"""

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
            max_tokens=4000,
        )
        
        content = response.choices[0].message.content
        print("✅ DeepSeek API 调用成功")
        return content
    
    except Exception as e:
        error_msg = f"# 报告生成失败\n\n错误：{str(e)}\n\n请检查 DEEPSEEK_API_KEY 是否正确。"
        print(f"❌ API 调用失败：{e}")
        return error_msg


def push_wechat(title: str, content: str) -> bool:
    """通过 PushPlus 推送到微信"""
    if not PUSHPLUS_TOKEN:
        print("⚠️ 未配置 PUSHPLUS_TOKEN，跳过推送")
        return False
    
    try:
        import requests
        
        # PushPlus 限制 4000 字符，截取摘要
        send_content = content[:3800] + "\n\n...（完整报告见 GitHub Actions Artifacts）" if len(content) > 3800 else content
        
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
    
    # 跳过周末（除非手动强制运行）
    force_run = os.environ.get("FORCE_RUN", "0") == "1"
    if now.weekday() >= 5 and not force_run:
        print(f"今天是 {['周一','周二','周三','周四','周五','周六','周日'][now.weekday()]}，跳过复盘。")
        return
    
    print(f"🚀 开始生成 {now.strftime('%Y-%m-%d')} A 股复盘报告...")
    
    # 检查配置
    if not LLM_API_KEY:
        print("❌ 未配置 DEEPSEEK_API_KEY，请在 GitHub Secrets 中设置")
        return
    
    # 构建提示词
    date_str = now.strftime("%Y%m%d")
    date_cn = now.strftime("%Y年%m月%d日")
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekdays[now.weekday()]
    
    user_prompt = USER_PROMPT.format(date_str=date_cn, weekday=weekday)
    
    # 生成报告
    report = call_deepseek(SYSTEM_PROMPT, user_prompt)
    
    # 保存报告
    filepath = save_report(report, date_str)
    
    # 推送到微信
    title = f"📈 A股复盘 {date_cn} {weekday}"
    push_wechat(title, report)
    
    print(f"🎉 全部完成！报告路径：{filepath}")


if __name__ == "__main__":
    main()
