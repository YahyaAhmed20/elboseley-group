#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🚀 Rovana Inventory System - Production Launcher
Author: Yahya Ahmed Abdelatif Mahran
Email: yahmdh6@gmail.com
License: Commercial - Unauthorized distribution prohibited
"""

import os
import sys
import traceback
import shutil
import datetime
import logging
from pathlib import Path

# =============================================================================
# ⚙️ إعدادات اللوج (لتتبع الأخطاء والمشاكل)
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# 🛡️ دوال الحماية والنسخ الاحتياطي
# =============================================================================

def get_data_directory():
    """
    تحديد مسار آمن لحفظ البيانات (خارج مجلد البرنامج)
    يعمل على ويندوز فقط (حسب متطلبات المشروع)
    """
    try:
        local_app_data = os.getenv('LOCALAPPDATA')
        if not local_app_data:
            # Fallback لو البيئة مش معرفة (نادراً)
            local_app_data = os.path.expanduser('~\\AppData\\Local')
        
        data_dir = Path(local_app_data) / 'Rovana'
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    except Exception as e:
        logger.error(f"❌ Failed to create data directory: {e}")
        # Fallback أخير: مجلد بجانب البرنامج
        fallback = Path(__file__).parent / 'data'
        fallback.mkdir(exist_ok=True)
        return fallback

def create_backup(db_path: Path, backup_dir: Path, keep_days: int = 7):
    """
    إنشاء نسخ احتياطي تلقائي لقاعدة البيانات
    + حذف النسخ القديمة تلقائياً
    """
    try:
        if not db_path.exists():
            logger.info("📭 No database file found to backup")
            return True
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"rovana_backup_{timestamp}.sqlite3"
        
        shutil.copy2(db_path, backup_file)
        logger.info(f"💾 Backup created: {backup_file}")
        
        # حذف النسخ الأقدم من `keep_days` أيام
        deleted = 0
        for old_backup in backup_dir.glob("rovana_backup_*.sqlite3"):
            try:
                file_age = datetime.datetime.now().timestamp() - old_backup.stat().st_mtime
                if file_age > (keep_days * 86400):  # 86400 ثانية في اليوم
                    old_backup.unlink()
                    deleted += 1
            except Exception as e:
                logger.warning(f"⚠️ Could not delete old backup {old_backup}: {e}")
        
        if deleted:
            logger.info(f"🗑️ Deleted {deleted} old backup(s)")
        
        return True
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        return False  # لا نوقف البرنامج لو النسخ الاحتياطي فشل

def run_migrations():
    """
    تشغيل ميجريشنز دجانجو أوتوماتيك
    عشان الجداول الجديدة تتضاف من غير ما البيانات تضيع
    """
    try:
        from django.core.management import call_command
        call_command('migrate', verbosity=0, interactive=False)
        logger.info("✅ Database migrations applied successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

# =============================================================================
# 🚀 نقطة الدخول الرئيسية
# =============================================================================

def main():
    logger.info("🚀 Rovana Inventory System - Starting...")
    
    try:
        # 🔥 1. تحديد مسار البيانات (قبل أي حاجة)
        DATA_DIR = get_data_directory()
        DB_PATH = DATA_DIR / "db.sqlite3"
        BACKUP_DIR = DATA_DIR / "backups"
        
        logger.info(f"📁 Data directory: {DATA_DIR}")
        logger.info(f"🗄️ Database path: {DB_PATH}")
        
        # 🔥 2. إعداد متغير البيئة لدجانجو (قبل أي import)
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
        
        # 🔥 3. تهيئة دجانجو
        import django
        django.setup()
        logger.info("✅ Django initialized")
        
        # 🔥 4. (اختياري لكن مفضل) إنشاء نسخ احتياطي قبل التشغيل
        # لو عايز توفر وقت التشغيل الأول، ممكن تشيل السطر ده
        if DB_PATH.exists():
            logger.info("🔄 Creating auto-backup...")
            create_backup(DB_PATH, BACKUP_DIR, keep_days=7)
        
        # 🔥 5. تشغيل الميجريشنز أوتوماتيك
        logger.info("🔄 Applying database migrations...")
        run_migrations()
        
        # 🔥 6. استيراد مكونات الويب
        import webbrowser
        from threading import Timer
        from waitress import serve
        from project.wsgi import application
        
        # 🔥 7. تغيير مجلد العمل لـ BASE_DIR
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        os.chdir(BASE_DIR)
        
        # 🔥 8. دالة فتح المتصفح
        def open_browser():
            try:
                webbrowser.open("http://127.0.0.1:8000")
                logger.info("🌐 Browser opened: http://127.0.0.1:8000")
            except Exception as e:
                logger.warning(f"⚠️ Could not open browser: {e}")
        
        # 🔥 9. رسالة البداية
        print("\n" + "="*60)
        print("  🏭 Rovana Inventory System - Ready")
        print(f"  📍 URL: http://127.0.0.1:8000")
        print(f"  💾 Data: {DATA_DIR}")
        print("="*60 + "\n")
        
        # 🔥 10. فتح المتصفح بعد ثانيتين
        Timer(2, open_browser).start()
        
        # 🔥 11. تشغيل السيرفر (Waitress - إنتاجي وثابت)
        logger.info("🎧 Starting server on http://127.0.0.1:8000")
        serve(
            application,
            host="127.0.0.1",
            port=8000,
            threads=4,  # عدد الثريدات للتعامل مع الطلبات المتزامنة
            channel_timeout=30  # وقت الانتظار للطلبات الطويلة
        )
        
    except KeyboardInterrupt:
        logger.info("👋 Shutdown requested by user")
        sys.exit(0)
        
    except Exception as e:
        logger.critical("🔥 FATAL ERROR", exc_info=True)
        print("\n" + "🔥"*20)
        print("حدث خطأ غير متوقع في تشغيل النظام")
        print(f"التفاصيل: {e}")
        print("🔥"*20 + "\n")
        traceback.print_exc()
        input("اضغط Enter للخروج...")
        sys.exit(1)

# =============================================================================
# 🏁 نقطة الدخول
# =============================================================================

if __name__ == "__main__":
    main()