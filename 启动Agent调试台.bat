@echo off
setlocal EnableExtensions
title Agent 调试台 - 自媒体平台
cd /d "%~dp0"

echo.
echo ============================================================
echo   Agent 调试台 - 只启动智能体并打开运行观察页
echo ============================================================
echo.

netstat -ano | findstr ":8001" | findstr "LISTENING" >nul
if not errorlevel 1 goto agent_ok
echo [1/2] 启动 Agent FastAPI（8001）...
start "Agent 调试台" cmd /k "cd /d %~dp0agent && .venv\Scripts\python.exe -m uvicorn main:app --port 8001"
goto agent_started
:agent_ok
echo [1/2] Agent 已在运行，跳过启动
:agent_started

echo [2/2] 等待 Agent 就绪...
ping -n 9 127.0.0.1 >nul
curl -s -o nul --max-time 5 http://localhost:8001/health
if errorlevel 1 (
    echo.
    echo [错误] Agent 还没有就绪，请查看“Agent 调试台”窗口里的报错。
    pause
    exit /b 1
)

echo Agent：OK
echo 打开 Agent 调试台：http://localhost:8001/debug
start "" "http://localhost:8001/debug"
echo.
echo 提示：调试台只允许本机访问，不写入正式的 audit_record。
echo 关闭本窗口不会停止 Agent；要停止请关闭“Agent 调试台”命令行窗口。
pause
