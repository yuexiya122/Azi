#!/bin/bash
# 自触发辅助：计算距离下一个目标小时的秒数并休眠
# 参数: $1 = 目标小时 (8=盘前, 15=午后)
# 最大单次休眠: 5小时 (18000秒)

TARGET_HOUR=$1
WEEKDAY=$(TZ='Asia/Shanghai' date +%u)

# 周末停链
if [ "$WEEKDAY" -ge 6 ]; then
  echo "⏹️ 周末，停止链条"
  exit 1
fi

# 计算当前北京时间
CURRENT_EPOCH=$(date +%s)
CURRENT_HOUR_BJ=$(TZ='Asia/Shanghai' date +%H)
CURRENT_MIN_BJ=$(TZ='Asia/Shanghai' date +%M)

echo "北京时间: ${CURRENT_HOUR_BJ}:${CURRENT_MIN_BJ} 星期${WEEKDAY}"

# 计算今天目标时间的 epoch (北京时间)
# 北京时间比UTC快8小时，所以北京0点 = UTC前一天的16点
TODAY_MIDNIGHT_UTC=$(date -d "today 00:00:00" +%s)
TODAY_MIDNIGHT_BJ=$((TODAY_MIDNIGHT_UTC - 8*3600))

# 今天目标时间的 epoch
TODAY_TARGET=$((TODAY_MIDNIGHT_BJ + TARGET_HOUR * 3600))

# 如果已过今天的目标时间，取明天的
if [ $CURRENT_EPOCH -ge $TODAY_TARGET ]; then
  NEXT_TARGET=$((TODAY_TARGET + 24*3600))
else
  NEXT_TARGET=$TODAY_TARGET
fi

# 计算需要休眠的秒数
SLEEP_SECONDS=$((NEXT_TARGET - CURRENT_EPOCH))
MAX_SLEEP=18000  # 最多休眠5小时

if [ $SLEEP_SECONDS -gt $MAX_SLEEP ]; then
  SLEEP_SECONDS=$MAX_SLEEP
fi

echo "目标时间: $(TZ='Asia/Shanghai' date -d @${NEXT_TARGET})"
echo "休眠: ${SLEEP_SECONDS}秒 ($(($SLEEP_SECONDS/60))分钟)"
sleep $SLEEP_SECONDS
echo "✅ 休眠结束"
