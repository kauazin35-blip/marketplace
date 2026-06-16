# ✂️ ClipForge — Cortador de Vídeo Automático (tipo OpusClip)

Ferramenta completa que transforma vídeos longos em **cortes verticais virais
(9:16)** automaticamente: transcreve o áudio, usa IA para encontrar os
**ganchos e temas** mais virais, reenquadra seguindo o rosto do falante e
**queima legendas** no estilo Reels/TikTok. Roda **100% local** — feito para
uma máquina com **GPU NVIDIA (RTX 5070)** e **Intel Core Ultra 7**.

```
Vídeo longo ──▶ Transcrição (Whisper/GPU) ──▶ IA acha os ganchos ──▶
        Reframe 9:16 (rosto) + Legendas ──▶ Cortes prontos pra baixar
```

---

## ✨ Funcionalidades

- 📁 **Upload de arquivo** ou ▶️ **link do YouTube** (`yt-dlp`)
- 🎙️ **Transcrição na GPU** com `faster-whisper` (timestamps por palavra)
- 🧠 **IA de cortes** que escolhe os melhores momentos por **gancho/tema** e dá
  um **score de viralidade** (Ollama offline, ou Claude opcional)
- 🎯 **Reframe 9:16** com rastreio de rosto (OpenCV)
- 💬 **Legendas virais** queimadas no vídeo (estilo karaokê/punchy)
- 🌐 **Site** com upload, progresso em tempo real e galeria de cortes
- 🔌 **Rede de segurança**: se não houver LLM, divide o vídeo automaticamente

---

## 🗂️ Estrutura do projeto

```
marketplace/
├── README.md
├── requirements.txt          # dependências Python
├── .env.example              # configuração (copie p/ .env)
├── run.sh / run.bat          # iniciar (Linux/Mac | Windows)
├── data/                     # uploads, áudio e cortes (gerado)
│   └── clips/                # cortes finais (.mp4)
├── backend/
│   └── app/
│       ├── main.py           # API FastAPI + serve o site
│       ├── config.py         # configurações (env)
│       ├── schemas.py        # modelos de dados (Pydantic)
│       ├── jobs.py           # fila de jobs + execução em thread
│       └── pipeline/
│           ├── media.py      # download YouTube + extração de áudio
│           ├── transcribe.py # faster-whisper (GPU)
│           ├── analyze.py    # IA: escolhe ganchos/temas (cérebro)
│           ├── captions.py   # legendas .ass estilo viral
│           ├── reframe.py    # crop 9:16 seguindo rosto (OpenCV)
│           └── render.py     # ffmpeg: corta + reframe + legenda
└── frontend/
    ├── index.html            # site
    ├── styles.css
    └── app.js
```

---

## 🚀 Como rodar

### 1. Pré-requisitos (instalar uma vez)

- **Python 3.10+**
- **FFmpeg** (inclui `ffprobe`) no PATH
  - Windows: `winget install Gyan.FFmpeg`
  - Linux: `sudo apt install ffmpeg`
- **GPU (recomendado):** drivers NVIDIA + **CUDA 12** + **cuDNN 9**
  (para o `faster-whisper` usar a 5070)
- **Ollama** (IA de cortes offline) — https://ollama.com
  ```bash
  ollama pull qwen2.5:7b      # modelo usado por padrão
  ```

### 2. Configurar

```bash
cp .env.example .env          # ajuste se quiser (modelo, idioma, etc.)
```

### 3. Iniciar

**Windows (sua máquina):**
```bat
run.bat
```
**Linux/Mac:**
```bash
./run.sh
```

Depois abra **http://localhost:8000** no navegador.

> Sem GPU? Defina `WHISPER_DEVICE=cpu` e `WHISPER_COMPUTE_TYPE=int8` no `.env`
> (funciona, só mais lento).

---

## ⚙️ Configurações úteis (`.env`)

| Variável | Padrão | O que faz |
|---|---|---|
| `WHISPER_MODEL` | `large-v3` | Precisão da transcrição (use `medium` p/ mais velocidade) |
| `WHISPER_DEVICE` | `cuda` | `cuda` (GPU) ou `cpu` |
| `LLM_PROVIDER` | `ollama` | `ollama` (offline) ou `claude` (API) |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Modelo local que escolhe os cortes |
| `MAX_CLIPS` | `10` | Quantos cortes gerar |
| `CLIP_MIN/MAX_SECONDS` | `15` / `75` | Duração dos cortes |
| `BURN_CAPTIONS` | `true` | Queimar legendas no vídeo |

---

## 🔌 API (resumo)

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/jobs` | Cria job (form: `file` **ou** `youtube_url`, `language`, `max_clips`) |
| `GET` | `/api/jobs/{id}` | Status + cortes do job |
| `GET` | `/api/jobs` | Lista todos os jobs |
| `GET` | `/api/health` | Checa ffmpeg, GPU e LLM |
| `GET` | `/clips/{arquivo}` | Baixa um corte |

---

## 🧠 Como a IA escolhe os cortes

`analyze.py` envia a transcrição (com tempos) para o LLM com um prompt de
"editor de virais", pedindo trechos com **gancho forte**, ideia completa e
potencial de compartilhamento. O retorno é um JSON com `start/end/título/
gancho/tema/score`. Há validação de duração e uma **heurística de fallback**
caso nenhum LLM esteja disponível — então o app **nunca quebra**.

---

## ⚠️ Observações

- O download de vídeos do YouTube deve respeitar os Termos de Uso da plataforma
  e direitos autorais. Use com conteúdo seu ou autorizado.
- Primeiro uso baixa o modelo Whisper (alguns GB) — pode demorar.
