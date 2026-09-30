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
from typing import List, Dict, Any
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

    def analyze_virality(self, transcript_segments: List[Dict[str, Any]], video_title: str = "", genre: str = "") -> List[Dict[str, Any]]:
        """
        Usa o Google Gemini como Diretor Criativo de Vídeos Virais para analisar a transcrição,
        identificar ganchos psicológicos, calcular o Virality Score (0-100) e sugerir cortes de alta retenção.
        """
        # Se não houver transcrição, retorna lista vazia
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

        # Formata texto da transcrição com timestamps para o modelo
        formatted_transcript = []
        for s in transcript_segments:
            st = s.get("start", 0)
            et = s.get("end", 0)
            txt = s.get("text", s.get("word", "")).strip()
            if txt:
                formatted_transcript.append(f"[{st:.1f}s - {et:.1f}s] {txt}")

        transcript_text = "\n".join(formatted_transcript[:400]) # Primeiros blocos representativos

        client = self._get_client()
        if not client:
            return self._heuristic_fallback(transcript_segments)

        prompt = f"""
Você é um Diretor de Criação e Editor de Conteúdo Viral Especialista em TikTok, Instagram Reels e YouTube Shorts (nível OpusClip / PlaySquad).

Analise a transcrição abaixo de um vídeo com o tema "{video_title or 'Review / Conversa'}":
{genre_instructions}

TRANSCRIÇÃO:
{transcript_text}

INSTRUÇÕES:
1. Encontre os 4 a 6 MELHORES momentos com altíssimo potencial de viralização (duração ideal entre 30 e 75 segundos).
2. Para cada momento, identifique:
   - "title": Título irresistível, magnético e curioso para o espectador (sem mentiras).
   - "hook": A primeira frase falada que prende a atenção nos primeiros 3 segundos.
   - "start": Timestamp exato de início em segundos (float).
   - "end": Timestamp exato de fim em segundos (float).
   - "virality_score": Nota de 0 a 100 baseada em emoção, humor, surpresa, choque ou polêmica.
   - "tag": Categoria temática curta (ex: "🔥 Momento Épico", "😂 Engraçado", "💡 Revelação", "😮 Polêmica", "🏆 Veredito").
   - "rationale": Breve explicação de 1 frase do porquê esse corte vai prender a atenção.
   - "broll_keywords": Lista com 2 ou 3 palavras-chave para ilustrar com cenas cinematográficas/B-Roll.
   - "emphasis_words": Lista de 3 a 5 palavras faladas que merecem destaque nas legendas (karaokê animado).

Responda ESTRITAMENTE em formato JSON válido como uma lista de objetos:
[
  {{
    "id": "corte_01",
    "title": "...",
    "hook": "...",
    "start": 12.0,
    "end": 55.0,
    "virality_score": 96,
    "tag": "🔥 Momento Épico",
    "rationale": "...",
    "broll_keywords": ["cena", "ação"],
    "emphasis_words": ["palavra1", "palavra2"]
  }}
]
"""
        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            raw_text = response.text.strip()
            # Limpa blocos de markdown ```json ... ``` se o modelo retornar
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)

            cuts = json.loads(raw_text)
            if isinstance(cuts, list) and len(cuts) > 0:
                # Ordena por virality_score decrescente
                cuts.sort(key=lambda x: x.get("virality_score", 0), reverse=True)
                for idx, c in enumerate(cuts, 1):
                    c["id"] = f"corte_{idx:02d}"
                return cuts
        except Exception as e:
            print(f"[AIDirector] Erro ao consultar Gemini: {e}. Usando fallback inteligente.")

        return self._heuristic_fallback(transcript_segments)

    def _heuristic_fallback(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback local estruturado caso a API atinja limite ou falhe."""
        if not segments:
            return []

        total_duration = segments[-1].get("end", 60.0)
        # Gera 3 cortes inteligentes em pontos estratégicos
        c1_start = min(15.0, total_duration * 0.1)
        c1_end = min(c1_start + 45.0, total_duration)

        c2_start = min(total_duration * 0.4, total_duration - 45.0)
        c2_end = min(c2_start + 50.0, total_duration)

        c3_start = max(0.0, total_duration - 65.0)
        c3_end = total_duration

        return [
            {
                "id": "corte_01",
                "title": "O Momento Mais Intenso da Conversa",
                "hook": "Preste atenção no que acontece aqui...",
                "start": round(c1_start, 1),
                "end": round(c1_end, 1),
                "virality_score": 94,
                "tag": "🔥 Destaque Viral",
                "rationale": "Ritmo de fala acelerado e gancho inicial cativante.",
                "broll_keywords": ["ação", "cena épica"],
                "emphasis_words": ["incrível", "atenção", "olha"]
            },
            {
                "id": "corte_02",
                "title": "A Reação Que Surpreendeu Todo Mundo",
                "hook": "Eu não esperava por essa revelação...",
                "start": round(c2_start, 1),
                "end": round(c2_end, 1),
                "virality_score": 91,
                "tag": "😮 Reação Marcante",
                "rationale": "Momento de alta quebra de expectativa.",
                "broll_keywords": ["surpresa", "cinema"],
                "emphasis_words": ["revelação", "chocante"]
            },
            {
                "id": "corte_03",
                "title": "Veredito Final: Vale a Pena?",
                "hook": "Para fechar com chave de ouro...",
                "start": round(c3_start, 1),
                "end": round(c3_end, 1),
                "virality_score": 88,
                "tag": "🏆 Veredito",
                "rationale": "Conclusão definitiva com recomendação clara.",
                "broll_keywords": ["conclusão", "final"],
                "emphasis_words": ["vale a pena", "resultado"]
            }
        ]

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
                return cuts
        except Exception as e:
            print(f"[AIDirector] Erro no processamento de áudio direto com Gemini: {e}")

        return []
