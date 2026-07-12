const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

type ChatMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};

type ChatRequest = {
  messages?: ChatMessage[];
  prompt?: string;
  model?: string;
  temperature?: number;
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405);
  }

  const apiKey = Deno.env.get("OPENROUTER_API_KEY");
  if (!apiKey) {
    return jsonResponse({ error: "OPENROUTER_API_KEY is not configured" }, 500);
  }

  let body: ChatRequest;
  try {
    body = await req.json();
  } catch {
    return jsonResponse({ error: "Invalid JSON body" }, 400);
  }

  const messages = normalizeMessages(body);
  if (!messages.length) {
    return jsonResponse({ error: "Provide a prompt or a messages array" }, 400);
  }

  const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "HTTP-Referer": Deno.env.get("APP_PUBLIC_URL") ?? "https://patrickeudess.github.io/AfriData-Ready/",
      "X-Title": "AfriData Ready",
    },
    body: JSON.stringify({
      model: body.model ?? "openai/gpt-4o-mini",
      messages,
      temperature: body.temperature ?? 0.2,
    }),
  });

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    return jsonResponse({
      error: "OpenRouter request failed",
      status: response.status,
      details: data,
    }, response.status);
  }

  return jsonResponse({
    answer: data?.choices?.[0]?.message?.content ?? "",
    raw: data,
  });
});

function normalizeMessages(body: ChatRequest): ChatMessage[] {
  if (Array.isArray(body.messages)) {
    return body.messages.filter((message) =>
      message &&
      ["system", "user", "assistant"].includes(message.role) &&
      typeof message.content === "string" &&
      message.content.trim()
    );
  }

  if (typeof body.prompt === "string" && body.prompt.trim()) {
    return [
      {
        role: "system",
        content: "Tu es l'assistant AfriData Ready. Reponds clairement et de facon concise.",
      },
      { role: "user", content: body.prompt.trim() },
    ];
  }

  return [];
}

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      ...corsHeaders,
      "Content-Type": "application/json",
    },
  });
}
