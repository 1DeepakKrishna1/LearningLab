@echo off
REM ============================================================
REM  Dummy REST API Servers - selective launcher
REM ============================================================
REM  Usage:
REM    run-servers.bat              -> interactive menu
REM    run-servers.bat 1            -> start Bookstore only
REM    run-servers.bat 1 3          -> start Bookstore + School
REM    run-servers.bat all          -> start all four
REM
REM  Each selected server starts in its OWN console window so you
REM  can close them independently.
REM
REM    1 = Bookstore  (FastAPI,     port 8001)
REM    2 = Inventory  (FastAPI,     port 8002)
REM    3 = School     (Spring Boot, port 8081)
REM    4 = Hospital   (Spring Boot, port 8082)
REM ============================================================
setlocal enabledelayedexpansion
set "ROOT=%~dp0"

REM --- If no arguments, show the interactive menu ---------------
if "%~1"=="" goto MENU

REM --- Arguments supplied: process them and exit ---------------
set "ARGS=%*"
if /I "%ARGS%"=="all" set "ARGS=1 2 3 4"
for %%S in (%ARGS%) do call :START %%S
echo.
echo Requested servers have been launched in separate windows.
goto END

:MENU
echo.
echo ============================================
echo   Dummy REST API Servers - Launcher
echo ============================================
echo   1 = Bookstore  (FastAPI,     port 8001)
echo   2 = Inventory  (FastAPI,     port 8002)
echo   3 = School     (Spring Boot, port 8081)
echo   4 = Hospital   (Spring Boot, port 8082)
echo   5 = ALL servers
echo   0 = Exit
echo ============================================
set "CHOICE="
set /p "CHOICE=Enter selection (e.g. 1 3  or  5 for all): "
if "%CHOICE%"=="" goto MENU
if "%CHOICE%"=="0" goto END
if "%CHOICE%"=="5" set "CHOICE=1 2 3 4"
for %%S in (%CHOICE%) do call :START %%S
echo.
echo Selected servers have been launched in separate windows.
goto END

REM ------------------------------------------------------------
REM  :START <n>  -> launch server number n in a new window
REM ------------------------------------------------------------
:START
if "%~1"=="1" (
    echo Starting Bookstore server [FastAPI] on port 8001 ...
    start "Bookstore (8001)" cmd /k "cd /d "%ROOT%python-fastapi\bookstore-server" && pip install -q -r requirements.txt && python main.py"
    goto :eof
)
if "%~1"=="2" (
    echo Starting Inventory server [FastAPI] on port 8002 ...
    start "Inventory (8002)" cmd /k "cd /d "%ROOT%python-fastapi\inventory-server" && pip install -q -r requirements.txt && python main.py"
    goto :eof
)
if "%~1"=="3" (
    echo Starting School server [Spring Boot] on port 8081 ...
    start "School (8081)" cmd /k "cd /d "%ROOT%java-springboot\school-server" && mvn spring-boot:run"
    goto :eof
)
if "%~1"=="4" (
    echo Starting Hospital server [Spring Boot] on port 8082 ...
    start "Hospital (8082)" cmd /k "cd /d "%ROOT%java-springboot\hospital-server" && mvn spring-boot:run"
    goto :eof
)
echo   [skip] Unknown selection: %~1
goto :eof

:END
endlocal
