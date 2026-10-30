@echo off
setlocal EnableExtensions
title 自媒体平台 - 一键启动
cd /d "%~dp0"

echo.
echo ============================================================
echo   自媒体内容审核与多平台适配系统 - 一键启动
echo ============================================================
echo.

rem ---------- 0) JDK17 / Maven ----------
if exist "F:/Dev/toolchains/jdk17/bin/java.exe" (
    set "JAVA_HOME=F:/Dev/toolchains/jdk17"
    set "PATH=F:/Dev/toolchains/jdk17/bin;F:/Dev/toolchains/maven/bin;%PATH%"
)
if not defined JAVA_HOME (
    echo [错误] 没有找到 JDK17。请安装 JDK17，或修改本脚本顶部的 JAVA_HOME 路径。
    pause
    exit /b 1
)

rem ---------- 1) MySQL ----------
netstat -ano | findstr ":3306" | findstr "LISTENING" >nul
if not errorlevel 1 goto mysql_ok
echo [1/4] MySQL 未运行，尝试启动 MySQL80 ...
net start MySQL80 >nul 2>&1
if not errorlevel 1 goto mysql_ok
echo.
echo [错误] MySQL 启动失败。请确认服务名是 MySQL80，或手动启动 MySQL 后重试。
pause
exit /b 1
:mysql_ok
echo [1/4] MySQL 已运行

rem ---------- 2) Backend ----------
netstat -ano | findstr ":8080" | findstr "LISTENING" >nul
if not errorlevel 1 goto backend_ok
echo [2/4] 启动后端 SpringBoot（8080）...
start "后端 SpringBoot" cmd /k "cd /d %~dp0backend && start-low-memory.bat"
goto backend_done
:backend_ok
echo [2/4] 后端已在运行，跳过
:backend_done

rem ---------- 3) Agent ----------
netstat -ano | findstr ":8001" | findstr "LISTENING" >nul
if not errorlevel 1 goto agent_ok
echo [3/4] 启动 Agent FastAPI（8001）...
start "智能体 FastAPI" cmd /k "cd /d %~dp0agent && .venv/Scripts/python.exe -m uvicorn main:app --port 8001"
goto agent_done
:agent_ok
echo [3/4] Agent 已在运行，跳过
:agent_done

rem ---------- 4) Frontend ----------
netstat -ano | findstr ":5173" | findstr "LISTENING" >nul
if not errorlevel 1 goto frontend_ok
echo [4/4] 启动前端 Vue（5173）...
start "前端 Vue" cmd /k "cd /d %~dp0frontend && npm run dev"
goto frontend_done
:frontend_ok
echo [4/4] 前端已在运行，跳过
:frontend_done

echo.
echo 等待服务就绪（约 25 秒）...
ping -n 26 127.0.0.1 >nul

echo.
echo 健康检查：
curl -s -o nul --max-time 5 http://localhost:8080/api/health
if errorlevel 1 echo   后端：未就绪，请查看“后端 SpringBoot”窗口
if not errorlevel 1 echo   后端：OK
curl -s -o nul --max-time 5 http://localhost:8001/health
if errorlevel 1 echo   Agent：未就绪，请查看“智能体 FastAPI”窗口
if not errorlevel 1 echo   Agent：OK
curl -s -o nul --max-time 5 http://localhost:5173/
if errorlevel 1 echo   前端：未就绪，请查看“前端 Vue”窗口
if not errorlevel 1 echo   前端：OK

echo.
echo 系统首页：http://localhost:5173/
echo Agent 调试台：http://localhost:8001/debug
echo 演示账号：admin / reviewer / creator3 / creator4 / creator5，密码均为 123456
echo.
start "" "http://localhost:5173/"
if /I "%~1"=="debug" start "" "http://localhost:8001/debug"

echo 启动完成。关闭本窗口不会停止服务；停止服务请关闭对应的命令行窗口。
echo.
pause
