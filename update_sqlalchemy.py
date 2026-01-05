"""Обновление SQLAlchemy для совместимости с Python 3.13."""
import subprocess
import sys

print("Обновляю SQLAlchemy для совместимости с Python 3.13...")
print("="*60)

try:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "sqlalchemy>=2.0.36"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✓ SQLAlchemy обновлен успешно")
        if result.stdout:
            print(result.stdout)
    else:
        print("✗ Ошибка обновления")
        print(result.stderr)
        
    print("\nТеперь попробуйте снова:")
    print("  py quick_check.py")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")

