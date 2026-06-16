#!/usr/bin/env bash
# Inicia o cortador de vídeo (Linux/Mac). Use run.bat no Windows.
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "==> Criando ambiente virtual..."
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "==> Instalando dependências..."
pip install -q -r requirements.txt

echo "==> Subindo o servidor em http://localhost:8000"
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
