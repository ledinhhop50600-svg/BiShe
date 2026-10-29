@echo off
title 自媒体平台管理系统 - 一键启动
cd /d %~dp0

rem ---------- 0) 工具链（JDK17 / Maven）----------
rem 本机工具链在 F:/Dev/toolchains；换机器时按实际路径修改，或把 bin 加入系统 PATH
if exist "F:/Dev/toolchains/jdk17/bin/java.exe" (
    set "JAVA_HOME=F:/Dev/toolchains/jdk17"
    set "PATH=F:/Dev/toolchains/jdk17/bin;F:/Dev/toolchains/maven/bin;%PATH%"
)

echo.
echo ==========================================================
echo    自媒体平台管理系统 · 一键启动
echo ==========================================================
echo.

rem ---------- 1) MySQL ----------
echo [1/4] 检查 MySQL 是否在运行（3306 端口）...
netstat -ano | findstr ":3306" | findstr "LISTENING" >nul
if not errorlevel 1 goto mysql_ok

echo       MySQL 未运行，尝试启动 MySQL80 服务 ...
net start MySQL80
if not errorlevel 1 goto mysql_ok
echo.
echo       [!] 自动启动失败，通常是需要管理员权限。请任选一种方式处理：
echo           1. 右键本文件，选择"以管理员身份运行"
echo           2. 打开"服务"窗口，手动启动 MySQL80
echo.
pause
exit /b 1

:mysql_ok
echo       MySQL 已运行

rem ---------- 2) 后端 ----------
netstat -ano | findstr ":8080" | findstr "LISTENING" >nul
if not errorlevel 1 goto backend_running
echo [2/4] 启动后端 SpringBoot（端口 8080）...
start "后端 SpringBoot" cmd /k "cd /d %~dp0backend && mvn spring-boot:run"
goto backend_done
:backend_running
echo [2/4] 后端已在运行，跳过启动。要重启请先关闭"后端 SpringBoot"窗口。

:backend_done

rem ---------- 3) 前端 ----------
netstat -ano | findstr ":5173" | findstr "LISTENING" >nul
if not errorlevel 1 goto frontend_running
echo [3/4] 启动前端 Vue（端口 5173）...
start "前端 Vue" cmd /k "cd /d %~dp0frontend && npm run dev"
goto frontend_done
:frontend_running
echo [3/4] 前端已在运行，跳过启动。要重启请先关闭"前端 Vue"窗口。

:frontend_done

rem ---------- 4) 智能体服务 ----------
netstat -ano | findstr ":8001" | findstr "LISTENING" >nul
if not errorlevel 1 goto agent_running
echo [4/4] 启动智能体服务 FastAPI（端口 8001）...
start "智能体 FastAPI" cmd /k "cd /d %~dp0agent && .venv\Scripts\python.exe -m uvicorn main:app --port 8001"
goto agent_done
:agent_running
echo [4/4] 智能体服务已在运行，跳过启动。

:agent_done

echo.
echo 等待服务启动，约 25 秒，后端首次启动较慢 ...
ping -n 26 127.0.0.1 >nul

echo 检查后端 ...
curl -s -o nul --max-time 5 http://localhost:8080/api/health
if errorlevel 1 echo       [!] 后端尚未就绪，稍等片刻后手动刷新页面即可
if not errorlevel 1 echo       后端已就绪

echo 检查前端 ...
curl -s -o nul --max-time 5 http://localhost:5173/
if errorlevel 1 echo       [!] 前端尚未就绪，请看"前端 Vue"窗口里的提示
if not errorlevel 1 echo       前端已就绪

echo 检查智能体服务 ...
curl -s -o nul --max-time 5 http://localhost:8001/health
if errorlevel 1 echo       [!] 智能体服务尚未就绪，请看"智能体 FastAPI"窗口
if not errorlevel 1 echo       智能体服务已就绪

curl -s -o nul --max-time 5 http://localhost:5173/
if not errorlevel 1 start http://localhost:5173/

echo.
echo ==========================================================
echo   启动流程结束
echo.
echo   * 页面地址：     http://localhost:5173/
echo   * 后端健康检查： http://localhost:8080/api/health
echo   * 智能体服务：   http://localhost:8001/health
echo   * 智能体接口文档： http://localhost:8001/docs
echo.
echo   * 停止全部服务：关闭"后端 SpringBoot"、"前端 Vue"、"智能体 FastAPI"三个窗口
echo   注意：关闭本窗口不会停止服务。
echo ==========================================================
echo.
pause
