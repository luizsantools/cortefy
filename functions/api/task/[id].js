/**
 * Cloudflare Pages Function: GET /api/task/:id
 */
export async function onRequestGet(context) {
    const { params } = context;
    const taskId = params.id;

    return new Response(JSON.stringify({
        task_id: taskId,
        status: "completed",
        progress: 100,
        message: "Operação concluída com sucesso!"
    }), {
        headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        }
    });
}
