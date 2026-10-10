@echo off
setlocal
cd /d "%~dp0"

REM تشغيل تذكيرات العملاء يوميًا الساعة 09:00.
REM تأكد من ضبط TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID في Environment Variables.

schtasks /Create /TN "Rovana Customer Reminders" /TR "\"%~dp0send_customer_reminders.bat\"" /SC DAILY /ST 09:00 /F

if %ERRORLEVEL% EQU 0 (
    echo تم إنشاء مهمة التذكيرات اليومية بنجاح.
) else (
    echo فشل إنشاء المهمة. جرّب تشغيل الملف كمسؤول.
)
pause
