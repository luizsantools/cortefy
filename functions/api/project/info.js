/**
 * Cloudflare Pages Function: GET /api/project/info?url=...
 * Obtém metadados instantâneos do YouTube na borda da Cloudflare
 */
export async function onRequestGet(context) {
    const { request } = context;
    const urlObj = new URL(request.url);
    const targetUrl = urlObj.searchParams.get("url") || "";

    if (!targetUrl) {
        return new Response(JSON.stringify({ error: "Parâmetro 'url' é obrigatório" }), {
            status: 400,
            headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }
        });
    }

    try {
        // Usa a API oEmbed pública do YouTube para obter título, canal e miniatura em alta resolução
        const oembedRes = await fetch(`https://www.youtube.com/oembed?url=${encodeURIComponent(targetUrl)}&format=json`);
        
        let title = "Vídeo do YouTube";
        let channel = "";
        let thumbnail = "";

        if (oembedRes.ok) {
            const data = await oembedRes.json();
            title = data.title || title;
            channel = data.author_name || channel;
            thumbnail = data.thumbnail_url || thumbnail;
        }

        // Extrai o ID do vídeo para construir a melhor miniatura possível
        const match = targetUrl.match(/(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/i);
        const videoId = match ? match[1] : "";
        if (videoId && !thumbnail) {
            thumbnail = `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;
        }

        return new Response(JSON.stringify({
            title: title,
            channel: channel,
            thumbnail: thumbnail,
            video_id: videoId,
            duration: 0,
            duration_formatted: ""
        }), {
            headers: {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600"
            }
        });
    } catch (err) {
        return new Response(JSON.stringify({
            title: "Vídeo do YouTube",
            channel: "",
            thumbnail: "",
            error: err.message
        }), {
            status: 200,
            headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }
        });
    }
}
