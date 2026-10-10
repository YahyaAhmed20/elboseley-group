@echo off
title Rovana Updater
echo ============================
echo   Rovana - جاري التحديث...
echo ============================

:: إيقاف البرنامج لو شغال
taskkill /f /im run.exe >nul 2>&1
timeout /t 2 >nul

:: تحديد مسار البرنامج القديم على الـ Desktop
set OLD=%USERPROFILE%\Desktop\run

:: نسخ الملفات الجديدة (من مجلد الـ update بجانب الـ bat)
xcopy /e /y /i "%~dp0*" "%OLD%\"

echo.
echo ✓ تم التحديث بنجاح!
echo جاري تشغيل البرنامج...
timeout /t 2 >nul

start "" "%OLD%\run.exe"
exit