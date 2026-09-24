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

    def ingest_youtube_audio(self, youtube_url: str, progress_callback=None) -> Dict[str, Any]:
        """
        Técnica Audio-First:
        Baixa APENAS a trilha de áudio compactada (M4A/Opus) em altíssima velocidade (poucos segundos),
        sem baixar os gigabytes pesados de vídeo.
        """
        if progress_callback:
            progress_callback(10, "Iniciando download ultra-rápido de áudio leve...")

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
            raise RuntimeError(f"Erro ao obter áudio do YouTube: {err[:300]}")

        # Pega metadados do vídeo (título, autor)
        title = "Vídeo do YouTube"
        try:
            cmd_meta = [ytdlp_bin, '--get-title', youtube_url]
            res_meta = subprocess.run(cmd_meta, stdout=subprocess.PIPE, text=True, creationflags=CREATE_NO_WINDOW)
            if res_meta.stdout.strip():
                title = res_meta.stdout.strip()
        except Exception:
            pass

        if progress_callback:
            progress_callback(40, f"Áudio leve obtido com sucesso! Analisando: {title[:40]}...")

        # Transcrição com Whisper
        return self.transcribe_audio_file(audio_output, video_title=title, progress_callback=progress_callback)

    def extract_audio_from_local_file(self, video_path: str, progress_callback=None) -> Dict[str, Any]:
        """Extrai áudio WAV 16kHz do arquivo de vídeo local."""
        if progress_callback:
            progress_callback(15, "Extraindo áudio do arquivo local...")

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
        """Transcreve o arquivo de áudio com marcações temporais de palavras."""
        if progress_callback:
            progress_callback(50, "Transcrevendo falas com Whisper IA...")

        model = self._get_whisper()
        res = model.transcribe(audio_file, language="pt", word_timestamps=True)

        words = []
        segments = []

        for seg in res.get("segments", []):
            segments.append({
                "start": seg.get("start", 0.0),
                "end": seg.get("end", 0.0),
                "text": seg.get("text", "").strip()
            })
            for w in seg.get("words", []):
                words.append({
                    "word": w.get("word", "").strip(),
                    "start": round(w.get("start", 0.0), 3),
                    "end": round(w.get("end", 0.0), 3)
                })

        if progress_callback:
            progress_callback(85, "Organizando palavras e preparando análise de viralidade...")

        return {
            "title": video_title,
            "audio_path": audio_file,
            "segments": segments,
            "words": words,
            "duration": segments[-1]["end"] if segments else 0.0
        }
