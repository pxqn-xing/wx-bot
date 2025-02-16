@echo off
setlocal enabledelayedexpansion

:: ���Python��װ
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ����δ��⵽Python���밲װPython 3.8����߰汾��
    pause
    exit /b 1
)

:: ��ȡPython�汾
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "pyversion=%%i"

:: �����汾��
for /f "tokens=1,2 delims=." %%a in ("%pyversion%") do (
    set major=%%a
    set minor=%%b
)

:: ��֤�汾Ҫ��
if %major% lss 3 (
    echo ����Python�汾%pyversion%���ͣ���Ҫ3.8����ߡ�
    pause
    exit /b 1
)

if %major% equ 3 if %minor% lss 8 (
    echo ����Python�汾%pyversion%���ͣ���Ҫ3.8����ߡ�
    pause
    exit /b 1
)

:: ���pip��װ
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ����δ��⵽pip����ȷ��pip�Ѱ�װ��
    pause
    exit /b 1
)

:: ��װ������
echo ���ڰ�װ������...
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ���������װʧ�ܡ�
    pause
    exit /b 1
)

echo �����������ѳɹ���װ��
pause