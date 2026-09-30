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

    def generate_ass_subtitles(
        self,
        words: List[Dict[str, Any]],
        cut_start: float,
        cut_end: float,
        output_path: str,
        style_key: str = "hormozi_pop",
        custom_color: Optional[str] = None,
        custom_font_size: Optional[int] = None,
        custom_margin_v: Optional[int] = None
    ) -> str:
        """Gera legendas animadas em formato Advanced SubStation Alpha (.ass) com 10 estilos estilo CapCut."""
        # 10 Modelos de Legendas Inspirados em Ferramentas Populares (CapCut/Hormozi/MrBeast)
        styles = {
            "hormozi_pop": {
                "name": "Hormozi Pop",
                "font": "Arial Black", "size": 76,
                "primary": "&H0000FFFF",  # Amarelo Vibrante
                "outline_color": "&H00000000", "outline_w": 7, "shadow": 3, "margin_v": 420
            },
            "neon_cyber": {
                "name": "Neon Cyber",
                "font": "Arial Black", "size": 74,
                "primary": "&H0066FF00",  # Verde Neon
                "outline_color": "&H00111111", "outline_w": 6, "shadow": 4, "margin_v": 420
            },
            "beast_bold": {
                "name": "Beast Bold",
                "font": "Impact", "size": 82,
                "primary": "&H0000FFFF",  # Amarelo com contorno vermelho
                "outline_color": "&H000000D0", "outline_w": 8, "shadow": 4, "margin_v": 420
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

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        def fmt_time(seconds: float) -> str:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            cs = int((seconds - int(seconds)) * 100)
            return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"

        # Filtra palavras do corte
        cut_words = [w for w in words if w.get("start", 0) >= cut_start and w.get("end", 0) <= cut_end]
        if not cut_words:
            cut_words = [{"word": "Cortefy", "start": cut_start, "end": cut_end}]

        # Agrupa em blocos de 2 a 3 palavras para ritmo viral estilo CapCut
        dialogue_lines = []
        chunk_size = 2 if len(cut_words) > 40 else 3
        for i in range(0, len(cut_words), chunk_size):
            chunk = cut_words[i:i + chunk_size]
            s_time = max(0.0, chunk[0]["start"] - cut_start)
            e_time = max(s_time + 0.35, chunk[-1]["end"] - cut_start)
            text_str = " ".join([c["word"].upper() for c in chunk])
            dialogue_lines.append(f"Dialogue: 0,{fmt_time(s_time)},{fmt_time(e_time)},Default,,0,0,0,,{text_str}")

        content = header + "\n".join(dialogue_lines)
        with open(output_path, "w", encoding="utf-8-sig") as f:
            f.write(content)

        return output_path

    def render_viral_cut(
        self,
        source_video: str,
        cut_info: Dict[str, Any],
        words: List[Dict[str, Any]],
        layout: str = "split_screen", # "split_screen" ou "portrait"
        broll_mode: str = "auto_extract", # "external" ou "auto_extract"
        broll_source: Optional[str] = None, # Link ou arquivo do trailer
        subtitle_style: str = "hormozi_pop",
        custom_color: Optional[str] = None,
        custom_font_size: Optional[int] = None,
        custom_margin_v: Optional[int] = None,
        speed: float = 1.05,
        enable_zoom: bool = True,
        enable_drift: bool = True,
        bgm_name: str = "Cyber Lounge Sem Copyright",
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

            # 2. Gera arquivo de legenda ASS
            if progress_cb:
                progress_cb(35, "Gerando legendas dinâmicas animadas...")
            self.generate_ass_subtitles(
                words, start, end, temp_ass,
                style_key=subtitle_style,
                custom_color=custom_color,
                custom_font_size=custom_font_size,
                custom_margin_v=custom_margin_v
            )

            # 3. Monta filtros de vídeo
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
                # Modo Portrait 9:16 vertical direto normalizado
                filter_chains.append(
                    "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,crop=608:1080:640:0,scale=1080:1920:flags=lanczos,setsar=1[vport]"
                )
                curr_v = "[vport]"

            # Velocidade acelerada para retenção (ex: 1.05x)
            if abs(speed - 1.0) > 0.01:
                filter_chains.append(f"{curr_v}setpts=(1/{speed:.2f})*PTS[vspeed]")
                curr_v = "[vspeed]"

            # Queima de legendas ASS animadas
            filter_chains.append(f"{curr_v}subtitles='{escaped_ass}'[vfinal]")

            # Filtro de áudio com preservação de tom vocal
            audio_filter = f"[0:a]atempo={speed:.2f}[afinal]" if abs(speed - 1.0) > 0.01 else ""
            audio_map = "[afinal]" if audio_filter else "0:a"

            filter_complex_str = ";".join(filter_chains)
            if audio_filter:
                filter_complex_str = f"{filter_complex_str};{audio_filter}"

            if progress_cb:
                progress_cb(75, "Renderizando vídeo final em 1080x1920...")

            cmd_render = [
                ffmpeg_bin, *inputs,
                '-filter_complex', filter_complex_str,
                '-map', '[vfinal]', '-map', audio_map,
                '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'fastdecode', '-threads', '0', '-crf', '22',
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
                if audio_filter:
                    fb_complex = f"{fb_complex};{audio_filter}"

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

