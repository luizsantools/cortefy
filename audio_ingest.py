import os
import sys
import subprocess
import json
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

class AudioIngestEngine:
    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = temp_dir or os.path.join(get_base_dir(), "temp_audio")
        os.makedirs(self.temp_dir, exist_ok=True)
        self._whisper_model = None

    def _get_whisper(self):
        if self._whisper_model is None:
            import whisper
            print("[AudioIngest] Carregando modelo Whisper...")
            self._whisper_model = whisper.load_model("base")
        return self._whisper_model

    def download_youtube_audio(self, youtube_url: str, progress_callback=None) -> tuple[str, str]:
        """Baixa apenas a trilha de áudio em segundos para processamento rápido."""
        if progress_callback:
            progress_callback(15, "Lendo o vídeo em alta velocidade...")

        ytdlp_bin = get_bin("yt-dlp")
        ffmpeg_bin = get_bin("ffmpeg")
        ffmpeg_dir = os.path.dirname(ffmpeg_bin) if os.path.exists(ffmpeg_bin) else ""

        audio_output = os.path.join(self.temp_dir, f"audio_{int(time.time())}.m4a")

        cmd = [
            ytdlp_bin,
            '-f', 'ba[ext=m4a]/ba/b',
            '-x', '--audio-format', 'm4a',
            '-o', audio_output,
        ]
        if ffmpeg_dir:
            cmd.extend(['--ffmpeg-location', ffmpeg_dir])
        cmd.append(youtube_url)

        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW
        )
        if res.returncode != 0:
            err = res.stderr.decode('utf-8', errors='replace').strip()
            raise RuntimeError(f"Não foi possível obter o vídeo: {err[:300]}")

        title = "Vídeo do YouTube"
        try:
            cmd_meta = [ytdlp_bin, '--get-title', youtube_url]
            res_meta = subprocess.run(cmd_meta, stdout=subprocess.PIPE, text=True, creationflags=CREATE_NO_WINDOW)
            if res_meta.stdout.strip():
                title = res_meta.stdout.strip()
        except Exception:
            pass

        if progress_callback:
            progress_callback(35, "Vídeo carregado! Ouvindo o que foi falado...")

        return audio_output, title

    def ingest_youtube_audio(self, youtube_url: str, progress_callback=None) -> Dict[str, Any]:
        audio_output, title = self.download_youtube_audio(youtube_url, progress_callback=progress_callback)
        return self.transcribe_audio_file(audio_output, video_title=title, progress_callback=progress_callback)

    def extract_audio_from_local_file(self, video_path: str, progress_callback=None) -> Dict[str, Any]:
        """Extrai áudio WAV do arquivo local."""
        if progress_callback:
            progress_callback(15, "Carregando arquivo de vídeo...")

        ffmpeg_bin = get_bin("ffmpeg")
        audio_output = os.path.join(self.temp_dir, f"local_audio_{int(time.time())}.wav")

        cmd = [
            ffmpeg_bin, '-i', video_path,
            '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
            audio_output, '-y'
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, creationflags=CREATE_NO_WINDOW)

        title = os.path.splitext(os.path.basename(video_path))[0]
        return self.transcribe_audio_file(audio_output, video_title=title, progress_callback=progress_callback)

    def transcribe_audio_file(self, audio_file: str, video_title: str = "", progress_callback=None) -> Dict[str, Any]:
        """Transcreve o arquivo de áudio de forma ultra-rápida sem travar o processamento."""
        if progress_callback:
            progress_callback(50, "Entendendo as falas da conversa...")

        model = self._get_whisper()
        res = model.transcribe(audio_file, language="pt", word_timestamps=False, fp16=False)

        words = []
        segments = []

        for seg in res.get("segments", []):
            st = seg.get("start", 0.0)
            et = seg.get("end", 0.0)
            txt = seg.get("text", "").strip()
            segments.append({
                "start": st,
                "end": et,
                "text": txt
            })
            raw_words = [w for w in txt.split() if w]
            if raw_words:
                step = (et - st) / len(raw_words)
                for i, w in enumerate(raw_words):
                    words.append({
                        "word": w,
                        "start": round(st + i * step, 3),
                        "end": round(st + (i + 1) * step, 3)
                    })

        if progress_callback:
            progress_callback(85, "Organizando as falas e ganchos virais...")

        return {
            "title": video_title,
            "audio_path": audio_file,
            "segments": segments,
            "words": words,
            "duration": segments[-1]["end"] if segments else 0.0
        }
