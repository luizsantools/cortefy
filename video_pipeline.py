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

class VideoPipeline:
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.path.join(get_base_dir(), "outputs")
        os.makedirs(self.output_dir, exist_ok=True)
        self.temp_dir = os.path.join(get_base_dir(), "temp_video")
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

            # Recorte local instantâneo via FFmpeg (0.05s)
            cmd_cut = [
                ffmpeg_bin,
                "-ss", f"{start:.2f}",
                "-to", f"{end:.2f}",
                "-i", source_cache_file,
                "-c", "copy",
                output_path, "-y"
            ]
            subprocess.run(cmd_cut, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, creationflags=CREATE_NO_WINDOW)
        else:
            cmd = [
                ffmpeg_bin,
                "-ss", f"{start:.2f}",
                "-to", f"{end:.2f}",
                "-i", source,
                "-c", "copy",
                output_path, "-y"
            ]
            subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, creationflags=CREATE_NO_WINDOW)

        return output_path

    def detect_speaker_x_center(self, video_path: str, start: float = 0.0, end: float = 10.0) -> int:
        """Detecta o centro horizontal do interlocutor no corte para enquadramento 9:16 preciso."""
        try:
            mid = (start + end) / 2.0
            ffmpeg_bin = get_bin("ffmpeg")
            sample_img = os.path.join(self.temp_dir, f"face_detect_{int(time.time()*1000)}.jpg")
            cmd = [
                ffmpeg_bin, "-y", "-ss", f"{mid:.2f}", "-i", video_path,
                "-vframes", "1", "-q:v", "3", sample_img
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
            if os.path.exists(sample_img) and os.path.getsize(sample_img) > 3000:
                import rembg
                import numpy as np
                from PIL import Image
                im = Image.open(sample_img)
                orig_w, orig_h = im.size
                small = im.copy()
                small.thumbnail((320, 180))
                session = rembg.new_session("u2netp")
                mask = rembg.remove(small, session=session, only_mask=True)
                arr = np.array(mask)
                col_sums = np.sum(arr > 40, axis=0)
                try:
                    os.remove(sample_img)
                except Exception:
                    pass
                if np.sum(col_sums) > 0:
                    x_ratio = np.average(np.arange(len(col_sums)), weights=col_sums) / len(col_sums)
                    x_center = int(x_ratio * orig_w)
                    crop_w = int(orig_h * (9 / 16))
                    return max(0, min(orig_w - crop_w, x_center - (crop_w // 2)))
        except Exception as e:
            print(f"[VideoPipeline] Detecção de centro de rosto: {e}")
        return 656  # Centro padrão em 1920x1080: (1920 - 608) / 2

    def generate_ass_subtitles(
        self,
        words: List[Dict[str, Any]],
        cut_start: float,
        cut_end: float,
        output_path: str,
        style_key: str = "hormozi_pop",
        custom_color: Optional[str] = None,
        custom_font_size: Optional[int] = None,
        custom_margin_v: Optional[int] = None,
        cut_info: Optional[Dict[str, Any]] = None,
        enable_motion_graphics: bool = True
    ) -> str:
        """Gera legendas ASS com animação dinâmica estilo CapCut, cores vibrantes e suporte a motion graphics."""
        styles = {
            "hormozi_pop": {
                "name": "Hormozi Pop",
                "font": "Impact", "size": 80,
                "primary": "&H0000FFFF",  # Amarelo Neon
                "outline_color": "&H00000000", "outline_w": 8, "shadow": 4, "margin_v": 420
            },
            "tiktok_bounce": {
                "name": "TikTok Bounce",
                "font": "Arial Black", "size": 76,
                "primary": "&H0000FF00",  # Verde Lima
                "outline_color": "&H00000000", "outline_w": 7, "shadow": 3, "margin_v": 420
            },
            "beast_impact": {
                "name": "MrBeast Impact",
                "font": "Impact", "size": 84,
                "primary": "&H000055FF",  # Vermelho / Laranja
                "outline_color": "&H00000000", "outline_w": 9, "shadow": 5, "margin_v": 420
            },
            "cyan_electric": {
                "name": "Ciano Elétrico",
                "font": "Arial Black", "size": 74,
                "primary": "&H00FFFF00",  # Ciano Elétrico
                "outline_color": "&H000A0A0A", "outline_w": 6, "shadow": 4, "margin_v": 420
            },
            "purple_viral": {
                "name": "Roxo Viral",
                "font": "Arial Black", "size": 74,
                "primary": "&H00F755A8",  # Púrpura TikTok
                "outline_color": "&H00000000", "outline_w": 6, "shadow": 3, "margin_v": 420
            },
            "clean_minimal": {
                "name": "Clean Minimal",
                "font": "Arial", "size": 66,
                "primary": "&H00FFFFFF",  # Branco puro
                "outline_color": "&H001F1F1F", "outline_w": 4, "shadow": 2, "margin_v": 400
            },
            "gold_karaoke": {
                "name": "Karaokê Dourado",
                "font": "Arial Black", "size": 76,
                "primary": "&H0020D0FF",  # Dourado Metálico
                "outline_color": "&H00000000", "outline_w": 7, "shadow": 3, "margin_v": 420
            },
            "fire_sunset": {
                "name": "Fogo Sunset",
                "font": "Impact", "size": 80,
                "primary": "&H000066FF",  # Laranja / Fogo
                "outline_color": "&H00000000", "outline_w": 7, "shadow": 3, "margin_v": 420
            },
            "emerald_vip": {
                "name": "Esmeralda VIP",
                "font": "Arial Black", "size": 74,
                "primary": "&H0078C850",  # Verde Esmeralda
                "outline_color": "&H00050505", "outline_w": 6, "shadow": 3, "margin_v": 420
            },
            "monochrome_3d": {
                "name": "Monocromo 3D",
                "font": "Impact", "size": 80,
                "primary": "&H00FFFFFF",  # Branco com sombra profunda
                "outline_color": "&H00000000", "outline_w": 8, "shadow": 5, "margin_v": 420
            }
        }
        cfg = dict(styles.get(style_key, styles["hormozi_pop"]))

        # Personalizações do usuário
        if custom_color:
            clean_hex = custom_color.lstrip('#')
            if len(clean_hex) == 6:
                r, g, b = clean_hex[0:2], clean_hex[2:4], clean_hex[4:6]
                cfg["primary"] = f"&H00{b}{g}{r}".upper()
        if custom_font_size and custom_font_size > 30:
            cfg["size"] = custom_font_size
        if custom_margin_v and custom_margin_v > 50:
            cfg["margin_v"] = custom_margin_v

        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{cfg['font']},{cfg['size']},{cfg['primary']},&H000000FF,{cfg['outline_color']},&H80000000,-1,0,0,0,100,100,1,0,1,{cfg['outline_w']},{cfg['shadow']},2,60,60,{cfg['margin_v']},1
Style: MotionPop,Arial,95,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,60,60,{cfg['margin_v'] + 120},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        def fmt_time(seconds: float) -> str:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            cs = int((seconds - int(seconds)) * 100)
            return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"

        # 1. Verifica se o usuário enviou legendas corrigidas/personalizadas
        edited_subs = cut_info.get("edited_subtitles") if cut_info else None
        if edited_subs and isinstance(edited_subs, list) and len(edited_subs) > 0:
            cut_words = edited_subs
        else:
            # Filtra palavras do corte com margem suave de 0.2s
            cut_words = [w for w in words if w.get("start", 0) >= (cut_start - 0.2) and w.get("end", 0) <= (cut_end + 0.2)]

        # Caso haja poucas palavras mapeadas, utiliza o gancho/título real para sincronizar as legendas
        if len(cut_words) < 3 and cut_info:
            fallback_text = cut_info.get("hook") or cut_info.get("text") or cut_info.get("title") or ""
            clean_text = re.sub(r'["“”]', '', fallback_text).strip()
            raw_w = [w for w in clean_text.split() if w]
            if raw_w:
                dur = max(3.0, cut_end - cut_start)
                step = dur / max(1, len(raw_w))
                cut_words = []
                for i, w in enumerate(raw_w):
                    s = cut_start + i * step
                    cut_words.append({
                        "word": w,
                        "start": round(s, 2),
                        "end": round(s + min(step, 0.4), 2)
                    })

        if not cut_words:
            cut_words = [{"word": "EDITIZE", "start": cut_start, "end": cut_end}]

        # Emojis para Motion Graphics virais
        viral_emojis = ["🔥", "⚡", "💥", "😱", "💡", "🎯", "🚀", "👑"]

        # Agrupa em blocos de 2 a 3 palavras com animação de impacto (Bounce / Pop)
        dialogue_lines = []
        chunk_size = 2 if len(cut_words) > 35 else 3
        for i in range(0, len(cut_words), chunk_size):
            chunk = cut_words[i:i + chunk_size]
            s_time = max(0.0, chunk[0]["start"] - cut_start)
            e_time = max(s_time + 0.35, chunk[-1]["end"] - cut_start)
            words_text = [c.get("word", "").upper() for c in chunk]
            text_str = " ".join(words_text)

            # Efeito Bounce / Pop ao surgir a palavra
            anim_text = f"{{\\t(0,70,\\fscx112\\fscy112)\\t(70,140,\\fscx100\\fscy100)}}{text_str}"
            dialogue_lines.append(f"Dialogue: 0,{fmt_time(s_time)},{fmt_time(e_time)},Default,,0,0,0,,{anim_text}")

            # Motion Graphics: insere sticker flutuante a cada ~5-7 segundos
            if enable_motion_graphics and (i % 6 == 0):
                emoji_choice = viral_emojis[(i // 6) % len(viral_emojis)]
                anim_emoji = f"{{\\t(0,90,\\fscx130\\fscy130)\\t(90,180,\\fscx100\\fscy100)}}{emoji_choice}"
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
        speed: float = 1.0,
        enable_zoom: bool = True,
        enable_drift: bool = True,
        center_face: bool = True,
        enable_motion_graphics: bool = True,
        enable_sound_effects: bool = True,
        bgm_name: str = "Cyber Lounge Sem Copyright",
        output_file: Optional[str] = None,
        progress_cb = None
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
        temp_segment = os.path.join(self.temp_dir, f"raw_{cid}_{timestamp_id}.mp4")
        temp_ass = os.path.join(self.temp_dir, f"sub_{cid}_{timestamp_id}.ass")
        temp_broll_ext = os.path.join(self.temp_dir, f"broll_ext_{cid}_{timestamp_id}.mp4")

        cleanup_files = [temp_segment, temp_ass, temp_broll_ext]

        try:
            # 1. Extrai ou baixa o segmento bruto do corte
            self.extract_or_download_segment(source_video, start, end, temp_segment)

            if not os.path.exists(temp_segment) or os.path.getsize(temp_segment) == 0:
                raise RuntimeError(f"Não foi possível obter o trecho de vídeo de {start}s a {end}s.")

            # 2. Gera arquivo de legenda ASS com animação e motion graphics
            if progress_cb:
                progress_cb(35, "Gerando legendas dinâmicas animadas...")
            self.generate_ass_subtitles(
                words, start, end, temp_ass,
                style_key=subtitle_style,
                custom_color=custom_color,
                custom_font_size=custom_font_size,
                custom_margin_v=custom_margin_v,
                cut_info=cut_info,
                enable_motion_graphics=enable_motion_graphics
            )

            # 3. Monta filtros de vídeo com efeitos dinâmicos completos
            if progress_cb:
                progress_cb(55, "Processando enquadramento 9:16 e dinamismo visual...")

            escaped_ass = temp_ass.replace('\\', '/').replace(':', r'\:')
            inputs = ['-i', temp_segment]
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
                # 1. Centralização Inteligente de Rostos
                if center_face:
                    base_x = self.detect_speaker_x_center(temp_segment, 0.0, min(8.0, duration))
                else:
                    base_x = 656

                # 2. Movimento Lateral (Drift) com Pan Suave
                if enable_drift:
                    crop_expr = f"crop=608:1080:x='clip({base_x}+24*sin(2*PI*t/6.5),0,in_w-608)':y=0"
                else:
                    crop_expr = f"crop=608:1080:{base_x}:0"

                # Modo Portrait 9:16 vertical direto normalizado
                filter_chains.append(
                    f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,{crop_expr},scale=1080:1920:flags=lanczos,setsar=1[vport]"
                )
                curr_v = "[vport]"

            # 3. Zoom Dinâmico Focal (Pulse sutil a cada ciclo)
            if enable_zoom:
                filter_chains.append(f"{curr_v}zoompan=z='1.0+0.05*sin(2*PI*in/100)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30[vzoom]")
                curr_v = "[vzoom]"

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
                    sfx_idx = len(inputs) // 2
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
                final_file, '-y'
            ]

            try:
                subprocess.run(cmd_render, capture_output=True, check=True, creationflags=CREATE_NO_WINDOW)
            except subprocess.CalledProcessError as e:
                err_log = e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)
                print(f"[Render Fallback] Legendas/filtro falharam: {err_log[:200]}")
                # Fallback sem legendas caso ocorra erro no filtro subtitles
                filter_chains_fb = [fc for fc in filter_chains if 'subtitles=' not in fc]
                last_node = curr_v.strip("[]")
                fb_complex = ";".join(filter_chains_fb)

                cmd_fb = [
                    ffmpeg_bin, *inputs,
                    '-filter_complex', fb_complex,
                    '-map', f"[{last_node}]", '-map', audio_map,
                    '-c:v', 'libx264', '-preset', 'ultrafast', '-threads', '0', '-crf', '22',
                    '-c:a', 'aac', '-b:a', '192k',
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

