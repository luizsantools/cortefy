/**
 * Cortefy.net — Cloudflare Worker Edge API
 * Orquestrador na borda global para o SaaS Cortefy
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // 1. Rota de Saúde & Status
    if (url.pathname === "/api/health") {
      return new Response(JSON.stringify({
        status: "online",
        service: "Cortefy.net Edge Network",
        edge_region: request.cf?.colo || "global",
        saas_ready: true,
        r2_connected: Boolean(env.CORTEFY_MEDIA),
        d1_connected: Boolean(env.DB)
      }), {
        headers: { "Content-Type": "application/json" }
      });
    }

    // 2. Rota de Análise de Vídeo
    if (url.pathname === "/api/project/analyze" && request.method === "POST") {
      try {
        const body = await request.json();
        // Em produção, o worker valida créditos do usuário no D1 e despacha para o pipeline de IA
        return new Response(JSON.stringify({
          task_id: "edge_" + crypto.randomUUID().slice(0, 8),
          message: "Vídeo recebido pela borda da Cloudflare."
        }), {
          headers: { "Content-Type": "application/json" }
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: "Requisição inválida" }), { status: 400 });
      }
    }

    // 3. Fallback: Entrega os arquivos estáticos do Frontend (HTML, CSS, JS) via ASSETS
    return env.ASSETS.fetch(request);
  }
};
