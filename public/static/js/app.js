// Cortefy — Motor do Aplicativo
let currentProjectId = null;
let currentCuts = [];
let selectedCut = null;
let pollingInterval = null;
let selectedGenre = "auto";
let selectedSubStyle = "hormozi_pop";
let previewDebounceTimer = null;

// Mensagens Flutuantes Amigáveis
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;
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

// Contador Mensal de Cortes
async function initMonthlyStats() {
    try {
        const res = await fetch("/api/monthly-stats");
        if (res.ok) {
            const data = await res.json();
            updateMonthlyUI(data.used, data.limit);
            localStorage.setItem("cortefy_monthly_used", data.used);
            localStorage.setItem("cortefy_monthly_limit", data.limit);
            return;
        }
    } catch (e) {
        // Fallback local
    }
    const used = parseInt(localStorage.getItem("cortefy_monthly_used") || "18");
    const limit = parseInt(localStorage.getItem("cortefy_monthly_limit") || "100");
    updateMonthlyUI(used, limit);
}

function updateMonthlyUI(used, limit) {
    const elUsed = document.getElementById("header-cuts-used");
    const elLimit = document.getElementById("header-cuts-limit");
    const elBar = document.getElementById("header-cuts-bar");
    if (elUsed) elUsed.innerText = used;
    if (elLimit) elLimit.innerText = limit;
    if (elBar) {
        const pct = Math.min(100, Math.round((used / limit) * 100));
        elBar.style.width = `${pct}%`;
    }
}

function incrementMonthlyCounter() {
    const elUsed = document.getElementById("header-cuts-used");
    const elLimit = document.getElementById("header-cuts-limit");
    const current = elUsed ? parseInt(elUsed.innerText) || 18 : 18;
    const limit = elLimit ? parseInt(elLimit.innerText) || 100 : 100;
    const next = Math.min(limit, current + 1);
    updateMonthlyUI(next, limit);
    localStorage.setItem("cortefy_monthly_used", next);

    fetch("/api/monthly-stats/increment", { method: "POST" }).catch(() => {});
}

// Alternar Tipo de Conteúdo (Gênero)
function setGenre(genre) {
    selectedGenre = genre;
    window.selectedGenre = genre;
    document.querySelectorAll(".genre-chip").forEach(el => {
        const isMatch = el.getAttribute("data-genre") === genre || el.id === `genre-btn-${genre}`;
        const radio = el.querySelector(".genre-radio");
        if (isMatch) {
            el.classList.add("genre-chip-active");
            el.style.backgroundColor = "rgba(0, 255, 102, 0.15)";
            el.style.borderColor = "#00FF66";
            el.style.color = "#00FF66";
            el.style.boxShadow = "0 0 16px rgba(0, 255, 102, 0.25)";
            if (radio) {
                radio.textContent = "●";
                radio.style.color = "#00FF66";
            }
        } else {
            el.classList.remove("genre-chip-active");
            el.style.backgroundColor = "rgba(255, 255, 255, 0.04)";
            el.style.borderColor = "rgba(255, 255, 255, 0.12)";
            el.style.color = "#A1A1AA";
            el.style.boxShadow = "none";
            if (radio) {
                radio.textContent = "○";
                radio.style.color = "#71717A";
            }
        }
    });
    const hidden = document.getElementById("selected-genre-input");
    if (hidden) hidden.value = genre;
}
window.setGenre = setGenre;

// Alternar Vídeo de Apoio (Tela Dividida)
function setBRollMode(mode) {
    const btnAuto = document.getElementById("btn-broll-auto");
    const btnExt = document.getElementById("btn-broll-ext");
    const extInput = document.getElementById("broll-external-input");

    if (mode === "auto_extract") {
        if (btnAuto) btnAuto.classList.add("tech-card-active");
        if (btnExt) btnExt.classList.remove("tech-card-active");
        if (extInput) extInput.style.display = "none";
    } else {
        if (btnExt) btnExt.classList.add("tech-card-active");
        if (btnAuto) btnAuto.classList.remove("tech-card-active");
        if (extInput) extInput.style.display = "block";
    }
}

// Alternar Modelo de Legendas (10 Opções)
function setSubStyle(styleKey) {
    selectedSubStyle = styleKey;
    window.selectedSubStyle = styleKey;
    document.querySelectorAll(".sub-card").forEach(el => {
        const isMatch = el.getAttribute("data-sub-style") === styleKey;
        const radio = el.querySelector(".sub-radio");
        if (isMatch) {
            el.classList.add("sub-card-active");
            if (radio) {
                radio.textContent = "●";
                radio.style.color = "#00FF66";
            }
        } else {
            el.classList.remove("sub-card-active");
            if (radio) {
                radio.textContent = "○";
                radio.style.color = "#71717A";
            }
        }
    });
    const hidden = document.getElementById("selected-sub-style-input");
    if (hidden) hidden.value = styleKey;
}
window.setSubStyle = setSubStyle;

// Gaveta de Personalização de Legenda
function toggleCustomizeDrawer() {
    const drawer = document.getElementById("sub-customizer-drawer");
    if (!drawer) return;
    const isHidden = drawer.style.display === "none" || !drawer.style.display;
    drawer.style.display = isHidden ? "block" : "none";
    if (isHidden) {
        drawer.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
}

function saveSubtitleTemplate() {
    const customColor = document.getElementById("custom-sub-color")?.value || "#00FF66";
    const customSize = document.getElementById("custom-sub-size")?.value || "76";
    const customPos = document.getElementById("custom-sub-position")?.value || "520";
    const currentStyle = window.selectedSubStyle || selectedSubStyle || "hormozi_pop";

    const templateData = {
        styleKey: currentStyle,
        color: customColor,
        size: customSize,
        position: customPos,
        timestamp: Date.now()
    };

    localStorage.setItem("cortefy_sub_template", JSON.stringify(templateData));
    
    const badge = document.getElementById("saved-template-badge");
    if (badge) badge.style.display = "inline-flex";

    showToast("Template salvo! Será aplicado automaticamente nos seus vídeos.", "success");
}

function loadSavedTemplate() {
    try {
        const raw = localStorage.getItem("cortefy_sub_template");
        if (raw) {
            const tpl = JSON.parse(raw);
            if (tpl.styleKey) setSubStyle(tpl.styleKey);
            const inputColor = document.getElementById("custom-sub-color");
            const labelColor = document.getElementById("custom-sub-color-label");
            const selectSize = document.getElementById("custom-sub-size");
            const selectPos = document.getElementById("custom-sub-position");
            const badge = document.getElementById("saved-template-badge");

            if (inputColor && tpl.color) {
                inputColor.value = tpl.color;
                if (labelColor) labelColor.innerText = tpl.color;
            }
            if (selectSize && tpl.size) selectSize.value = tpl.size;
            if (selectPos && tpl.position) selectPos.value = tpl.position;
            if (badge) badge.style.display = "inline-flex";
        }
    } catch (e) {
        console.warn("Falha ao carregar template:", e);
    }
}

// Detecção Automática do Link e Prévia Instantânea
function initUrlListener() {
    const input = document.getElementById("input-main-url");
    if (!input) return;

    input.addEventListener("input", () => {
        clearTimeout(previewDebounceTimer);
        previewDebounceTimer = setTimeout(() => {
            handleUrlChange(input.value.trim());
        }, 300);
    });

    input.addEventListener("paste", () => {
        setTimeout(() => {
            handleUrlChange(input.value.trim());
        }, 100);
    });

    if (input.value.trim()) {
        handleUrlChange(input.value.trim());
    }

    // Color picker label listener
    const colorPicker = document.getElementById("custom-sub-color");
    const colorLabel = document.getElementById("custom-sub-color-label");
    if (colorPicker && colorLabel) {
        colorPicker.addEventListener("input", (e) => {
            colorLabel.innerText = e.target.value.toUpperCase();
        });
    }
}

async function handleUrlChange(url) {
    const previewCard = document.getElementById("video-preview-card");
    const spinner = document.getElementById("preview-loading-spinner");
    if (!url) {
        if (previewCard) previewCard.style.display = "none";
        if (spinner) spinner.style.display = "none";
        return;
    }

    const ytMatch = url.match(/(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/i);
    if (!ytMatch) {
        if (previewCard) previewCard.style.display = "none";
        if (spinner) spinner.style.display = "none";
        return;
    }

    const videoId = ytMatch[1];
    if (spinner) spinner.style.display = "inline-flex";

    const fallbackThumb = `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;
    document.getElementById("preview-thumb").src = fallbackThumb;
    document.getElementById("preview-title").innerText = "Identificando vídeo...";
    document.getElementById("preview-channel").innerText = "YouTube";
    document.getElementById("preview-duration").innerText = "12:00";
    if (previewCard) previewCard.style.display = "flex";

    try {
        const oembedPromise = fetch(`https://www.youtube.com/oembed?url=${encodeURIComponent(url)}&format=json`)
            .then(r => r.ok ? r.json() : null)
            .catch(() => null);

        const infoPromise = fetch(`/api/video-info?url=${encodeURIComponent(url)}`)
            .then(r => r.ok ? r.json() : fetch(`/api/project/info?url=${encodeURIComponent(url)}`).then(r2 => r2.ok ? r2.json() : null))
            .catch(() => null);

        const [oembedData, infoData] = await Promise.all([oembedPromise, infoPromise]);

        const title = infoData?.title || oembedData?.title || "Vídeo Selecionado";
        const channel = infoData?.channel || oembedData?.author_name || "";
        const thumb = infoData?.thumbnail || oembedData?.thumbnail_url || fallbackThumb;
        const durationFormatted = infoData?.duration_formatted || "";

        document.getElementById("preview-thumb").src = thumb;
        document.getElementById("preview-title").innerText = title;
        document.getElementById("preview-channel").innerText = channel ? `Canal: ${channel}` : "";
        if (durationFormatted && durationFormatted !== "00:00") {
            document.getElementById("preview-duration").innerText = durationFormatted;
            document.getElementById("preview-duration").style.display = "inline-block";
        } else {
            document.getElementById("preview-duration").style.display = "none";
        }

        if (previewCard) previewCard.style.display = "flex";
    } catch (e) {
        console.warn("Prévia simplificada:", e);
    } finally {
        if (spinner) spinner.style.display = "none";
    }
}

// PASSO 6: Avançar e Gerar Cortes Virais
async function startAnalysis() {
    const url = document.getElementById("input-main-url").value.trim();
    const isAutoBroll = document.getElementById("btn-broll-auto")?.classList.contains("tech-card-active") ?? true;
    const brollUrl = document.getElementById("input-broll-url")?.value.trim() || "";
    const activeGenre = window.selectedGenre || document.getElementById("selected-genre-input")?.value || selectedGenre || "auto";

    if (!url) {
        showToast("Por favor, cole um link do YouTube para começar.", "error");
        document.getElementById("input-main-url").focus();
        return;
    }

    const btn = document.getElementById("btn-advance");
    btn.disabled = true;
    btn.innerHTML = `<span class="radar-dot"></span><span>Analisando vídeo em alta velocidade...</span>`;

    const progSection = document.getElementById("progress-section");
    if (progSection) progSection.style.display = "block";
    updateProgress(15, "Lendo o vídeo em alta velocidade...");

    try {
        const res = await fetch("/api/project/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                source_url: url,
                broll_mode: isAutoBroll ? "auto_extract" : "external",
                broll_url: brollUrl,
                genre: activeGenre
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
        btn.innerHTML = `<span>⚡ Avançar e Gerar Cortes Virais</span>`;
        if (progSection) progSection.style.display = "none";
    }
}

function updateProgress(percent, message) {
    const fill = document.getElementById("progress-fill");
    const text = document.getElementById("progress-status");
    const pct = document.getElementById("progress-percent");

    if (fill) fill.style.width = `${percent}%`;
    if (text) text.innerHTML = `<span class="radar-dot"></span><span>${message}</span>`;
    if (pct) pct.innerText = `${percent}%`;
}

function pollTask(taskId) {
    if (pollingInterval) clearInterval(pollingInterval);

    pollingInterval = setInterval(async () => {
        try {
            const res = await fetch(`/api/task/${taskId}`);
            const task = await res.json();

            updateProgress(task.progress, task.message);

            if (task.status === "completed") {
                clearInterval(pollingInterval);
                currentProjectId = task.result.project_id;
                currentCuts = task.result.cuts || [];

                document.getElementById("progress-section").style.display = "none";
                const btn = document.getElementById("btn-advance");
                btn.disabled = false;
                btn.innerHTML = `<span>⚡ Avançar e Gerar Cortes Virais</span>`;

                const titleDisplay = document.getElementById("project-title-display");
                if (titleDisplay) titleDisplay.innerText = task.result.title || "Vídeo Selecionado";

                renderCutsList(currentCuts, false);

                const cutsSection = document.getElementById("cuts-section");
                if (cutsSection) {
                    cutsSection.style.display = "block";
                    cutsSection.scrollIntoView({ behavior: "smooth", block: "start" });
                }

                showToast(`Encontramos ${currentCuts.length} momentos virais incríveis!`, "success");
            } else if (task.status === "error") {
                clearInterval(pollingInterval);
                showToast(task.message || "Erro no processamento.", "error");
                const btn = document.getElementById("btn-advance");
                btn.disabled = false;
                btn.innerHTML = `<span>⚡ Avançar e Gerar Cortes Virais</span>`;
            }
        } catch (e) {
            console.error("Erro no polling:", e);
        }
    }, 1000);
}

// Renderização dos Cards de Cortes Ranqueados
function renderCutsList(cuts, append = false) {
    const container = document.getElementById("cuts-container");
    if (!container) return;

    if (!append) {
        container.innerHTML = "";
    }

    cuts.forEach((cut) => {
        const durationSec = Math.round(cut.end - cut.start);
        const startFmt = formatSeconds(cut.start);
        const endFmt = formatSeconds(cut.end);
        const score = cut.virality_score || 85;

        let scoreBadgeClass = "score-pill-viral";
        let scoreLabel = "⚡ Potencial Viral";
        if (score < 85 && score >= 75) {
            scoreBadgeClass = "score-pill-high";
            scoreLabel = "🔥 Alto Impacto";
        } else if (score < 75) {
            scoreBadgeClass = "score-pill-mid";
            scoreLabel = "✨ Bom Engajamento";
        }

        const tagText = cut.tag || scoreLabel;
        const captionText = cut.caption_seo || `${cut.title} 🔥\n\nVocê teria a mesma reação? Comente aqui embaixo!\n\n#foryou #viral #cortes #shorts #reels`;

        const card = document.createElement("div");
        card.id = `card-cut-${cut.id}`;
        card.className = "tech-card p-5 flex flex-col justify-between gap-4 border border-white/10 hover:border-white/20 transition-all";

        card.innerHTML = `
            <div class="space-y-3">
                <!-- Cabeçalho do Card: Selo de Viralidade e Minutagem -->
                <div class="flex items-center justify-between gap-2 flex-wrap">
                    <span class="${scoreBadgeClass}">
                        <span>${score}/100</span>
                        <span>${tagText}</span>
                    </span>
                    <span class="text-xs font-mono text-zinc-400 bg-white/5 px-2.5 py-1 rounded-md border border-white/5">
                        ⏱️ ${startFmt} - ${endFmt} (${durationSec}s)
                    </span>
                </div>

                <!-- Título Chamativo -->
                <h3 class="text-base font-bold text-white leading-snug">
                    ${escapeHtml(cut.title)}
                </h3>

                <!-- Gancho Inicial -->
                <div class="p-2.5 rounded-lg bg-white/5 border border-white/5 text-xs text-zinc-300 flex items-start gap-2">
                    <span class="text-[#00FF66] font-bold shrink-0">🎯</span>
                    <div>
                        <strong class="text-white">Gancho inicial (3s):</strong>
                        <span>"${escapeHtml(cut.hook || 'Preste atenção nisso...')}"</span>
                    </div>
                </div>

                <!-- Legenda com SEO para Redes Sociais -->
                <div class="space-y-1.5 pt-1">
                    <div class="flex items-center justify-between">
                        <span class="text-[11px] font-semibold text-zinc-400">LEGENDA COM SEO PRONTA PARA POSTAR:</span>
                        <button type="button" onclick="copyCaption(this, decodeURIComponent('${encodeURIComponent(captionText)}'))" class="btn-copy-seo">
                            <span>📋 Copiar Legenda</span>
                        </button>
                    </div>
                    <div class="seo-caption-box">${escapeHtml(captionText)}</div>
                </div>
            </div>

            <!-- Botão de Ação: Criar Vídeo (MP4) -->
            <div class="pt-3 border-t border-white/5 flex items-center justify-between gap-3">
                <span class="text-xs text-zinc-400">9:16 Vertical • Pronto</span>
                <button type="button" onclick="renderCut('${cut.id}')" class="btn-neon text-xs py-2.5 px-4 font-bold">
                    <span>🚀 Criar Vídeo (MP4)</span>
                </button>
            </div>
        `;

        container.appendChild(card);
    });
}

function formatSeconds(sec) {
    const s = Math.floor(sec || 0);
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return `${m.toString().padStart(2, '0')}:${rem.toString().padStart(2, '0')}`;
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.innerText = text || "";
    return div.innerHTML;
}

// 1-Clique Copiar Legenda
function copyCaption(btn, text) {
    if (!text) return;

    const performCopy = () => {
        const originalHtml = btn.innerHTML;
        btn.innerHTML = `<span>✓ Copiado!</span>`;
        btn.classList.add("copied");

        setTimeout(() => {
            btn.innerHTML = originalHtml;
            btn.classList.remove("copied");
        }, 2500);

        showToast("Legenda e hashtags copiadas com sucesso!", "success");
    };

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(performCopy).catch(() => {
            fallbackCopy(text);
            performCopy();
        });
    } else {
        fallbackCopy(text);
        performCopy();
    }
}

function fallbackCopy(text) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(ta);
}

// Botão "Gerar +5 Cortes"
async function generateMoreCuts() {
    if (!currentProjectId) {
        showToast("Nenhum projeto ativo para buscar mais cortes.", "error");
        return;
    }

    const btn = document.getElementById("btn-more-cuts");
    btn.disabled = true;
    btn.innerHTML = `<span class="radar-dot"></span><span>Buscando +5 momentos virais...</span>`;

    try {
        const res = await fetch("/api/project/more-cuts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ project_id: currentProjectId })
        });

        if (!res.ok) {
            throw new Error("Não foi possível gerar mais cortes agora.");
        }

        const data = await res.json();
        const newCuts = data.new_cuts || [];

        if (newCuts.length === 0) {
            showToast("Todos os melhores momentos já foram gerados!", "info");
        } else {
            currentCuts.push(...newCuts);
            renderCutsList(newCuts, true);
            showToast(`+5 novos cortes adicionados com sucesso!`, "success");

            // Rola suavemente até o primeiro novo corte
            const firstNewCard = document.getElementById(`card-cut-${newCuts[0].id}`);
            if (firstNewCard) {
                firstNewCard.scrollIntoView({ behavior: "smooth", block: "center" });
            }
        }
    } catch (e) {
        showToast(e.message, "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>⚡ Gerar +5 Cortes Deste Vídeo</span>`;
    }
}

// Renderizar Corte Escolhido
async function renderCut(cutId) {
    if (!currentProjectId) return;

    const customColor = document.getElementById("custom-sub-color")?.value || "#00FF66";
    const customSize = parseInt(document.getElementById("custom-sub-size")?.value || "76");
    const customPos = parseInt(document.getElementById("custom-sub-position")?.value || "520");
    const subStyle = window.selectedSubStyle || selectedSubStyle || "hormozi_pop";

    const enableZoom = document.getElementById("toggle-zoom")?.checked ?? true;
    const enableDrift = document.getElementById("toggle-drift")?.checked ?? true;

    const renderSection = document.getElementById("render-progress-section");
    const renderFill = document.getElementById("render-progress-fill");
    const renderStatus = document.getElementById("render-progress-status");

    if (renderSection) {
        renderSection.style.display = "block";
        renderSection.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    if (renderFill) renderFill.style.width = "10%";
    if (renderStatus) renderStatus.innerText = "Iniciando renderização de vídeo em alta velocidade...";

    try {
        const res = await fetch("/api/project/render", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                project_id: currentProjectId,
                cut_id: cutId,
                layout: "split_screen",
                subtitle_style: subStyle,
                custom_color: customColor,
                custom_font_size: customSize,
                custom_margin_v: customPos,
                enable_zoom: enableZoom,
                enable_drift: enableDrift,
                speed: 1.05
            })
        });

        if (!res.ok) {
            throw new Error("Falha ao iniciar renderização.");
        }

        const data = await res.json();
        pollRenderTask(data.render_task_id);
    } catch (e) {
        showToast(e.message, "error");
        if (renderSection) renderSection.style.display = "none";
    }
}

function pollRenderTask(renderTaskId) {
    const poll = setInterval(async () => {
        try {
            const res = await fetch(`/api/task/${renderTaskId}`);
            const task = await res.json();

            const renderFill = document.getElementById("render-progress-fill");
            const renderStatus = document.getElementById("render-progress-status");
            const renderSection = document.getElementById("render-progress-section");

            if (renderFill) renderFill.style.width = `${task.progress}%`;
            if (renderStatus) renderStatus.innerText = task.message;

            if (task.status === "completed") {
                clearInterval(poll);
                showToast("Vídeo pronto com sucesso!", "success");
                if (renderSection) renderSection.style.display = "none";
                incrementMonthlyCounter();
                openVideoModal(task.output_url, task.filename);
            } else if (task.status === "error") {
                clearInterval(poll);
                showToast("Não foi possível gerar o vídeo. Tente novamente.", "error");
                if (renderSection) renderSection.style.display = "none";
            }
        } catch (e) {
            console.error(e);
        }
    }, 1200);
}

// Modal do Vídeo Pronto
function openVideoModal(videoUrl, filename) {
    const modal = document.getElementById("video-modal");
    const video = document.getElementById("modal-video-player");
    const downloadBtn = document.getElementById("modal-download-btn");

    if (video) video.src = videoUrl;
    if (downloadBtn) {
        downloadBtn.href = `/api/download/${filename}`;
        downloadBtn.download = filename;
    }

    if (modal) modal.style.display = "flex";
    if (video) video.play().catch(() => {});
}

function closeVideoModal() {
    const modal = document.getElementById("video-modal");
    const video = document.getElementById("modal-video-player");
    if (video) video.pause();
    if (modal) modal.style.display = "none";
}

// Inicialização
document.addEventListener("DOMContentLoaded", () => {
    initMonthlyStats();
    initUrlListener();
    loadSavedTemplate();

    // Event listeners para chips de gênero
    document.querySelectorAll(".genre-chip").forEach(btn => {
        btn.addEventListener("click", (e) => {
            const g = btn.getAttribute("data-genre");
            if (g) setGenre(g);
        });
    });

    // Event listeners para cards de legenda
    document.querySelectorAll(".sub-card").forEach(card => {
        card.addEventListener("click", () => {
            const s = card.getAttribute("data-sub-style");
            if (s) setSubStyle(s);
        });
    });
});
