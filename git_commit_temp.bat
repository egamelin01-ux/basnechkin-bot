@echo off
chcp 65001 >nul
git add src/agent_router.py src/deepseek_client.py
git commit -m "Исправлено несоответствие требований к длине басен и усилены инструкции" -m "- Синхронизированы требования к длине: везде 500-800 слов (было несоответствие 800-900 vs 500-800)" -m "- Усилены инструкции для модели с явным указанием обязательности соблюдения длины" -m "- Исправлено в agent_router.py и deepseek_client.py"
del git_commit_temp.bat

