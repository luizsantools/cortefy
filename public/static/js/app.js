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
        <span style="color: ${type === 'success' ? '#FF5C00' : type === 'error' ? '#EF4444' : '#0052FF'}; font-weight: 900; font-size: 16px;">${icon}</span>
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
            localStorage.setItem("editize_monthly_used", data.used);
            localStorage.setItem("editize_monthly_limit", data.limit);
            return;
        }
    } catch (e) {
        // Fallback local
    }
    const used = parseInt(localStorage.getItem("editize_monthly_used") || localStorage.getItem("cortefy_monthly_used") || "18");
    const limit = parseInt(localStorage.getItem("editize_monthly_limit") || localStorage.getItem("cortefy_monthly_limit") || "100");
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
    localStorage.setItem("editize_monthly_used", next);

    fetch("/api/monthly-stats/increment", { method: "POST" }).catch(() => {});
}

// Alternar Tipo de Conteúdo (Gênero)
function setGenre(genre) {
    selectedGenre = genre;
    window.selectedGenre = genre;
    document.querySelectorAll(".genre-chip").forEach(el => {
        const isMatch = el.getAttribute("data-genre") === genre || el.id === `genre-btn-${genre}`;
        const radio = el.querySelector(".genre-radio");
        const title = el.querySelector(".text-sm");
        const desc = el.querySelector("p");
        if (isMatch) {
            el.classList.add("genre-chip-active");
            el.style.backgroundColor = "#FF5C00";
            el.style.borderColor = "#000000";
            el.style.color = "#FFFFFF";
            el.style.boxShadow = "4px 4px 0px #000000";
            if (radio) {
                radio.textContent = "●";
                radio.style.color = "#FFFFFF";
            }
            if (title) title.style.color = "#FFFFFF";
            if (desc) desc.style.color = "#FFF3EB";
        } else {
            el.classList.remove("genre-chip-active");
            el.style.backgroundColor = "#FFFFFF";
            el.style.borderColor = "#000000";
            el.style.color = "#000000";
            el.style.boxShadow = "3px 3px 0px #000000";
            if (radio) {
                radio.textContent = "○";
                radio.style.color = "#000000";
            }
            if (title) title.style.color = "#000000";
            if (desc) desc.style.color = "#4B5563";
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
                radio.style.color = "#FF5C00";
            }
        } else {
            el.classList.remove("sub-card-active");
            if (radio) {
                radio.textContent = "○";
                radio.style.color = "#000000";
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
    const customColor = document.getElementById("custom-sub-color")?.value || "#FF5C00";
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

    localStorage.setItem("editize_sub_template", JSON.stringify(templateData));
    
    const badge = document.getElementById("saved-template-badge");
    if (badge) badge.style.display = "inline-flex";

    showToast("Template salvo! Será aplicado automaticamente nos seus vídeos.", "success");
}

function loadSavedTemplate() {
    try {
        const raw = localStorage.getItem("editize_sub_template") || localStorage.getItem("cortefy_sub_template");
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
    const activeSubStyle = window.selectedSubStyle || selectedSubStyle || "hormozi_pop";
    const customColor = document.getElementById("custom-sub-color")?.value || "";
    const customSize = parseInt(document.getElementById("custom-sub-size")?.value) || 75;
    const customMargin = parseInt(document.getElementById("custom-sub-position")?.value) || 420;
    const toggleZoom = document.getElementById("toggle-zoom")?.checked ?? true;
    const toggleDrift = document.getElementById("toggle-drift")?.checked ?? true;
    const toggleCenterFace = document.getElementById("toggle-center-face")?.checked ?? true;
    const toggleMotionGraphics = document.getElementById("toggle-motion-graphics")?.checked ?? true;
    const toggleSoundEffects = document.getElementById("toggle-sound-effects")?.checked ?? true;

    if (!url) {
        showToast("Por favor, cole um link do YouTube para começar.", "error");
        document.getElementById("input-main-url").focus();
        return;
    }

    const btn = document.getElementById("btn-advance");
    btn.disabled = true;
    btn.innerHTML = `<span class="radar-dot"></span><span>Analisando e editando os cortes virais...</span>`;

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
                genre: activeGenre,
                subtitle_style: activeSubStyle,
                custom_color: customColor,
                custom_size: customSize,
                custom_margin: customMargin,
                enable_zoom: toggleZoom,
                enable_drift: toggleDrift,
                center_face: toggleCenterFace,
                motion_graphics: toggleMotionGraphics,
                sound_effects: toggleSoundEffects,
                layout: (brollUrl && !isAutoBroll) ? "split_screen" : "portrait"
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
        card.className = "tech-card p-5 flex flex-col md:flex-row gap-5 items-start";

        const videoSrc = cut.video_url || "";

        card.innerHTML = `
            <!-- Player 9:16 Embutido -->
            <div class="relative w-full md:w-52 aspect-[9/16] bg-black rounded-xl overflow-hidden border-[3px] border-black shadow-[4px_4px_0px_#000] shrink-0 self-center md:self-start">
                <video id="player-cut-${cut.id}" src="${videoSrc}" controls playsinline preload="metadata" class="w-full h-full object-cover"></video>
                <span class="absolute top-2 left-2 bg-black/85 text-[#FF5C00] text-[10px] font-mono px-2 py-0.5 rounded border border-black font-bold">9:16 VERTICAL</span>
            </div>

            <!-- Informações, Ganchos, SEO e Botões -->
            <div class="flex-1 flex flex-col justify-between gap-3 w-full">
                <!-- Cabeçalho do Card: Selo de Viralidade e Minutagem -->
                <div class="flex items-center justify-between gap-2 flex-wrap">
                    <span class="${scoreBadgeClass}">
                        <span>${score}/100</span>
                        <span>${tagText}</span>
                    </span>
                    <span class="text-xs font-mono text-black font-extrabold bg-[#F4F3EE] px-2.5 py-1 rounded-md border-2 border-black shadow-[2px_2px_0px_#000]">
                        ⏱️ ${startFmt} - ${endFmt} (${durationSec}s)
                    </span>
                </div>

                <!-- Título Chamativo -->
                <h3 class="text-base font-black text-black leading-snug font-display">
                    ${escapeHtml(cut.title)}
                </h3>

                <!-- Gancho Inicial -->
                <div class="p-2.5 rounded-lg bg-[#FFF3EB] border-2 border-black shadow-[2px_2px_0px_#000] text-xs text-black flex items-start gap-2">
                    <span class="text-[#FF5C00] font-black shrink-0 text-sm">🎯</span>
                    <div>
                        <strong class="text-black font-extrabold">Gancho inicial (3s):</strong>
                        <span class="font-medium">"${escapeHtml(cut.hook || 'Preste atenção nisso...')}"</span>
                    </div>
                </div>

                <!-- Legenda com SEO para Redes Sociais (Editável em Tempo Real) -->
                <div class="space-y-1.5 pt-1">
                    <div class="flex items-center justify-between flex-wrap gap-2">
                        <div class="flex items-center gap-2">
                            <span class="text-[11px] font-black text-zinc-800 uppercase tracking-wider">LEGENDA COM SEO (EDITÁVEL):</span>
                            <span id="tag-badge-${cut.id}" class="badge-blue text-[10px] font-black">5 / 5 hashtags</span>
                        </div>
                        <div class="flex items-center gap-1.5">
                            <button type="button" onclick="saveCaption('${cut.id}')" class="btn-copy-seo" title="Salvar alterações na legenda">
                                <span>💾 Salvar Legenda</span>
                            </button>
                            <button type="button" onclick="copyCaptionById('${cut.id}', this)" class="btn-copy-seo" title="Copiar legenda para a área de transferência">
                                <span>📋 Copiar</span>
                            </button>
                        </div>
                    </div>
                    <textarea id="caption-input-${cut.id}" oninput="updateHashtagBadge('${cut.id}')" class="seo-caption-box font-medium w-full text-xs font-sans resize-y focus:outline-none focus:border-[#FF5C00]" rows="4">${escapeHtml(captionText)}</textarea>
                </div>

                <!-- Botões de Ação: Baixar MP4 Imediato e Opções -->
                <div class="pt-3 border-t-2 border-black flex flex-wrap items-center justify-between gap-3">
                    <span class="text-xs text-zinc-700 font-bold">9:16 Vertical • Efeitos Ativos</span>
                    <div class="flex items-center gap-2 flex-wrap">
                        <a id="btn-download-${cut.id}" href="${videoSrc || '#'}" download="${escapeHtml(cut.title || cut.id)}.mp4" class="btn-neon text-xs py-2 px-3.5 font-black flex items-center gap-1.5 shadow-[2px_2px_0px_#000]">
                            <span>⬇️ Baixar Vídeo</span>
                        </a>
                        <button type="button" onclick="openSubtitleEditorModal('${cut.id}')" class="btn-secondary text-xs py-2 px-3 font-black flex items-center gap-1.5" title="Corrigir termos, estilo ou frases faladas da legenda">
                            <span>✏️ Corrigir Legenda</span>
                        </button>
                        <button type="button" onclick="generateThumbnailsForCut('${cut.id}')" class="btn-blue text-xs py-2 px-3 font-black flex items-center gap-1.5" title="Gerar 3 opções de Thumbnails para YouTube com Clickscore">
                            <span>🎨 3 Thumbnails</span>
                        </button>
                    </div>
                </div>
            </div>
        `;

        container.appendChild(card);
        updateHashtagBadge(cut.id);
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

// --- SISTEMA DE LEGENDA SEO & HASHTAGS (LIMITE 5 TAGS) ---

function updateHashtagBadge(cutId) {
    const input = document.getElementById(`caption-input-${cutId}`);
    const badge = document.getElementById(`tag-badge-${cutId}`);
    if (!input || !badge) return;

    const val = input.value || "";
    const matches = val.match(/#[^\s#]+/g) || [];
    const count = matches.length;

    if (count > 5) {
        badge.className = "text-[10px] font-black px-2 py-0.5 rounded-md border-2 border-black bg-[#FF3333] text-white shadow-[1px_1px_0px_#000]";
        badge.innerText = `${count} / 5 (máx 5 no Instagram!)`;
    } else if (count === 5) {
        badge.className = "badge-neon text-[10px] font-black";
        badge.innerText = `5 / 5 hashtags ✓`;
    } else {
        badge.className = "badge-blue text-[10px] font-black";
        badge.innerText = `${count} / 5 hashtags`;
    }
}

async function saveCaption(cutId) {
    if (!currentProjectId) {
        showToast("Projeto não encontrado.", "error");
        return;
    }
    const input = document.getElementById(`caption-input-${cutId}`);
    if (!input) return;
    const captionVal = input.value.trim();

    try {
        const res = await fetch("/api/cut/update-caption", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                project_id: currentProjectId,
                cut_id: cutId,
                caption_seo: captionVal
            })
        });

        if (!res.ok) throw new Error("Não foi possível salvar a legenda.");
        const data = await res.json();

        // Atualiza objeto em memória
        const cut = currentCuts.find(c => c.id === cutId);
        if (cut && data.cut) {
            cut.caption_seo = data.cut.caption_seo;
        }

        updateHashtagBadge(cutId);
        showToast("Legenda salva com sucesso!", "success");
    } catch (e) {
        showToast(e.message || "Erro ao salvar legenda", "error");
    }
}

function copyCaptionById(cutId, btn) {
    const input = document.getElementById(`caption-input-${cutId}`);
    if (!input) return;
    copyCaption(btn, input.value);
}

// --- MODAL DE CORREÇÃO DE LEGENDA DO VÍDEO (9:16) ---

let activeEditingCutId = null;

function openSubtitleEditorModal(cutId) {
    const cut = currentCuts.find(c => c.id === cutId);
    if (!cut) {
        showToast("Corte não encontrado.", "error");
        return;
    }

    activeEditingCutId = cutId;
    const modal = document.getElementById("modal-subtitle-editor");
    const textArea = document.getElementById("edit-sub-text");
    const styleSelect = document.getElementById("edit-sub-style");
    const colorInput = document.getElementById("edit-sub-color");
    const colorLabel = document.getElementById("edit-sub-color-label");

    // Preenche com o texto falado (transcrição do corte ou hook)
    let initialText = "";
    if (cut.edited_subtitles && Array.isArray(cut.edited_subtitles)) {
        initialText = cut.edited_subtitles.map(w => w.word).join(" ");
    } else if (cut.transcription) {
        initialText = cut.transcription;
    } else if (cut.subtitles && Array.isArray(cut.subtitles)) {
        initialText = cut.subtitles.map(s => s.text).join(" ");
    } else {
        initialText = cut.hook || "";
    }

    if (textArea) textArea.value = initialText;
    if (styleSelect) styleSelect.value = cut.subtitle_style || window.selectedSubStyle || "hormozi_pop";
    if (colorInput) {
        const col = cut.custom_color || "#FFE500";
        colorInput.value = col;
        if (colorLabel) colorLabel.innerText = col.toUpperCase();
    }

    if (modal) modal.style.display = "flex";
}

function closeSubtitleEditorModal() {
    const modal = document.getElementById("modal-subtitle-editor");
    if (modal) modal.style.display = "none";
    activeEditingCutId = null;
}

async function submitSubtitleCorrection() {
    if (!currentProjectId || !activeEditingCutId) {
        showToast("Selecione um corte primeiro.", "error");
        return;
    }

    const cutId = activeEditingCutId;
    const textArea = document.getElementById("edit-sub-text");
    const styleSelect = document.getElementById("edit-sub-style");
    const colorInput = document.getElementById("edit-sub-color");
    const saveBtn = document.getElementById("btn-save-subtitles");

    const editedText = textArea ? textArea.value.trim() : "";
    const subStyle = styleSelect ? styleSelect.value : "hormozi_pop";
    const subColor = colorInput ? colorInput.value : "#FFE500";

    if (!editedText) {
        showToast("Digite o texto das falas da legenda.", "warning");
        return;
    }

    const origBtnHtml = saveBtn ? saveBtn.innerHTML : "";
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<span class="radar-dot"></span><span>Regerando corte 9:16 com nova legenda...</span>`;
    }

    try {
        const res = await fetch("/api/cut/update-subtitles", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                project_id: currentProjectId,
                cut_id: cutId,
                edited_text: editedText,
                subtitle_style: subStyle,
                custom_color: subColor
            })
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || "Erro ao regerar vídeo com novas legendas.");
        }

        const data = await res.json();
        const updatedVideoUrl = data.video_url;

        // Atualiza o player do card
        const cardPlayer = document.getElementById(`player-cut-${cutId}`);
        if (cardPlayer) {
            cardPlayer.src = updatedVideoUrl;
            cardPlayer.load();
        }

        // Atualiza o botão de download do card
        const dlBtn = document.getElementById(`btn-download-${cutId}`);
        if (dlBtn) {
            dlBtn.href = updatedVideoUrl;
        }

        // Atualiza dados locais
        const cut = currentCuts.find(c => c.id === cutId);
        if (cut) {
            cut.video_url = updatedVideoUrl;
            cut.subtitle_style = subStyle;
            cut.custom_color = subColor;
            if (data.cut) {
                cut.edited_subtitles = data.cut.edited_subtitles;
            }
        }

        closeSubtitleEditorModal();
        showToast("Vídeo 9:16 regerado com a nova legenda!", "success");

        // Abre modal para visualização imediata
        openVideoModal(updatedVideoUrl, `${cut?.title || cutId}.mp4`);
    } catch (e) {
        showToast(e.message || "Erro ao salvar legendas", "error");
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = origBtnHtml;
        }
    }
}

// --- GERAÇÃO DE 3 THUMBNAILS VIRAL YOUTUBE COM CLICKSCORE ---

async function generateProjectThumbnails(cutId = null) {
    if (!currentProjectId) {
        showToast("Nenhum vídeo em processamento.", "error");
        return;
    }

    const thumbsSection = document.getElementById("thumbs-section");
    const container = document.getElementById("thumbs-container");
    if (!thumbsSection || !container) return;

    thumbsSection.style.display = "block";
    thumbsSection.scrollIntoView({ behavior: "smooth", block: "start" });

    container.innerHTML = `
        <div class="col-span-full py-12 flex flex-col items-center justify-center text-center space-y-4">
            <div class="radar-dot w-6 h-6 bg-[#FF5C00]"></div>
            <div class="space-y-1">
                <h3 class="text-base font-black text-black">Gerando 3 Thumbnails em Alta Qualidade...</h3>
                <p class="text-xs text-zinc-600 font-medium">Recortando o interlocutor, buscando artes da obra na web e calculando o Clickscore de CTR.</p>
            </div>
        </div>
    `;

    try {
        const res = await fetch("/api/project/thumbnails", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                project_id: currentProjectId,
                cut_id: cutId
            })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "Erro ao gerar thumbnails.");
        }

        const data = await res.json();
        renderThumbnailsList(data.thumbnails || [], data.subject || "");
        showToast("3 Thumbnails para YouTube geradas com sucesso!", "success");
    } catch (e) {
        container.innerHTML = `
            <div class="col-span-full p-6 tech-card border-2 border-red-500 text-center">
                <p class="text-sm font-black text-red-600">Erro: ${escapeHtml(e.message)}</p>
                <button onclick="generateProjectThumbnails()" class="mt-3 btn-secondary text-xs">Tentar Novamente</button>
            </div>
        `;
        showToast(e.message, "error");
    }
}

function generateThumbnailsForCut(cutId) {
    generateProjectThumbnails(cutId);
}

function renderThumbnailsList(thumbnails, subject) {
    const container = document.getElementById("thumbs-container");
    if (!container) return;

    if (!thumbnails || thumbnails.length === 0) {
        container.innerHTML = `<div class="col-span-full text-center py-8 text-zinc-600 font-bold">Nenhuma thumbnail gerada.</div>`;
        return;
    }

    container.innerHTML = "";

    thumbnails.forEach((thumb, index) => {
        const score = thumb.clickscore || 85;
        const strategyTitle = thumb.strategy_name || thumb.name || `Opção ${index + 1}`;
        const description = thumb.description || thumb.rationale || "";
        const badgeText = thumb.badge || `Variação 0${index + 1}`;
        const breakdown = thumb.score_breakdown || thumb.metrics || {};
        const faceEmotion = breakdown.facial_emotion || breakdown.face_emotion || 92;
        const mobileRead = breakdown.mobile_readability || 95;
        const visualContrast = breakdown.visual_contrast || breakdown.contrast || 90;
        const curiosity = breakdown.curiosity_gap || 94;
        const titles = thumb.suggested_titles || (thumb.suggested_title ? [thumb.suggested_title] : []);

        // Cor do badge de Clickscore
        let scoreBadgeClass = "badge-neon";
        let scoreEmoji = "🔥";
        if (score >= 90) {
            scoreBadgeClass = "bg-[#25F4EE] text-black font-black border-2 border-black shadow-[2px_2px_0px_#000] px-2.5 py-1 rounded-md text-xs";
            scoreEmoji = "🚀 Alta Conversão";
        } else if (score >= 80) {
            scoreBadgeClass = "bg-[#FFE500] text-black font-black border-2 border-black shadow-[2px_2px_0px_#000] px-2.5 py-1 rounded-md text-xs";
            scoreEmoji = "⚡ Ótimo CTR";
        } else {
            scoreBadgeClass = "bg-[#FFF] text-black font-black border-2 border-black shadow-[2px_2px_0px_#000] px-2.5 py-1 rounded-md text-xs";
            scoreEmoji = "👍 Bom Potencial";
        }

        const card = document.createElement("div");
        card.className = "preview-card p-4 space-y-4 flex flex-col justify-between";
        card.innerHTML = `
            <div class="space-y-3">
                <!-- Cabeçalho da Variação -->
                <div class="flex items-center justify-between gap-2 border-b-2 border-black pb-2">
                    <div>
                        <span class="badge-blue text-[10px] font-black uppercase">${escapeHtml(badgeText)}</span>
                        <h3 class="text-sm font-black text-black leading-snug font-display mt-1">
                            ${escapeHtml(strategyTitle)}
                        </h3>
                    </div>
                    <div class="text-right">
                        <div class="${scoreBadgeClass}">
                            Clickscore: <span class="font-extrabold text-sm">${score}</span>/100
                        </div>
                        <span class="text-[10px] font-bold text-zinc-600 block mt-0.5">${scoreEmoji}</span>
                    </div>
                </div>

                <!-- Preview 16:9 Imagem Ultra Qualidade -->
                <div class="relative w-full aspect-video rounded-lg overflow-hidden border-2 border-black shadow-[3px_3px_0px_#000] bg-black group">
                    <img src="${thumb.image_url}" alt="Thumbnail ${index + 1}" class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105" loading="lazy">
                    <div class="absolute bottom-2 left-2 bg-black/80 text-white text-[10px] font-mono px-2 py-0.5 rounded border border-white/20">
                        1280x720 • HD
                    </div>
                </div>

                <p class="text-[11px] text-zinc-600 font-medium">
                    ${escapeHtml(description)}
                </p>

                <!-- Breakdown de Clickscore -->
                <div class="p-2.5 rounded-lg bg-[#F4F3EE] border-2 border-black text-[11px] space-y-1">
                    <strong class="text-black font-extrabold block uppercase text-[10px]">Métricas de CTR Estimadas:</strong>
                    <div class="grid grid-cols-2 gap-1 text-[10px] font-mono">
                        <div>Expressão Facial: <b class="text-black">${faceEmotion}%</b></div>
                        <div>Legibilidade Mobile: <b class="text-black">${mobileRead}%</b></div>
                        <div>Contraste Visual: <b class="text-black">${visualContrast}%</b></div>
                        <div>Gatilho Curiosidade: <b class="text-black">${curiosity}%</b></div>
                    </div>
                </div>

                <!-- Títulos Sugeridos para YouTube -->
                ${titles.length > 0 ? `
                <div class="space-y-1.5 pt-1">
                    <span class="text-[10px] font-black text-zinc-800 uppercase tracking-wider block">Títulos Sugeridos para CTR Alto:</span>
                    <div class="space-y-1">
                        ${titles.slice(0, 2).map(t => `
                            <div class="p-1.5 bg-white border border-black rounded text-[11px] font-bold text-black flex items-center justify-between gap-1 shadow-[1px_1px_0px_#000]">
                                <span class="truncate">"${escapeHtml(t)}"</span>
                                <button type="button" onclick="copySuggestedTitle(this, '${escapeHtml(t).replace(/'/g, "\\'")}')" class="text-[10px] font-black text-[#0052FF] hover:underline shrink-0">Copiar</button>
                            </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
            </div>

            <!-- Botão de Download da Imagem 1280x720 -->
            <div class="pt-3 border-t-2 border-black flex gap-2">
                <a href="${thumb.image_url}" download="thumb_${thumb.id || thumb.variation_id || index + 1}.jpg" class="btn-neon w-full justify-center text-xs py-2.5 font-black shadow-[2px_2px_0px_#000]">
                    <span>⬇️ Baixar Thumbnail (1280x720)</span>
                </a>
            </div>
        `;
        container.appendChild(card);
    });
}

function copySuggestedTitle(btn, titleText) {
    if (!titleText) return;
    const orig = btn.innerText;
    navigator.clipboard.writeText(titleText).then(() => {
        btn.innerText = "✓";
        setTimeout(() => { btn.innerText = orig; }, 2000);
        showToast("Título copiado!", "success");
    }).catch(() => {
        fallbackCopy(titleText);
        btn.innerText = "✓";
        setTimeout(() => { btn.innerText = orig; }, 2000);
        showToast("Título copiado!", "success");
    });
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

    const customColor = document.getElementById("custom-sub-color")?.value || "#FF5C00";
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

    const isAutoBroll = document.getElementById("btn-broll-auto")?.classList.contains("tech-card-active") ?? true;
    const brollUrl = document.getElementById("input-broll-url")?.value?.trim() || "";

    try {
        const res = await fetch("/api/project/render", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                project_id: currentProjectId,
                cut_id: cutId,
                layout: "split_screen",
                broll_mode: isAutoBroll ? "auto_extract" : "external",
                broll_source: brollUrl,
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
        pollRenderTask(data.render_task_id, cutId);
    } catch (e) {
        showToast(e.message, "error");
        if (renderSection) renderSection.style.display = "none";
    }
}

function pollRenderTask(renderTaskId, cutId = null) {
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

                // Atualiza o player embutido do próprio card
                if (cutId) {
                    const cardPlayer = document.getElementById(`player-cut-${cutId}`);
                    if (cardPlayer) {
                        cardPlayer.src = task.output_url;
                        cardPlayer.load();
                    }
                    const cardEl = document.getElementById(`card-cut-${cutId}`);
                    if (cardEl) {
                        const dlBtn = cardEl.querySelector("a[download]");
                        if (dlBtn) dlBtn.href = task.output_url;
                    }
                }

                openVideoModal(task.output_url, task.filename);
            } else if (task.status === "error") {
                clearInterval(poll);
                showToast(task.message || "Não foi possível gerar o vídeo. Tente novamente.", "error");
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

    // Listener para o color picker da legenda no modal
    const subColorInput = document.getElementById("edit-sub-color");
    if (subColorInput) {
        subColorInput.addEventListener("input", (e) => {
            const lbl = document.getElementById("edit-sub-color-label");
            if (lbl) lbl.innerText = e.target.value.toUpperCase();
        });
    }
});
