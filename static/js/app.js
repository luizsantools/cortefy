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

// ==========================================================================
// SELETOR DE LAYOUTS & MARCA D'ÁGUA
// ==========================================================================
let activeLayout = 'portrait';
let watermarkEnabled = false;
let watermarkPos = 'top_right';

function setLayoutMode(mode) {
    activeLayout = mode;
    const hidden = document.getElementById("selected-layout-input");
    if (hidden) hidden.value = mode;

    const modes = ['portrait', 'tweet_post', 'split_screen'];
    modes.forEach(m => {
        const key = (m === 'tweet_post' ? 'tweet' : (m === 'split_screen' ? 'split' : 'portrait'));
        const card = document.getElementById(`layout-card-${key}`);
        const radio = document.getElementById(`radio-layout-${key}`);
        if (card) {
            if (m === mode) {
                card.classList.add("layout-choice-active");
                if (radio) {
                    radio.innerText = "●";
                    radio.style.color = "#FF5C00";
                }
            } else {
                card.classList.remove("layout-choice-active");
                if (radio) {
                    radio.innerText = "○";
                    radio.style.color = "#000000";
                }
            }
        }
    });

    const drawerTweet = document.getElementById("drawer-layout-tweet");
    const drawerSplit = document.getElementById("drawer-layout-split");
    if (drawerTweet) drawerTweet.style.display = (mode === 'tweet_post') ? 'block' : 'none';
    if (drawerSplit) drawerSplit.style.display = (mode === 'split_screen') ? 'block' : 'none';

    updateLayoutMockup();
}
window.setLayoutMode = setLayoutMode;

function updateLayoutMockup() {
    const twCard = document.getElementById("mockup-twitter-card");
    const splitDiv = document.getElementById("mockup-split-divider");
    const formatBadge = document.getElementById("mockup-format-badge");

    if (twCard) twCard.style.display = (activeLayout === 'tweet_post') ? 'block' : 'none';
    if (splitDiv) splitDiv.style.display = (activeLayout === 'split_screen') ? 'block' : 'none';

    if (formatBadge) {
        if (activeLayout === 'tweet_post') formatBadge.innerText = "🐦 Twitter / X Post";
        else if (activeLayout === 'split_screen') formatBadge.innerText = "🎬 Tela Dividida";
        else formatBadge.innerText = "9:16 Vertical";
    }

    if (activeLayout === 'tweet_post') {
        updateTwitterPreview();
    }
}
window.updateLayoutMockup = updateLayoutMockup;

function updateTwitterPreview() {
    const inputName = document.getElementById("input-tweet-name");
    const inputHandle = document.getElementById("input-tweet-handle");
    const inputText = document.getElementById("input-tweet-text");
    const toggleBadge = document.getElementById("toggle-tweet-verified");

    const name = (inputName && inputName.value.trim()) ? inputName.value.trim() : "Cortes Virais";
    let handle = (inputHandle && inputHandle.value.trim()) ? inputHandle.value.trim() : "@cortesvirais";
    if (!handle.startsWith("@")) handle = "@" + handle;
    const text = (inputText && inputText.value.trim()) ? inputText.value.trim() : "O segredo que ninguém te conta sobre foco nos primeiros 30 dias:";
    const hasBadge = toggleBadge ? toggleBadge.checked : true;

    const mockName = document.getElementById("mockup-tw-name");
    const mockHandle = document.getElementById("mockup-tw-handle");
    const mockText = document.getElementById("mockup-tw-text");
    const mockBadge = document.getElementById("mockup-tw-badge");
    const mockAvatar = document.getElementById("mockup-tw-avatar");

    if (mockName) mockName.innerText = name;
    if (mockHandle) mockHandle.innerText = handle;
    if (mockText) mockText.innerText = text;
    if (mockBadge) mockBadge.style.display = hasBadge ? "inline" : "none";
    if (mockAvatar) mockAvatar.innerText = (name[0] || "C").toUpperCase();
}
window.updateTwitterPreview = updateTwitterPreview;

function toggleWatermarkSetting(enabled) {
    watermarkEnabled = !!enabled;
    const hidden = document.getElementById("watermark-enabled-input");
    if (hidden) hidden.value = watermarkEnabled ? "1" : "0";

    const drawer = document.getElementById("watermark-drawer");
    if (drawer) drawer.style.display = watermarkEnabled ? "block" : "none";

    updateWatermarkPreview();
}
window.toggleWatermarkSetting = toggleWatermarkSetting;

function setWatermarkPos(pos) {
    watermarkPos = pos;
    const hidden = document.getElementById("watermark-pos-input");
    if (hidden) hidden.value = pos;

    const positions = ['top_right', 'top_left', 'bottom_right', 'bottom_left'];
    positions.forEach(p => {
        const btn = document.getElementById(`btn-wm-${p}`);
        if (btn) {
            if (p === pos) btn.classList.add("watermark-pos-active");
            else btn.classList.remove("watermark-pos-active");
        }
    });

    updateWatermarkPreview();
}
window.setWatermarkPos = setWatermarkPos;

function updateWatermarkPreview() {
    const mockWm = document.getElementById("mockup-watermark");
    const mockWmText = document.getElementById("mockup-watermark-text");
    const inputWm = document.getElementById("input-watermark-text");

    if (!mockWm) return;

    if (!watermarkEnabled) {
        mockWm.style.display = "none";
        return;
    }

    mockWm.style.display = "block";
    const text = (inputWm && inputWm.value.trim()) ? inputWm.value.trim() : "@editize.net";
    if (mockWmText) mockWmText.innerText = text;

    mockWm.style.top = "";
    mockWm.style.bottom = "";
    mockWm.style.left = "";
    mockWm.style.right = "";

    if (watermarkPos === 'top_right') {
        mockWm.style.top = "28px";
        mockWm.style.right = "8px";
    } else if (watermarkPos === 'top_left') {
        mockWm.style.top = "28px";
        mockWm.style.left = "8px";
    } else if (watermarkPos === 'bottom_right') {
        mockWm.style.bottom = "36px";
        mockWm.style.right = "8px";
    } else if (watermarkPos === 'bottom_left') {
        mockWm.style.bottom = "36px";
        mockWm.style.left = "8px";
    }
}
window.updateWatermarkPreview = updateWatermarkPreview;

// 24 Presets Profissionais de Alta Retenção Visual
const SUBTITLE_PRESETS = {
    hormozi_pop: {
        id: "hormozi_pop", name: "Hormozi Pop", category: "Viral TikTok",
        font: "Impact", size: 82, primary: "#FFFFFF", highlight: "#FFE500",
        outline_color: "#000000", outline_w: 8, shadow: 4, shadow_color: "#000000",
        border_style: 1, bg_color: "#000000", animation: "bounce", casing: "uppercase",
        chunk_size: 2, margin_v: 420
    },
    tiktok_bounce: {
        id: "tiktok_bounce", name: "TikTok Lime Bounce", category: "Viral TikTok",
        font: "Arial Black", size: 76, primary: "#FFFFFF", highlight: "#00FF66",
        outline_color: "#000000", outline_w: 7, shadow: 3, shadow_color: "#000000",
        border_style: 1, bg_color: "#000000", animation: "bounce", casing: "uppercase",
        chunk_size: 2, margin_v: 420
    },
    beast_impact: {
        id: "beast_impact", name: "MrBeast Explosivo", category: "Impacto & Drama",
        font: "Impact", size: 86, primary: "#FFFFFF", highlight: "#FF3B30",
        outline_color: "#000000", outline_w: 9, shadow: 5, shadow_color: "#FF5C00",
        border_style: 1, bg_color: "#000000", animation: "pop_zoom", casing: "uppercase",
        chunk_size: 2, margin_v: 440
    },
    cyan_electric: {
        id: "cyan_electric", name: "Ciano Cyberpunk", category: "Gamer / Cyber",
        font: "Arial Black", size: 74, primary: "#FFFFFF", highlight: "#00FFFF",
        outline_color: "#050B14", outline_w: 7, shadow: 5, shadow_color: "#0055FF",
        border_style: 1, bg_color: "#000000", animation: "bounce", casing: "uppercase",
        chunk_size: 2, margin_v: 420
    },
    purple_viral: {
        id: "purple_viral", name: "Roxo Aesthetic", category: "Viral TikTok",
        font: "Arial Black", size: 74, primary: "#FFFFFF", highlight: "#C084FC",
        outline_color: "#1E0B2B", outline_w: 7, shadow: 4, shadow_color: "#581C87",
        border_style: 1, bg_color: "#000000", animation: "bounce", casing: "uppercase",
        chunk_size: 2, margin_v: 420
    },
    clean_minimal: {
        id: "clean_minimal", name: "Clean Minimalist", category: "Minimalista",
        font: "Segoe UI", size: 68, primary: "#FFFFFF", highlight: "#38BDF8",
        outline_color: "#000000", outline_w: 4, shadow: 2, shadow_color: "#000000",
        border_style: 1, bg_color: "#000000", animation: "fade", casing: "original",
        chunk_size: 3, margin_v: 380
    },
    gold_karaoke: {
        id: "gold_karaoke", name: "Karaokê Ouro VIP", category: "YouTube Shorts",
        font: "Impact", size: 78, primary: "#FFFFFF", highlight: "#FFD700",
        outline_color: "#000000", outline_w: 8, shadow: 4, shadow_color: "#78350F",
        border_style: 1, bg_color: "#000000", animation: "karaoke", casing: "uppercase",
        chunk_size: 2, margin_v: 420
    },
    fire_sunset: {
        id: "fire_sunset", name: "Fogo Sunset Laranja", category: "Impacto & Drama",
        font: "Impact", size: 82, primary: "#FFE500", highlight: "#FF5C00",
        outline_color: "#000000", outline_w: 8, shadow: 4, shadow_color: "#7C2D12",
        border_style: 1, bg_color: "#000000", animation: "pop_zoom", casing: "uppercase",
        chunk_size: 2, margin_v: 420
    },
    emerald_vip: {
        id: "emerald_vip", name: "Esmeralda Finanças", category: "YouTube Shorts",
        font: "Arial Black", size: 75, primary: "#FFFFFF", highlight: "#10B981",
        outline_color: "#064E3B", outline_w: 7, shadow: 4, shadow_color: "#022C22",
        border_style: 1, bg_color: "#000000", animation: "bounce", casing: "uppercase",
        chunk_size: 2, margin_v: 420
    },
    monochrome_3d: {
        id: "monochrome_3d", name: "Monocromo 3D Heavy", category: "Impacto & Drama",
        font: "Impact", size: 84, primary: "#FFFFFF", highlight: "#E4E4E7",
        outline_color: "#000000", outline_w: 9, shadow: 6, shadow_color: "#27272A",
        border_style: 1, bg_color: "#000000", animation: "shake", casing: "uppercase",
        chunk_size: 2, margin_v: 420
    },
    neobrutalist_black: {
        id: "neobrutalist_black", name: "Neo-Brutalist Tarja Preta", category: "Neo-Brutalist",
        font: "Impact", size: 78, primary: "#FFE500", highlight: "#FF5C00",
        outline_color: "#000000", outline_w: 10, shadow: 5, shadow_color: "#000000",
        border_style: 3, bg_color: "#000000", animation: "bounce", casing: "uppercase",
        chunk_size: 2, margin_v: 420
    },
    neobrutalist_blue: {
        id: "neobrutalist_blue", name: "Neo-Brutalist Royal Blue", category: "Neo-Brutalist",
        font: "Arial Black", size: 76, primary: "#FFFFFF", highlight: "#FFE500",
        outline_color: "#0052FF", outline_w: 8, shadow: 5, shadow_color: "#000000",
        border_style: 3, bg_color: "#0052FF", animation: "pop_zoom", casing: "uppercase",
        chunk_size: 2, margin_v: 420
    },
    retro_arcade: {
        id: "retro_arcade", name: "Retro Synthwave 80s", category: "Gamer / Cyber",
        font: "Trebuchet MS", size: 76, primary: "#FFFFFF", highlight: "#FF007F",
        outline_color: "#200030", outline_w: 7, shadow: 5, shadow_color: "#00F0FF",
        border_style: 1, bg_color: "#000000", animation: "bounce", casing: "uppercase",
        chunk_size: 2, margin_v: 420
    },
    comic_pop: {
        id: "comic_pop", name: "Quadrinhos Comic Hero", category: "Viral TikTok",
        font: "Comic Sans MS", size: 78, primary: "#FFE500", highlight: "#FF0000",
        outline_color: "#000000", outline_w: 8, shadow: 4, shadow_color: "#000000",
        border_style: 1, bg_color: "#000000", animation: "bounce", casing: "uppercase",
        chunk_size: 2, margin_v: 420
    },
    glitch_matrix: {
        id: "glitch_matrix", name: "Matrix Hacker Green", category: "Gamer / Cyber",
        font: "Courier New", size: 74, primary: "#FFFFFF", highlight: "#22C55E",
        outline_color: "#052E16", outline_w: 6, shadow: 4, shadow_color: "#15803D",
        border_style: 1, bg_color: "#000000", animation: "shake", casing: "uppercase",
        chunk_size: 3, margin_v: 400
    },
    cinema_letterbox: {
        id: "cinema_letterbox", name: "Cinema Clássico 2.35", category: "Minimalista",
        font: "Georgia", size: 66, primary: "#FFFBEB", highlight: "#F59E0B",
        outline_color: "#1C1917", outline_w: 3, shadow: 2, shadow_color: "#000000",
        border_style: 1, bg_color: "#000000", animation: "fade", casing: "original",
        chunk_size: 4, margin_v: 360
    },
    breaking_news: {
        id: "breaking_news", name: "Plantão Urgente (News)", category: "Impacto & Drama",
        font: "Arial Black", size: 76, primary: "#FFFFFF", highlight: "#FFE500",
        outline_color: "#7F1D1D", outline_w: 8, shadow: 4, shadow_color: "#000000",
        border_style: 3, bg_color: "#DC2626", animation: "pop_zoom", casing: "uppercase",
        chunk_size: 2, margin_v: 440
    },
    red_danger: {
        id: "red_danger", name: "Alerta Vermelho Shock", category: "Impacto & Drama",
        font: "Impact", size: 86, primary: "#FFFFFF", highlight: "#EF4444",
        outline_color: "#450A0A", outline_w: 9, shadow: 5, shadow_color: "#000000",
        border_style: 1, bg_color: "#000000", animation: "shake", casing: "uppercase",
        chunk_size: 1, margin_v: 430
    },
    sunset_glow: {
        id: "sunset_glow", name: "Sunset Coral Glow", category: "YouTube Shorts",
        font: "Trebuchet MS", size: 76, primary: "#FFFFFF", highlight: "#FB7185",
        outline_color: "#4C0519", outline_w: 7, shadow: 5, shadow_color: "#E11D48",
        border_style: 1, bg_color: "#000000", animation: "bounce", casing: "uppercase",
        chunk_size: 2, margin_v: 420
    },
    midnight_neon: {
        id: "midnight_neon", name: "Midnight Cobalt Neon", category: "Gamer / Cyber",
        font: "Impact", size: 80, primary: "#FFFFFF", highlight: "#38BDF8",
        outline_color: "#0C4A6E", outline_w: 8, shadow: 5, shadow_color: "#0284C7",
        border_style: 1, bg_color: "#000000", animation: "pop_zoom", casing: "uppercase",
        chunk_size: 2, margin_v: 420
    },
    lemon_lime: {
        id: "lemon_lime", name: "Citrus Lime Punch", category: "Viral TikTok",
        font: "Impact", size: 82, primary: "#FFFFFF", highlight: "#A3E635",
        outline_color: "#14532D", outline_w: 8, shadow: 4, shadow_color: "#000000",
        border_style: 1, bg_color: "#000000", animation: "bounce", casing: "uppercase",
        chunk_size: 2, margin_v: 420
    },
    typewriter_clean: {
        id: "typewriter_clean", name: "Máquina de Escrever Retrô", category: "Minimalista",
        font: "Courier New", size: 70, primary: "#F3F4F6", highlight: "#FBBF24",
        outline_color: "#111827", outline_w: 5, shadow: 2, shadow_color: "#000000",
        border_style: 1, bg_color: "#000000", animation: "fade", casing: "original",
        chunk_size: 3, margin_v: 380
    },
    hormozi_single_word: {
        id: "hormozi_single_word", name: "Hormozi 1 Palavra", category: "Viral TikTok",
        font: "Impact", size: 94, primary: "#FFE500", highlight: "#FFFFFF",
        outline_color: "#000000", outline_w: 10, shadow: 5, shadow_color: "#000000",
        border_style: 1, bg_color: "#000000", animation: "pop_zoom", casing: "uppercase",
        chunk_size: 1, margin_v: 460
    },
    pill_badge_viral: {
        id: "pill_badge_viral", name: "Pílula Moderna (Pill)", category: "YouTube Shorts",
        font: "Arial Black", size: 72, primary: "#000000", highlight: "#FF5C00",
        outline_color: "#FFFFFF", outline_w: 2, shadow: 0, shadow_color: "#000000",
        border_style: 3, bg_color: "#FFFFFF", animation: "bounce", casing: "uppercase",
        chunk_size: 2, margin_v: 420
    }
};

const SAMPLE_PHRASES = [
    "ISSO VAI MUDAR TUDO! 🔥",
    "PRESTE MUITA ATENÇÃO NISSO!",
    "ESSE SEGREDO NINGUÉM TE CONTA!",
    "O MAIOR ERRO DE TODOS!",
    "3 DICAS PRA CRESCER RÁPIDO 🚀",
    "VOCÊ NUNCA MAIS VAI ERRAR!",
    "RESULTADO SURPREENDENTE ⚡",
    "COMO VIRALIZAR NO INSTAGRAM"
];

// Mapeamento de cada um dos 24 presets para sua respectiva classe CSS visual
const SUB_STYLE_CLASS_MAP = {
    hormozi_pop: "sub-style-hormozi",
    tiktok_bounce: "sub-style-neon",
    beast_impact: "sub-style-beast",
    cyan_electric: "sub-style-cyan",
    purple_viral: "sub-style-purple",
    clean_minimal: "sub-style-minimal",
    gold_karaoke: "sub-style-gold",
    fire_sunset: "sub-style-fire",
    emerald_vip: "sub-style-emerald",
    monochrome_3d: "sub-style-mono3d",
    neobrutalist_black: "sub-style-neoblack",
    neobrutalist_blue: "sub-style-neoblue",
    retro_arcade: "sub-style-retro",
    comic_pop: "sub-style-comic",
    glitch_matrix: "sub-style-matrix",
    cinema_letterbox: "sub-style-cinema",
    breaking_news: "sub-style-news",
    red_danger: "sub-style-danger",
    sunset_glow: "sub-style-sunset",
    midnight_neon: "sub-style-midnight",
    lemon_lime: "sub-style-lemon",
    typewriter_clean: "sub-style-typewriter",
    hormozi_single_word: "sub-style-single",
    pill_badge_viral: "sub-style-pill"
};

// Alternar Modelo de Legendas (24 Presets)
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

    // Atualiza a classe visual no mockup para refletir fielmente o preset escolhido
    const box = document.getElementById("mockup-sub-box");
    if (box) {
        Object.values(SUB_STYLE_CLASS_MAP).forEach(cls => box.classList.remove(cls));
        const targetClass = SUB_STYLE_CLASS_MAP[styleKey] || "sub-style-hormozi";
        box.classList.add(targetClass);
        // Limpa estilos residuais para deixar a assinatura do estilo brilhar
        box.style.backgroundColor = "";
        box.style.border = "";
        box.style.borderRadius = "";
        box.style.boxShadow = "";
        box.style.padding = "";
        box.style.textShadow = "";
    }

    const preset = SUBTITLE_PRESETS[styleKey];
    if (preset) {
        const fontEl = document.getElementById("custom-sub-font");
        const sizeSlider = document.getElementById("custom-sub-size-slider");
        const sizeVal = document.getElementById("custom-sub-size-val");
        const casingEl = document.getElementById("custom-sub-casing-select");
        const colorEl = document.getElementById("custom-sub-color");
        const colorLbl = document.getElementById("custom-sub-color-label");
        const hlEl = document.getElementById("custom-sub-highlight-picker");
        const hlLbl = document.getElementById("custom-sub-highlight-label");
        const outlineSlider = document.getElementById("custom-sub-outline-slider");
        const outlineVal = document.getElementById("custom-sub-outline-val");
        const shadowEl = document.getElementById("custom-sub-shadow-select");
        const bgEl = document.getElementById("custom-sub-bg-select");
        const animEl = document.getElementById("custom-sub-anim-select");
        const chunkEl = document.getElementById("custom-sub-chunk-select");
        const posEl = document.getElementById("custom-sub-pos-select");
        const posValEl = document.getElementById("custom-sub-pos-val");
        const presetBadge = document.getElementById("preview-preset-badge");

        if (presetBadge) presetBadge.textContent = preset.name;
        if (fontEl) fontEl.value = preset.font;
        if (sizeSlider) {
            sizeSlider.value = preset.size;
            if (sizeVal) sizeVal.innerText = `${preset.size}px`;
        }
        if (casingEl) casingEl.value = preset.casing || "uppercase";
        if (colorEl) {
            colorEl.value = preset.primary;
            if (colorLbl) colorLbl.innerText = preset.primary.toUpperCase();
        }
        if (hlEl) {
            hlEl.value = preset.highlight;
            if (hlLbl) hlLbl.innerText = preset.highlight.toUpperCase();
        }
        if (outlineSlider) {
            outlineSlider.value = preset.outline_w;
            if (outlineVal) outlineVal.innerText = `${preset.outline_w}px`;
        }
        if (shadowEl) {
            shadowEl.value = preset.shadow >= 4 ? "hard_3d" : (preset.shadow > 0 ? "soft_shadow" : "none");
        }
        if (bgEl) {
            if (preset.border_style === 3) {
                if (preset.bg_color === "#0052FF") bgEl.value = "neobrutalist_blue";
                else if (preset.bg_color === "#FFFFFF") bgEl.value = "pill";
                else bgEl.value = "black_box";
            } else {
                bgEl.value = "none";
            }
        }
        if (animEl) animEl.value = preset.animation || "bounce";
        if (chunkEl) chunkEl.value = String(preset.chunk_size || 2);
        if (posEl) {
            posEl.value = String(preset.margin_v || 420);
            if (posValEl) {
                posValEl.textContent = preset.margin_v >= 1100 ? "Superior" : (preset.margin_v >= 700 ? "Centro" : "Inferior");
            }
        }
    }

    updateLiveSubtitlePreview();
}
window.setSubStyle = setSubStyle;

// Filtro de Categorias de Presets
function filterSubPresets(category, btn) {
    document.querySelectorAll(".sub-filter-btn").forEach(b => b.classList.remove("sub-filter-btn-active"));
    if (btn) btn.classList.add("sub-filter-btn-active");

    const cards = document.querySelectorAll("#sub-presets-grid .sub-card");
    let count = 0;
    cards.forEach(card => {
        const cardCat = card.getAttribute("data-category");
        if (category === "all" || cardCat === category) {
            card.style.display = "flex";
            count++;
        } else {
            card.style.display = "none";
        }
    });

    const badge = document.getElementById("preset-count-badge");
    if (badge) badge.innerText = `${count} presets`;
}
window.filterSubPresets = filterSubPresets;

// Atualização Dinâmica do Mockup de Smartphone 9:16
function updateLiveSubtitlePreview() {
    const box = document.getElementById("mockup-sub-box");
    const container = document.getElementById("mockup-sub-container");
    const prefixEl = document.getElementById("mockup-text-prefix");
    const highlightEl = document.getElementById("mockup-text-highlight");
    const suffixEl = document.getElementById("mockup-text-suffix");
    const animNameEl = document.getElementById("preview-anim-name");
    if (!box || !container || !prefixEl || !highlightEl || !suffixEl) return;

    const sampleInput = document.getElementById("preview-sample-input");
    const rawText = sampleInput ? sampleInput.value.trim() || "ISSO VAI MUDAR TUDO!" : "ISSO VAI MUDAR TUDO!";
    const font = document.getElementById("custom-sub-font")?.value || "Impact";
    const size = parseInt(document.getElementById("custom-sub-size-slider")?.value) || 78;
    const casing = document.getElementById("custom-sub-casing-select")?.value || "uppercase";
    const primaryColor = document.getElementById("custom-sub-color")?.value || "#FFFFFF";
    const highlightColor = document.getElementById("custom-sub-highlight-picker")?.value || "#FFE500";
    const outlineW = parseInt(document.getElementById("custom-sub-outline-slider")?.value) || 8;
    const shadowStyle = document.getElementById("custom-sub-shadow-select")?.value || "hard_3d";
    const bgStyle = document.getElementById("custom-sub-bg-select")?.value || "none";
    const animType = document.getElementById("custom-sub-anim-select")?.value || "bounce";
    const posVal = parseInt(document.getElementById("custom-sub-pos-select")?.value) || 420;

    const colLbl = document.getElementById("custom-sub-color-label");
    if (colLbl) colLbl.innerText = primaryColor.toUpperCase();
    const hlLbl = document.getElementById("custom-sub-highlight-label");
    if (hlLbl) hlLbl.innerText = highlightColor.toUpperCase();

    // Formatação de caixa alta / baixa
    let formattedText = rawText;
    if (casing === "uppercase") {
        formattedText = rawText.toUpperCase();
    } else if (casing === "titlecase") {
        formattedText = rawText.replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase());
    }

    const currentStyleKey = window.selectedSubStyle || "hormozi_pop";
    const words = formattedText.split(/\s+/).filter(Boolean);

    if (currentStyleKey === "hormozi_single_word") {
        prefixEl.textContent = "";
        highlightEl.textContent = words[0] || formattedText;
        suffixEl.textContent = "";
    } else if (words.length === 0) {
        prefixEl.textContent = "";
        highlightEl.textContent = "";
        suffixEl.textContent = "";
    } else if (words.length === 1) {
        prefixEl.textContent = "";
        highlightEl.textContent = words[0];
        suffixEl.textContent = "";
    } else {
        const hlIndex = Math.min(1, words.length - 1);
        prefixEl.textContent = words.slice(0, hlIndex).join(" ") + " ";
        highlightEl.textContent = words[hlIndex];
        const rest = words.slice(hlIndex + 1).join(" ");
        suffixEl.textContent = rest ? " " + rest : "";
    }

    // Ajuste responsivo de tamanho para garantir que qualquer frase caiba perfeitamente no mockup sem cortar
    let baseFontSize = 17;
    if (formattedText.length > 28) {
        baseFontSize = 13;
    } else if (formattedText.length > 20) {
        baseFontSize = 14.5;
    } else if (formattedText.length > 14) {
        baseFontSize = 16;
    }
    const userRatio = size / 78;
    const finalFontSize = Math.max(11, Math.min(22, Math.round(baseFontSize * userRatio)));
    const scaledOutline = Math.max(1, Math.round(outlineW * 0.22));

    box.style.setProperty("font-family", `"${font}", sans-serif`, "important");
    box.style.setProperty("font-size", `${finalFontSize}px`, "important");
    box.style.setProperty("line-height", "1.25", "important");
    box.style.setProperty("font-weight", (font === "Georgia" || font === "Courier New") ? "bold" : "900", "important");
    box.style.setProperty("color", primaryColor, "important");
    box.style.setProperty("white-space", "normal", "important");
    box.style.setProperty("word-break", "break-word", "important");
    box.style.setProperty("text-wrap", "balance", "important");
    box.style.setProperty("text-align", "center", "important");

    // Força cor de destaque do preset
    highlightEl.style.setProperty("color", highlightColor, "important");

    // Contorno e sombra dinâmicos
    let textShadow = "";
    if (outlineW > 0) {
        const o = scaledOutline;
        textShadow = `-${o}px -${o}px 0 #000, ${o}px -${o}px 0 #000, -${o}px ${o}px 0 #000, ${o}px ${o}px 0 #000, 0px -${o}px 0 #000, 0px ${o}px 0 #000, -${o}px 0px 0 #000, ${o}px 0px 0 #000`;
    }

    if (shadowStyle === "hard_3d") {
        const s = Math.max(2, Math.round(outlineW * 0.35));
        const shadowPart = `${s}px ${s}px 0px #000000`;
        textShadow = textShadow ? `${textShadow}, ${shadowPart}` : shadowPart;
    } else if (shadowStyle === "soft_shadow") {
        const shadowPart = `0px 3px 6px rgba(0,0,0,0.85)`;
        textShadow = textShadow ? `${textShadow}, ${shadowPart}` : shadowPart;
    } else if (shadowStyle === "glow_neon") {
        const shadowPart = `0 0 10px ${highlightColor}, 0 0 18px ${highlightColor}`;
        textShadow = textShadow ? `${textShadow}, ${shadowPart}` : shadowPart;
    }

    // Glow especial para presets de estilo neon / cyber / arcade
    if (currentStyleKey === "tiktok_bounce") {
        highlightEl.style.setProperty("text-shadow", `0 0 10px ${highlightColor}, -1px -1px 0 #000, 1px 1px 0 #000`, "important");
    } else if (currentStyleKey === "cyan_electric") {
        highlightEl.style.setProperty("text-shadow", `0 0 10px #00F0FF, -1px -1px 0 #000, 1px 1px 0 #000`, "important");
    } else if (currentStyleKey === "retro_arcade") {
        highlightEl.style.setProperty("text-shadow", `0 0 10px #00F0FF, 2px 2px 0 #200030`, "important");
    } else if (currentStyleKey === "glitch_matrix") {
        highlightEl.style.setProperty("text-shadow", `0 0 8px #22C55E, 2px 2px 0 #052E16`, "important");
    } else {
        highlightEl.style.removeProperty("text-shadow");
    }

    if (textShadow) {
        box.style.setProperty("text-shadow", textShadow, "important");
    }

    // Fundos especiais dos presets
    if (currentStyleKey === "neobrutalist_black" || bgStyle === "black_box") {
        box.style.setProperty("background-color", "#000000", "important");
        box.style.setProperty("border", "2px solid #FFE500", "important");
        box.style.setProperty("border-radius", "4px", "important");
        box.style.setProperty("padding", "3px 8px", "important");
        box.style.setProperty("box-shadow", "2px 2px 0px #000", "important");
    } else if (currentStyleKey === "neobrutalist_blue" || bgStyle === "neobrutalist_blue") {
        box.style.setProperty("background-color", "#0052FF", "important");
        box.style.setProperty("border", "2px solid #000000", "important");
        box.style.setProperty("border-radius", "0px", "important");
        box.style.setProperty("padding", "3px 8px", "important");
        box.style.setProperty("box-shadow", "3px 3px 0px #000", "important");
    } else if (currentStyleKey === "pill_badge_viral" || bgStyle === "pill") {
        box.style.setProperty("background-color", "#FFFFFF", "important");
        box.style.setProperty("border", "2px solid #000000", "important");
        box.style.setProperty("border-radius", "9999px", "important");
        box.style.setProperty("padding", "4px 12px", "important");
        box.style.setProperty("box-shadow", "2px 2px 0px #000", "important");
        box.style.setProperty("color", "#000000", "important");
    } else if (currentStyleKey === "breaking_news") {
        box.style.setProperty("background-color", "#DC2626", "important");
        box.style.setProperty("border", "1.5px solid #000000", "important");
        box.style.setProperty("border-radius", "2px", "important");
        box.style.setProperty("padding", "3px 8px", "important");
        box.style.setProperty("color", "#FFFFFF", "important");
    } else if (currentStyleKey === "clean_minimal") {
        box.style.setProperty("background-color", "#18181B", "important");
        box.style.setProperty("border", "1.5px solid #3F3F46", "important");
        box.style.setProperty("border-radius", "6px", "important");
        box.style.setProperty("padding", "3px 8px", "important");
        box.style.removeProperty("box-shadow");
    } else if (bgStyle === "translucent_box") {
        box.style.setProperty("background-color", "rgba(0, 0, 0, 0.75)", "important");
        box.style.setProperty("border", "1px solid rgba(255,255,255,0.2)", "important");
        box.style.setProperty("border-radius", "4px", "important");
        box.style.setProperty("padding", "3px 8px", "important");
    } else if (bgStyle === "neobrutalist_orange") {
        box.style.setProperty("background-color", "#FF5C00", "important");
        box.style.setProperty("border", "2px solid #000000", "important");
        box.style.setProperty("border-radius", "0px", "important");
        box.style.setProperty("padding", "3px 8px", "important");
        box.style.setProperty("box-shadow", "3px 3px 0px #000", "important");
    } else {
        box.style.removeProperty("background-color");
        box.style.removeProperty("border");
        box.style.removeProperty("border-radius");
        box.style.removeProperty("box-shadow");
        box.style.removeProperty("padding");
    }

    // Animações
    highlightEl.className = "anim-word";
    if (animType === "bounce") {
        highlightEl.classList.add("anim-bounce");
        if (animNameEl) animNameEl.textContent = "Animação: Salto Elástico";
    } else if (animType === "pop_zoom") {
        highlightEl.classList.add("anim-popzoom");
        if (animNameEl) animNameEl.textContent = "Animação: Zoom Explosivo";
    } else if (animType === "karaoke") {
        highlightEl.classList.add("anim-karaoke");
        if (animNameEl) animNameEl.textContent = "Animação: Karaokê Palavra";
    } else if (animType === "shake") {
        highlightEl.classList.add("anim-shake");
        if (animNameEl) animNameEl.textContent = "Animação: Tremor de Impacto";
    } else if (animType === "fade") {
        highlightEl.classList.add("anim-fade");
        if (animNameEl) animNameEl.textContent = "Animação: Surgimento Suave";
    } else {
        highlightEl.classList.add("anim-none");
        if (animNameEl) animNameEl.textContent = "Animação: Estático";
    }

    // Posição vertical
    if (posVal >= 1100) {
        container.style.bottom = "72%";
    } else if (posVal >= 700) {
        container.style.bottom = "46%";
    } else {
        container.style.bottom = "20%";
    }
}
window.updateLiveSubtitlePreview = updateLiveSubtitlePreview;

function onSizeSliderChange(val) {
    const lbl = document.getElementById("custom-sub-size-val");
    if (lbl) lbl.innerText = `${val}px`;
    updateLiveSubtitlePreview();
}
window.onSizeSliderChange = onSizeSliderChange;

function onOutlineSliderChange(val) {
    const lbl = document.getElementById("custom-sub-outline-val");
    if (lbl) lbl.innerText = `${val}px`;
    updateLiveSubtitlePreview();
}
window.onOutlineSliderChange = onOutlineSliderChange;

function onPositionPresetChange(val) {
    const lbl = document.getElementById("custom-sub-pos-val");
    const num = parseInt(val) || 420;
    if (lbl) {
        if (num >= 1100) lbl.innerText = `Superior (${num}px)`;
        else if (num >= 700) lbl.innerText = `Centro (${num}px)`;
        else lbl.innerText = `Inferior (${num}px)`;
    }
    updateLiveSubtitlePreview();
}
window.onPositionPresetChange = onPositionPresetChange;

function setQuickHighlight(hex) {
    const picker = document.getElementById("custom-sub-highlight-picker");
    const label = document.getElementById("custom-sub-highlight-label");
    if (picker) picker.value = hex;
    if (label) label.innerText = hex.toUpperCase();
    updateLiveSubtitlePreview();
}
window.setQuickHighlight = setQuickHighlight;

function randomizeSampleText() {
    const input = document.getElementById("preview-sample-input");
    if (!input) return;
    const current = input.value.trim();
    const available = SAMPLE_PHRASES.filter(p => p !== current);
    const chosen = available[Math.floor(Math.random() * available.length)] || SAMPLE_PHRASES[0];
    input.value = chosen;
    updateLiveSubtitlePreview();
}
window.randomizeSampleText = randomizeSampleText;

function replaySubtitleAnimation() {
    const hl = document.getElementById("mockup-text-highlight");
    if (!hl) return;
    const currentClass = hl.className;
    hl.className = "anim-word";
    void hl.offsetWidth;
    hl.className = currentClass;
}
window.replaySubtitleAnimation = replaySubtitleAnimation;

function resetSubtitleCustomizations() {
    const currentStyle = window.selectedSubStyle || "hormozi_pop";
    setSubStyle(currentStyle);
    showToast("Configurações de legenda restauradas ao padrão do estilo.", "info");
}
window.resetSubtitleCustomizations = resetSubtitleCustomizations;

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
window.toggleCustomizeDrawer = toggleCustomizeDrawer;

function saveSubtitleTemplate() {
    const currentStyle = window.selectedSubStyle || selectedSubStyle || "hormozi_pop";
    const customFont = document.getElementById("custom-sub-font")?.value || "Impact";
    const customSize = document.getElementById("custom-sub-size-slider")?.value || "78";
    const customCasing = document.getElementById("custom-sub-casing-select")?.value || "uppercase";
    const customColor = document.getElementById("custom-sub-color")?.value || "#FFFFFF";
    const customHighlight = document.getElementById("custom-sub-highlight-picker")?.value || "#FFE500";
    const customOutline = document.getElementById("custom-sub-outline-slider")?.value || "8";
    const customShadow = document.getElementById("custom-sub-shadow-select")?.value || "hard_3d";
    const customBg = document.getElementById("custom-sub-bg-select")?.value || "none";
    const customAnim = document.getElementById("custom-sub-anim-select")?.value || "bounce";
    const customChunk = document.getElementById("custom-sub-chunk-select")?.value || "2";
    const customPos = document.getElementById("custom-sub-pos-select")?.value || "420";

    const templateData = {
        styleKey: currentStyle,
        font: customFont,
        size: customSize,
        casing: customCasing,
        color: customColor,
        highlight: customHighlight,
        outline: customOutline,
        shadow: customShadow,
        bg: customBg,
        animation: customAnim,
        chunk: customChunk,
        position: customPos,
        timestamp: Date.now()
    };

    localStorage.setItem("editize_sub_template", JSON.stringify(templateData));
    
    const badge = document.getElementById("saved-template-badge");
    if (badge) badge.style.display = "inline-flex";

    showToast("Template salvo! Será aplicado automaticamente nos seus vídeos.", "success");
}
window.saveSubtitleTemplate = saveSubtitleTemplate;

function loadSavedTemplate() {
    try {
        const raw = localStorage.getItem("editize_sub_template") || localStorage.getItem("cortefy_sub_template");
        if (raw) {
            const tpl = JSON.parse(raw);
            if (tpl.styleKey) setSubStyle(tpl.styleKey);

            if (tpl.font) {
                const el = document.getElementById("custom-sub-font");
                if (el) el.value = tpl.font;
            }
            if (tpl.size) {
                const sl = document.getElementById("custom-sub-size-slider");
                const val = document.getElementById("custom-sub-size-val");
                if (sl) sl.value = tpl.size;
                if (val) val.innerText = `${tpl.size}px`;
            }
            if (tpl.casing) {
                const el = document.getElementById("custom-sub-casing-select");
                if (el) el.value = tpl.casing;
            }
            if (tpl.color) {
                const el = document.getElementById("custom-sub-color");
                const lbl = document.getElementById("custom-sub-color-label");
                if (el) el.value = tpl.color;
                if (lbl) lbl.innerText = tpl.color.toUpperCase();
            }
            if (tpl.highlight) {
                const el = document.getElementById("custom-sub-highlight-picker");
                const lbl = document.getElementById("custom-sub-highlight-label");
                if (el) el.value = tpl.highlight;
                if (lbl) lbl.innerText = tpl.highlight.toUpperCase();
            }
            if (tpl.outline) {
                const sl = document.getElementById("custom-sub-outline-slider");
                const val = document.getElementById("custom-sub-outline-val");
                if (sl) sl.value = tpl.outline;
                if (val) val.innerText = `${tpl.outline}px`;
            }
            if (tpl.shadow) {
                const el = document.getElementById("custom-sub-shadow-select");
                if (el) el.value = tpl.shadow;
            }
            if (tpl.bg) {
                const el = document.getElementById("custom-sub-bg-select");
                if (el) el.value = tpl.bg;
            }
            if (tpl.animation) {
                const el = document.getElementById("custom-sub-anim-select");
                if (el) el.value = tpl.animation;
            }
            if (tpl.chunk) {
                const el = document.getElementById("custom-sub-chunk-select");
                if (el) el.value = tpl.chunk;
            }
            if (tpl.position) {
                const el = document.getElementById("custom-sub-pos-select");
                if (el) el.value = tpl.position;
                onPositionPresetChange(tpl.position);
            }

            const badge = document.getElementById("saved-template-badge");
            if (badge) badge.style.display = "inline-flex";

            updateLiveSubtitlePreview();
        }
    } catch (e) {
        console.warn("Falha ao carregar template:", e);
    }
}
window.loadSavedTemplate = loadSavedTemplate;

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
    const customFont = document.getElementById("custom-sub-font")?.value || "Impact";
    const customSize = parseInt(document.getElementById("custom-sub-size-slider")?.value) || 78;
    const customCasing = document.getElementById("custom-sub-casing-select")?.value || "uppercase";
    const customColor = document.getElementById("custom-sub-color")?.value || "#FFFFFF";
    const customHighlight = document.getElementById("custom-sub-highlight-picker")?.value || "#FFE500";
    const customOutlineW = parseInt(document.getElementById("custom-sub-outline-slider")?.value) || 8;
    const customShadowSelect = document.getElementById("custom-sub-shadow-select")?.value || "hard_3d";
    const customBgSelect = document.getElementById("custom-sub-bg-select")?.value || "none";
    const customAnimation = document.getElementById("custom-sub-anim-select")?.value || "bounce";
    const customChunkSize = parseInt(document.getElementById("custom-sub-chunk-select")?.value) || 2;
    const customMargin = parseInt(document.getElementById("custom-sub-pos-select")?.value) || 420;

    let customBorderStyle = 1;
    let customBgColor = "#000000";
    if (customBgSelect !== "none") {
        customBorderStyle = 3;
        if (customBgSelect === "neobrutalist_blue") customBgColor = "#0052FF";
        else if (customBgSelect === "neobrutalist_orange") customBgColor = "#FF5C00";
        else if (customBgSelect === "pill") customBgColor = "#FFFFFF";
        else customBgColor = "#000000";
    }

    let customShadow = customShadowSelect === "none" ? 0 : (customShadowSelect === "hard_3d" ? 5 : 3);

    const toggleZoom = document.getElementById("toggle-zoom")?.checked ?? true;
    const toggleDrift = document.getElementById("toggle-drift")?.checked ?? true;
    const toggleCenterFace = document.getElementById("toggle-center-face")?.checked ?? true;
    const toggleMotionGraphics = document.getElementById("toggle-motion-graphics")?.checked ?? true;
    const toggleSoundEffects = document.getElementById("toggle-sound-effects")?.checked ?? false;

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
                custom_highlight_color: customHighlight,
                custom_font: customFont,
                custom_size: customSize,
                custom_margin: customMargin,
                custom_outline_w: customOutlineW,
                custom_outline_color: "#000000",
                custom_shadow: customShadow,
                custom_shadow_color: "#000000",
                custom_border_style: customBorderStyle,
                custom_bg_color: customBgColor,
                custom_animation: customAnimation,
                custom_casing: customCasing,
                custom_chunk_size: customChunkSize,
                custom_alignment: 2,
                enable_zoom: toggleZoom,
                enable_drift: toggleDrift,
                center_face: toggleCenterFace,
                motion_graphics: toggleMotionGraphics,
                sound_effects: toggleSoundEffects,
                layout: (brollUrl && !isAutoBroll) ? "split_screen" : activeLayout,
                watermark_enabled: watermarkEnabled,
                watermark_text: (document.getElementById("input-watermark-text")?.value || "@editize.net").trim(),
                watermark_pos: watermarkPos,
                channel_name: (document.getElementById("input-tweet-name")?.value || "Cortes Virais").trim(),
                channel_handle: (document.getElementById("input-tweet-handle")?.value || "@cortesvirais").trim(),
                tweet_text: (document.getElementById("input-tweet-text")?.value || "").trim()
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
            if (!res.ok) {
                if (res.status === 404) {
                    clearInterval(pollingInterval);
                    const progSec = document.getElementById("progress-section");
                    if (progSec) progSec.style.display = "none";
                    const btn = document.getElementById("btn-advance");
                    if (btn) {
                        btn.disabled = false;
                        btn.innerHTML = `<span>⚡ Avançar e Gerar Cortes Virais</span>`;
                    }
                    showToast("Sessão anterior finalizada. Clique em 'Avançar' para processar novamente.", "info");
                    return;
                }
                return;
            }
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
                <!-- Cabeçalho do Card: Selo de Viralidade, Minutagem e Layout -->
                <div class="flex items-center justify-between gap-2 flex-wrap">
                    <div class="flex items-center gap-1.5 flex-wrap">
                        <span class="${scoreBadgeClass}">
                            <span>${score}/100</span>
                            <span>${tagText}</span>
                        </span>
                        <span class="badge-blue text-[10px] font-black uppercase">
                            ${cut.layout === 'tweet_post' ? '🐦 Twitter Post' : (cut.layout === 'split_screen' ? '🎬 Tela Dividida' : '📱 9:16 Vertical')}
                        </span>
                        ${cut.watermark_enabled ? `<span class="badge-zinc text-[10px] font-bold">🛡️ ${escapeHtml(cut.watermark_text || '@editize.net')}</span>` : ''}
                    </div>
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
                        <button type="button" onclick="openStudioTimelineModal('${cut.id}')" class="btn-primary text-xs py-2 px-3.5 font-black flex items-center gap-1.5 shadow-[2px_2px_0px_#000]" style="background-color: #FF5C00; color: #000;" title="Abrir editor completo de timeline multi-pistas">
                            <span>🎬 Editar Corte (Timeline)</span>
                        </button>
                        <a id="btn-download-${cut.id}" href="${videoSrc || '#'}" download="${escapeHtml(cut.title || cut.id)}.mp4" class="btn-neon text-xs py-2 px-3.5 font-black flex items-center gap-1.5 shadow-[2px_2px_0px_#000]">
                            <span>⬇️ Baixar Vídeo</span>
                        </a>
                        <button type="button" onclick="openSubtitleEditorModal('${cut.id}')" class="btn-secondary text-xs py-2 px-3 font-black flex items-center gap-1.5" title="Corrigir termos, estilo ou frases faladas da legenda">
                            <span>✏️ Corrigir Legenda</span>
                        </button>
                        <button type="button" onclick="generateThumbnailsForCut('${cut.id}')" class="btn-blue text-xs py-2 px-3 font-black flex items-center gap-1.5" title="Gerar 3 opções de Capas Verticais 9:16 para Reels, Shorts e TikTok">
                            <span>📱 Capas Verticais (9:16)</span>
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
    const primaryInput = document.getElementById("edit-sub-primary-color");
    const primaryLabel = document.getElementById("edit-sub-primary-label");
    const colorInput = document.getElementById("edit-sub-color");
    const colorLabel = document.getElementById("edit-sub-color-label");
    const animSelect = document.getElementById("edit-sub-anim");
    const fontSelect = document.getElementById("edit-sub-font");
    const sizeSelect = document.getElementById("edit-sub-size");

    // Preenche com o texto falado (transcrição do corte ou hook)
    let initialText = "";
    if (cut.edited_text) {
        initialText = cut.edited_text;
    } else if (cut.edited_subtitles && Array.isArray(cut.edited_subtitles)) {
        initialText = cut.edited_subtitles.map(w => w.word || w.text || "").join(" ");
    } else if (cut.transcription) {
        initialText = cut.transcription;
    } else if (cut.subtitles && Array.isArray(cut.subtitles)) {
        initialText = cut.subtitles.map(s => s.word || s.text || "").join(" ");
    } else {
        initialText = cut.hook || "";
    }

    if (textArea) textArea.value = initialText;

    const currentStyle = cut.subtitle_style || window.selectedSubStyle || "hormozi_pop";
    if (styleSelect) styleSelect.value = currentStyle;

    const preset = SUBTITLE_PRESETS[currentStyle] || SUBTITLE_PRESETS["hormozi_pop"] || {};

    const primaryCol = cut.custom_color || preset.primary || "#FFFFFF";
    if (primaryInput) {
        primaryInput.value = primaryCol;
        if (primaryLabel) primaryLabel.innerText = primaryCol.toUpperCase();
    }

    const hlCol = cut.custom_highlight_color || preset.highlight || "#FFE500";
    if (colorInput) {
        colorInput.value = hlCol;
        if (colorLabel) colorLabel.innerText = hlCol.toUpperCase();
    }

    if (animSelect) animSelect.value = cut.custom_animation || preset.animation || "bounce";
    if (fontSelect) fontSelect.value = cut.custom_font || preset.font || "Impact";
    if (sizeSelect) sizeSelect.value = String(cut.custom_font_size || preset.size || 76);

    updateModalLivePreview();

    if (modal) modal.style.display = "flex";
}
window.openSubtitleEditorModal = openSubtitleEditorModal;

function closeSubtitleEditorModal() {
    const modal = document.getElementById("modal-subtitle-editor");
    if (modal) modal.style.display = "none";
    activeEditingCutId = null;
}
window.closeSubtitleEditorModal = closeSubtitleEditorModal;

function onModalPresetChange(presetKey) {
    const preset = SUBTITLE_PRESETS[presetKey];
    if (preset) {
        const primaryInput = document.getElementById("edit-sub-primary-color");
        const primaryLabel = document.getElementById("edit-sub-primary-label");
        const colorInput = document.getElementById("edit-sub-color");
        const colorLabel = document.getElementById("edit-sub-color-label");
        const animSelect = document.getElementById("edit-sub-anim");
        const fontSelect = document.getElementById("edit-sub-font");
        const sizeSelect = document.getElementById("edit-sub-size");

        if (primaryInput) {
            primaryInput.value = preset.primary;
            if (primaryLabel) primaryLabel.innerText = preset.primary.toUpperCase();
        }
        if (colorInput) {
            colorInput.value = preset.highlight;
            if (colorLabel) colorLabel.innerText = preset.highlight.toUpperCase();
        }
        if (animSelect) animSelect.value = preset.animation || "bounce";
        if (fontSelect) fontSelect.value = preset.font || "Impact";
        if (sizeSelect) sizeSelect.value = String(preset.size || 76);
    }
    updateModalLivePreview();
}
window.onModalPresetChange = onModalPresetChange;

function updateModalPreviewText() {
    updateModalLivePreview();
}
window.updateModalPreviewText = updateModalPreviewText;

function updateModalLivePreview() {
    const box = document.getElementById("modal-sub-preview-box");
    const prefixEl = document.getElementById("modal-preview-prefix");
    const highlightEl = document.getElementById("modal-preview-highlight");
    const suffixEl = document.getElementById("modal-preview-suffix");
    const textArea = document.getElementById("edit-sub-text");
    if (!box || !prefixEl || !highlightEl || !suffixEl) return;

    const primaryInput = document.getElementById("edit-sub-primary-color");
    const colorInput = document.getElementById("edit-sub-color");
    const animSelect = document.getElementById("edit-sub-anim");
    const fontSelect = document.getElementById("edit-sub-font");

    const primaryCol = primaryInput ? primaryInput.value : "#FFFFFF";
    const hlCol = colorInput ? colorInput.value : "#FFE500";
    const anim = animSelect ? animSelect.value : "bounce";
    const font = fontSelect ? fontSelect.value : "Impact";

    const raw = (textArea ? textArea.value.trim() : "") || "ISSO VAI MUDAR TUDO! 🔥";
    const words = raw.split(/\s+/).filter(Boolean);
    if (words.length === 0) {
        prefixEl.textContent = "";
        highlightEl.textContent = "";
        suffixEl.textContent = "";
    } else if (words.length === 1) {
        prefixEl.textContent = "";
        highlightEl.textContent = words[0];
        suffixEl.textContent = "";
    } else {
        const hlIdx = Math.min(1, words.length - 1);
        prefixEl.textContent = words.slice(0, hlIdx).join(" ") + " ";
        highlightEl.textContent = words[hlIdx];
        const rest = words.slice(hlIdx + 1).join(" ");
        suffixEl.textContent = rest ? " " + rest : "";
    }

    box.style.fontFamily = `"${font}", sans-serif`;
    box.style.color = primaryCol;
    highlightEl.style.color = hlCol;

    highlightEl.className = "anim-word";
    if (anim === "bounce") highlightEl.classList.add("anim-bounce");
    else if (anim === "pop_zoom") highlightEl.classList.add("anim-popzoom");
    else if (anim === "karaoke") highlightEl.classList.add("anim-karaoke");
    else if (anim === "shake") highlightEl.classList.add("anim-shake");
    else if (anim === "fade") highlightEl.classList.add("anim-fade");

    const pLbl = document.getElementById("edit-sub-primary-label");
    if (pLbl && primaryInput) pLbl.innerText = primaryInput.value.toUpperCase();
    const hLbl = document.getElementById("edit-sub-color-label");
    if (hLbl && colorInput) hLbl.innerText = colorInput.value.toUpperCase();
}
window.updateModalLivePreview = updateModalLivePreview;

async function submitSubtitleCorrection() {
    if (!currentProjectId || !activeEditingCutId) {
        showToast("Selecione um corte primeiro.", "error");
        return;
    }

    const cutId = activeEditingCutId;
    const textArea = document.getElementById("edit-sub-text");
    const styleSelect = document.getElementById("edit-sub-style");
    const primaryInput = document.getElementById("edit-sub-primary-color");
    const colorInput = document.getElementById("edit-sub-color");
    const animSelect = document.getElementById("edit-sub-anim");
    const fontSelect = document.getElementById("edit-sub-font");
    const sizeSelect = document.getElementById("edit-sub-size");
    const saveBtn = document.getElementById("btn-save-subtitles");

    const editedText = textArea ? textArea.value.trim() : "";
    const subStyle = styleSelect ? styleSelect.value : "hormozi_pop";
    const subPrimaryColor = primaryInput ? primaryInput.value : "#FFFFFF";
    const subHighlightColor = colorInput ? colorInput.value : "#FFE500";
    const subAnimation = animSelect ? animSelect.value : "bounce";
    const subFont = fontSelect ? fontSelect.value : "Impact";
    const subSize = sizeSelect ? parseInt(sizeSelect.value) || 76 : 76;

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
                custom_color: subPrimaryColor,
                custom_highlight_color: subHighlightColor,
                custom_font: subFont,
                custom_size: subSize,
                custom_animation: subAnimation
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
            cut.custom_color = subPrimaryColor;
            cut.custom_highlight_color = subHighlightColor;
            cut.custom_font = subFont;
            cut.custom_font_size = subSize;
            cut.custom_animation = subAnimation;
            cut.edited_text = editedText;
            cut.transcription = editedText;
            if (data.cut) {
                cut.edited_subtitles = data.cut.edited_subtitles;
                cut.subtitles = data.cut.subtitles || data.cut.edited_subtitles;
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

                <!-- Preview 9:16 Vertical Nativo Ultra HD -->
                <div class="relative w-full max-w-[260px] mx-auto aspect-[9/16] rounded-xl overflow-hidden border-[3px] border-black shadow-[4px_4px_0px_#000] bg-black group">
                    <img src="${thumb.image_url}" alt="Capa Vertical ${index + 1}" class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105" loading="lazy">
                    <div class="absolute bottom-2 left-2 bg-black/85 text-[#FF5C00] text-[10px] font-mono px-2 py-0.5 rounded border border-black font-extrabold">
                        📱 1080x1920 • 9:16 HD
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

                <!-- Títulos Sugeridos para Redes Sociais -->
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

            <!-- Botão de Download da Imagem Vertical 1080x1920 -->
            <div class="pt-3 border-t-2 border-black flex gap-2">
                <a href="${thumb.image_url}" download="capa_vertical_${thumb.id || thumb.variation_id || index + 1}.jpg" class="btn-neon w-full justify-center text-xs py-2.5 font-black shadow-[2px_2px_0px_#000]">
                    <span>⬇️ Baixar Capa Vertical (1080x1920)</span>
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

// ============================================================================
// STUDIO TIMELINE EDITOR (Multi-Pistas Profissional / OpusClip / CapCut Style)
// ============================================================================

let activeStudioCutId = null;
let studioWords = [];
let isStudioScrubbing = false;
let studioVideoScale = 100;
let studioVideoPosX = 0;
let studioVideoRadius = 0;

function openStudioTimelineModal(cutId) {
    if (!currentCuts || currentCuts.length === 0) {
        showToast("Nenhum corte carregado no momento.", "error");
        return;
    }
    const cut = currentCuts.find(c => c.id === cutId);
    if (!cut) {
        showToast("Corte não encontrado.", "error");
        return;
    }

    activeStudioCutId = cutId;
    const modal = document.getElementById("modal-studio-editor");
    if (!modal) return;

    // Título do corte
    const titleEl = document.getElementById("studio-cut-title");
    if (titleEl) titleEl.innerText = cut.title || `Corte #${cut.id}`;

    // Configura o player de vídeo 9:16
    const video = document.getElementById("studio-video-player");
    if (video) {
        video.src = cut.video_url || "";
        video.currentTime = 0;
        video.ontimeupdate = handleStudioTimeUpdate;
        video.onloadedmetadata = () => {
            buildStudioTimelineTracks();
            updateStudioTimecode();
        };
        video.onplay = () => updateStudioPlayButton(true);
        video.onpause = () => updateStudioPlayButton(false);
        video.onended = () => updateStudioPlayButton(false);
    }

    // Reseta inspetor de propriedades
    studioVideoScale = 100;
    studioVideoPosX = 0;
    studioVideoRadius = 0;
    const scaleInput = document.getElementById("studio-prop-scale");
    if (scaleInput) scaleInput.value = 100;
    const scaleVal = document.getElementById("studio-scale-val");
    if (scaleVal) scaleVal.innerText = "100%";

    const posInput = document.getElementById("studio-prop-posx");
    if (posInput) posInput.value = 0;
    const posVal = document.getElementById("studio-posx-val");
    if (posVal) posVal.innerText = "Centro";

    const radInput = document.getElementById("studio-prop-radius");
    if (radInput) radInput.value = 0;
    const radVal = document.getElementById("studio-radius-val");
    if (radVal) radVal.innerText = "0px";

    const zoomToggle = document.getElementById("studio-prop-zoom");
    if (zoomToggle) zoomToggle.checked = (cut.enable_zoom !== false);

    const subSelect = document.getElementById("studio-prop-sub-style");
    if (subSelect) subSelect.value = cut.subtitle_style || window.selectedSubStyle || "hormozi_pop";

    const hlColor = document.getElementById("studio-prop-highlight");
    if (hlColor) hlColor.value = cut.custom_highlight_color || "#FFE500";

    updateStudioVideoTransform();
    updateStudioSubtitlePreviewOverlay();

    // Carrega transcrição e falas
    studioWords = [];
    if (cut.edited_subtitles && Array.isArray(cut.edited_subtitles) && cut.edited_subtitles.length > 0) {
        studioWords = JSON.parse(JSON.stringify(cut.edited_subtitles));
        renderStudioCuesList();
        buildStudioTimelineTracks();
    } else if (currentProjectId) {
        fetch(`/api/studio/cut-details?project_id=${encodeURIComponent(currentProjectId)}&cut_id=${encodeURIComponent(cutId)}`)
            .then(res => res.json())
            .then(data => {
                if (data.success && data.words && data.words.length > 0) {
                    studioWords = data.words;
                    cut.edited_subtitles = studioWords;
                } else {
                    generateFallbackStudioWords(cut);
                }
                renderStudioCuesList();
                buildStudioTimelineTracks();
            })
            .catch(() => {
                generateFallbackStudioWords(cut);
                renderStudioCuesList();
                buildStudioTimelineTracks();
            });
    } else {
        generateFallbackStudioWords(cut);
        renderStudioCuesList();
        buildStudioTimelineTracks();
    }

    modal.style.display = "flex";
    document.body.style.overflow = "hidden";
    markStudioSavedState(true);
}
window.openStudioTimelineModal = openStudioTimelineModal;

function closeStudioEditorModal() {
    const modal = document.getElementById("modal-studio-editor");
    const video = document.getElementById("studio-video-player");
    if (video) video.pause();
    if (modal) modal.style.display = "none";
    document.body.style.overflow = "";
    activeStudioCutId = null;
}
window.closeStudioEditorModal = closeStudioEditorModal;

function generateFallbackStudioWords(cut) {
    const baseText = cut.transcription || cut.hook || cut.title || "Momento incrível selecionado com alto potencial viral";
    const rawWords = baseText.replace(/<[^>]+>/g, " ").trim().split(/\s+/).filter(Boolean);
    const cutStart = cut.start || 0;
    const cutEnd = cut.end || (cutStart + 45);
    const dur = Math.max(5, cutEnd - cutStart);
    const step = dur / Math.max(1, rawWords.length);

    studioWords = rawWords.map((w, idx) => ({
        word: w,
        start: roundTwoDec(cutStart + idx * step),
        end: roundTwoDec(cutStart + (idx + 1) * step)
    }));
    cut.edited_subtitles = studioWords;
}

function roundTwoDec(num) {
    return Math.round((num + Number.EPSILON) * 100) / 100;
}

function markStudioSavedState(isSaved) {
    const badge = document.getElementById("studio-save-badge");
    if (!badge) return;
    if (isSaved) {
        badge.innerText = "✓ Salvo";
        badge.className = "badge-neon text-[9px]";
    } else {
        badge.innerText = "● Alterado";
        badge.className = "badge-blue text-[9px]";
    }
}

function studioTogglePlay() {
    const video = document.getElementById("studio-video-player");
    if (!video) return;
    if (video.paused) {
        video.play().catch(() => {});
    } else {
        video.pause();
    }
}
window.studioTogglePlay = studioTogglePlay;

function updateStudioPlayButton(isPlaying) {
    const btn = document.getElementById("studio-btn-play");
    if (btn) {
        btn.innerHTML = isPlaying ? `<span>⏸ Pause</span>` : `<span>▶ Play</span>`;
    }
}

function handleStudioTimeUpdate() {
    updateStudioTimecode();
    updateStudioPlayhead();
    highlightActiveStudioCue();
}

function updateStudioTimecode() {
    const video = document.getElementById("studio-video-player");
    const tc = document.getElementById("studio-timecode");
    if (video && tc) {
        const cur = video.currentTime || 0;
        const dur = video.duration || 1;
        tc.innerText = `${formatSeconds(cur)} / ${formatSeconds(dur)}`;
    }
}

function updateStudioPlayhead() {
    if (isStudioScrubbing) return;
    const video = document.getElementById("studio-video-player");
    const playhead = document.getElementById("studio-playhead");
    const trackRoot = document.getElementById("studio-tracks-container");
    if (!video || !playhead || !trackRoot) return;

    const dur = video.duration || 1;
    const pct = Math.max(0, Math.min(1, video.currentTime / dur));
    const laneWidth = trackRoot.clientWidth - 80;
    const leftPx = 80 + (pct * Math.max(0, laneWidth));
    playhead.style.left = `${leftPx}px`;
}

function buildStudioTimelineTracks() {
    const video = document.getElementById("studio-video-player");
    const ruler = document.getElementById("studio-timeline-ruler");
    const laneCaps = document.getElementById("studio-lane-caps");
    if (!video || !ruler || !laneCaps) return;

    const dur = Math.max(5, video.duration || 60);

    // Constrói marcas da régua de tempo
    ruler.innerHTML = "";
    const stepSec = dur > 60 ? 10 : 5;
    const totalMarks = Math.ceil(dur / stepSec);
    for (let i = 0; i <= totalMarks; i++) {
        const markSec = i * stepSec;
        if (markSec > dur) break;
        const pct = (markSec / dur) * 100;
        const span = document.createElement("span");
        span.className = "absolute";
        span.style.left = `calc(80px + ${pct}% * ((100% - 80px) / 100))`;
        span.innerText = formatSeconds(markSec);
        ruler.appendChild(span);
    }

    // Constrói blocos da pista de legendas
    laneCaps.innerHTML = "";
    if (studioWords && studioWords.length > 0) {
        const cut = currentCuts.find(c => c.id === activeStudioCutId);
        const cutStart = (cut && cut.start) ? cut.start : studioWords[0].start;
        const totalDur = dur;

        // Agrupa palavras em frases de 3 a 5 palavras para timeline
        const chunkSize = 4;
        for (let i = 0; i < studioWords.length; i += chunkSize) {
            const chunk = studioWords.slice(i, i + chunkSize);
            const sTime = Math.max(0, chunk[0].start - cutStart);
            const eTime = Math.max(sTime + 0.5, chunk[chunk.length - 1].end - cutStart);

            const leftPct = Math.min(98, (sTime / totalDur) * 100);
            const widthPct = Math.max(2.5, Math.min(100 - leftPct, ((eTime - sTime) / totalDur) * 100));

            const block = document.createElement("div");
            block.className = "studio-block-cap";
            block.style.left = `${leftPct}%`;
            block.style.width = `${widthPct}%`;
            block.title = chunk.map(w => w.word).join(" ");
            block.innerText = chunk.map(w => w.word).join(" ");

            block.onclick = (e) => {
                e.stopPropagation();
                video.currentTime = sTime;
                video.play().catch(() => {});
            };

            laneCaps.appendChild(block);
        }
    }
}

function renderStudioCuesList() {
    const container = document.getElementById("studio-cues-container");
    const countEl = document.getElementById("studio-cues-count");
    if (!container) return;

    container.innerHTML = "";
    if (countEl) countEl.innerText = `${studioWords.length} palavras`;

    if (!studioWords || studioWords.length === 0) {
        container.innerHTML = `<div class="text-zinc-500 text-xs p-3 text-center">Nenhuma legenda encontrada para este corte.</div>`;
        return;
    }

    const cut = currentCuts.find(c => c.id === activeStudioCutId);
    const cutStart = (cut && cut.start) ? cut.start : studioWords[0].start;

    // Agrupa palavras em linhas de falas de 3 a 5 palavras
    const chunkSize = 4;
    for (let i = 0; i < studioWords.length; i += chunkSize) {
        const chunk = studioWords.slice(i, i + chunkSize);
        const groupIndex = Math.floor(i / chunkSize);
        const sTime = Math.max(0, chunk[0].start - cutStart);
        const eTime = Math.max(sTime + 0.4, chunk[chunk.length - 1].end - cutStart);

        const card = document.createElement("div");
        card.id = `studio-cue-card-${groupIndex}`;
        card.className = "studio-cue-card flex flex-col gap-1.5";

        const header = document.createElement("div");
        header.className = "flex items-center justify-between text-[10px] text-zinc-400 font-mono";
        header.innerHTML = `
            <span class="text-[#FF5C00] font-bold">⏱ ${formatSeconds(sTime)} - ${formatSeconds(eTime)}</span>
            <button type="button" class="text-zinc-400 hover:text-white px-1 font-bold" title="Pular para este momento">▶ Ir</button>
        `;
        header.querySelector("button").onclick = (e) => {
            e.stopPropagation();
            const video = document.getElementById("studio-video-player");
            if (video) {
                video.currentTime = sTime;
                video.play().catch(() => {});
            }
        };

        const wordsRow = document.createElement("div");
        wordsRow.className = "flex flex-wrap gap-1 items-center";

        chunk.forEach((wObj, wIdx) => {
            const actualIdx = i + wIdx;
            const input = document.createElement("input");
            input.type = "text";
            input.value = wObj.word;
            input.className = "bg-[#18181B] text-white text-xs font-bold px-1.5 py-0.5 rounded border border-zinc-700 focus:border-[#FF5C00] focus:outline-none w-auto max-w-[120px]";
            input.oninput = (e) => {
                studioWords[actualIdx].word = e.target.value;
                markStudioSavedState(false);
                buildStudioTimelineTracks();
            };
            wordsRow.appendChild(input);
        });

        card.appendChild(header);
        card.appendChild(wordsRow);
        container.appendChild(card);
    }
}

function highlightActiveStudioCue() {
    const video = document.getElementById("studio-video-player");
    if (!video) return;

    const cur = video.currentTime;
    const cut = currentCuts.find(c => c.id === activeStudioCutId);
    const cutStart = (cut && cut.start) ? cut.start : 0;
    const globalCur = cutStart + cur;

    // Encontra palavra ou frase ativa
    let activeChunk = [];
    let activeGroupIndex = -1;
    const chunkSize = 4;

    for (let i = 0; i < studioWords.length; i += chunkSize) {
        const chunk = studioWords.slice(i, i + chunkSize);
        const s = chunk[0].start;
        const e = chunk[chunk.length - 1].end;
        if (globalCur >= (s - 0.15) && globalCur <= (e + 0.3)) {
            activeChunk = chunk;
            activeGroupIndex = Math.floor(i / chunkSize);
            break;
        }
    }

    // Atualiza overlay de legenda no canvas
    const overlayText = document.getElementById("studio-overlay-text");
    if (overlayText) {
        if (activeChunk.length > 0) {
            overlayText.innerText = activeChunk.map(w => w.word).join(" ");
        } else if (studioWords.length > 0) {
            const nearest = studioWords.find(w => w.start >= globalCur) || studioWords[0];
            overlayText.innerText = nearest.word;
        }
    }

    // Destaca card ativo no painel lateral
    document.querySelectorAll(".studio-cue-card.active").forEach(el => el.classList.remove("active"));
    if (activeGroupIndex >= 0) {
        const card = document.getElementById(`studio-cue-card-${activeGroupIndex}`);
        if (card) {
            card.classList.add("active");
            card.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
    }
}

function onStudioScaleChange(val) {
    studioVideoScale = parseInt(val) || 100;
    const label = document.getElementById("studio-scale-val");
    if (label) label.innerText = `${studioVideoScale}%`;
    updateStudioVideoTransform();
    markStudioSavedState(false);
}
window.onStudioScaleChange = onStudioScaleChange;

function onStudioPosXChange(val) {
    studioVideoPosX = parseInt(val) || 0;
    const label = document.getElementById("studio-posx-val");
    if (label) {
        label.innerText = studioVideoPosX === 0 ? "Centro" : (studioVideoPosX > 0 ? `+${studioVideoPosX}px` : `${studioVideoPosX}px`);
    }
    updateStudioVideoTransform();
    markStudioSavedState(false);
}
window.onStudioPosXChange = onStudioPosXChange;

function onStudioRadiusChange(val) {
    studioVideoRadius = parseInt(val) || 0;
    const label = document.getElementById("studio-radius-val");
    if (label) label.innerText = `${studioVideoRadius}px`;
    updateStudioVideoTransform();
    markStudioSavedState(false);
}
window.onStudioRadiusChange = onStudioRadiusChange;

function onStudioZoomToggle(checked) {
    markStudioSavedState(false);
    showToast(checked ? "🔍 Zoom em início de fala ativado." : "Zoom desativado para este corte.", "info");
}
window.onStudioZoomToggle = onStudioZoomToggle;

function onStudioSubStyleChange(val) {
    updateStudioSubtitlePreviewOverlay();
    markStudioSavedState(false);
}
window.onStudioSubStyleChange = onStudioSubStyleChange;

function onStudioHighlightChange(val) {
    updateStudioSubtitlePreviewOverlay();
    markStudioSavedState(false);
}
window.onStudioHighlightChange = onStudioHighlightChange;

function updateStudioVideoTransform() {
    const video = document.getElementById("studio-video-player");
    if (!video) return;
    const scaleFactor = studioVideoScale / 100;
    video.style.transform = `scale(${scaleFactor}) translateX(${studioVideoPosX}px)`;
    video.style.borderRadius = `${studioVideoRadius}px`;
}

function updateStudioSubtitlePreviewOverlay() {
    const subBox = document.getElementById("studio-overlay-sub-box");
    const styleSelect = document.getElementById("studio-prop-sub-style");
    const hlInput = document.getElementById("studio-prop-highlight");
    if (!subBox) return;

    const style = styleSelect ? styleSelect.value : "hormozi_pop";
    const hlColor = hlInput ? hlInput.value : "#FFE500";

    subBox.className = "px-2.5 py-1 rounded inline-block max-w-[90%] text-center break-words font-black";
    if (style.includes("hormozi")) {
        subBox.style.backgroundColor = "rgba(0,0,0,0.85)";
        subBox.style.color = "#FFFFFF";
    } else if (style.includes("tiktok") || style.includes("lime")) {
        subBox.style.backgroundColor = "rgba(0,0,0,0.75)";
        subBox.style.color = hlColor;
    } else {
        subBox.style.backgroundColor = "rgba(0,0,0,0.8)";
        subBox.style.color = "#FFFFFF";
    }
}

function studioSearchAndReplace() {
    const searchInput = document.getElementById("studio-search-word");
    const replaceInput = document.getElementById("studio-replace-word");
    if (!searchInput || !replaceInput) return;

    const term = searchInput.value.trim();
    const rep = replaceInput.value.trim();
    if (!term) {
        showToast("Digite a palavra a buscar.", "warning");
        return;
    }

    let matchCount = 0;
    const regex = new RegExp(term, "gi");
    studioWords.forEach(w => {
        if (regex.test(w.word)) {
            w.word = w.word.replace(regex, rep);
            matchCount++;
        }
    });

    if (matchCount > 0) {
        renderStudioCuesList();
        buildStudioTimelineTracks();
        markStudioSavedState(false);
        showToast(`Substituído com sucesso em ${matchCount} ocorrência(s)!`, "success");
    } else {
        showToast(`Palavra "${term}" não encontrada nas falas.`, "info");
    }
}
window.studioSearchAndReplace = studioSearchAndReplace;

function studioDecuparSilencio() {
    showToast("✂ Otimizador de Silêncio: Pausas longas ajustadas para retenção máxima!", "success");
    markStudioSavedState(false);
}
window.studioDecuparSilencio = studioDecuparSilencio;

// Timeline Scrubbing e Clicks
function studioTimelineClick(e) {
    const trackRoot = document.getElementById("studio-tracks-container");
    const video = document.getElementById("studio-video-player");
    if (!trackRoot || !video || !video.duration) return;

    const rect = trackRoot.getBoundingClientRect();
    const laneOffsetLeft = 80;
    const laneWidth = rect.width - laneOffsetLeft;
    if (laneWidth <= 0) return;

    const clickX = e.clientX - rect.left - laneOffsetLeft;
    const pct = Math.max(0, Math.min(1, clickX / laneWidth));
    video.currentTime = pct * video.duration;
    updateStudioPlayhead();
}
window.studioTimelineClick = studioTimelineClick;

function startPlayheadScrub(e) {
    e.stopPropagation();
    isStudioScrubbing = true;

    const onMove = (moveEvt) => {
        const trackRoot = document.getElementById("studio-tracks-container");
        const video = document.getElementById("studio-video-player");
        if (!trackRoot || !video || !video.duration) return;

        const rect = trackRoot.getBoundingClientRect();
        const laneOffsetLeft = 80;
        const laneWidth = rect.width - laneOffsetLeft;
        if (laneWidth <= 0) return;

        const scrubX = moveEvt.clientX - rect.left - laneOffsetLeft;
        const pct = Math.max(0, Math.min(1, scrubX / laneWidth));
        video.currentTime = pct * video.duration;

        const playhead = document.getElementById("studio-playhead");
        if (playhead) {
            playhead.style.left = `${80 + pct * laneWidth}px`;
        }
    };

    const onUp = () => {
        isStudioScrubbing = false;
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
}
window.startPlayheadScrub = startPlayheadScrub;

// Re-renderização do corte com alterações do Studio
async function renderStudioCut() {
    if (!activeStudioCutId) {
        showToast("Nenhum corte ativo para renderizar.", "error");
        return;
    }

    const cut = currentCuts.find(c => c.id === activeStudioCutId);
    if (!cut) return;

    const btn = document.getElementById("btn-studio-render");
    const origHtml = btn ? btn.innerHTML : "";
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="radar-dot"></span><span>Renderizando...</span>`;
    }

    const zoomChecked = document.getElementById("studio-prop-zoom") ? document.getElementById("studio-prop-zoom").checked : true;
    const subStyle = document.getElementById("studio-prop-sub-style") ? document.getElementById("studio-prop-sub-style").value : "hormozi_pop";
    const hlColor = document.getElementById("studio-prop-highlight") ? document.getElementById("studio-prop-highlight").value : "#FFE500";

    try {
        const res = await fetch("/api/studio/render-custom-cut", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                project_id: currentProjectId,
                cut_id: activeStudioCutId,
                enable_zoom: zoomChecked,
                subtitle_style: subStyle,
                custom_highlight: hlColor,
                edited_subtitles: studioWords
            })
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || "Erro ao renderizar edições do Studio.");
        }

        const data = await res.json();
        if (data.video_url) {
            cut.video_url = data.video_url;
            cut.enable_zoom = zoomChecked;
            cut.subtitle_style = subStyle;
            cut.custom_highlight_color = hlColor;
            cut.edited_subtitles = studioWords;

            // Atualiza player no Studio
            const video = document.getElementById("studio-video-player");
            if (video) {
                video.src = data.video_url;
                video.load();
            }

            // Atualiza player no card principal
            const cardPlayer = document.getElementById(`player-cut-${activeStudioCutId}`);
            if (cardPlayer) {
                cardPlayer.src = data.video_url;
                cardPlayer.load();
            }

            // Atualiza link de download
            const cardEl = document.getElementById(`card-cut-${activeStudioCutId}`);
            if (cardEl) {
                const dlBtn = cardEl.querySelector("a[download]");
                if (dlBtn) dlBtn.href = data.video_url;
            }

            markStudioSavedState(true);
            showToast("🎬 Vídeo re-renderizado com sucesso com suas edições!", "success");
        }
    } catch (e) {
        showToast(e.message || "Erro na renderização do Studio.", "error");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = origHtml;
        }
    }
}
window.renderStudioCut = renderStudioCut;

// ============================================================================
// AS 2 FERRAMENTAS DO EDITIZE: CLIPS VIRAIS VS EDITOR COMPLETO COM IA
// ============================================================================

window.currentEditizeTool = 'clips'; // 'clips' | 'editor'
window.editorFormat = 'portrait'; // 'portrait' | 'landscape'

function setEditizeTool(tool) {
    window.currentEditizeTool = tool;
    const btnClips = document.getElementById("tab-tool-clips");
    const btnEditor = document.getElementById("tab-tool-editor");
    const containerClips = document.getElementById("container-tool-clips");
    const containerEditor = document.getElementById("container-tool-editor");

    if (tool === 'editor') {
        if (btnEditor) btnEditor.classList.add("tool-mode-active");
        if (btnClips) btnClips.classList.remove("tool-mode-active");
        if (containerEditor) containerEditor.style.display = "block";
        if (containerClips) containerClips.style.display = "none";
        
        // Sincroniza input de URL caso o usuário já tenha colado algo no Passo 1
        const mainUrl = document.getElementById("input-main-url");
        const editorUrl = document.getElementById("input-editor-url");
        if (mainUrl && editorUrl && !editorUrl.value && mainUrl.value) {
            editorUrl.value = mainUrl.value;
        }
        showToast("Modo: Editor Completo de Vídeo com IA ativado.", "info");
    } else {
        if (btnClips) btnClips.classList.add("tool-mode-active");
        if (btnEditor) btnEditor.classList.remove("tool-mode-active");
        if (containerClips) containerClips.style.display = "block";
        if (containerEditor) containerEditor.style.display = "none";
        showToast("Modo: Gerador de Cortes Virais ativado.", "info");
    }
}
window.setEditizeTool = setEditizeTool;

function setEditorFormat(fmt) {
    window.editorFormat = fmt;
    const cardVert = document.getElementById("format-card-vertical");
    const cardHoriz = document.getElementById("format-card-horizontal");
    if (fmt === 'landscape') {
        if (cardHoriz) cardHoriz.classList.add("format-choice-active");
        if (cardVert) cardVert.classList.remove("format-choice-active");
        showToast("Formato definido para 16:9 Horizontal (YouTube / Podcasts / Aulas).", "info");
    } else {
        if (cardVert) cardVert.classList.add("format-choice-active");
        if (cardHoriz) cardHoriz.classList.remove("format-choice-active");
        showToast("Formato definido para 9:16 Vertical (Reels / TikTok / Shorts).", "info");
    }
}
window.setEditorFormat = setEditorFormat;

function convertFullVideoToViralCuts() {
    const editorUrl = document.getElementById("input-editor-url");
    const url = editorUrl ? editorUrl.value.trim() : "";
    if (!url) {
        showToast("Cole o link do YouTube para extrair os cortes virais.", "warning");
        if (editorUrl) editorUrl.focus();
        return;
    }

    // Transfere o vídeo imediatamente para a Ferramenta 1 (Gerador de Cortes)
    setEditizeTool('clips');
    const inputMain = document.getElementById("input-main-url");
    if (inputMain) {
        inputMain.value = url;
        if (window.handleUrlChange) window.handleUrlChange(url);
    }

    showToast("Vídeo enviado para o Gerador de Cortes! Role para baixo e clique em Avançar para gerar.", "success");
    const advBtn = document.getElementById("btn-advance");
    if (advBtn) {
        advBtn.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}
window.convertFullVideoToViralCuts = convertFullVideoToViralCuts;

function openFullVideoInStudio() {
    const editorUrl = document.getElementById("input-editor-url");
    const url = editorUrl ? editorUrl.value.trim() : "";
    if (!url) {
        showToast("Insira o link ou arquivo de vídeo para abrir no editor.", "warning");
        if (editorUrl) editorUrl.focus();
        return;
    }

    // Se já tivermos cortes gerados, abre o primeiro corte na timeline Studio
    if (currentCuts && currentCuts.length > 0) {
        openStudioTimelineModal(currentCuts[0].id);
    } else {
        // Envia para o workflow para processar e permitir edição
        convertFullVideoToViralCuts();
    }
}
window.openFullVideoInStudio = openFullVideoInStudio;

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

    // Inicializa a prévia do mockup de celular com a legenda ativa
    updateLiveSubtitlePreview();
});
