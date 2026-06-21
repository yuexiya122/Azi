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

SYSTEM_PROMPT = """你是一位拥有 15 年 A 股实战经验的量化交易分析师，擅长从量能、资金、技术面、情绪面四个维度进行短线条复盘分析。

风格要求：
- 数据驱动，每个结论有依据
- 短线条思维，关注 1-3 个交易日
- 理性冷静，不盲目乐观也不过度恐慌
- 可操作，给出明确策略

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
# 周末提示词（周六专用：消息汇总 + 下周展望）
# ============================================================

WEEKEND_SATURDAY_PROMPT = """## 任务：周末消息面精复盘 + 下周展望

**日期**：{date_str}（周六）
**本周最后交易日**：{friday_str}（周五）

---

### 📡 一、周末重大消息面梳理

请你基于训练数据中**最新可获取的市场资讯**，对本周五收盘后至周六的重大消息进行全面梳理：

#### 1. 宏观政策消息
- 央行动态（LPR、MLF、降准降息信号）
- 国务院/各部委重大政策发布
- 中美关系/地缘政治动态
- **对 A 股的传导逻辑**

#### 2. 产业政策消息
- 各行业重大利好/利空政策
- 新兴产业扶持政策（AI、新能源、半导体、生物医药等）
- 监管政策变化（数据安全、反垄断、金融监管等）
- **受益板块排序（TOP5）**

#### 3. 上市公司公告精选
- 重大资产重组 / 并购事件
- 业绩预告 / 业绩修正
- 大股东增减持动态
- IPO / 再融资速度变化

#### 4. 全球市场联动
- 美股周五收盘表现（道指/纳指/标普）
- 港股走势回顾
- 大宗商品（原油、黄金、铜、锂）价格变化
- 汇率波动（离岸人民币/USD）
- **对 A 股周一的传导效应**

---

### 🔬 二、周五最后一个交易日精细化复盘

对周五（{friday_str}）的市场进行**精细化拆解**：

#### 周五盘面特征
- 分时走势特征（高开低走 / 低开高走 / V型反转 / 冲高回落）
- 尾盘资金动向（抢筹还是出逃）
- 各时段量能分布

#### 周五主线与暗线
- 当日最强主线题材及龙头股
- 暗线资金布局方向（被忽视但有资金流入的板块）
- 非主线但有异动的标的

#### 周五龙虎榜 / 机构动向
- 机构席位净买入 TOP5 标的
- 游资席位动向分析
- 机构与游资的共识与分歧

#### 周五炸板 / 跌停复盘
- 炸板原因分析
- 跌停个股是否构成系统性信号？

---

### 📊 三、本周市场回顾

#### 本周核心指数周线表现
| 指数 | 周涨跌幅 | 周成交量 | 趋势判断 |
|------|---------|---------|---------|
| 上证指数 | - | - | - |
| 深证成指 | - | - | - |
| 创业板指 | - | - | - |
| 科创50 | - | - | - |

#### 本周最强主线回顾
- 本周贯穿全周的题材是什么？
- 主线是否在周五出现退潮信号？
- 次主线是否在周五出现接力信号？

#### 本周赚钱效应评估
- 本周上涨家数占比
- 连板高度变化趋势（上升/下降/持平）
- 市场情绪周期定位：冰点 / 修复 / 主升 / 高潮 / 分歧

---

### 🟢 四、周末利好板块与标的深挖

基于以上所有分析，列出**周末消息面明确利好的板块和个股**：

#### 利好板块 TOP5
对每个板块列出：
1. **板块名称** — 利好逻辑（政策/事件/业绩/资金）
2. **发酵强度判断**（已充分发酵 / 正在发酵 / 尚未发酵）
3. **核心标的 3-5 个**（龙头 + 补涨逻辑）
4. **周一预期走势**（高开高走 / 高开低走 / 震荡 / 分化）
5. **参与条件**（什么情况下可以参与？什么情况下必须放弃？）

#### 潜在利空板块
- 哪些板块周末出现利空信号？
- 周一是否需要回避？

---

### 🔴 五、下周一风险与机会研判

#### 机会方向（最多 3 个）
1. **方向一**：具体逻辑 + 关注标的类型 + 触发条件
2. **方向二**：同上
3. **方向三**：同上

#### 风险预警（至少 2 个）
1. **风险一**：具体风险 + 应对策略
2. **风险二**：具体风险 + 应对策略

#### 下周一操作框架
- **集合竞价关注要点**（9:15-9:25 需要盯什么）
- **开盘 30 分钟信号判断**（强势/弱势/震荡的标准）
- **仓位配置建议**（几成进攻，几成防守）
- **止损纪律**

---

### 六、一句话总结
不超过 50 字给下周一做一个定性：
> "本周末消息面 [偏暖/偏冷/中性]，核心变量是 XXX，下周一预计 [高开/低开/平开] 后 [震荡走强/震荡走弱/窄幅震荡]，重点关注 XXX 板块。"
"""

# ============================================================
# 周末提示词（周日专用：精细化策略 + 下周交易计划）
# ============================================================

WEEKEND_SUNDAY_PROMPT = """## 任务：周末精复盘总结 + 下周完整交易计划

**日期**：{date_str}（周日）
**上一个交易日**：{friday_str}（周五）

---

### 📡 一、周末消息面最终定论

综合周六日的全部消息面变化，对周末舆情做出**最终判断**：

#### 周末舆情温度计
- 整体舆情评级：🔥🔥🔥🔥🔥（五星最热）→ 评 X 星
- 看多声音占比：约 X%
- 看空声音占比：约 X%
- 中性声音占比：约 X%
- **情绪一致性**：一致看多 / 多空分歧大 / 普遍观望

#### 周末发酵最充分的 3 个题材
对每个题材说明：发酵程度 → 一致性预期 → 周一是兑现还是接力？

#### 周末预期差（被低估的方向）
- 有哪些利好消息在周末没有被充分讨论？
- 这些预期差可能在哪一天爆发？

---

### 📈 二、技术面精解

#### 上证指数日线结构分析
- 当前处于什么浪型位置？
- 关键均线位置（5/10/20/60 日线）及排列状态
- MACD 金叉/死叉位置及 DIF/DEA 数值
- KDJ 是否超买/超卖
- BOLL 带位置（上轨/中轨/下轨）
- **关键支撑位**：XXX 点（逻辑）
- **关键压力位**：XXX 点（逻辑）

#### 创业板指结构分析
- 同样的技术指标分析
- 与上证的结构强弱对比
- 风格切换信号是否存在？

#### 成交量能分析
- 近 5 个交易日的量能趋势（放量/缩量/平量）
- 缩量是洗盘还是失去动力？
- 放量是进攻还是出货？

---

### 💰 三、资金面全景

#### 本周北向资金全周复盘
- 本周累计净流入/流出：XXX 亿
- 每日北向资金进出节奏
- 北向加仓 TOP5 板块
- 北向减仓 TOP5 板块
- 北向资金趋势是中期转多还是转空？

#### 主力资金 / 融资融券
- 本周主力资金整体流向
- 融资余额变化趋势
- 两融标的重要变化

---

### 🎯 四、下周完整交易计划

#### 下周市场推演（分 3 种情景）

**情景一：强势（概率 X%）**
- 触发条件（什么信号出现判定为此情景）
- 指数空间预测（压力位到哪）
- 最佳策略：满仓进攻 / 重仓 / 中等仓位
- 核心配置方向

**情景二：震荡（概率 X%）**
- 触发条件
- 指数区间预测（箱体上下沿）
- 最佳策略：高抛低吸 / 控仓轮动
- 核心配置方向

**情景三：弱势（概率 X%）**
- 触发条件
- 指数支撑位预测（跌到哪）
- 最佳策略：减仓防守 / 空仓观望
- 避险品种

#### 下周一具体操作计划

**集合竞价（9:15-9:25）**
- 观察哪些个股的竞价量能和开盘价
- 什么情况说明超预期？
- 什么情况说明低于预期？

**早盘（9:30-10:30）**
- 前 30 分钟的量能和方向判断
- 是追还是等？

**尾盘（14:30-15:00）**
- 是否需要尾盘建仓/加仓？
- 什么信号需要尾盘出货？

#### 下周核心股票池

列出下周重点关注标的（板块 + 具体个股），对每个标的说明：

| 代码/名称 | 所属板块 | 关注逻辑 | 买入区间 | 止损位 | 目标位 | 持仓周期 |
|-----------|---------|---------|---------|--------|--------|---------|
| 示例 | AI | 政策催化 | 10.5-11 | 9.8 | 13 | 1-3天 |

（请列 5-10 个核心标的）

---

### 📋 五、下周交易纪律

- **总仓位上限**：X 成
- **单票仓位上限**：X 成
- **单日亏损上限**：总资金的 X%
- **无条件止损信号**：
  1. XXX
  2. XXX
- **禁止行为清单**：
  1. XXX
  2. XXX

---

### 六、一句话总结
不超过 50 字给下周定调：
> "下周预计整体 [偏多/偏空/震荡]，周初看 XXX，周末关键变量是 XXX，核心策略为 [积极进攻/攻守兼备/防守为主]。"
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
