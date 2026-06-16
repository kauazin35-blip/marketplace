@echo off
REM Inicia o cortador de video (Windows). Para sua maquina: RTX 5070 + Core Ultra 7.
cd /d "%~dp0"

if not exist ".venv" (
  echo ==^> Criando ambiente virtual...
  python -m venv .venv
)
call .venv\Scripts\activate.bat

echo ==^> Instalando dependencias...
pip install -q -r requirements.txt

echo ==^> Subindo o servidor em http://localhost:8000
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
