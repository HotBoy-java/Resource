# PotatoTool 自动更新任务脚本 - PowerShell 版本
# 适用于 Windows 任务计划程序

# 设置错误处理
$ErrorActionPreference = "Continue"

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# 获取项目根目录
$ProjectDir = Split-Path -Parent $ScriptDir

# 切换到项目根目录
Set-Location $ProjectDir

# 日志文件
$LogFile = Join-Path $ProjectDir "auto_update.log"
$ErrorLogFile = Join-Path $ProjectDir "auto_update_error.log"

# 获取当前时间
$DateTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# 记录开始
"========================================" | Out-File -FilePath $LogFile -Append -Encoding UTF8
"[$DateTime] 开始自动更新" | Out-File -FilePath $LogFile -Append -Encoding UTF8
"========================================" | Out-File -FilePath $LogFile -Append -Encoding UTF8

# 执行 Python 脚本（自动回答 'y' 进行推送）
$PythonScript = Join-Path $ScriptDir "auto_update.py"

try {
    # 创建进程启动信息
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "python"
    $psi.Arguments = "`"$PythonScript`""
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    
    # 启动进程
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    $process.Start() | Out-Null
    
    # 向标准输入写入 'y'
    $process.StandardInput.WriteLine("y")
    $process.StandardInput.Close()
    
    # 读取输出
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    
    # 等待进程完成
    $process.WaitForExit()
    
    # 记录输出
    $stdout | Out-File -FilePath $LogFile -Append -Encoding UTF8
    if ($stderr) {
        $stderr | Out-File -FilePath $ErrorLogFile -Append -Encoding UTF8
    }
    
    # 检查执行结果
    if ($process.ExitCode -eq 0) {
        "[$DateTime] 更新成功" | Out-File -FilePath $LogFile -Append -Encoding UTF8
        Write-Host "更新成功" -ForegroundColor Green
    } else {
        "[$DateTime] 更新失败 (错误代码: $($process.ExitCode))" | Out-File -FilePath $LogFile -Append -Encoding UTF8
        Write-Host "更新失败" -ForegroundColor Red
    }
} catch {
    $ErrorMessage = $_.Exception.Message
    "[$DateTime] 执行出错: $ErrorMessage" | Out-File -FilePath $ErrorLogFile -Append -Encoding UTF8
    Write-Host "执行出错: $ErrorMessage" -ForegroundColor Red
}

"" | Out-File -FilePath $LogFile -Append -Encoding UTF8

