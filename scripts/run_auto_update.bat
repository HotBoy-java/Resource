@echo off
REM PotatoTool 自动更新任务脚本 - Windows 版本
REM 适用于 Windows 任务计划程序

REM 设置编码为UTF-8
chcp 65001 >nul

REM 获取脚本所在目录
set SCRIPT_DIR=%~dp0
REM 移除末尾的反斜杠
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

REM 获取项目根目录（脚本目录的上一级）
for %%I in ("%SCRIPT_DIR%\..") do set PROJECT_DIR=%%~fI

REM 切换到项目根目录
cd /d "%PROJECT_DIR%"

REM 日志文件
set LOG_FILE=%PROJECT_DIR%\auto_update.log
set ERROR_LOG=%PROJECT_DIR%\auto_update_error.log

REM 获取当前时间
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a:%%b)
set DATETIME=%mydate% %mytime%

REM 记录开始
echo ======================================== >> "%LOG_FILE%"
echo [%DATETIME%] 开始自动更新 >> "%LOG_FILE%"
echo ======================================== >> "%LOG_FILE%"

REM 执行 Python 脚本（自动回答 'y' 进行推送）
echo y | python "%SCRIPT_DIR%\auto_update.py" >> "%LOG_FILE%" 2>> "%ERROR_LOG%"

REM 检查执行结果
if %ERRORLEVEL% EQU 0 (
    echo [%DATETIME%] 更新成功 >> "%LOG_FILE%"
) else (
    echo [%DATETIME%] 更新失败 ^(错误代码: %ERRORLEVEL%^) >> "%LOG_FILE%"
)

echo. >> "%LOG_FILE%"

