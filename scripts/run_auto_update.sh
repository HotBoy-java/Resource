#!/bin/bash
# PotatoTool 自动更新任务脚本
# 适用于 cron 定时任务

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 项目根目录
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 切换到项目根目录
cd "$PROJECT_DIR" || exit 1

# 日志文件（保存在项目根目录）
LOG_FILE="$PROJECT_DIR/auto_update.log"
DATE=$(date "+%Y-%m-%d %H:%M:%S")

# 记录开始
echo "========================================" >> "$LOG_FILE"
echo "[$DATE] 开始自动更新" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 执行 Python 脚本（自动回答 'y' 进行推送）
echo "y" | python3 "$SCRIPT_DIR/auto_update.py" >> "$LOG_FILE" 2>&1

# 检查执行结果
if [ $? -eq 0 ]; then
    echo "[$DATE] 更新成功" >> "$LOG_FILE"
else
    echo "[$DATE] 更新失败" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"


