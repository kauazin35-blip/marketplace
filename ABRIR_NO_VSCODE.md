# 🚀 Como abrir e rodar no VS Code

## 1. Descompacte o .zip
Extraia a pasta `marketplace` para onde quiser (ex.: Área de Trabalho).

## 2. Abra no VS Code
- Abra o **VS Code**
- Menu **Arquivo → Abrir Pasta…** → selecione a pasta `marketplace`
- (Opcional) Instale a extensão **Claude / Claude Code** e a extensão **Python**

## 3. Instale tudo (1 clique)
No VS Code, abra o terminal (**Terminal → Novo Terminal**) e rode:
```bat
setup.bat
```
Isso instala Python/FFmpeg (se faltar), cria o ambiente, instala as libs,
cria o `.env` e baixa o modelo de IA do Ollama.

> Falta o **Ollama**? Baixe em https://ollama.com/download , instale e rode
> `ollama pull qwen2.5:7b`.

## 4. Inicie o site
```bat
run.bat
```
Quando aparecer `Uvicorn running on http://0.0.0.0:8000`, abra no navegador:
```
http://localhost:8000
```

## 5. Usar
Suba um vídeo **ou** cole um link do YouTube → **Gerar cortes** → baixe os cortes 9:16 com legenda.

---

### Dicas
- **Sem GPU?** No `.env` troque `WHISPER_DEVICE=cpu` e `WHISPER_COMPUTE_TYPE=int8`.
- **Quer testar rápido?** No `.env` use `WHISPER_MODEL=tiny` (menos preciso, bem mais rápido).
- **Indicador de saúde** no topo do site mostra `ffmpeg ✓ · GPU ✓ · ollama ✓`.

### Pedir ajuda ao Claude dentro do VS Code
Abra o chat do Claude e diga, por exemplo:
> "Leia o README.md e me ajude a rodar este projeto" ou
> "Adicione proporção 1:1 e 4:5 nos cortes".
