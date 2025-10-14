#!/bin/bash
# PotatoTool 自动更新 - Crontab 设置脚本

echo "=========================================="
echo "  PotatoTool 自动更新定时任务设置"
echo "=========================================="
echo ""

# 获取脚本绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_SCRIPT="$SCRIPT_DIR/run_auto_update.sh"

echo "工作目录: $SCRIPT_DIR"
echo "执行脚本: $RUN_SCRIPT"
echo ""

# 检查脚本是否存在
if [ ! -f "$RUN_SCRIPT" ]; then
    echo "❌ 错误: 未找到 run_auto_update.sh"
    exit 1
fi

# 确保脚本有执行权限
chmod +x "$RUN_SCRIPT"
chmod +x "$SCRIPT_DIR/auto_update.py"

echo "✓ 脚本权限已设置"
echo ""

# 显示 crontab 配置选项
echo "请选择定时任务频率:"
echo "1) 每天凌晨 2 点"
echo "2) 每周一凌晨 2 点"
echo "3) 每月 1 号凌晨 2 点"
echo "4) 自定义"
echo "5) 仅查看当前 crontab"
echo "0) 取消"
echo ""

read -p "请输入选项 (0-5): " choice

case $choice in
    1)
        CRON_ENTRY="0 2 * * * $RUN_SCRIPT"
        DESCRIPTION="每天凌晨 2 点"
        ;;
    2)
        CRON_ENTRY="0 2 * * 1 $RUN_SCRIPT"
        DESCRIPTION="每周一凌晨 2 点"
        ;;
    3)
        CRON_ENTRY="0 2 1 * * $RUN_SCRIPT"
        DESCRIPTION="每月 1 号凌晨 2 点"
        ;;
    4)
        echo ""
        echo "Crontab 格式: 分 时 日 月 周"
        echo "例如: 0 2 * * * 表示每天 2:00"
        echo ""
        read -p "请输入 crontab 时间表达式: " cron_time
        CRON_ENTRY="$cron_time $RUN_SCRIPT"
        DESCRIPTION="自定义时间"
        ;;
    5)
        echo ""
        echo "当前的 crontab 配置:"
        echo "=========================================="
        crontab -l 2>/dev/null || echo "(无)"
        echo "=========================================="
        exit 0
        ;;
    0)
        echo "已取消"
        exit 0
        ;;
    *)
        echo "❌ 无效的选项"
        exit 1
        ;;
esac

echo ""
echo "准备添加的 crontab 条目:"
echo "----------------------------------------"
echo "$CRON_ENTRY"
echo "----------------------------------------"
echo "描述: $DESCRIPTION"
echo ""

read -p "确认添加? (y/n): " confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "已取消"
    exit 0
fi

# 添加到 crontab
(crontab -l 2>/dev/null | grep -v "$RUN_SCRIPT"; echo "$CRON_ENTRY") | crontab -

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 定时任务设置成功！"
    echo ""
    echo "当前的 crontab 配置:"
    echo "=========================================="
    crontab -l
    echo "=========================================="
    echo ""
    echo "提示:"
    echo "- 查看日志: tail -f $(dirname $SCRIPT_DIR)/auto_update.log"
    echo "- 查看定时任务: crontab -l"
    echo "- 编辑定时任务: crontab -e"
    echo "- 删除所有定时任务: crontab -r"
else
    echo ""
    echo "❌ 设置失败"
    exit 1
fi


