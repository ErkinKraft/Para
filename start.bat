@echo off
chcp 65001 >nul
title ErkinKraft Launcher
color 4
mode con cols=60 lines=30

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║                                                      ║
setlocal enabledelayedexpansion
set "line1=   ███████╗██████╗ ██╗  ██╗██╗███╗   ██╗"
set "line2=   ██╔════╝██╔══██╗██║ ██╔╝██║████╗  ██║"
set "line3=   █████╗  ██████╔╝█████╔╝ ██║██╔██╗ ██║"
set "line4=   ██╔══╝  ██╔══██╗██╔═██╗ ██║██║╚██╗██║"
set "line5=   ███████╗██║  ██║██║  ██╗██║██║ ╚████║"
set "line6=   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝"
set "line7=   ██╗  ██╗██████╗  █████╗ ███████╗████████╗"
set "line8=   ██║ ██╔╝██╔══██╗██╔══██╗██╔════╝╚══██╔══╝"
set "line9=   █████╔╝ ██████╔╝███████║█████╗     ██║"
set "line10=  ██╔═██╗ ██╔══██╗██╔══██║██╔══╝     ██║"
set "line11=  ██║  ██╗██║  ██║██║  ██║██║        ██║"
set "line12=  ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝        ╚═╝"

for /l %%i in (1,1,12) do (
    echo ║   !line%%i!   ║
)
echo ║                                                      ║
echo ╚══════════════════════════════════════════════════════╝
echo.
echo        [1] Запустить
echo        [2] Установить зависимости
echo        [3] Выход
echo.
set /p choice="Выберите действие (1-3): "

if "%choice%"=="1" (
    echo.
    echo Запускаю пару...
    timeout /t 2 >nul
    python main.py
) else if "%choice%"=="2" (
    echo.
    echo Запускаю install.bat...
    timeout /t 2 >nul
    install.bat
) else if "%choice%"=="3" (
    echo.
    echo Покеда!
    timeout /t 1 >nul
    exit
) else (
    echo.
    echo Неверный выбор! Попробуйте снова.
    timeout /t 2 >nul
    cls
    %0
)                             
