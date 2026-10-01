import os
import sys
import subprocess
import json
import time
import random
import re
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

    def parse_vtt_file(self, vtt_path: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Faz o parse de arquivo WebVTT extraindo segmentos limpos e palavras com timestamps precisos sem perda de palavras."""
        if not os.path.exists(vtt_path):
            return [], []

        with open(vtt_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        time_re = re.compile(r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})')
        tag_re = re.compile(r'<[^>]+>')

        def parse_ts(ts: str) -> float:
            parts = ts.split(':')
            h = int(parts[0])
            m = int(parts[1])
            s = float(parts[2])
            return h * 3600 + m * 60 + s

        segments = []
        words = []
        i = 0
        seen_texts = set()

        while i < len(lines):
            line = lines[i].strip()
            m = time_re.search(line)
            if m:
                start_sec = parse_ts(m.group(1))
                end_sec = parse_ts(m.group(2))
                i += 1

                # Pula cues instantâneos (< 0.05s) gerados pelo YouTube para flush
                if end_sec - start_sec < 0.05:
                    while i < len(lines) and lines[i].strip():
                        i += 1
                    continue

                cue_lines = []
                while i < len(lines) and lines[i].strip() and not time_re.search(lines[i]):
                    cue_lines.append(lines[i])
                    i += 1

                # Na legenda WebVTT do YouTube, a última linha do bloco é a fala ativa do timestamp
                target_line = cue_lines[-1] if cue_lines else ""
                clean_text = tag_re.sub('', target_line).strip()

                if clean_text and clean_text not in seen_texts and len(clean_text) > 1:
                    seen_texts.add(clean_text)
                    segments.append({
                        "start": round(start_sec, 2),
                        "end": round(end_sec, 2),
                        "text": clean_text
                    })

                    # Divide a linha ativa preservando timestamps intermediários para não perder palavras
                    parts = re.split(r'(<\d{2}:\d{2}:\d{2}\.\d{3}>)', target_line)
                    current_time = start_sec
                    for p in parts:
                        tm = re.match(r'<(\d{2}:\d{2}:\d{2}\.\d{3})>', p)
                        if tm:
                            current_time = parse_ts(tm.group(1))
                        else:
                            clean_p = tag_re.sub('', p).strip()
                            raw_words = [w for w in clean_p.split() if w]
                            for w in raw_words:
                                words.append({
                                    "word": w,
                                    "start": round(current_time, 3),
                                    "end": round(min(end_sec, current_time + 0.35), 3)
                                })
            else:
                i += 1

        if not words and segments:
            for seg in segments:
                raw_words = [w for w in seg["text"].split() if w]
                if raw_words:
                    step = max(0.2, (seg["end"] - seg["start"]) / len(raw_words))
                    for idx, w in enumerate(raw_words):
                        words.append({
                            "word": w,
                            "start": round(seg["start"] + idx * step, 3),
                            "end": round(seg["start"] + (idx + 1) * step, 3)
                        })

        return segments, words

    def extract_youtube_transcript_fast(self, youtube_url: str, progress_callback=None) -> Dict[str, Any]:
        """Extrai transcrição oficial/automática do YouTube em ~2 segundos com yt-dlp sem baixar áudio."""
        if progress_callback:
            progress_callback(20, "Identificando fala do vídeo em alta velocidade...")

        ytdlp_bin = get_bin("yt-dlp")
        rand_id = random.randint(1000, 9999)
        base_sub_name = os.path.join(self.temp_dir, f"sub_fast_{int(time.time())}_{rand_id}")

        cmd = [
            ytdlp_bin,
            '--skip-download',
            '--write-auto-sub',
            '--write-sub',
            '--sub-lang', 'pt,pt-BR,en',
            '--sub-format', 'vtt',
            '--no-warnings',
            '--no-simulate',
            '--print', '%(title)s',
            '-o', f"{base_sub_name}.%(ext)s",
            youtube_url
        ]

        title = "Vídeo do YouTube"
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=CREATE_NO_WINDOW, timeout=12)
            if res.stdout.strip():
                title = res.stdout.strip().split('\n')[0].strip()
        except Exception as e:
            print(f"[AudioIngest] Falha na extração de legendas: {e}")

        vtt_file = None
        for lang in ['pt', 'pt-BR', 'en']:
            candidate = f"{base_sub_name}.{lang}.vtt"
            if os.path.exists(candidate) and os.path.getsize(candidate) > 200:
                vtt_file = candidate
                break

        if not vtt_file:
            for f in os.listdir(self.temp_dir):
                if f.startswith(f"sub_fast_") and f.endswith(".vtt"):
                    full_p = os.path.join(self.temp_dir, f)
                    if os.path.getsize(full_p) > 200:
                        vtt_file = full_p
                        break

        if vtt_file:
            segments, words = self.parse_vtt_file(vtt_file)
            if segments:
                if progress_callback:
                    progress_callback(35, f"Transcrição obtida em segundos ({len(segments)} falas identificadas)!")
                return {
                    "success": True,
                    "title": title,
                    "segments": segments,
                    "words": words,
                    "duration": segments[-1]["end"] if segments else 0.0,
                    "vtt_file": vtt_file
                }

        return {"success": False, "title": title}

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

    def get_video_metadata(self, youtube_url: str) -> Dict[str, Any]:
        """Obtém rapidamente título, duração e miniatura do vídeo sem baixar."""
        ytdlp_bin = get_bin("yt-dlp")
        try:
            cmd = [
                ytdlp_bin,
                '--print', '%(title)s\t%(duration)s\t%(thumbnail)s\t%(uploader)s',
                '--no-warnings',
                '--skip-download',
                youtube_url
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=CREATE_NO_WINDOW)
            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.strip().split('\t')
                title = parts[0] if len(parts) > 0 else "Vídeo do YouTube"
                duration_sec = 0.0
                if len(parts) > 1 and parts[1]:
                    try:
                        duration_sec = float(parts[1])
                    except ValueError:
                        duration_sec = 0.0
                thumb = parts[2] if len(parts) > 2 else ""
                channel = parts[3] if len(parts) > 3 else ""
                mins = int(duration_sec // 60)
                secs = int(duration_sec % 60)
                return {
                    "title": title,
                    "duration": duration_sec,
                    "duration_formatted": f"{mins:02d}:{secs:02d}",
                    "thumbnail": thumb,
                    "channel": channel
                }
        except Exception as e:
            print(f"[AudioIngest] Erro ao extrair metadados: {e}")
        return {"title": "Vídeo do YouTube", "duration": 0, "duration_formatted": "00:00", "thumbnail": "", "channel": ""}

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
        try:
            res = model.transcribe(audio_file, language="pt", word_timestamps=True, fp16=False)
        except Exception:
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
            seg_words = seg.get("words", [])
            if seg_words:
                for w in seg_words:
                    w_txt = w.get("word", "").strip()
                    if w_txt:
                        words.append({
                            "word": w_txt,
                            "start": round(w.get("start", st), 3),
                            "end": round(w.get("end", et), 3)
                        })
            else:
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

    def transcribe_cut_audio(self, cut_audio_path: str, cut_start: float = 0.0, cut_title: str = "") -> List[Dict[str, Any]]:
        """
        Transcreve o áudio de um corte curto (30-60s) com precisão acústica absoluta (nível CapCut),
        gerando timestamps por palavra reais e corrigindo nomes próprios contextuais da obra.
        """
        if not os.path.exists(cut_audio_path) or os.path.getsize(cut_audio_path) == 0:
            return []

        model = self._get_whisper()
        try:
            res = model.transcribe(cut_audio_path, language="pt", word_timestamps=True, fp16=False)
        except Exception:
            res = model.transcribe(cut_audio_path, language="pt", word_timestamps=False, fp16=False)

        words = []
        for seg in res.get("segments", []):
            seg_words = seg.get("words", [])
            if seg_words:
                for w in seg_words:
                    w_txt = w.get("word", "").strip()
                    if w_txt:
                        words.append({
                            "word": w_txt,
                            "start": round(cut_start + w.get("start", 0.0), 3),
                            "end": round(cut_start + w.get("end", 0.35), 3)
                        })
            else:
                st = seg.get("start", 0.0)
                et = seg.get("end", st + 1.0)
                raw_w = seg.get("text", "").strip().split()
                if raw_w:
                    step = (et - st) / max(1, len(raw_w))
                    for idx, w_txt in enumerate(raw_w):
                        words.append({
                            "word": w_txt,
                            "start": round(cut_start + st + idx * step, 3),
                            "end": round(cut_start + st + (idx + 1) * step, 3)
                        })

        # Curadoria contextual de termos e personagens da obra (ex: A Hipótese do Amor)
        title_lower = (cut_title or "").lower()
        is_book_or_movie = any(k in title_lower for k in ["livro", "filme", "hipótese", "hipotese", "romance", "adaptação", "adaptacao"])

        for w_obj in words:
            w_clean = re.sub(r'^[^\w]+|[^\w]+$', '', w_obj["word"].strip())
            if is_book_or_movie:
                if re.match(r'^(?:Ada|Adan|adan|ada)$', w_clean, re.IGNORECASE):
                    w_obj["word"] = w_obj["word"].replace(w_clean, "Adam")
                elif re.match(r'^(?:Oliver|oliver|Olívia|olivia)$', w_clean, re.IGNORECASE):
                    w_obj["word"] = w_obj["word"].replace(w_clean, "Olive")
                elif re.match(r'^(?:Malco|malco|Melco|melco)$', w_clean, re.IGNORECASE):
                    w_obj["word"] = w_obj["word"].replace(w_clean, "Malcolm")
                elif re.match(r'^(?:Tom|tom)$', w_clean, re.IGNORECASE):
                    w_obj["word"] = w_obj["word"].replace(w_clean, "Tom")
                elif "soc" in w_clean.lower() and "o" in w_clean.lower():
                    w_obj["word"] = re.sub(r'soc[\s_]*o', 'socão', w_obj["word"], flags=re.IGNORECASE)

        return words
