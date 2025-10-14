# PotatoTool 自动更新 - Windows 任务计划程序设置脚本
# 需要管理员权限运行

# 检查管理员权限
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  错误：需要管理员权限" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "请右键点击 PowerShell，选择 '以管理员身份运行'，然后重新执行此脚本。" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  PotatoTool 自动更新定时任务设置" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

# 检测运行脚本类型
Write-Host "请选择要执行的脚本类型：" -ForegroundColor Yellow
Write-Host "1) PowerShell 脚本 (推荐)"
Write-Host "2) 批处理脚本 (.bat)"
Write-Host "0) 取消"
Write-Host ""

$scriptChoice = Read-Host "请输入选项 (0-2)"

switch ($scriptChoice) {
    "1" {
        $RunScript = Join-Path $ScriptDir "run_auto_update.ps1"
        $ScriptType = "PowerShell"
        $Action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$RunScript`""
    }
    "2" {
        $RunScript = Join-Path $ScriptDir "run_auto_update.bat"
        $ScriptType = "批处理"
        $Action = New-ScheduledTaskAction -Execute "$RunScript"
    }
    "0" {
        Write-Host "已取消" -ForegroundColor Yellow
        exit 0
    }
    default {
        Write-Host "无效的选项" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "工作目录: $ProjectDir" -ForegroundColor Gray
Write-Host "执行脚本: $RunScript" -ForegroundColor Gray
Write-Host "脚本类型: $ScriptType" -ForegroundColor Gray
Write-Host ""

# 检查脚本是否存在
if (-not (Test-Path $RunScript)) {
    Write-Host "错误: 未找到脚本文件 $RunScript" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host "请选择定时任务频率：" -ForegroundColor Yellow
Write-Host "1) 每天凌晨 2:00"
Write-Host "2) 每天凌晨 3:00"
Write-Host "3) 每周一凌晨 2:00"
Write-Host "4) 每月 1 号凌晨 2:00"
Write-Host "5) 自定义时间"
Write-Host "6) 查看现有任务"
Write-Host "7) 删除任务"
Write-Host "0) 取消"
Write-Host ""

$choice = Read-Host "请输入选项 (0-7)"

$TaskName = "PotatoTool-AutoUpdate"

switch ($choice) {
    "1" {
        $Trigger = New-ScheduledTaskTrigger -Daily -At "02:00"
        $Description = "每天凌晨 2:00 自动更新 PotatoTool 资源"
    }
    "2" {
        $Trigger = New-ScheduledTaskTrigger -Daily -At "03:00"
        $Description = "每天凌晨 3:00 自动更新 PotatoTool 资源"
    }
    "3" {
        $Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "02:00"
        $Description = "每周一凌晨 2:00 自动更新 PotatoTool 资源"
    }
    "4" {
        # 创建月度触发器（每月1号）
        $Trigger = New-ScheduledTaskTrigger -Daily -At "02:00"
        # 月度触发需要通过 XML 配置，这里使用一个变通方法
        $Description = "每月 1 号凌晨 2:00 自动更新 PotatoTool 资源"
        Write-Host "注意：月度任务将设置为每天运行，建议在创建后手动调整为每月运行。" -ForegroundColor Yellow
    }
    "5" {
        Write-Host ""
        Write-Host "请输入执行时间 (格式: HH:MM，例如 14:30):" -ForegroundColor Yellow
        $customTime = Read-Host "时间"
        
        Write-Host ""
        Write-Host "请选择频率：" -ForegroundColor Yellow
        Write-Host "1) 每天"
        Write-Host "2) 每周"
        Write-Host "3) 每月"
        $freqChoice = Read-Host "选项 (1-3)"
        
        switch ($freqChoice) {
            "1" {
                $Trigger = New-ScheduledTaskTrigger -Daily -At $customTime
                $Description = "每天 $customTime 自动更新 PotatoTool 资源"
            }
            "2" {
                Write-Host "请输入星期几 (Monday/Tuesday/Wednesday/Thursday/Friday/Saturday/Sunday):"
                $dayOfWeek = Read-Host "星期"
                $Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $dayOfWeek -At $customTime
                $Description = "每周 $dayOfWeek $customTime 自动更新 PotatoTool 资源"
            }
            "3" {
                $Trigger = New-ScheduledTaskTrigger -Daily -At $customTime
                $Description = "每月 $customTime 自动更新 PotatoTool 资源"
                Write-Host "注意：建议创建后手动调整为月度触发。" -ForegroundColor Yellow
            }
            default {
                Write-Host "无效的选项" -ForegroundColor Red
                exit 1
            }
        }
    }
    "6" {
        Write-Host ""
        Write-Host "现有的 PotatoTool 自动更新任务：" -ForegroundColor Cyan
        Write-Host "==========================================" -ForegroundColor Cyan
        $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($existingTask) {
            $existingTask | Format-List TaskName, State, Triggers, Actions
        } else {
            Write-Host "未找到任务" -ForegroundColor Yellow
        }
        Write-Host "==========================================" -ForegroundColor Cyan
        Read-Host "按回车键退出"
        exit 0
    }
    "7" {
        Write-Host ""
        $confirmDelete = Read-Host "确认删除任务 '$TaskName'? (y/n)"
        if ($confirmDelete -eq "y" -or $confirmDelete -eq "Y") {
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
            Write-Host "任务已删除" -ForegroundColor Green
        } else {
            Write-Host "已取消" -ForegroundColor Yellow
        }
        Read-Host "按回车键退出"
        exit 0
    }
    "0" {
        Write-Host "已取消" -ForegroundColor Yellow
        exit 0
    }
    default {
        Write-Host "无效的选项" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "准备创建的任务计划：" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "任务名称: $TaskName"
Write-Host "描述: $Description"
Write-Host "执行脚本: $RunScript"
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""

$confirm = Read-Host "确认创建? (y/n)"

if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "已取消" -ForegroundColor Yellow
    exit 0
}

# 删除可能存在的旧任务
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# 创建任务设置
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# 获取当前用户
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType ServiceAccount -RunLevel Highest

# 注册任务
try {
    Register-ScheduledTask -TaskName $TaskName `
                          -Description $Description `
                          -Trigger $Trigger `
                          -Action $Action `
                          -Settings $Settings `
                          -Principal $Principal `
                          -Force | Out-Null
    
    Write-Host ""
    Write-Host "✅ 定时任务设置成功！" -ForegroundColor Green
    Write-Host ""
    Write-Host "任务详情：" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State, Description
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "提示：" -ForegroundColor Yellow
    Write-Host "- 查看日志: Get-Content '$ProjectDir\auto_update.log' -Tail 50"
    Write-Host "- 手动运行: Start-ScheduledTask -TaskName '$TaskName'"
    Write-Host "- 查看任务: Get-ScheduledTask -TaskName '$TaskName'"
    Write-Host "- 打开任务计划程序: taskschd.msc"
    Write-Host ""
    
} catch {
    Write-Host ""
    Write-Host "❌ 创建任务失败：$($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
}

Read-Host "按回车键退出"

