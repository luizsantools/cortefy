/**
 * Cloudflare Pages Function: GET /api/health
 */
export async function onRequestGet(context) {
    const { request, env } = context;
    const hasGemini = Boolean(env.GEMINI_API_KEY);

    return new Response(JSON.stringify({
        status: "online",
        service: "Cortefy Cloudflare Pages Full-Stack",
        edge_region: request.cf?.colo || "global",
        gemini_ready: hasGemini,
        r2_connected: Boolean(env.CORTEFY_MEDIA),
        d1_connected: Boolean(env.DB),
        saas_version: "2.5.0",
        timestamp: Date.now()
    }), {
        headers: {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*"
        }
    });
}
