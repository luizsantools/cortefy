import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import re
import random
import time
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class AIDirector:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        self._client = None

    def _get_client(self):
        if self._client is None and self.api_key:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def analyze_virality(self, transcript_segments: List[Dict[str, Any]], video_title: str = "", genre: str = "", batch_index: int = 1, exclude_cuts: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Analisa a transcrição com IA para identificar ganchos psicológicos, calcular o Virality Score (0-100),
        gerar legendas de alta conversão com SEO e sugerir cortes ranqueados.
        """
        if not transcript_segments:
            return []

        genre_instructions = ""
        if genre and genre != "auto":
            genre_map = {
                "podcast": "ESTILO DE CONTEÚDO: Podcast / Entrevista. Priorize diálogos envolventes, histórias pessoais e momentos de debate.",
                "commentary": "ESTILO DE CONTEÚDO: Comentários / Opinião. Priorize opiniões contundentes, reações e tiradas de efeito.",
                "academic": "ESTILO DE CONTEÚDO: Aulas / Dicas. Priorize insights claros, ensinamentos práticos e momentos 'eureka'.",
                "vlog": "ESTILO DE CONTEÚDO: Histórias / Vlogs. Priorize reviravoltas, suspense e storytelling cativante."
            }
            genre_instructions = genre_map.get(genre, f"ESTILO DE CONTEÚDO: {genre}.")

        exclude_instructions = ""
        if exclude_cuts:
            ranges = [f"{c.get('start', 0):.0f}s-{c.get('end', 0):.0f}s" for c in exclude_cuts]
            exclude_instructions = f"IMPORTANTE: Não repita os trechos já utilizados nestes intervalos de tempo: {', '.join(ranges)}. Encontre 5 NOVOS momentos diferentes."

        formatted_transcript = []
        for s in transcript_segments:
            st = s.get("start", 0)
            et = s.get("end", 0)
            txt = s.get("text", s.get("word", "")).strip()
            if txt:
                formatted_transcript.append(f"[{st:.1f}s - {et:.1f}s] {txt}")

        transcript_text = "\n".join(formatted_transcript[:600])

        client = self._get_client()
        if not client:
            return self._heuristic_fallback(transcript_segments, batch_index=batch_index)

        prompt = f"""
Você é um Diretor de Criação e Especialista em Vídeos Virais para TikTok, Instagram Reels e YouTube Shorts.

Analise a transcrição abaixo do vídeo "{video_title or 'Vídeo Selecionado'}":
{genre_instructions}
{exclude_instructions}

TRANSCRIÇÃO:
{transcript_text}

INSTRUÇÕES:
1. Encontre exatamente 5 MELHORES momentos com altíssimo potencial de viralização (duração ideal entre 30 e 70 segundos).
2. Para cada momento, retorne:
   - "title": Título magnético e curioso para prender a atenção.
   - "hook": A primeira frase falada que prende a atenção nos primeiros 3 segundos.
   - "start": Timestamp de início em segundos (float).
   - "end": Timestamp de fim em segundos (float).
   - "virality_score": Nota de 0 a 100 baseada em emoção, surpresa, valor prático ou humor.
   - "tag": Categoria curta (ex: "⚡ Potencial Viral", "🔥 Momento Épico", "💡 Dica de Ouro", "😂 Engraçado", "🏆 Veredito").
   - "caption_seo": Texto completo da legenda para postar no TikTok/Instagram/Shorts. Deve conter um gancho instigante em 1-2 linhas, chamada para ação (CTA) e 8 a 12 hashtags estratégicas relevantes (ex: #foryou #viral #cortes #podcast #shorts #reels).
   - "rationale": Breve justificativa de 1 frase.

Responda ESTRITAMENTE em formato JSON (uma lista com 5 objetos):
[
  {{
    "id": "corte_01",
    "title": "...",
    "hook": "...",
    "start": 12.0,
    "end": 52.0,
    "virality_score": 97,
    "tag": "⚡ Potencial Viral",
    "caption_seo": "Você teria a mesma reação? 👀 Veja até o final e me diga nos comentários!\n\nSalva esse vídeo para não esquecer.\n\n#cortes #viral #podcast #shorts #reels #foryou #foryoupage #tiktokbrasil",
    "rationale": "Ritmo acelerado e quebra de expectativa no gancho."
  }}
]
"""
        models_to_try = ["gemini-3.5-flash-lite", self.model_name, "gemini-3.6-flash"]

        def _call_model():
            for candidate_model in models_to_try:
                try:
                    response = client.models.generate_content(
                        model=candidate_model,
                        contents=prompt
                    )
                    raw_text = response.text.strip()
                    if raw_text.startswith("```"):
                        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                        raw_text = re.sub(r"\s*```$", "", raw_text)

                    cuts = json.loads(raw_text, strict=False)
                    if isinstance(cuts, list) and len(cuts) > 0:
                        cuts.sort(key=lambda x: x.get("virality_score", 0), reverse=True)
                        start_id = (batch_index - 1) * 5 + 1
                        for idx, c in enumerate(cuts, start_id):
                            c["id"] = f"corte_{idx:02d}"
                            if "caption_seo" not in c or not c["caption_seo"]:
                                c["caption_seo"] = f"{c.get('title', 'Corte Viral')} 🔥\n\nO que você achou desse momento? Comente aqui embaixo!\n\n#foryou #viral #cortes #shorts #reels #podcast"
                        return cuts[:5]
                except Exception as e:
                    print(f"[AIDirector] Candidato {candidate_model} falhou: {str(e)[:100]}")
            return None

        # Executa chamada com timeout de 14 segundos sem bloquear no shutdown
        import concurrent.futures
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_call_model)
        try:
            result = future.result(timeout=14.0)
            if result:
                executor.shutdown(wait=False)
                return result
        except concurrent.futures.TimeoutError:
            print("[AIDirector] API demorou mais de 14s, ativando inteligência de cortes relâmpago.")
        except Exception as e:
            print(f"[AIDirector] Erro geral na chamada: {e}")
        finally:
            try:
                executor.shutdown(wait=False)
            except Exception:
                pass

        return self._heuristic_fallback(transcript_segments, video_title=video_title, batch_index=batch_index, exclude_cuts=exclude_cuts)

    def _heuristic_fallback(self, segments: List[Dict[str, Any]], video_title: str = "", batch_index: int = 1, exclude_cuts: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Gerador inteligente e ultra-rápido de cortes virais a partir das frases reais do vídeo (0.01s)."""
        if not segments:
            return []

        total_duration = segments[-1].get("end", 60.0)
        exclude_ranges = []
        if exclude_cuts:
            for c in exclude_cuts:
                exclude_ranges.append((c.get("start", 0), c.get("end", 0)))

        # Escaneia o vídeo procurando blocos de 35 a 65 segundos com alta densidade de fala
        candidates = []
        step_stride = max(1, len(segments) // 25)
        for i in range(0, len(segments), step_stride):
            start_seg = segments[i]
            start_time = start_seg.get("start", 0)

            # Acumula até 45s à frente
            j = i
            accumulated_text = []
            while j < len(segments) and (segments[j].get("end", 0) - start_time) < 45.0:
                txt = segments[j].get("text", segments[j].get("word", "")).strip()
                if txt:
                    accumulated_text.append(txt)
                j += 1

            if j < len(segments):
                end_time = segments[j].get("end", start_time + 40.0)
                duration = end_time - start_time
                if 30.0 <= duration <= 75.0:
                    full_text = " ".join(accumulated_text)

                    # Verifica se colide com cortes anteriores
                    overlap = False
                    for es, ee in exclude_ranges:
                        if not (end_time < es or start_time > ee):
                            overlap = True
                            break

                    if not overlap and len(full_text.split()) >= 20:
                        words_count = len(full_text.split())
                        wpm = (words_count / duration) * 60
                        score = min(99, int(75 + min(20, wpm / 10) + (4 if "?" in full_text else 0) + (3 if "!" in full_text else 0)))

                        # Extrai gancho dos primeiros 3 segundos
                        sentences = re.split(r'[.!?]', full_text)
                        first_sentence = sentences[0].strip() if sentences else ""
                        hook = first_sentence if len(first_sentence) > 10 else " ".join(full_text.split()[:10]) + "..."

                        candidates.append({
                            "start": round(start_time, 1),
                            "end": round(end_time, 1),
                            "duration": round(duration, 1),
                            "text": full_text,
                            "hook": hook,
                            "score": score
                        })

        # Ordena candidatos por pontuação viral
        candidates.sort(key=lambda x: x["score"], reverse=True)
        selected = []
        for cand in candidates:
            if len(selected) >= 5:
                break
            if any(abs(cand["start"] - s["start"]) < 25.0 for s in selected):
                continue
            selected.append(cand)

        # Se necessário, preenche com posições proporcionais
        step = total_duration / 6.0
        while len(selected) < 5:
            idx = len(selected)
            s_time = max(5.0, idx * step)
            e_time = min(total_duration, s_time + 40.0)
            selected.append({
                "start": round(s_time, 1),
                "end": round(e_time, 1),
                "duration": round(e_time - s_time, 1),
                "text": "Trecho com alto potencial de engajamento.",
                "hook": "Preste muita atenção no que acontece aqui...",
                "score": 88 - idx * 2
            })

        tags = ["⚡ Potencial Viral", "🔥 Momento Épico", "💡 Dica de Ouro", "😮 Revelação", "🏆 Veredito"]
        cuts = []
        start_id = (batch_index - 1) * 5 + 1

        for idx, item in enumerate(selected):
            cid = f"corte_{start_id + idx:02d}"
            hook = item["hook"]
            clean_title = re.sub(r'^[^\w]+', '', hook)[:50].strip()
            if len(clean_title) < 15:
                clean_title = f"{video_title or 'Momento Viral'} - Destaque #{idx+1}"

            cuts.append({
                "id": cid,
                "title": clean_title,
                "hook": hook,
                "start": item["start"],
                "end": item["end"],
                "virality_score": item["score"],
                "tag": tags[idx % len(tags)],
                "caption_seo": f"{clean_title} 👀\n\n{hook}\n\nO que você achou dessa parte? Comente aqui embaixo e salva esse vídeo!\n\n#foryou #viral #cortes #podcast #shorts #reels #explore",
                "rationale": f"Ritmo dinâmico de fala com {int(item['duration'])}s de duração e gancho forte."
            })

        cuts.sort(key=lambda x: x["virality_score"], reverse=True)
        return cuts

    def analyze_audio_directly(self, audio_path: str, video_title: str = "", genre: str = "") -> List[Dict[str, Any]]:
        """
        Envia o áudio diretamente para o Gemini 3.6 Flash na nuvem.
        Processa até 1 hora de áudio em menos de 20 segundos!
        """
        client = self._get_client()
        if not client or not os.path.exists(audio_path):
            return []

        genre_instructions = ""
        if genre and genre != "auto":
            genre_map = {
                "podcast": "ESTILO DE CONTEÚDO: Podcast / Entrevista. Priorize diálogos envolventes, histórias pessoais e momentos de debate.",
                "commentary": "ESTILO DE CONTEÚDO: Comentários / Opinião. Priorize opiniões contundentes, reações e tiradas de efeito.",
                "academic": "ESTILO DE CONTEÚDO: Aulas / Dicas. Priorize insights claros, ensinamentos práticos e momentos 'eureka'.",
                "vlog": "ESTILO DE CONTEÚDO: Histórias / Vlogs. Priorize reviravoltas, suspense e storytelling cativante."
            }
            genre_instructions = genre_map.get(genre, f"ESTILO DE CONTEÚDO: {genre}.")

        prompt = f"""
Você é um Diretor de Criação e Especialista em Vídeos Virais para TikTok, Instagram Reels e YouTube Shorts.
Ouça com atenção este áudio do vídeo "{video_title or 'Conversa / Review'}".
{genre_instructions}

Identifique os 4 a 6 MELHORES momentos (com duração entre 30 e 70 segundos) com altíssimo potencial de prender a atenção.
Para cada corte, retorne:
- "title": Título irresistível em português, simples e chamativo (sem clickbait falso).
- "hook": A primeira frase de abertura dos primeiros 3 segundos.
- "start": Segundo de início exato (float, ex: 69.0).
- "end": Segundo de término exato (float, ex: 112.0).
- "virality_score": Nota de 0 a 100 baseada na emoção, humor ou intensidade.
- "tag": Categoria (ex: "😂 Engraçado", "🔥 Momento Épico", "💡 Dica de Ouro", "😮 Reação Marcante", "🏆 Veredito").
- "rationale": Breve justificativa de 1 frase.

Responda ESTRITAMENTE em formato JSON (uma lista de objetos):
[
  {{
    "id": "corte_01",
    "title": "...",
    "hook": "...",
    "start": 69.0,
    "end": 112.0,
    "virality_score": 96,
    "tag": "🔥 Destaque"
  }}
]
"""
        try:
            print("[AIDirector] Enviando áudio leve para análise direta no Gemini...")
            audio_file = client.files.upload(file=audio_path)
            
            res = None
            for attempt in range(3):
                try:
                    res = client.models.generate_content(
                        model=self.model_name,
                        contents=[audio_file, prompt]
                    )
                    break
                except Exception as e:
                    if attempt < 2 and ("503" in str(e) or "UNAVAILABLE" in str(e)):
                        import time
                        time.sleep(2.0)
                        continue
                    raise e

            raw_text = res.text.strip() if res else ""
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)

            cuts = json.loads(raw_text)
            if isinstance(cuts, list) and len(cuts) > 0:
                cuts.sort(key=lambda x: x.get("virality_score", 0), reverse=True)
                for idx, c in enumerate(cuts, 1):
                    c["id"] = f"corte_{idx:02d}"
                    if "caption_seo" not in c or not c["caption_seo"]:
                        c["caption_seo"] = f"{c.get('title', 'Corte Viral')} 🔥\n\nO que você achou desse momento? Comente aqui embaixo!\n\n#foryou #viral #cortes #shorts #reels #podcast"
                return cuts[:5]
        except Exception as e:
            print(f"[AIDirector] Erro no processamento de áudio direto com Gemini: {e}")

        return []
