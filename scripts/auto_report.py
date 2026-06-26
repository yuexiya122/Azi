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

SYSTEM_PROMPT = """你是A股专业量化复盘分析师，输出风格对标「淘股吧题材淘金 + 开盘啦一图复盘」。

核心能力：
1. 从涨停数据中提取主力资金意图——不是报数据，是解读数据
2. 识别每个题材的「龙头」（情绪锚，连板领涨）和「中军」（大市值定海神针），区分情绪龙vs趋势龙
3. 通过连板高度、炸板率、封板率、龙-中联动变化判断情绪周期位置
4. 识别预期差：市场一致看好的方向哪里可能坑人，被忽视的方向哪里有机会
5. 概率化思维：每个预判给概率，每个情景给触发条件

铁律：
- 每段3-5句话，拒绝废话，拒绝"可能""或许""关注"
- 数据先行，逻辑直给，观点鲜明
- 涨停梯队、最强风口（含龙头中军）、情绪周期是核心三要素
- 每个风口必须标注龙一+中军，板块无大市值中军则标明"暂无中军（小票情绪炒作）"
- 总字数400-600字（手机一屏半看完）"""

USER_PROMPT = """## 任务：A股量化复盘（对标淘股吧题材淘金 + 开盘啦一图复盘）

日期：{date_str}（{weekday}）

按以下7段格式输出，每段3-5句，总字数500-650。基于上方注入的真实涨停数据进行精准分析，严禁编造数字。

【涨停全景】
涨停X家（昨X家）| 炸板X家 | 封板率X% | 连板最高X板（XX股，情绪龙）| 晋级率1进2：X%，2进3：X%
数据解读：（涨跌趋势+做多做空信号，1句话）

【题材淘金 · 龙头中军】（对标淘股吧格式，核心段落）
基于上方真实涨停+市值数据，列出TOP5风口。每个风口必须标注龙头+中军：

▎🔥 XX板块（涨停X家）
  龙一：XX股（X板 | 封板X亿 | 市值X亿 | 首次封板HH:MM）— 龙性判断：情绪连板龙/趋势加速龙
  中军：XX股（涨X% | 市值X亿）— 如果中军不动，板块高度有限；中军若补涨，龙头空间打开
  板块逻辑：一句话说清资金为什么干这个方向

▎🔥 XX板块（涨停X家）
  龙一：XX股（X板 | 封板X亿）
  中军：XX股 / 暂无中军（全部小票，纯情绪博弈）
  板块逻辑：XX

（按涨停家数排序TOP5，每板块含龙一+中军+逻辑）

资金博弈：游资在XX方向抱团龙头，机构在XX方向买入中军，量化在XX方向做T。板块轮动：XX→XX，明天预判切换到XX。

【连板天梯】（对标开盘啦梯队全景）
X板：XX股（X连板，封单X亿/换手X% | 市值X亿）→ 龙性：情绪锚/空间板，明天晋级概率X%，关键看XX
X板：XX股、XX股 → 谁晋级谁掉队？中军XX股走势对板块影响？
...（全梯队列出至2板）
首板核心：XX、XX（明日1进2潜力，原因一句）
梯队判断：完整/断层 → 赚钱效应扩散/收缩，明日预期X

【情绪周期】（对标开盘啦情绪定位）
当前阶段：冰点→修复→主升→高潮→退潮→混沌（单选）
三向量化：
① 涨停数趋势：近3日 X→X→X
② 连板晋级率：1进2=X%，2进3=X%
③ 龙-中联动：龙一XX股封板时中军XX股跟涨/背离 → 跟涨=板块健康，背离=内部分歧
周期定位：X阶段第X天 → 历史上类似位置次日X%概率走向X

【三派观点】（各60-90字）
▎游资视角：情绪龙XX股（X板）是全场锚。明天竞价高开X%且封单>X万手→做多XX方向首板补涨；低开炸板→空仓。游资今日方向：XX进、XX出。中军XX是防御锚，破位必须清仓。
▎题材视角：主线XX（龙一XX/中军XX）处于X阶段，龙-中联动健康/背离。暗线XX悄悄走强（中军XX市值X亿涨X%），散户未注意。明天主线若分歧，资金可能切换至XX。
▎量化视角：涨停X家+晋级率X%+封板率X%+龙中联动评分X，量化综合评分X/10。明日做多概率X%，建议仓位X成。致命恶化信号：龙一炸板或中军跌超X%。

【明日作战计划】
竞价锚点（9:15-9:25）：
→ 龙一XX股封单量（>X万手超预期，<X万手不及预期）
→ 中军XX股竞价（高开=主线确认，低开=分歧预警）

情景推演：
→ 情景A（概率X%）：XX信号 → 加仓至X成，主攻XX方向
→ 情景B（概率X%）：XX信号 → 减仓至X成，只留中军底仓

今日机会：XX方向（标的类型+买点条件）
致命风险：龙一炸板或中军跌停 → 无条件清仓
仓位：X成 | 止损：XX"""


# ============================================================
# 周末提示词（周六：消息面深挖 + 发酵题材 + 量化预判）
# ============================================================

WEEKEND_SATURDAY_PROMPT = """## 任务：周末消息深挖 + 发酵题材量化分析

日期：{date_str}（周六）| 节前最后交易日：{friday_str}

按以下6段极简格式输出，总字数350-500：

【节前收官速览】
涨停X家 | 跌停X家 | 连板最高X板（XX股，情绪龙）| 炸板率X% | 封板率X%
最强：XX（X家涨停，龙一XX/中军XX），退潮：XX
量化定性：资金在XX方向抱团，XX方向出逃，情绪处于X周期阶段

【周末重磅消息量化评估】
🟢 利好①：事件一句话 → 利好板块XX → 量化评估：影响级别X星，持续性X天，周一高开X%以上/以下
🟢 利好②：同上
🟢 利好③：同上
🔴 利空①：事件一句话 → 影响板块XX → 量化评估：影响级别X星，周一低开X%概率大

【周末发酵题材排行榜】（核心段落，重点写）
按发酵强度排序TOP5，每个题材给出发酵程度和量化评估：

① XX题材：发酵强度🔥X星，核心催化：XX，全周末讨论量级：XX级别
   → 市场一致性预期：XX
   → 量化视角：预期差在哪？一致性过强=周一高开兑现概率X%；预期不足=如果竞价超预期可追
   → 核心标的类型：XX（XX股风格）
   → 周一策略：高开X%以上不追 / 平开或低开可轻仓试错 / 放弃

② XX题材：（同上格式）
③ XX题材：（同上格式）
④ XX题材：（同上格式）
⑤ XX题材：（同上格式）

预期差最大的1个方向：XX（周末没发酵但下周有催化），如果周一XX信号出现，爆发力最强。

【全球联动量化】
美股假期表现：道指X%、纳指X%、标普X% → 对A股传导：偏多/偏空/中性
大宗商品：原油X%、黄金X%、铜X% → 利好/利空XX板块
汇率：离岸人民币X → 北向资金倾向：流入/流出
VIX恐慌指数：XX → 全球风险偏好：上升/下降

【大神周末观点速递】
模拟三位淘股吧知名复盘大神的周末核心观点（各80-100字）：

▎游资视角：节前最高X板XX股是情绪龙风向标，周一竞价如果XX则继续做多XX方向，如果炸板则空仓等冰点。注意中军XX股走势——中军若破位，题材行情结束。
▎题材视角：本周末发酵最充分的是XX题材（风险：一致性过高），预期差最大的反而是XX题材（逻辑：XX）。下周一看XX题材是走强更强还是分歧转一致。
▎量化视角：涨停数X、炸板率X%、连板晋级率X%，量化模型显示周一做多概率X%，建议仓位X成。如果XX指标恶化则降至X成。

【下周一量化预判】
情景A（概率X%）：触发条件XX → 指数区间XX-XX → 策略：XX
情景B（概率X%）：触发条件XX → 指数区间XX-XX → 策略：XX
情景C（概率X%）：触发条件XX → 指数区间XX-XX → 策略：XX
竞价核心看点：XX板块集合竞价量能，XX龙头的封单变化
仓位：X成（进攻X/防守X）| 止损：XX破XX或XX信号

【一句话】
"周末消息面偏X（量化评分X/10），发酵最狠的是XX但一致性风险X星，预期差在XX方向，下周一策略：XX。" """

# ============================================================
# 周末提示词（周日：下周作战计划 + 量化策略）
# ============================================================

WEEKEND_SUNDAY_PROMPT = """## 任务：下周量化作战计划

日期：{date_str}（周日）| 节前最后交易日：{friday_str}

按以下6段极简格式输出，总字数350-500：

【周末舆情量化终判】
舆情总评分：X/10（10分最热）
一致性方向：X成看多、X成看空、X成观望 → 市场处于过度一致/合理分歧/极度悲观
周末发酵TOP3题材终判：
① XX题材：发酵X星，一致性XX，周一高开兑现概率X%
② XX题材：发酵X星，一致性XX，周一继续接力概率X%
③ XX题材：发酵X星，一致性XX，周一走势预判XX
预期差终判：XX方向被集体忽视（如果爆发，弹性最大），XX方向一致性过强（大概率坑人）

【节前盘面量化复盘】
主线：XX题材（龙一XX/中军XX，涨停X家，持续X天，封板率X%）→ 量化评估：处于主升第X天/高潮/分歧阶段
暗线：XX（中军XX市值X亿涨X%，散户参与度低，机构在吸筹）→ 量化评估：蓄力阶段，关注XX催化
退潮：XX方向退潮信号明显（龙一XX断板/炸板率X%/资金流出X亿）→ 量化评估：退潮第X天，还需X天消化
游资态度：积极（连板晋级率X%）/佛系（晋级率低于X%）/机构主导（趋势中军成交占比X%）
情绪周期位置：当前处于X阶段 → 历史相似阶段后X%概率走向X

【淘股吧大神观点提炼】（★ 核心段落，请充分模拟3位大神的风格各写一段）
基于节前最后一个交易日的盘面，模拟以下3位淘股吧/雪球知名复盘大神的观点（每人100-150字）：

▎游资派代表（风格：只看涨停梯队和情绪，不关心大盘）
"X板高度XX股是当前情绪龙，梯队X。如果周一它X走势，则情绪走向X；如果它X走势，则情绪走向X。中军XX股必须盯着——中军破位=板块行情结束。首板里重点关注XX方向（逻辑：XX），XX方向已经不香了（理由：XX）。周一策略：竞价看龙一，高开X%以上放弃，平开/低开且XX信号出现可以小仓试错。"

▎题材派代表（风格：聚焦主线题材的持续性和发酵阶段）
"本周主线是XX（龙一XX/中军XX，涨停X家），该题材处于X阶段（启动/主升/高潮/分歧），持续性判断：龙-中联动健康则还能走X天，背离则进入退潮。暗线XX的中军XX悄悄在涨，逻辑是XX，散户还没注意到。下周最值得关注的切换方向是XX（逻辑：XX）。风险提示：现在一致性最强的是XX方向，但越是高一致性越容易周一高开低走。"

▎量化派代表（风格：用数据说话，强调概率和纪律）
"节前最后交易日数据：涨停X家，炸板率X%，封板率X%，连板晋级率X%。这些数据组合在过去3年出现X次，次日上涨概率X%，平均涨幅X%。当前情绪周期量化评分：X/10。系统信号：仓位建议X成，进攻方向XX（得分X），防守方向XX。最大风险点：XX指标如果恶化至X以下，必须无条件减仓。"

【下周事件催化日历】
周一X日：XX事件 → 影响方向XX
周二X日：XX事件 → 影响方向XX
...（列本周最重要的3-5个催化事件）

【核心股票池】（量化筛选）
按爆发力排序，区分龙头/中军角色：

| 方向 | 角色 | 标的参考 | 逻辑 | 爆发力 | 买点 | 止损 | 概率 |
|------|------|---------|------|--------|------|------|------|
| XX   | 龙一 | XX股    | 一句话逻辑 | X星 | XX-XX | XX | X% |
| XX   | 中军 | XX股    | 一句话逻辑 | X星 | XX-XX | XX | X% |
（列4-6个方向，每方向标注龙一/龙二/中军角色）

筛选标准：成交量在均量1.5倍以上 + 封板率>60% + 属于周末发酵题材

【下周量化策略框架】
总仓位上限：X成
配置结构：进攻X成（XX方向） + 防守X成（XX方向） + 现金X成
情景推演：
→ 情景A（概率X%）：XX信号 → 加仓到X成 → 主攻XX
→ 情景B（概率X%）：XX信号 → 减仓到X成 → 只留XX底仓
→ 情景C（概率X%）：XX信号 → 清仓 → 空仓观望

【交易纪律】
单票上限：X成 | 单日亏损上限：X% | 单周亏损上限：X%
无条件撤退：
1. XX板块龙头跌停
2. 上证跌破XX点
3. 北向单日净流出超XX亿
翻车预案：如果周一走势完全相反，第一时间XX，不扛单不补仓

【一句话】
"下周量化评分X/10，核心矛盾是XX vs XX，最确定的机会在XX方向（概率X%），最大风险是XX（概率X%），策略：XX。" """

# ============================================================
# 盘前简报提示词（每天 8:50 推送）
# ============================================================

MORNING_PROMPT = """## 任务：盘前简报（9点前必读）

日期：{date_str}（{weekday}）| 昨日：{yesterday_str}

按以下6段极简格式输出，总字数350-500：

【隔夜全球速览】
美股：道指X%、纳指X%、标普X% → 对A股传导：偏多/偏空/中性
中概股：XX涨X%、XX跌X%
A50期货：涨/跌X% → 预示开盘方向
大宗：原油X%、黄金X%、铜X%
汇率：离岸人民币X、美元指数X → 北向资金倾向
一句话：外围偏X，A股大概率X开

【盘前重磅】
🟢 利好：一句话 + 利好板块XX
🔴 利空：一句话 + 影响板块XX
（只列今日盘前6小时内发布的消息，没有就写"盘前消息面平静"）

【昨日复盘精华】
昨日涨停X家 | 炸板率X% | 连板最高X板（XX股，情绪龙）
最强风口：XX（X家涨停，龙一XX/中军XX）
情绪周期：处于X阶段，昨天已经X
三派速评：
▎游资：情绪龙XX股是锚，今日竞价如果X则做多，X则防守。如果中军XX破位则是退潮信号。
▎题材：主线XX（龙一XX/中军XX）还在X阶段，还能走X天；暗线XX蠢蠢欲动
▎量化：昨日数据模型显示今日做多概率X%，建议仓位X成

【今日操作策略】
竞价锚点（9:15-9:25）：
→ 龙一XX股封单量（>X万手超预期 → 主线确认）
→ 中军XX股竞价（高开X%=主线健康，低开=分歧预警）
开盘（9:30-10:00）应对：
→ 如果高开高走+龙一中军联动 → 加仓到X成，主攻XX
→ 如果高开低走+龙一炸板 → 立刻减仓到X成，只留中军底仓
→ 如果低开震荡 → 观望，等10点后方向确认
今日机会：1-2个方向 + 具体买点条件
今日风险：龙一炸板或中军跳水 → 无条件撤退
仓位：X成 | 止损：XX

【今日事件提醒】
今日盘中需关注：XX点发布的XX数据 / XX公司的XX公告 / XX会议
对盘面的影响预判：XX

【盘前一句话】
"今日外围偏X，A股预判X开后X走势，核心盯XX板块+XX股的竞价，策略：XX。" """


# ============================================================
# 午间总结提示词（12:00 推送）
# ============================================================

NOON_PROMPT = """## 任务：午间盘面总结

日期：{date_str}（{weekday}）

按以下5段极简格式输出，总字数300-450：

【上午指数概览】
上证X点（X%）| 深成指X点（X%）| 创业板X点（X%）| 科创50 X点（X%）
半日成交X亿（昨日上午X亿）→ 放量/缩量
涨跌比X:X | 涨停X家 | 跌停X家
一句话定性：上午X强X弱，资金在X方向进攻/防守

【上午最强风口】🔥
风口1：XX板块（X家涨停，龙一XX/中军XX）— 逻辑
风口2：XX板块（X家涨停，龙一XX/中军XX）— 逻辑
风口3：XX板块（X家涨停，龙一XX/中军暂无）— 逻辑
上午资金路线：开盘XX方向领涨 → X点XX方向接力 → 收盘前XX方向异动

【上午连板 + 龙头追踪】
最高板：X板XX股（封单X万手，换手X%）→ 情绪龙，下午晋级概率？
中军观察：XX板块中军XX股（涨X%/市值X亿）→ 中军稳=板块稳，中军跳水=雷
连板梯队：X板X只、X板X只、X板X只 → 梯队完整/断层
上午最强个股：龙一XX（逻辑）| 最坑个股：XX（原因）
首板值得关注：XX、XX（下午可能发酵）

【主线暗线 + 资金切换】
主线：XX（龙一XX/中军XX，上午涨停X家，持续X天）→ 下午预判：继续加强/分歧
暗线：XX（悄悄在涨X%，板块内X只红盘）→ 下午是否爆发？
退潮方向：XX（上午资金流出X亿/炸板X家）→ 龙一XX是否扛得住？
资金切换信号：从XX流向XX（X点到X点趋势最明显）

【下午操作策略】
下午重点观察：
→ 如果XX板块午后继续加强 → 今天主线确认，尾盘可加仓
→ 如果XX龙头炸板 → 情绪退潮信号，减仓防守
→ 如果成交量萎缩X%以下 → 观望不操作
下午机会：1个方向 + 条件
下午风险：1个致命信号
仓位：保持X成 / 加至X成 / 减至X成

【一句话】
"上午X强X弱，核心矛盾是XX，下午预判X走势，策略：XX。" """


# ============================================================
# 核心函数
# ============================================================

# ============================================================
# 实时数据抓取
# ============================================================

def fetch_real_data(mode: str = "afternoon") -> str:
    """使用 akshare 抓取真实市场数据"""
    parts = []
    today = datetime.now().strftime("%Y%m%d")
    yesterday = (datetime.now() - __import__('datetime').timedelta(days=1)).strftime("%Y%m%d")
    # 如果今天是周末，用最近一个交易日
    try:
        import akshare as ak
    except ImportError:
        parts.append("⚠️ akshare 未安装，使用训练数据分析")
        return "\n".join(parts)
    
    try:
        # === 1. 实时指数（东方财富） ===
        try:
            df_idx = ak.stock_zh_index_spot_em()
            targets = ['上证指数','深证成指','创业板指','科创50']
            for _, r in df_idx[df_idx['名称'].isin(targets)].iterrows():
                parts.append(f"【{r['名称']}】{r['最新价']:.2f}（{r['涨跌幅']:+.2f}%）成交{r.get('成交额',0)/1e8:.0f}亿")
        except:
            # 备用：直接爬同花顺页面
            try:
                import requests
                r = requests.get("https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html", 
                               headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                if r.status_code == 200:
                    parts.append("【指数数据】已从同花顺获取页面，请基于此分析")
            except:
                pass
        
        # === 2. 涨停板数据 + 晋级率 + 板块统计 ===
        try:
            zt_date = yesterday if mode == "morning" else today
            # 动态备选日期：今天→昨天→前天→大前天（避免硬编码过期数据）
            from datetime import timedelta
            fallback_dates = []
            for offset in range(5):
                fd = (datetime.now() - timedelta(days=offset)).strftime("%Y%m%d")
                if fd not in fallback_dates:
                    fallback_dates.append(fd)
            
            attempt_dates = [zt_date] + [d for d in fallback_dates if d != zt_date]
            df_zt = None
            actual_date_used = None
            
            for attempt_date in attempt_dates:
                try:
                    df_try = ak.stock_zt_pool_em(date=attempt_date)
                    if len(df_try) > 0:
                        df_zt = df_try
                        actual_date_used = attempt_date
                        break
                except:
                    continue
            
            if df_zt is None:
                parts.append("⚠️ 涨停数据抓取失败（所有日期均无数据），请检查 akshare 或网络")
            else:
                # --- 基本统计 ---
                zt_count = len(df_zt)
                lb_counts = df_zt['连板数'].value_counts().to_dict()
                max_lb = int(df_zt['连板数'].max())
                zb_count = int(df_zt['炸板次数'].sum())
                try:
                    fb_rate = f"{zb_count/(zt_count+zb_count)*100:.0f}%" if (zt_count+zb_count)>0 else "N/A"
                except:
                    fb_rate = "N/A"
                
                # 连板天梯
                lb_parts = []
                for k in sorted(lb_counts.keys(), reverse=True):
                    lb_parts.append(f"{int(k)}板:{int(lb_counts[k])}只")
                lb_str = " > ".join(lb_parts)
                
                # --- 晋级率（对比昨日数据） ---
                try:
                    yday_attempt = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
                    df_zt_yday = ak.stock_zt_pool_em(date=yday_attempt)
                    if len(df_zt_yday) > 0:
                        yday_counts = df_zt_yday['连板数'].value_counts().to_dict()
                        jjl_parts = []
                        for bn in range(1, 6):
                            today_n = int(lb_counts.get(bn, 0))
                            yday_n = int(yday_counts.get(bn-1, 0))
                            r = f"{today_n/yday_n*100:.0f}%" if yday_n > 0 else "-"
                            jjl_parts.append(f"{bn-1}进{bn}:{r}({today_n}/{yday_n})")
                        parts.append(f"【晋级率】{' | '.join(jjl_parts)}")
                except:
                    pass
                
                # --- 板块涨停统计 ---
                try:
                    sector_counts = df_zt['所属行业'].value_counts().head(8)
                    sector_str = "；".join(f"{k}({int(v)}家)" for k, v in sector_counts.items())
                    parts.append(f"【板块涨停统计】{sector_str}")
                except:
                    pass
                
                # --- 【题材淘金】龙头/中军识别 ---
                try:
                    ld_parts = []
                    top_sectors = df_zt['所属行业'].value_counts().head(6)
                    
                    for sector_name, zt_n in top_sectors.items():
                        sector_stocks = df_zt[df_zt['所属行业'] == sector_name].sort_values(
                            ['连板数', '封板资金'], ascending=[False, False]
                        )
                        
                        if len(sector_stocks) == 0:
                            continue
                        
                        # 龙一：连板最高
                        l1 = sector_stocks.iloc[0]
                        l1_lb = int(l1.get('连板数', 0))
                        l1_fund = l1.get('封板资金', 0) / 1e8
                        l1_mcap = l1.get('流通市值', 0) / 1e8
                        l1_time = str(l1.get('首次封板时间', '--'))
                        l1_str = f"龙一：{l1['名称']}({l1_lb}板|封板{l1_fund:.1f}亿|市值{l1_mcap:.0f}亿|首封{l1_time})"
                        
                        # 龙二
                        l2_str = ""
                        if len(sector_stocks) > 1:
                            l2 = sector_stocks.iloc[1]
                            l2_lb = int(l2.get('连板数', 0))
                            l2_fund = l2.get('封板资金', 0) / 1e8
                            if l2_lb >= 1:
                                l2_str = f"\n  龙二：{l2['名称']}({l2_lb}板|封板{l2_fund:.1f}亿)"
                        
                        # 中军：同板块内市值>100亿的涨停股
                        big_stocks = sector_stocks[sector_stocks['流通市值'] > 100e8]
                        if len(big_stocks) > 0:
                            zj = big_stocks.iloc[0]
                            zj_mcap = zj.get('流通市值', 0) / 1e8
                            zj_str = f"\n  中军：{zj['名称']}(市值{zj_mcap:.0f}亿|连板{int(zj.get('连板数',0))}板|封板{zj.get('封板资金',0)/1e8:.1f}亿)"
                        else:
                            zj_str = "\n  中军：暂无（板块大市值尚未涨停，纯小票情绪）"
                        
                        ld_parts.append(f"▎{sector_name}(涨停{int(zt_n)}家)\n  {l1_str}{l2_str}{zj_str}")
                    
                    if ld_parts:
                        parts.append(f"【题材淘金·龙头中军（数据日期 {actual_date_used}）】\n" + "\n\n".join(ld_parts))
                except Exception as e:
                    parts.append(f"⚠️ 龙头识别异常: {e}")
                
                # 汇总（带数据日期标注）
                date_label = f" (数据日期 {actual_date_used})" if actual_date_used != zt_date else ""
                parts.append(f"【涨停数据{date_label}】涨停{zt_count}家 | 炸板{zb_count}次 | 炸板率{fb_rate} | 最高{max_lb}板 | 连板天梯：{lb_str}")
                
                # TOP涨停明细
                top_cols = [c for c in ['名称','连板数','涨停统计','所属行业','封板资金','换手率'] if c in df_zt.columns]
                top_zt = df_zt[top_cols].head(12).to_dict('records')
                zt_summary = "；".join(
                    f"{z.get('名称','')}({z.get('连板数','')}板/{z.get('涨停统计','')}/{z.get('所属行业','')})" 
                    for z in top_zt
                )
                parts.append(f"【涨停TOP12】{zt_summary}")
                
                # 连板股明细
                lb_gt1 = df_zt[df_zt['连板数'] > 1].sort_values('连板数', ascending=False)
                if len(lb_gt1) > 0:
                    lb_detail = "；".join(
                        f"{r['名称']}：{r['连板数']}板({r.get('涨停统计','')}|{r.get('所属行业','')})"
                        for _, r in lb_gt1.iterrows()
                    )
                    parts.append(f"【连板股明细】{lb_detail}")
        except Exception as e:
            parts.append(f"⚠️ 涨停数据获取异常: {e}")
        
        # === 3. 板块排行 ===
        try:
            df_sector = ak.stock_board_industry_name_em()
            top5 = df_sector.nlargest(5, '涨跌幅')
            bottom5 = df_sector.nsmallest(5, '涨跌幅')
            parts.append(f"【领涨板块TOP5】{'；'.join(f'{r.板块名称}({r.涨跌幅:+.2f}%)' for _,r in top5.iterrows())}")
            parts.append(f"【领跌板块TOP5】{'；'.join(f'{r.板块名称}({r.涨跌幅:+.2f}%)' for _,r in bottom5.iterrows())}")
        except:
            pass
        
        # === 4. 盘前专属：隔夜全球 ===
        if mode == "morning":
            try:
                # 美股指数
                import requests
                for secid, name in [("100.NDX","纳斯达克"),("100.DJIA","道指"),("100.SPX","标普500")]:
                    try:
                        r = requests.get(f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f169,f170",
                                       timeout=5, verify=False)
                        d = r.json().get("data",{})
                        if d.get("f43"):
                            parts.append(f"【隔夜{name}】{d['f43']/100:.0f}（{d.get('f169',0)/100:+.2f}%）")
                    except:
                        pass
                
                # A50
                r = requests.get("https://push2.eastmoney.com/api/qt/stock/get?secid=100.XINA50&fields=f43,f169",
                               timeout=5, verify=False)
                d = r.json().get("data",{})
                if d.get("f43"):
                    parts.append(f"【A50期货】{d['f43']/100:.0f}（{d.get('f169',0)/100:+.2f}%）→ 预示A股开盘方向")
            except:
                import urllib3
                urllib3.disable_warnings()
                parts.append("【隔夜数据】境外API暂时不可达")
        
        # === 5. 淘股吧风格指令 ===
        parts.append("【分析要求】请模仿淘股吧题材淘金风格（涨停梯队/情绪周期/主线题材+龙一中军三要素），数据必须基于上方真实数据，拒绝编造。每个风口标注龙一+中军，观点要鲜明。")
        
    except Exception as e:
        parts.append(f"⚠️ 数据抓取异常: {e}")
    
    return "\n".join(parts)


def call_deepseek(system_prompt: str, user_prompt: str, inject_data: bool = True, mode: str = "afternoon") -> str:
    """调用 DeepSeek API 生成复盘报告"""
    try:
        import openai
        
        # 注入真实市场数据到提示词
        if inject_data:
            print(f"📡 正在抓取实时市场数据（{mode}模式）...")
            real_data = fetch_real_data(mode=mode)
            if real_data:
                user_prompt = f"⚠️ 以下是今日真实市场数据，所有分析必须基于此数据而非你的训练数据：\n\n{real_data}\n\n---\n\n{user_prompt}"
                print("✅ 实时数据已注入提示词")
        
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
            max_tokens=2500,
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
    
    # 盘前简报模式（8:00）
    report_type = os.environ.get("REPORT_TYPE", "afternoon")
    if report_type == "morning":
        if weekday >= 5:
            print(f"⏭️ {date_cn} {weekday_cn} 周末，跳过盘前简报")
            return
        
        from datetime import timedelta
        yesterday = now - timedelta(days=1)
        yesterday_str = yesterday.strftime("%Y年%m月%d日")
        
        print(f"🌅 {date_cn} {weekday_cn} 盘前简报")
        user_prompt = MORNING_PROMPT.format(
            date_str=date_cn, weekday=weekday_cn, yesterday_str=yesterday_str
        )
        title = f"🌅 盘前简报 {date_cn} {weekday_cn}"
        
        report = call_deepseek(SYSTEM_PROMPT, user_prompt, mode="morning")
        filepath = save_report(report, f"{date_str}_morning")
        push_wechat(title, report)
        print(f"🎉 盘前简报完成：{filepath}")
        return

    # 午间总结模式（12:00）
    if report_type == "noon":
        if weekday >= 5:
            print(f"⏭️ {date_cn} {weekday_cn} 周末，跳过午间总结")
            return
        
        print(f"☀️ {date_cn} {weekday_cn} 午间总结")
        user_prompt = NOON_PROMPT.format(date_str=date_cn, weekday=weekday_cn)
        title = f"☀️ 午间盘面 {date_cn} {weekday_cn}"
        
        report = call_deepseek(SYSTEM_PROMPT, user_prompt, mode="afternoon")
        filepath = save_report(report, f"{date_str}_noon")
        push_wechat(title, report)
        print(f"🎉 午间总结完成：{filepath}")
        return
        return
    
    # ------ 以下为原有午后复盘逻辑 ------
    
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
        
    else:  # 周一至周五：统一使用日常复盘模板
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
