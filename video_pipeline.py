import os
import sys
import re
import random
import subprocess
import time
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
        Extrai o trecho exato de 30-75 segundos:
        - Se for URL do YouTube: baixa APENAS a fatia específica com --download-sections em 1080p.
        - Se for arquivo local: recorta com FFmpeg -ss e -to instantaneamente.
        """
        ffmpeg_bin = get_bin("ffmpeg")

        if source.startswith("http://") or source.startswith("https://"):
            ytdlp_bin = get_bin("yt-dlp")
            ffmpeg_dir = os.path.dirname(ffmpeg_bin) if os.path.exists(ffmpeg_bin) else ""
            
            cmd = [
                ytdlp_bin,
                '-f', 'bestvideo[height<=1080]+bestaudio/best',
                '--merge-output-format', 'mp4',
                '--download-sections', f"*{start:.1f}-{end:.1f}",
                '--force-keyframes-at-cuts',
                '-o', output_path
            ]
            if ffmpeg_dir:
                cmd.extend(['--ffmpeg-location', ffmpeg_dir])
            cmd.append(source)
            
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
            if res.returncode != 0:
                # Fallback: se download-sections falhar, baixa padrão recortando via ffmpeg
                cmd_fb = [ytdlp_bin, '-f', 'best[height<=1080]', '-o', output_path + "_raw.mp4", source]
                subprocess.run(cmd_fb, check=True, creationflags=CREATE_NO_WINDOW)
                # Recorta
                cmd_cut = [ffmpeg_bin, '-ss', str(start), '-to', str(end), '-i', output_path + "_raw.mp4", '-c', 'copy', output_path, '-y']
                subprocess.run(cmd_cut, check=True, creationflags=CREATE_NO_WINDOW)
                if os.path.exists(output_path + "_raw.mp4"):
                    os.remove(output_path + "_raw.mp4")
        else:
            cmd = [
                ffmpeg_bin,
                '-ss', f"{start:.2f}",
                '-to', f"{end:.2f}",
                '-i', source,
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                '-c:a', 'aac',
                output_path, '-y'
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, creationflags=CREATE_NO_WINDOW)

        return output_path

    def generate_ass_subtitles(self, words: List[Dict[str, Any]], cut_start: float, cut_end: float, output_path: str, style_key: str = "yellow_viral") -> str:
        """Gera legendas animadas em formato Advanced SubStation Alpha (.ass) com BOM UTF-8."""
        styles = {
            "yellow_viral": {
                "font": "Arial Black", "size": 74,
                "primary": "&H0000FFFF",  # Amarelo vibrante
                "outline_color": "&H00000000", "outline_w": 6, "shadow": 2, "margin_v": 420
            },
            "cyan_neon": {
                "font": "Arial Black", "size": 72,
                "primary": "&H00FFFF00",  # Ciano Neon
                "outline_color": "&H00101010", "outline_w": 6, "shadow": 3, "margin_v": 420
            },
            "white_black": {
                "font": "Impact", "size": 78,
                "primary": "&H00FFFFFF",  # Branco clássico
                "outline_color": "&H00000000", "outline_w": 7, "shadow": 3, "margin_v": 420
            }
        }
        cfg = styles.get(style_key, styles["yellow_viral"])

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
            # Fallback se não houver palavras mapeadas
            cut_words = [{"word": "Cortefy AI", "start": cut_start, "end": cut_end}]

        # Agrupa em blocos de 3 palavras para ritmo viral
        dialogue_lines = []
        chunk_size = 3
        for i in range(0, len(cut_words), chunk_size):
            chunk = cut_words[i:i + chunk_size]
            s_time = max(0.0, chunk[0]["start"] - cut_start)
            e_time = max(s_time + 0.4, chunk[-1]["end"] - cut_start)
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
        subtitle_style: str = "yellow_viral",
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
        duration = end - start

        if progress_cb:
            progress_cb(10, f"Obtendo trecho em alta resolução ({int(duration)}s)...")

        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', f"{cid}_{title}") + ".mp4"
        final_file = os.path.join(self.output_dir, safe_name)

        temp_segment = os.path.join(self.temp_dir, f"raw_{cid}_{int(time.time())}.mp4")
        temp_ass = os.path.join(self.temp_dir, f"sub_{cid}_{int(time.time())}.ass")
        temp_broll = os.path.join(self.temp_dir, f"broll_{cid}_{int(time.time())}.mp4")

        # 1. Extrai ou baixa o segmento bruto
        self.extract_or_download_segment(source_video, start, end, temp_segment)

        # 2. Gera arquivo de legenda ASS
        if progress_cb:
            progress_cb(35, "Gerando legendas dinâmicas animadas...")
        self.generate_ass_subtitles(words, start, end, temp_ass, style_key=subtitle_style)

        # 3. Monta filtros de vídeo
        if progress_cb:
            progress_cb(55, "Processando enquadramento de vídeo e cortes de cena...")

        escaped_ass = temp_ass.replace('\\', '/').replace(':', '\\:')
        inputs = ['-i', temp_segment]
        filter_parts = []

        if layout == "split_screen":
            # Tela Dividida: Topo (B-Roll) 1080x960, Base (Apresentador) 1080x960
            if broll_mode == "external" and broll_source and os.path.exists(broll_source):
                cmd_broll = [
                    ffmpeg_bin, '-stream_loop', '-1', '-i', broll_source,
                    '-t', f"{duration:.2f}", '-an',
                    '-vf', 'scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960',
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
                    temp_broll, '-y'
                ]
            else:
                # Auto-extrai trecho de cena do próprio vídeo
                cmd_broll = [
                    ffmpeg_bin, '-stream_loop', '-1', '-ss', '10.0', '-i', temp_segment,
                    '-t', f"{duration:.2f}", '-an',
                    '-vf', 'scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960',
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
                    temp_broll, '-y'
                ]
            subprocess.run(cmd_broll, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, creationflags=CREATE_NO_WINDOW)
            inputs.extend(['-i', temp_broll])

            filter_parts.append(
                f"[1:v]scale=1080:960:flags=lanczos,setsar=1[top];"
                f"[0:v]crop=608:540:640:150,scale=1080:960:flags=lanczos,setsar=1[bot];"
                f"[top][bot]vstack[vsplit];"
            )
            curr_v = "[vsplit]"
        else:
            # Modo Portrait 9:16 vertical direto
            filter_parts.append(
                f"[0:v]crop=608:1080:640:0,scale=1080:1920:flags=lanczos,setsar=1[vport];"
            )
            curr_v = "[vport]"

        # Velocidade de vídeo
        if abs(speed - 1.0) > 0.01:
            filter_parts.append(f"{curr_v}setpts=(1/{speed:.2f})*PTS[vspeed];")
            curr_v = "[vspeed]"

        # Queima de legendas ASS
        filter_parts.append(f"{curr_v}subtitles='{escaped_ass}'[vfinal]")

        # Filtro de áudio com speed preservando pitch
        audio_filter = f"[0:a]atempo={speed:.2f}[afinal]" if abs(speed - 1.0) > 0.01 else ""
        audio_map = "[afinal]" if audio_filter else "0:a"

        if progress_cb:
            progress_cb(75, "Renderizando vídeo final em 1080x1920...")

        cmd_render = [ffmpeg_bin] + inputs + ['-filter_complex', "".join(filter_parts)]
        if audio_filter:
            cmd_render[-2] = cmd_render[-2] + ";" + audio_filter

        cmd_render.extend([
            '-map', '[vfinal]', '-map', audio_map,
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '20',
            '-c:a', 'aac', '-b:a', '192k',
            final_file, '-y'
        ])

        subprocess.run(cmd_render, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, creationflags=CREATE_NO_WINDOW)

        # Limpeza de arquivos temporários
        for f in [temp_segment, temp_ass, temp_broll]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

        if progress_cb:
            progress_cb(100, "Corte renderizado com sucesso!")

        return final_file
