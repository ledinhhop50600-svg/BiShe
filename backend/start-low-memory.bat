@echo off
cd /d %~dp0
rem Low-memory launcher: prefer the packaged jar so no Maven parent JVM stays alive.
rem Build once with: mvn -DskipTests package
setlocal
rem Drop a stale JAVA_HOME (e.g. a toolchain that moved), then fall back to the local JDK 17.
if defined JAVA_HOME if not exist "%JAVA_HOME%/bin/java.exe" set "JAVA_HOME="
if not defined JAVA_HOME if exist "F:/Dev/toolchains/jdk17/bin/java.exe" set "JAVA_HOME=F:/Dev/toolchains/jdk17"
set "JAR=target/backend-0.0.1-SNAPSHOT.jar"
set "JAVA_EXE=java"
if defined JAVA_HOME set "JAVA_EXE=%JAVA_HOME%/bin/java.exe"
if not exist "%JAR%" (
    echo [low-memory] jar not found; falling back to mvn spring-boot:run
    echo [low-memory] run "mvn -DskipTests package" to remove the Maven parent JVM
    call mvn -Dspring-boot.run.jvmArguments="-Xms64m -Xmx256m -Xss512k -XX:MaxMetaspaceSize=128m -XX:+UseSerialGC" spring-boot:run
    exit /b
)
echo [low-memory] running %JAR%
"%JAVA_EXE%" -Xms64m -Xmx256m -Xss512k -XX:MaxMetaspaceSize=128m -XX:+UseSerialGC -jar "%JAR%"
