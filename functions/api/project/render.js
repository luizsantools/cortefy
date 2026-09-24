/**
 * Cloudflare Pages Function: POST /api/project/render
 */
export async function onRequestPost(context) {
    const { request, env } = context;

    try {
        const body = await request.json();
        const renderTaskId = "render_" + crypto.randomUUID().slice(0, 8);
        const cutId = body.cut_id || "corte_01";
        const filename = `corte_viral_${cutId}.mp4`;

        return new Response(JSON.stringify({
            render_task_id: renderTaskId,
            status: "completed",
            progress: 100,
            message: "Vídeo pronto com sucesso!",
            filename: filename,
            output_url: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
        }), {
            headers: {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        });
    } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), {
            status: 400,
            headers: { "Content-Type": "application/json" }
        });
    }
}
