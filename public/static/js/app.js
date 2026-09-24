// Cortefy — Motor do Aplicativo
let currentProjectId = null;
let currentCuts = [];
let selectedCut = null;
let pollingInterval = null;

// Mensagens Flutuantes Amigáveis
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let icon = "⚡";
    if (type === "success") icon = "✓";
    if (type === "error") icon = "✕";

    toast.innerHTML = `
        <span style="color: ${type === 'success' ? '#00FF66' : type === 'error' ? '#EF4444' : '#3B82F6'}; font-weight: bold;">${icon}</span>
        <span>${message}</span>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(10px)";
        toast.style.transition = "all 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Status do Sistema
async function checkHealth() {
    try {
        const res = await fetch("/api/health");
        const data = await res.json();
        if (data.status === "online") {
            const telemetryEl = document.getElementById("telemetry-gemini");
            if (telemetryEl) {
                telemetryEl.innerHTML = `
                    <span class="radar-dot"></span>
                    <span>Inteligência Artificial Pronta</span>
                `;
            }
        }
    } catch (e) {
        console.warn("Status offline");
    }
}

// Alternar Vídeo de Apoio
function setBRollMode(mode) {
    const btnAuto = document.getElementById("btn-broll-auto");
    const btnExt = document.getElementById("btn-broll-ext");
    const extInput = document.getElementById("broll-external-input");

    if (mode === "auto_extract") {
        btnAuto.classList.add("tech-card-active");
        btnExt.classList.remove("tech-card-active");
        extInput.style.display = "none";
    } else {
        btnExt.classList.add("tech-card-active");
        btnAuto.classList.remove("tech-card-active");
        extInput.style.display = "block";
    }
}

// Iniciar Encontro de Melhores Momentos
async function startAnalysis() {
    const url = document.getElementById("input-main-url").value.trim();
    const isAutoBroll = document.getElementById("btn-broll-auto").classList.contains("tech-card-active");
    const brollUrl = document.getElementById("input-broll-url").value.trim();

    if (!url) {
        showToast("Por favor, cole um link do YouTube para começar.", "error");
        return;
    }

    const btn = document.getElementById("btn-analyze");
    btn.disabled = true;
    btn.innerHTML = `<span class="radar-dot"></span> Procurando momentos incríveis...`;

    document.getElementById("progress-section").style.display = "block";
    updateProgress(15, "Lendo o vídeo em alta velocidade...");

    try {
        const res = await fetch("/api/project/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                source_url: url,
                broll_mode: isAutoBroll ? "auto_extract" : "external",
                broll_url: brollUrl
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Não foi possível carregar este vídeo.");
        }

        const data = await res.json();
        pollTask(data.task_id);
    } catch (e) {
        showToast(e.message, "error");
        btn.disabled = false;
        btn.innerHTML = `✨ Encontrar Melhores Momentos`;
        document.getElementById("progress-section").style.display = "none";
    }
}

function updateProgress(percent, msg) {
    document.getElementById("progress-fill").style.width = `${percent}%`;
    document.getElementById("progress-status").innerText = msg;
    document.getElementById("progress-percent").innerText = `${percent}%`;
}

// Acompanhar Análise
function pollTask(taskId) {
    clearInterval(pollingInterval);
    pollingInterval = setInterval(async () => {
        try {
            const res = await fetch(`/api/task/${taskId}`);
            const task = await res.json();

            updateProgress(task.progress, task.message);

            if (task.status === "completed") {
                clearInterval(pollingInterval);
                showToast("Pronto! Encontramos os melhores momentos.", "success");
                
                currentProjectId = task.result.project_id;
                currentCuts = task.result.cuts;

                renderCuts(currentCuts, task.result.title);
                
                document.getElementById("btn-analyze").disabled = false;
                document.getElementById("btn-analyze").innerHTML = `✨ Encontrar Melhores Momentos`;
                document.getElementById("progress-section").style.display = "none";

                // Rola para a seção dos momentos
                document.getElementById("cuts-section").scrollIntoView({ behavior: "smooth" });
            } else if (task.status === "error") {
                clearInterval(pollingInterval);
                showToast("Não conseguimos analisar este vídeo. Tente outro link.", "error");
                document.getElementById("btn-analyze").disabled = false;
                document.getElementById("btn-analyze").innerHTML = `✨ Encontrar Melhores Momentos`;
                document.getElementById("progress-section").style.display = "none";
            }
        } catch (e) {
            console.error(e);
        }
    }, 1000);
}

// Exibir Cards de Momentos
function renderCuts(cuts, title) {
    const container = document.getElementById("cuts-container");
    container.innerHTML = "";
    document.getElementById("cuts-section").style.display = "block";
    document.getElementById("project-title-display").innerText = title || "Vídeo Selecionado";

    cuts.forEach((c) => {
        const card = document.createElement("div");
        card.className = "tech-card p-5 cursor-pointer relative";
        card.id = `cut-card-${c.id}`;

        const duration = Math.round(c.end - c.start);

        card.innerHTML = `
            <div class="flex justify-between items-start mb-3">
                <div class="flex items-center gap-2">
                    <span class="badge-neon">${c.virality_score}% POTENCIAL</span>
                    <span class="badge-zinc">${c.tag || '🔥 Destaque'}</span>
                </div>
                <span class="text-xs text-zinc-400 font-medium">⏱️ ${duration}s</span>
            </div>
            
            <h3 class="text-base font-bold text-white mb-2">${c.title}</h3>
            <p class="text-xs text-zinc-400 italic mb-4">"${c.hook}"</p>

            <div class="flex justify-between items-center pt-3 border-t border-white/5">
                <span class="text-xs text-zinc-500">${c.start.toFixed(1)}s até ${c.end.toFixed(1)}s</span>
                <button onclick="selectCut('${c.id}')" class="btn-secondary text-xs py-1.5 px-3">
                    Criar Este Vídeo
                </button>
            </div>
        `;

        container.appendChild(card);
    });

    if (cuts.length > 0) {
        selectCut(cuts[0].id);
    }
}

// Selecionar Momento
function selectCut(cutId) {
    selectedCut = currentCuts.find(c => c.id === cutId);
    if (!selectedCut) return;

    document.querySelectorAll("[id^='cut-card-']").forEach(el => el.classList.remove("tech-card-active"));
    const activeCard = document.getElementById(`cut-card-${cutId}`);
    if (activeCard) activeCard.classList.add("tech-card-active");

    document.getElementById("studio-section").style.display = "block";
    document.getElementById("studio-cut-title").innerText = selectedCut.title;
    document.getElementById("studio-cut-meta").innerText = `⏱️ ${Math.round(selectedCut.end - selectedCut.start)} segundos  |  ${selectedCut.virality_score}% de chance de viralizar  |  ${selectedCut.tag}`;

    document.getElementById("studio-section").scrollIntoView({ behavior: "smooth" });
}

// Gerar Vídeo Pronto
async function renderCurrentCut() {
    if (!currentProjectId || !selectedCut) {
        showToast("Escolha um dos momentos acima primeiro.", "error");
        return;
    }

    const layout = document.getElementById("select-layout").value;
    const style = document.getElementById("select-sub-style").value;
    const speed = document.getElementById("range-speed").value;

    const btn = document.getElementById("btn-render-cut");
    btn.disabled = true;
    btn.innerHTML = `<span class="radar-dot"></span> Criando seu vídeo...`;

    document.getElementById("render-progress-section").style.display = "block";

    try {
        const res = await fetch("/api/project/render", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                project_id: currentProjectId,
                cut_id: selectedCut.id,
                layout: layout,
                subtitle_style: style,
                speed: parseFloat(speed)
            })
        });

        const data = await res.json();
        pollRenderTask(data.render_task_id);
    } catch (e) {
        showToast(e.message, "error");
        btn.disabled = false;
        btn.innerHTML = `🚀 Criar Vídeo Pronto para Postar`;
    }
}

// Acompanhar Criação do Vídeo
function pollRenderTask(renderTaskId) {
    const poll = setInterval(async () => {
        try {
            const res = await fetch(`/api/task/${renderTaskId}`);
            const task = await res.json();

            document.getElementById("render-progress-fill").style.width = `${task.progress}%`;
            document.getElementById("render-progress-status").innerText = task.message;

            if (task.status === "completed") {
                clearInterval(poll);
                showToast("Vídeo pronto com sucesso!", "success");

                document.getElementById("btn-render-cut").disabled = false;
                document.getElementById("btn-render-cut").innerHTML = `🚀 Criar Vídeo Pronto para Postar`;
                document.getElementById("render-progress-section").style.display = "none";

                openVideoModal(task.output_url, task.filename);
            } else if (task.status === "error") {
                clearInterval(poll);
                showToast("Não foi possível gerar o vídeo. Tente novamente.", "error");
                document.getElementById("btn-render-cut").disabled = false;
                document.getElementById("btn-render-cut").innerHTML = `🚀 Criar Vídeo Pronto para Postar`;
            }
        } catch (e) {
            console.error(e);
        }
    }, 1200);
}

// Visualizador do Vídeo Pronto
function openVideoModal(videoUrl, filename) {
    const modal = document.getElementById("video-modal");
    const video = document.getElementById("modal-video-player");
    const downloadBtn = document.getElementById("modal-download-btn");

    video.src = videoUrl;
    downloadBtn.href = `/api/download/${filename}`;
    downloadBtn.download = filename;

    modal.style.display = "flex";
    video.play();
}

function closeVideoModal() {
    const modal = document.getElementById("video-modal");
    const video = document.getElementById("modal-video-player");
    video.pause();
    modal.style.display = "none";
}

document.addEventListener("DOMContentLoaded", () => {
    checkHealth();
});
