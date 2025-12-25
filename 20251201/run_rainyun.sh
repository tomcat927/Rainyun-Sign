#!/bin/bash

# 雨云签到自动化执行脚本
# 每天 8,9,10,11,12 点的随机分钟执行

cd /root || exit

# 定义日志路径和最大大小（1MB = 1048576 字节）
LOG_FILE="/root/python/rainyun.log"
MAX_SIZE=1048576  # 1MB

# 检查日志文件是否存在且超过最大大小
if [[ -f "$LOG_FILE" ]] && [[ $(stat -c%s "$LOG_FILE") -gt $MAX_SIZE ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 日志文件超过 ${MAX_SIZE} 字节，清空日志。" > "$LOG_FILE"
fi

# 激活虚拟环境
source venv/bin/activate

# 随机延迟 0~59 分钟
sleep $((RANDOM % 60 * 60))

# 执行 Python 脚本并追加日志
python rainyun.py >> "$LOG_FILE" 2>&1

# 记录执行完成时间
echo "[$(date '+%Y-%m-%d %H:%M:%S')] rainyun.py 执行完成" >> "$LOG_FILE"

# 退出虚拟环境（推荐）
deactivate