@echo off
REM @Auth: Potato
REM @date 2023/4/12 17:22

REM $1 [必填] 新添文件
REM $2 [必填] 更新内容、可为时间字符串
REM $3 [选填] 移除文件

if not "%~3"=="" (
    git rm %~3
)

git add %~1
timeout /t 3 /nobreak >nul
git commit -m "update-%~2"
timeout /t 3 /nobreak >nul
git push -u origin main -f
