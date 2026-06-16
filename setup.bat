@echo off
REM ============================================================
REM  ClipForge - Instalacao automatica (Windows)
REM  Roda uma vez. Depois use run.bat para iniciar o site.
REM ============================================================
cd /d "%~dp0"
echo.
echo ====== ClipForge - Setup ======
echo.

REM 1) Verifica Python
where python >nul 2>&1
if errorlevel 1 (
  echo [!] Python nao encontrado. Instalando via winget...
  winget install -e --id Python.Python.3.12
  echo [!] Feche e reabra este arquivo apos a instalacao do Python.
  pause
  exit /b
)

REM 2) Verifica FFmpeg
where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo [!] FFmpeg nao encontrado. Instalando via winget...
  winget install -e --id Gyan.FFmpeg
  echo [!] Feche e reabra este arquivo apos a instalacao do FFmpeg.
  pause
  exit /b
)

REM 3) Ambiente virtual + dependencias
if not exist ".venv" (
  echo ==^> Criando ambiente virtual...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
echo ==^> Instalando dependencias Python (pode demorar)...
python -m pip install --upgrade pip -q
pip install -q -r requirements.txt

REM 4) .env
if not exist ".env" (
  copy .env.example .env >nul
  echo ==^> Arquivo .env criado.
)

REM 5) Ollama (IA dos cortes)
where ollama >nul 2>&1
if errorlevel 1 (
  echo.
  echo [!] Ollama nao encontrado. Baixe e instale em: https://ollama.com/download
  echo     Depois rode:  ollama pull qwen2.5:7b
) else (
  echo ==^> Baixando modelo de IA (qwen2.5:7b)...
  ollama pull qwen2.5:7b
)

echo.
echo ====== Tudo pronto! ======
echo Agora rode:  run.bat
echo E abra:      http://localhost:8000
echo.
pause
