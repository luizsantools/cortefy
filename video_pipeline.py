import os
import sys
import re
import random
import subprocess
import time
import hashlib
from typing import Dict, Any, List, Optional

CREATE_NO_WINDOW = 0x08000000 if sys.platform == 'win32' else 0

def get_base_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))

def get_bin(name: str) -> str:
    ext = ".exe" if sys.platform == "win32" else ""
    local_bin = os.path.join(get_base_dir(), "bin", name + ext)
    if os.path.exists(local_bin):
        return local_bin
    local_bin2 = os.path.join(os.path.dirname(get_base_dir()), "viral_clipper_app", "bin", name + ext)
    if os.path.exists(local_bin2):
        return local_bin2
    return name

def hex_to_ass(hex_str: Optional[str], default_hex: str = "#FFFFFF", alpha: str = "00") -> str:
    """Converte hexadecimal (#RRGGBB) para o formato ASS (&HAABBGGRR)."""
    val = (hex_str or default_hex).strip().lstrip("#")
    if len(val) == 3:
        val = "".join([c * 2 for c in val])
    if len(val) != 6:
        val = "FFFFFF"
    r, g, b = val[0:2], val[2:4], val[4:6]
    return f"&H{alpha}{b}{g}{r}".upper()

def get_subtitle_presets_dict() -> Dict[str, Dict[str, Any]]:
    """Retorna os 24 presets de legendas de alta retenção visual."""
    return {
        "hormozi_pop": {
            "id": "hormozi_pop", "name": "Hormozi Pop", "category": "Viral TikTok", "badge": "🔥 VIRAL",
            "font": "Impact", "size": 82, "primary": "#FFFFFF", "highlight": "#FFE500",
            "outline_color": "#000000", "outline_w": 8, "shadow": 4, "shadow_color": "#000000",
            "border_style": 1, "bg_color": "#000000", "animation": "bounce", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 420, "alignment": 2
        },
        "tiktok_bounce": {
            "id": "tiktok_bounce", "name": "TikTok Lime Bounce", "category": "Viral TikTok", "badge": "⚡ TIKTOK",
            "font": "Arial Black", "size": 76, "primary": "#FFFFFF", "highlight": "#00FF66",
            "outline_color": "#000000", "outline_w": 7, "shadow": 3, "shadow_color": "#000000",
            "border_style": 1, "bg_color": "#000000", "animation": "bounce", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 420, "alignment": 2
        },
        "beast_impact": {
            "id": "beast_impact", "name": "MrBeast Explosivo", "category": "Impacto & Drama", "badge": "💥 IMPACTO",
            "font": "Impact", "size": 86, "primary": "#FFFFFF", "highlight": "#FF3B30",
            "outline_color": "#000000", "outline_w": 9, "shadow": 5, "shadow_color": "#FF5C00",
            "border_style": 1, "bg_color": "#000000", "animation": "pop_zoom", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 440, "alignment": 2
        },
        "cyan_electric": {
            "id": "cyan_electric", "name": "Ciano Cyberpunk", "category": "Gamer / Cyber", "badge": "🎮 CYBER",
            "font": "Arial Black", "size": 74, "primary": "#FFFFFF", "highlight": "#00FFFF",
            "outline_color": "#050B14", "outline_w": 7, "shadow": 5, "shadow_color": "#0055FF",
            "border_style": 1, "bg_color": "#000000", "animation": "bounce", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 420, "alignment": 2
        },
        "purple_viral": {
            "id": "purple_viral", "name": "Roxo Aesthetic", "category": "Viral TikTok", "badge": "💜 ESTÉTICO",
            "font": "Arial Black", "size": 74, "primary": "#FFFFFF", "highlight": "#C084FC",
            "outline_color": "#1E0B2B", "outline_w": 7, "shadow": 4, "shadow_color": "#581C87",
            "border_style": 1, "bg_color": "#000000", "animation": "bounce", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 420, "alignment": 2
        },
        "clean_minimal": {
            "id": "clean_minimal", "name": "Clean Minimalist", "category": "Minimalista", "badge": "✨ CLEAN",
            "font": "Segoe UI", "size": 68, "primary": "#FFFFFF", "highlight": "#38BDF8",
            "outline_color": "#000000", "outline_w": 4, "shadow": 2, "shadow_color": "#000000",
            "border_style": 1, "bg_color": "#000000", "animation": "fade", "casing": "original",
            "chunk_size": 3, "margin_v": 380, "alignment": 2
        },
        "gold_karaoke": {
            "id": "gold_karaoke", "name": "Karaokê Ouro VIP", "category": "YouTube Shorts", "badge": "👑 VIP",
            "font": "Impact", "size": 78, "primary": "#FFFFFF", "highlight": "#FFD700",
            "outline_color": "#000000", "outline_w": 8, "shadow": 4, "shadow_color": "#78350F",
            "border_style": 1, "bg_color": "#000000", "animation": "karaoke", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 420, "alignment": 2
        },
        "fire_sunset": {
            "id": "fire_sunset", "name": "Fogo Sunset Laranja", "category": "Impacto & Drama", "badge": "🔥 FOGO",
            "font": "Impact", "size": 82, "primary": "#FFE500", "highlight": "#FF5C00",
            "outline_color": "#000000", "outline_w": 8, "shadow": 4, "shadow_color": "#7C2D12",
            "border_style": 1, "bg_color": "#000000", "animation": "pop_zoom", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 420, "alignment": 2
        },
        "emerald_vip": {
            "id": "emerald_vip", "name": "Esmeralda Finanças", "category": "YouTube Shorts", "badge": "💎 FINANÇAS",
            "font": "Arial Black", "size": 75, "primary": "#FFFFFF", "highlight": "#10B981",
            "outline_color": "#064E3B", "outline_w": 7, "shadow": 4, "shadow_color": "#022C22",
            "border_style": 1, "bg_color": "#000000", "animation": "bounce", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 420, "alignment": 2
        },
        "monochrome_3d": {
            "id": "monochrome_3d", "name": "Monocromo 3D Heavy", "category": "Impacto & Drama", "badge": "🗿 3D",
            "font": "Impact", "size": 84, "primary": "#FFFFFF", "highlight": "#E4E4E7",
            "outline_color": "#000000", "outline_w": 9, "shadow": 6, "shadow_color": "#27272A",
            "border_style": 1, "bg_color": "#000000", "animation": "shake", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 420, "alignment": 2
        },
        "neobrutalist_black": {
            "id": "neobrutalist_black", "name": "Neo-Brutalist Tarja Preta", "category": "Neo-Brutalist", "badge": "🖤 EDITIZE",
            "font": "Impact", "size": 78, "primary": "#FFE500", "highlight": "#FF5C00",
            "outline_color": "#000000", "outline_w": 10, "shadow": 5, "shadow_color": "#000000",
            "border_style": 3, "bg_color": "#000000", "animation": "bounce", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 420, "alignment": 2
        },
        "neobrutalist_blue": {
            "id": "neobrutalist_blue", "name": "Neo-Brutalist Royal Blue", "category": "Neo-Brutalist", "badge": "💙 EDITIZE",
            "font": "Arial Black", "size": 76, "primary": "#FFFFFF", "highlight": "#FFE500",
            "outline_color": "#0052FF", "outline_w": 8, "shadow": 5, "shadow_color": "#000000",
            "border_style": 3, "bg_color": "#0052FF", "animation": "pop_zoom", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 420, "alignment": 2
        },
        "retro_arcade": {
            "id": "retro_arcade", "name": "Retro Synthwave 80s", "category": "Gamer / Cyber", "badge": "🕹️ RETRO",
            "font": "Trebuchet MS", "size": 76, "primary": "#FFFFFF", "highlight": "#FF007F",
            "outline_color": "#200030", "outline_w": 7, "shadow": 5, "shadow_color": "#00F0FF",
            "border_style": 1, "bg_color": "#000000", "animation": "bounce", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 420, "alignment": 2
        },
        "comic_pop": {
            "id": "comic_pop", "name": "Quadrinhos Comic Hero", "category": "Viral TikTok", "badge": "💬 COMIC",
            "font": "Comic Sans MS", "size": 78, "primary": "#FFE500", "highlight": "#FF0000",
            "outline_color": "#000000", "outline_w": 8, "shadow": 4, "shadow_color": "#000000",
            "border_style": 1, "bg_color": "#000000", "animation": "bounce", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 420, "alignment": 2
        },
        "glitch_matrix": {
            "id": "glitch_matrix", "name": "Matrix Hacker Green", "category": "Gamer / Cyber", "badge": "💻 HACKER",
            "font": "Courier New", "size": 74, "primary": "#FFFFFF", "highlight": "#22C55E",
            "outline_color": "#052E16", "outline_w": 6, "shadow": 4, "shadow_color": "#15803D",
            "border_style": 1, "bg_color": "#000000", "animation": "shake", "casing": "uppercase",
            "chunk_size": 3, "margin_v": 400, "alignment": 2
        },
        "cinema_letterbox": {
            "id": "cinema_letterbox", "name": "Cinema Clássico 2.35", "category": "Minimalista", "badge": "🎬 CINEMA",
            "font": "Georgia", "size": 66, "primary": "#FFFBEB", "highlight": "#F59E0B",
            "outline_color": "#1C1917", "outline_w": 3, "shadow": 2, "shadow_color": "#000000",
            "border_style": 1, "bg_color": "#000000", "animation": "fade", "casing": "original",
            "chunk_size": 4, "margin_v": 360, "alignment": 2
        },
        "breaking_news": {
            "id": "breaking_news", "name": "Plantão Urgente (News)", "category": "Impacto & Drama", "badge": "🚨 PLANTÃO",
            "font": "Arial Black", "size": 76, "primary": "#FFFFFF", "highlight": "#FFE500",
            "outline_color": "#7F1D1D", "outline_w": 8, "shadow": 4, "shadow_color": "#000000",
            "border_style": 3, "bg_color": "#DC2626", "animation": "pop_zoom", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 440, "alignment": 2
        },
        "red_danger": {
            "id": "red_danger", "name": "Alerta Vermelho Shock", "category": "Impacto & Drama", "badge": "⚠️ ALERTA",
            "font": "Impact", "size": 86, "primary": "#FFFFFF", "highlight": "#EF4444",
            "outline_color": "#450A0A", "outline_w": 9, "shadow": 5, "shadow_color": "#000000",
            "border_style": 1, "bg_color": "#000000", "animation": "shake", "casing": "uppercase",
            "chunk_size": 1, "margin_v": 430, "alignment": 2
        },
        "sunset_glow": {
            "id": "sunset_glow", "name": "Sunset Coral Glow", "category": "YouTube Shorts", "badge": "🌅 SUNSET",
            "font": "Trebuchet MS", "size": 76, "primary": "#FFFFFF", "highlight": "#FB7185",
            "outline_color": "#4C0519", "outline_w": 7, "shadow": 5, "shadow_color": "#E11D48",
            "border_style": 1, "bg_color": "#000000", "animation": "bounce", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 420, "alignment": 2
        },
        "midnight_neon": {
            "id": "midnight_neon", "name": "Midnight Cobalt Neon", "category": "Gamer / Cyber", "badge": "🌌 NEON",
            "font": "Impact", "size": 80, "primary": "#FFFFFF", "highlight": "#38BDF8",
            "outline_color": "#0C4A6E", "outline_w": 8, "shadow": 5, "shadow_color": "#0284C7",
            "border_style": 1, "bg_color": "#000000", "animation": "pop_zoom", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 420, "alignment": 2
        },
        "lemon_lime": {
            "id": "lemon_lime", "name": "Citrus Lime Punch", "category": "Viral TikTok", "badge": "🍋 CITRUS",
            "font": "Impact", "size": 82, "primary": "#FFFFFF", "highlight": "#A3E635",
            "outline_color": "#14532D", "outline_w": 8, "shadow": 4, "shadow_color": "#000000",
            "border_style": 1, "bg_color": "#000000", "animation": "bounce", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 420, "alignment": 2
        },
        "typewriter_clean": {
            "id": "typewriter_clean", "name": "Máquina de Escrever", "category": "Minimalista", "badge": "📜 RETRÔ",
            "font": "Courier New", "size": 70, "primary": "#F3F4F6", "highlight": "#FBBF24",
            "outline_color": "#111827", "outline_w": 5, "shadow": 2, "shadow_color": "#000000",
            "border_style": 1, "bg_color": "#000000", "animation": "fade", "casing": "original",
            "chunk_size": 3, "margin_v": 380, "alignment": 2
        },
        "hormozi_single_word": {
            "id": "hormozi_single_word", "name": "Hormozi 1 Palavra (Ultra Fast)", "category": "Viral TikTok", "badge": "⚡ 1 PALAVRA",
            "font": "Impact", "size": 94, "primary": "#FFE500", "highlight": "#FFFFFF",
            "outline_color": "#000000", "outline_w": 10, "shadow": 5, "shadow_color": "#000000",
            "border_style": 1, "bg_color": "#000000", "animation": "pop_zoom", "casing": "uppercase",
            "chunk_size": 1, "margin_v": 460, "alignment": 2
        },
        "pill_badge_viral": {
            "id": "pill_badge_viral", "name": "Pílula Moderna (Pill Box)", "category": "YouTube Shorts", "badge": "💊 PÍLULA",
            "font": "Arial Black", "size": 72, "primary": "#000000", "highlight": "#FF5C00",
            "outline_color": "#FFFFFF", "outline_w": 2, "shadow": 0, "shadow_color": "#000000",
            "border_style": 3, "bg_color": "#FFFFFF", "animation": "bounce", "casing": "uppercase",
            "chunk_size": 2, "margin_v": 420, "alignment": 2
        }
    }

class VideoPipeline:
    def __init__(self, output_dir: Optional[str] = None):
        self.base_dir = get_base_dir()
        self.output_dir = output_dir or os.path.join(self.base_dir, "outputs")
        os.makedirs(self.output_dir, exist_ok=True)
        self.temp_dir = os.path.join(self.base_dir, "temp_video")
        os.makedirs(self.temp_dir, exist_ok=True)

    def extract_or_download_segment(self, source: str, start: float, end: float, output_path: str) -> str:
        """
        Extrai o trecho do vídeo com velocidade máxima:
        - Para URLs do YouTube: baixa o vídeo fonte em alta velocidade uma única vez e recorta localmente em 0.05s.
        - Para arquivos locais: recorta diretamente em 0.05s.
        """
        ffmpeg_bin = get_bin("ffmpeg")

        if source.startswith("http://") or source.startswith("https://"):
            ytdlp_bin = get_bin("yt-dlp")
            ffmpeg_dir = os.path.dirname(ffmpeg_bin) if os.path.exists(ffmpeg_bin) else ""
            
            # Identificador do vídeo para reaproveitar download entre cortes
            url_hash = hashlib.md5(source.encode("utf-8")).hexdigest()[:12]
            source_cache_file = os.path.join(self.temp_dir, f"source_{url_hash}.mp4")

            # Baixa vídeo completo apenas se não existir ou estiver vazio
            if not os.path.exists(source_cache_file) or os.path.getsize(source_cache_file) < 10000:
                cmd_down = [
                    ytdlp_bin,
                    "--no-playlist",
                    "--force-overwrites",
                    "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                    "--merge-output-format", "mp4",
                    "-o", source_cache_file
                ]
                if ffmpeg_dir:
                    cmd_down.extend(["--ffmpeg-location", ffmpeg_dir])
                cmd_down.append(source)
                subprocess.run(cmd_down, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, creationflags=CREATE_NO_WINDOW)

            # Recorte local com sincronização milimétrica e normalização de timestamps
            cmd_cut = [
                ffmpeg_bin,
                "-ss", f"{start:.3f}",
                "-to", f"{end:.3f}",
                "-i", source_cache_file,
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
                "-c:a", "aac", "-b:a", "192k",
                "-avoid_negative_ts", "make_zero",
                output_path, "-y"
            ]
            subprocess.run(cmd_cut, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, creationflags=CREATE_NO_WINDOW)
        else:
            cmd = [
                ffmpeg_bin,
                "-ss", f"{start:.3f}",
                "-to", f"{end:.3f}",
                "-i", source,
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
                "-c:a", "aac", "-b:a", "192k",
                "-avoid_negative_ts", "make_zero",
                output_path, "-y"
            ]
            subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, creationflags=CREATE_NO_WINDOW)

        return output_path

    def detect_speaker_x_center(self, video_path: str, start: float = 0.0, end: float = 10.0) -> int:
        """Detecta o centro horizontal do interlocutor no corte usando amostragem multi-ponto e mediana para enquadramento 9:16 impecável."""
        try:
            ffmpeg_bin = get_bin("ffmpeg")
            dur = max(2.0, end - start)
            detected_x = []

            import rembg
            import numpy as np
            from PIL import Image
            session = rembg.new_session("u2netp")

            # Amostra 5 pontos ao longo do corte (15%, 35%, 50%, 65%, 85%)
            for frac in [0.15, 0.35, 0.50, 0.65, 0.85]:
                t = start + frac * dur
                sample_img = os.path.join(self.temp_dir, f"face_detect_{int(time.time()*1000)}_{int(frac*100)}.jpg")
                cmd = [
                    ffmpeg_bin, "-y", "-ss", f"{t:.2f}", "-i", video_path,
                    "-vframes", "1", "-q:v", "3", sample_img
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
                if os.path.exists(sample_img) and os.path.getsize(sample_img) > 3000:
                    try:
                        im = Image.open(sample_img)
                        orig_w, orig_h = im.size
                        small = im.copy()
                        small.thumbnail((320, 180))
                        mask = rembg.remove(small, session=session, only_mask=True)
                        arr = np.array(mask)
                        col_sums = np.sum(arr > 40, axis=0)
                        if np.sum(col_sums) > 0:
                            x_ratio = np.average(np.arange(len(col_sums)), weights=col_sums) / len(col_sums)
                            detected_x.append(int(x_ratio * orig_w))
                    finally:
                        try:
                            os.remove(sample_img)
                        except Exception:
                            pass

            if detected_x:
                med_center = int(np.median(detected_x))
                crop_w = int(1080 * (9 / 16))
                return max(0, min(1920 - crop_w, med_center - (crop_w // 2)))
        except Exception as e:
            print(f"[VideoPipeline] Detecção de centro de rosto multi-ponto: {e}")
        return 656  # Centro padrão em 1920x1080: (1920 - 608) / 2

    def generate_ass_subtitles(
        self,
        words: List[Dict[str, Any]],
        cut_start: float,
        cut_end: float,
        output_path: str,
        style_key: str = "hormozi_pop",
        custom_color: Optional[str] = None,
        custom_highlight_color: Optional[str] = None,
        custom_font: Optional[str] = None,
        custom_font_size: Optional[int] = None,
        custom_outline_color: Optional[str] = None,
        custom_outline_w: Optional[int] = None,
        custom_shadow: Optional[int] = None,
        custom_shadow_color: Optional[str] = None,
        custom_border_style: Optional[int] = None,
        custom_bg_color: Optional[str] = None,
        custom_animation: Optional[str] = None,
        custom_casing: Optional[str] = None,
        custom_chunk_size: Optional[int] = None,
        custom_margin_v: Optional[int] = None,
        custom_alignment: Optional[int] = None,
        cut_info: Optional[Dict[str, Any]] = None,
        enable_motion_graphics: bool = True
    ) -> str:
        """Gera legendas ASS com 24 estilos de alta conversão, animações dinâmicas e controle total de tipografia, cores e efeitos."""
        
        # Extrai preferências personalizadas de cut_info se disponíveis
        if cut_info:
            custom_color = custom_color or cut_info.get("custom_color")
            custom_highlight_color = custom_highlight_color or cut_info.get("custom_highlight_color")
            custom_font = custom_font or cut_info.get("custom_font")
            custom_font_size = custom_font_size or cut_info.get("custom_font_size")
            custom_outline_color = custom_outline_color or cut_info.get("custom_outline_color")
            custom_outline_w = custom_outline_w if custom_outline_w is not None else cut_info.get("custom_outline_w")
            custom_shadow = custom_shadow if custom_shadow is not None else cut_info.get("custom_shadow")
            custom_shadow_color = custom_shadow_color or cut_info.get("custom_shadow_color")
            custom_border_style = custom_border_style if custom_border_style is not None else cut_info.get("custom_border_style")
            custom_bg_color = custom_bg_color or cut_info.get("custom_bg_color")
            custom_animation = custom_animation or cut_info.get("custom_animation")
            custom_casing = custom_casing or cut_info.get("custom_casing")
            custom_chunk_size = custom_chunk_size or cut_info.get("custom_chunk_size")
            custom_margin_v = custom_margin_v or cut_info.get("custom_margin_v")
            custom_alignment = custom_alignment or cut_info.get("custom_alignment")

        # 24 Presets Profissionais de Alta Retenção
        presets = get_subtitle_presets_dict()
        cfg = dict(presets.get(style_key, presets["hormozi_pop"]))

        # Aplica customizações manuais sobre o preset selecionado
        font_name = custom_font or cfg["font"]
        font_size = custom_font_size or cfg["size"]
        primary_hex = custom_color or cfg["primary"]
        highlight_hex = custom_highlight_color or cfg.get("highlight", "#FFE500")
        outline_hex = custom_outline_color or cfg["outline_color"]
        outline_w = custom_outline_w if custom_outline_w is not None else cfg["outline_w"]
        shadow_val = custom_shadow if custom_shadow is not None else cfg["shadow"]
        shadow_hex = custom_shadow_color or cfg.get("shadow_color", "#000000")
        border_style = custom_border_style if custom_border_style is not None else cfg.get("border_style", 1)
        bg_hex = custom_bg_color or cfg.get("bg_color", "#000000")
        anim_type = custom_animation or cfg.get("animation", "bounce")
        casing = custom_casing or cfg.get("casing", "uppercase")
        chunk_size = custom_chunk_size or cfg.get("chunk_size", 2)
        margin_v = custom_margin_v or cfg.get("margin_v", 420)
        alignment = custom_alignment or cfg.get("alignment", 2)

        # Conversão para formato nativo de cores ASS (&HAABBGGRR)
        primary_ass = hex_to_ass(primary_hex)
        highlight_ass = hex_to_ass(highlight_hex)
        outline_ass = hex_to_ass(outline_hex)
        if border_style == 3:
            # Caixa ou tarja sólida/translúcida
            back_ass = hex_to_ass(bg_hex, alpha="30")
        else:
            # Sombra projetada
            back_ass = hex_to_ass(shadow_hex, alpha="80")

        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_ass},&H000000FF,{outline_ass},{back_ass},-1,0,0,0,100,100,1,0,{border_style},{outline_w},{shadow_val},{alignment},60,60,{margin_v},1
Style: MotionPop,Arial,95,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,60,60,{margin_v + 120},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        def fmt_time(seconds: float) -> str:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            cs = int((seconds - int(seconds)) * 100)
            return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"

        def clean_word(w: str) -> str:
            if not w:
                return ""
            # Remove qualquer tag HTML como <br>, <br/>, <br class="...">, <span>, etc.
            w = re.sub(r'<[^>]+>', '', str(w))
            # Remove quebras de linha e caracteres de controle
            w = re.sub(r'[\r\n\t]+', ' ', w)
            # Remove chaves ASS para evitar injeção de tags acidentais
            w = w.replace('{', '').replace('}', '').strip()
            return w

        def apply_case(w: str) -> str:
            w = clean_word(w)
            if not w:
                return ""
            if casing == "uppercase":
                return w.upper()
            elif casing == "titlecase":
                return w.capitalize()
            return w

        # 1. Verifica se o usuário enviou legendas corrigidas/personalizadas
        edited_subs = cut_info.get("edited_subtitles") if cut_info else None
        if edited_subs and isinstance(edited_subs, list) and len(edited_subs) > 0:
            cut_words = edited_subs
        else:
            cut_words = [w for w in words if w.get("start", 0) >= (cut_start - 0.2) and w.get("end", 0) <= (cut_end + 0.2)]

        if len(cut_words) < 3 and cut_info:
            fallback_text = cut_info.get("hook") or cut_info.get("text") or cut_info.get("title") or ""
            clean_text = re.sub(r'<[^>]+>', ' ', fallback_text)
            clean_text = re.sub(r'["“”]', '', clean_text).strip()
            raw_w = [w for w in clean_text.split() if clean_word(w)]
            if raw_w:
                dur = max(3.0, cut_end - cut_start)
                step = dur / max(1, len(raw_w))
                cut_words = []
                for i, w in enumerate(raw_w):
                    cw = clean_word(w)
                    if cw:
                        s = cut_start + i * step
                        cut_words.append({
                            "word": cw,
                            "start": round(s, 2),
                            "end": round(s + min(step, 0.4), 2)
                        })

        # Sanitiza rigorosamente cut_words para eliminar qualquer resíduo de <br> ou tags HTML
        sanitized_words = []
        for w_item in cut_words:
            w_str = clean_word(w_item.get("word", ""))
            if w_str:
                sanitized_words.append({**w_item, "word": w_str})
        cut_words = sanitized_words

        if not cut_words:
            cut_words = [{"word": "EDITIZE", "start": cut_start, "end": cut_end}]

        viral_emojis = ["🔥", "⚡", "💥", "😱", "💡", "🎯", "🚀", "👑", "👀", "✨"]
        dialogue_lines = []
        step_chunk = max(1, min(6, chunk_size))

        for i in range(0, len(cut_words), step_chunk):
            chunk = cut_words[i:i + step_chunk]
            s_time = max(0.0, chunk[0]["start"] - cut_start)
            e_time = max(s_time + 0.35, chunk[-1]["end"] - cut_start)

            if anim_type == "karaoke" and len(chunk) > 1:
                # Efeito Karaokê palavra por palavra
                for k_idx, active_w in enumerate(chunk):
                    w_s = max(s_time, active_w.get("start", cut_start) - cut_start)
                    w_e = max(w_s + 0.25, active_w.get("end", cut_start + 0.4) - cut_start)
                    parts = []
                    for j_idx, w_obj in enumerate(chunk):
                        w_text = apply_case(w_obj.get("word", ""))
                        if j_idx == k_idx:
                            parts.append(f"{{\\1c{highlight_ass}\\t(0,60,\\fscx114\\fscy114)\\t(60,120,\\fscx100\\fscy100)}}{w_text}{{\\1c{primary_ass}}}")
                        else:
                            parts.append(w_text)
                    line_str = " ".join(parts)
                    dialogue_lines.append(f"Dialogue: 0,{fmt_time(w_s)},{fmt_time(w_e)},Default,,0,0,0,,{line_str}")
            elif anim_type == "bounce":
                # Salto elástico no surgimento
                raw_words = [apply_case(c.get("word", "")) for c in chunk]
                if len(raw_words) > 1:
                    line_str = " ".join(raw_words[:-1]) + f" {{\\1c{highlight_ass}}}" + raw_words[-1]
                else:
                    line_str = f"{{\\1c{highlight_ass}}}" + raw_words[0]
                anim_tag = r"{\t(0,70,\fscx114\fscy114)\t(70,140,\fscx100\fscy100)}"
                dialogue_lines.append(f"Dialogue: 0,{fmt_time(s_time)},{fmt_time(e_time)},Default,,0,0,0,,{anim_tag}{line_str}")
            elif anim_type == "pop_zoom":
                # Zoom de impacto explosivo
                raw_words = [apply_case(c.get("word", "")) for c in chunk]
                if len(raw_words) > 1:
                    line_str = " ".join(raw_words[:-1]) + f" {{\\1c{highlight_ass}}}" + raw_words[-1]
                else:
                    line_str = f"{{\\1c{highlight_ass}}}" + raw_words[0]
                anim_tag = r"{\fscx85\fscy85\t(0,85,\fscx112\fscy112)\t(85,160,\fscx100\fscy100)}"
                dialogue_lines.append(f"Dialogue: 0,{fmt_time(s_time)},{fmt_time(e_time)},Default,,0,0,0,,{anim_tag}{line_str}")
            elif anim_type == "shake":
                # Tremor de tensão/urgência
                raw_words = [apply_case(c.get("word", "")) for c in chunk]
                line_str = " ".join(raw_words)
                anim_tag = r"{\t(0,40,\frz2.5)\t(40,80,\frz-2.5)\t(80,120,\frz0)}"
                dialogue_lines.append(f"Dialogue: 0,{fmt_time(s_time)},{fmt_time(e_time)},Default,,0,0,0,,{anim_tag}{line_str}")
            elif anim_type == "fade":
                # Surgimento suave elegante
                raw_words = [apply_case(c.get("word", "")) for c in chunk]
                line_str = " ".join(raw_words)
                anim_tag = r"{\fad(100,70)}"
                dialogue_lines.append(f"Dialogue: 0,{fmt_time(s_time)},{fmt_time(e_time)},Default,,0,0,0,,{anim_tag}{line_str}")
            else:
                # Estático com nitidez absoluta
                raw_words = [apply_case(c.get("word", "")) for c in chunk]
                line_str = " ".join(raw_words)
                dialogue_lines.append(f"Dialogue: 0,{fmt_time(s_time)},{fmt_time(e_time)},Default,,0,0,0,,{line_str}")

            # Motion Graphics: emojis a cada ~6 blocos se habilitado
            if enable_motion_graphics and (i % 6 == 0):
                emoji_choice = viral_emojis[(i // 6) % len(viral_emojis)]
                anim_emoji = r"{\t(0,90,\fscx130\fscy130)\t(90,180,\fscx100\fscy100)}" + emoji_choice
                dialogue_lines.append(f"Dialogue: 1,{fmt_time(s_time)},{fmt_time(min(e_time + 0.3, s_time + 1.2))},MotionPop,,0,0,0,,{anim_emoji}")

        content = header + "\n".join(dialogue_lines)
        with open(output_path, "w", encoding="utf-8-sig") as f:
            f.write(content)

        return output_path

    def render_viral_cut(
        self,
        source_video: str,
        cut_info: Dict[str, Any],
        words: List[Dict[str, Any]],
        layout: str = "portrait", # "portrait" ou "split_screen"
        broll_mode: str = "auto_extract", # "external" ou "auto_extract"
        broll_source: Optional[str] = None, # Link ou arquivo do trailer
        subtitle_style: str = "hormozi_pop",
        custom_color: Optional[str] = None,
        custom_font_size: Optional[int] = None,
        custom_margin_v: Optional[int] = None,
        custom_highlight_color: Optional[str] = None,
        custom_font: Optional[str] = None,
        custom_outline_color: Optional[str] = None,
        custom_outline_w: Optional[int] = None,
        custom_shadow: Optional[int] = None,
        custom_shadow_color: Optional[str] = None,
        custom_border_style: Optional[int] = None,
        custom_bg_color: Optional[str] = None,
        custom_animation: Optional[str] = None,
        custom_casing: Optional[str] = None,
        custom_chunk_size: Optional[int] = None,
        custom_alignment: Optional[int] = None,
        speed: float = 1.0,
        enable_zoom: bool = True,
        enable_drift: bool = True,
        center_face: bool = True,
        enable_motion_graphics: bool = True,
        enable_sound_effects: bool = True,
        bgm_name: str = "Cyber Lounge Sem Copyright",
        output_file: Optional[str] = None,
        progress_cb = None,
        **kwargs
    ) -> str:
        """Renderiza o corte viral final com alta retenção em formato 9:16 (1080x1920)."""
        ffmpeg_bin = get_bin("ffmpeg")
        cid = cut_info.get("id", "corte_01")
        title = cut_info.get("title", "corte")
        start = cut_info.get("start", 0.0)
        end = cut_info.get("end", 30.0)
        duration = max(5.0, end - start)

        if progress_cb:
            progress_cb(10, f"Obtendo trecho em alta resolução ({int(duration)}s)...")

        if output_file:
            final_file = output_file
        else:
            safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', f"{cid}_{title}") + ".mp4"
            final_file = os.path.join(self.output_dir, safe_name)

        timestamp_id = int(time.time() * 1000)
        temp_ass = os.path.join(self.temp_dir, f"sub_{cid}_{timestamp_id}.ass")
        temp_broll_ext = os.path.join(self.temp_dir, f"broll_ext_{cid}_{timestamp_id}.mp4")

        cleanup_files = [temp_ass, temp_broll_ext]

        try:
            # 1. Garante que o vídeo fonte é local (se for URL, faz download do original com cache)
            local_source = source_video
            if source_video.startswith("http://") or source_video.startswith("https://"):
                url_hash = hashlib.md5(source_video.encode("utf-8")).hexdigest()[:12]
                local_source = os.path.join(self.temp_dir, f"source_{url_hash}.mp4")
                if not os.path.exists(local_source) or os.path.getsize(local_source) < 10000:
                    ytdlp_bin = get_bin("yt-dlp")
                    ffmpeg_dir = os.path.dirname(ffmpeg_bin) if os.path.exists(ffmpeg_bin) else ""
                    cmd_down = [
                        ytdlp_bin,
                        "--no-playlist",
                        "--force-overwrites",
                        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                        "--merge-output-format", "mp4",
                        "-o", local_source
                    ]
                    if ffmpeg_dir:
                        cmd_down.extend(["--ffmpeg-location", ffmpeg_dir])
                    cmd_down.append(source_video)
                    subprocess.run(cmd_down, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, creationflags=CREATE_NO_WINDOW)

            if not os.path.exists(local_source) or os.path.getsize(local_source) == 0:
                raise RuntimeError(f"Não foi possível obter o vídeo fonte para o corte.")

            # 2. Garante legendas de altíssima precisão acústica (nível CapCut)
            cut_words_to_use = words
            if cut_info and cut_info.get("edited_subtitles"):
                cut_words_to_use = cut_info["edited_subtitles"]
            elif cut_info and cut_info.get("edited_words"):
                cut_words_to_use = cut_info["edited_words"]
            else:
                try:
                    if progress_cb:
                        progress_cb(25, "Ouvindo falas com precisão acústica avançada...")
                    cut_audio_temp = os.path.join(self.temp_dir, f"cut_audio_{cid}_{timestamp_id}.wav")
                    cmd_audio = [
                        ffmpeg_bin,
                        "-ss", f"{start:.3f}",
                        "-to", f"{end:.3f}",
                        "-i", local_source,
                        "-vn", "-ar", "16000", "-ac", "1",
                        cut_audio_temp, "-y"
                    ]
                    subprocess.run(cmd_audio, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, creationflags=CREATE_NO_WINDOW)
                    cleanup_files.append(cut_audio_temp)

                    from audio_ingest import AudioIngestEngine
                    if not hasattr(self, "_audio_engine") or self._audio_engine is None:
                        self._audio_engine = AudioIngestEngine(self.temp_dir)

                    precise_words = self._audio_engine.transcribe_cut_audio(cut_audio_temp, cut_start=start, cut_title=title)
                    if precise_words and len(precise_words) > 0:
                        cut_words_to_use = precise_words
                except Exception as ex_sub:
                    print(f"[VideoPipeline] Transcrição acústica direta: {ex_sub}")

            # Gera arquivo de legenda ASS com animação e motion graphics
            if progress_cb:
                progress_cb(35, "Gerando legendas dinâmicas animadas...")
            self.generate_ass_subtitles(
                cut_words_to_use, start, end, temp_ass,
                style_key=subtitle_style,
                custom_color=custom_color,
                custom_font_size=custom_font_size,
                custom_margin_v=custom_margin_v,
                custom_highlight_color=custom_highlight_color,
                custom_font=custom_font,
                custom_outline_color=custom_outline_color,
                custom_outline_w=custom_outline_w,
                custom_shadow=custom_shadow,
                custom_shadow_color=custom_shadow_color,
                custom_border_style=custom_border_style,
                custom_bg_color=custom_bg_color,
                custom_animation=custom_animation,
                custom_casing=custom_casing,
                custom_chunk_size=custom_chunk_size,
                custom_alignment=custom_alignment,
                cut_info=cut_info,
                enable_motion_graphics=enable_motion_graphics
            )

            # 3. Monta filtros de vídeo com efeitos dinâmicos completos em 9:16 direto
            if progress_cb:
                progress_cb(55, "Processando enquadramento 9:16 e dinamismo visual...")

            escaped_ass = temp_ass.replace('\\', '/').replace(':', r'\:')
            # Busca direta com precisão de milissegundos e áudio 100% em sincronia
            inputs = ['-ss', f"{start:.3f}", '-to', f"{end:.3f}", '-i', local_source]
            filter_chains = []

            # Tratamento de Layout
            if layout == "split_screen":
                has_external_broll = False
                if broll_mode == "external" and broll_source:
                    if broll_source.startswith("http://") or broll_source.startswith("https://"):
                        try:
                            self.extract_or_download_segment(broll_source, 0.0, duration, temp_broll_ext)
                            if os.path.exists(temp_broll_ext) and os.path.getsize(temp_broll_ext) > 1000:
                                inputs.extend(['-stream_loop', '-1', '-i', temp_broll_ext])
                                has_external_broll = True
                        except Exception as be:
                            print(f"[Aviso] Falha ao obter vídeo externo de apoio: {be}")
                    elif os.path.exists(broll_source):
                        inputs.extend(['-stream_loop', '-1', '-i', broll_source])
                        has_external_broll = True

                if has_external_broll:
                    filter_chains.append(
                        "[1:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,setsar=1[top];"
                        "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,crop=608:540:640:150,scale=1080:960:flags=lanczos,setsar=1[bot];"
                        "[top][bot]vstack[vsplit]"
                    )
                else:
                    # Modo Auto-Extract em passo único de alto desempenho
                    filter_chains.append(
                        "[0:v]split=2[v_top_in][v_bot_in];"
                        "[v_top_in]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,setsar=1[top];"
                        "[v_bot_in]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,crop=608:540:640:150,scale=1080:960:flags=lanczos,setsar=1[bot];"
                        "[top][bot]vstack[vsplit]"
                    )
                curr_v = "[vsplit]"
            else:
                # 1. Centralização Inteligente e Estabilização de Rosto
                if center_face:
                    base_x = self.detect_speaker_x_center(local_source, start, end)
                else:
                    base_x = 656

                # Garante limites válidos dentro do quadro 1920x1080
                base_x = max(0, min(1920 - 608, int(base_x)))

                # 2. Zoom Dinâmico Inteligente em Início de Fala (Punch-in Zoom estilo CapCut / OpusClip)
                if enable_zoom:
                    zoom_w = 520
                    zoom_h = 924
                    zoom_x = max(0, min(1920 - zoom_w, base_x + 44))

                    zoom_intervals = []
                    words_src = cut_words_to_use or []
                    if words_src:
                        last_end_time = 0.0
                        next_allowed_zoom = 5.5
                        for idx_w, w_item in enumerate(words_src):
                            w_s = max(0.0, w_item.get("start", 0) - start)
                            w_e = max(w_s, w_item.get("end", 0) - start)
                            is_pause = (w_s - last_end_time) > 0.35
                            prev_w = str(words_src[idx_w - 1].get("word", "")) if idx_w > 0 else ""
                            is_sentence = idx_w == 0 or is_pause or prev_w.endswith(('.', '!', '?'))

                            if is_sentence and w_s >= next_allowed_zoom and (w_s + 3.5) < (end - start - 2.5):
                                z_dur = min(3.8, (end - start) - w_s - 1.0)
                                zoom_intervals.append((round(w_s, 2), round(w_s + z_dur, 2)))
                                next_allowed_zoom = w_s + 14.0
                            last_end_time = w_e

                    if not zoom_intervals:
                        total_d = end - start
                        if total_d >= 35.0:
                            zoom_intervals = [(round(total_d * 0.22, 2), round(total_d * 0.22 + 3.5, 2)), (round(total_d * 0.62, 2), round(total_d * 0.62 + 3.5, 2))]
                        elif total_d >= 15.0:
                            zoom_intervals = [(round(total_d * 0.35, 2), round(total_d * 0.35 + 3.0, 2))]

                    if zoom_intervals:
                        zoom_cond = "+".join([f"between(t,{zs:.2f},{ze:.2f})" for zs, ze in zoom_intervals])
                        crop_expr = (
                            f"crop=w='if({zoom_cond},{zoom_w},608)':"
                            f"h='if({zoom_cond},{zoom_h},1080)':"
                            f"x='if({zoom_cond},{zoom_x},{base_x})':"
                            f"y=0"
                        )
                    else:
                        crop_expr = f"crop=608:1080:{base_x}:0"
                else:
                    crop_expr = f"crop=608:1080:{base_x}:0"

                # Modo Portrait 9:16 vertical direto estabilizado em alta definição
                filter_chains.append(
                    f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,{crop_expr},scale=1080:1920:flags=lanczos,setsar=1[vport]"
                )
                curr_v = "[vport]"

            # Velocidade acelerada para retenção (ex: 1.05x)
            if abs(speed - 1.0) > 0.01:
                filter_chains.append(f"{curr_v}setpts=(1/{speed:.2f})*PTS[vspeed]")
                curr_v = "[vspeed]"

            # Queima de legendas ASS animadas
            filter_chains.append(f"{curr_v}subtitles='{escaped_ass}'[vfinal]")

            # 4. Filtro de áudio com preservação vocal e Efeitos Sonoros (Whoosh / Pops)
            audio_chains = []
            main_audio = "[0:a]"
            if abs(speed - 1.0) > 0.01:
                audio_chains.append(f"[0:a]atempo={speed:.2f}[aspeed]")
                main_audio = "[aspeed]"

            if enable_sound_effects:
                sfx_whoosh = os.path.join(self.base_dir, "static", "sfx", "whoosh.wav")
                if os.path.exists(sfx_whoosh):
                    sfx_idx = inputs.count('-i')
                    inputs.extend(['-i', sfx_whoosh])
                    audio_chains.append(f"[{sfx_idx}:a]adelay=150|150,volume=0.55[sfx_w]")
                    audio_chains.append(f"{main_audio}[sfx_w]amix=inputs=2:duration=first:dropout_transition=2[afinal]")
                    audio_map = "[afinal]"
                else:
                    audio_map = main_audio
            else:
                audio_map = main_audio

            if audio_chains:
                filter_chains.extend(audio_chains)

            filter_complex_str = ";".join(filter_chains)

            if progress_cb:
                progress_cb(75, "Renderizando vídeo final em 1080x1920...")

            cmd_render = [
                ffmpeg_bin, *inputs,
                '-filter_complex', filter_complex_str,
                '-map', '[vfinal]', '-map', audio_map,
                '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'fastdecode', '-threads', '0', '-crf', '22',
                '-c:a', 'aac', '-b:a', '192k',
                '-avoid_negative_ts', 'make_zero',
                final_file, '-y'
            ]

            try:
                subprocess.run(cmd_render, capture_output=True, check=True, creationflags=CREATE_NO_WINDOW)
            except subprocess.CalledProcessError as e:
                err_log = e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)
                print(f"[Render Fallback] Legendas/filtro falharam: {err_log[:200]}")
                # Fallback garantindo sempre 9:16 vertical mesmo que o filtro de legendas falhe
                filter_chains_fb = [fc for fc in filter_chains if 'subtitles=' not in fc]
                last_node = curr_v.strip("[]")
                fb_complex = ";".join(filter_chains_fb)

                cmd_fb = [
                    ffmpeg_bin, *inputs,
                    '-filter_complex', fb_complex,
                    '-map', f"[{last_node}]", '-map', audio_map,
                    '-c:v', 'libx264', '-preset', 'ultrafast', '-threads', '0', '-crf', '22',
                    '-c:a', 'aac', '-b:a', '192k',
                    '-avoid_negative_ts', 'make_zero',
                    final_file, '-y'
                ]
                subprocess.run(cmd_fb, capture_output=True, check=True, creationflags=CREATE_NO_WINDOW)

            if progress_cb:
                progress_cb(100, "Corte renderizado com sucesso!")

            return final_file

        finally:
            for f in cleanup_files:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception:
                        pass

