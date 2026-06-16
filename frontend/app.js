// Frontend do ClipForge — comunica com a API FastAPI.

const $ = (sel) => document.querySelector(sel);

let selectedFile = null;
let pollTimer = null;

// ---------- Saúde do sistema ----------
async function checkHealth() {
  const el = $("#health");
  try {
    const r = await fetch("/api/health");
    const h = await r.json();
    const parts = [];
    parts.push(h.ffmpeg ? "ffmpeg ✓" : "ffmpeg ✗");
    parts.push(h.gpu_cuda ? "GPU ✓" : "GPU —");
    parts.push(h.llm_ready ? `${h.llm_provider} ✓` : `${h.llm_provider} ✗`);
    el.textContent = parts.join("  ·  ");
    el.className = "health " + (h.ffmpeg && h.llm_ready ? "ok" : "bad");
  } catch {
    el.textContent = "API offline";
    el.className = "health bad";
  }
}

// ---------- Abas ----------
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const target = tab.dataset.tab;
    $("#panel-upload").classList.toggle("hidden", target !== "upload");
    $("#panel-youtube").classList.toggle("hidden", target !== "youtube");
  });
});

// ---------- Dropzone ----------
const dropzone = $("#dropzone");
const fileInput = $("#fileInput");

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) setFile(fileInput.files[0]);
});
["dragover", "dragenter"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.add("drag");
  })
);
["dragleave", "drop"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag");
  })
);
dropzone.addEventListener("drop", (e) => {
  if (e.dataTransfer.files.length) setFile(e.dataTransfer.files[0]);
});

function setFile(file) {
  selectedFile = file;
  $("#fileName").textContent = file.name;
}

// ---------- Iniciar job ----------
$("#startBtn").addEventListener("click", async () => {
  const ytUrl = $("#youtubeUrl").value.trim();
  const activeTab = document.querySelector(".tab.active").dataset.tab;

  if (activeTab === "upload" && !selectedFile) {
    alert("Escolha um arquivo de vídeo.");
    return;
  }
  if (activeTab === "youtube" && !ytUrl) {
    alert("Cole um link do YouTube.");
    return;
  }

  const form = new FormData();
  if (activeTab === "upload") form.append("file", selectedFile);
  else form.append("youtube_url", ytUrl);
  form.append("language", $("#language").value);
  form.append("max_clips", $("#maxClips").value);

  $("#startBtn").disabled = true;
  showProgress(true);

  try {
    const r = await fetch("/api/jobs", { method: "POST", body: form });
    if (!r.ok) throw new Error((await r.json()).detail || "Erro ao criar job");
    const job = await r.json();
    pollJob(job.id);
  } catch (err) {
    alert(err.message);
    $("#startBtn").disabled = false;
    showProgress(false);
  }
});

// ---------- Polling de status ----------
function pollJob(jobId) {
  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const r = await fetch(`/api/jobs/${jobId}`);
      const job = await r.json();
      updateProgress(job);

      if (job.status === "done") {
        clearInterval(pollTimer);
        $("#startBtn").disabled = false;
        renderClips(job.clips);
      } else if (job.status === "error") {
        clearInterval(pollTimer);
        $("#startBtn").disabled = false;
        $("#statusMsg").textContent = "❌ " + (job.error || "Erro desconhecido");
      }
    } catch {
      /* mantém tentando */
    }
  }, 1500);
}

// ---------- UI de progresso ----------
function showProgress(show) {
  $("#progressCard").classList.toggle("hidden", !show);
  if (show) $("#results").classList.add("hidden");
}

const STATUS_LABELS = {
  queued: "Na fila…",
  downloading: "Baixando vídeo…",
  transcribing: "Transcrevendo (GPU)…",
  analyzing: "IA achando os ganchos…",
  rendering: "Renderizando cortes…",
  done: "Concluído!",
  error: "Erro",
};

function updateProgress(job) {
  $("#statusLabel").textContent = STATUS_LABELS[job.status] || job.status;
  $("#progressPct").textContent = (job.progress || 0) + "%";
  $("#barFill").style.width = (job.progress || 0) + "%";
  $("#statusMsg").textContent = job.message || "";
  if (job.transcript_preview) {
    $("#transcript").textContent = "“" + job.transcript_preview + "…”";
  }
}

// ---------- Galeria de cortes ----------
function scoreClass(s) {
  if (s >= 75) return "high";
  if (s >= 50) return "mid";
  return "low";
}

function renderClips(clips) {
  showProgress(false);
  $("#results").classList.remove("hidden");
  const grid = $("#clipGrid");
  grid.innerHTML = "";

  clips.forEach((c) => {
    const card = document.createElement("div");
    card.className = "clip";
    card.innerHTML = `
      <video src="${c.url}" controls preload="metadata"></video>
      <div class="clip-body">
        <div class="clip-title">${escapeHtml(c.title)}</div>
        ${c.theme ? `<div class="clip-theme">#${escapeHtml(c.theme)}</div>` : ""}
        <div class="clip-meta">
          <span>${c.duration}s</span>
          <span class="score ${scoreClass(c.virality_score)}">🔥 ${c.virality_score}</span>
        </div>
        <a class="clip-dl" href="${c.url}" download>⬇️ Baixar</a>
      </div>`;
    grid.appendChild(card);
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

// ---------- Init ----------
checkHealth();
setInterval(checkHealth, 15000);
