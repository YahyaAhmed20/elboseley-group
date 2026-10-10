import os
import shutil
import subprocess
import sys

VERSION = "1.1"  # غير الرقم دا مع كل إصدار

def build():
    print(f"🔨 Building Rovana v{VERSION}...")
    
    # 1. مسح القديم
    if os.path.exists("dist"):
        shutil.rmtree("dist")
        print("🗑️ Old dist deleted")
    
    # 2. PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "run.py",
        "--add-data", "templates;templates",
        "--add-data", "static;static",
        "--hidden-import=waitress",
        "--hidden-import=django",
        "--hidden-import=rest_framework",
        "--noconfirm"
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print("❌ Build failed!")
        return
    
    # 3. كتابة رقم الإصدار جوه dist
    with open(f"dist/run/version.txt", "w") as f:
        f.write(VERSION)
    
    # 4. نسخ update.bat جوه dist
    shutil.copy("update.bat", "dist/run/update.bat")
    
    print(f"✅ Build successful! → dist/run/")
    print(f"📦 ابعت مجلد dist/run/ كامل للشركة")

if __name__ == "__main__":
    build()