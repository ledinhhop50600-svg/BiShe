@echo off
netstat -ano | findstr ":8080" | findstr "LISTENING" >nul
echo A_errorlevel=%errorlevel%
netstat -ano | findstr ":8080" | findstr "LISTENING" >nul 2>&1
echo B_errorlevel=%errorlevel%
netstat -ano | findstr ":5555" | findstr "LISTENING" >nul
echo C_δռ�ö˿�_errorlevel=%errorlevel%
netstat -ano | findstr ":8080" | findstr "LISTENING"
echo D_errorlevel=%errorlevel%
