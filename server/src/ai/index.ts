/**
 * AI client dispatch — mirrors backend/ai.py.
 * Abstracts over Anthropic, OpenAI-compatible, and local (Qwen on 5052).
 */

import OpenAI from "openai"

type Endpoint = "anthropic" | "openai" | "ollama" | "local"

interface Message { role: "user" | "assistant"; content: string }

const DEFAULTS: Record<string, { baseUrl: string; model: string; apiKey: string }> = {
  local:    { baseUrl: "http://localhost:5052/v1", model: "Qwen/Qwen2.5-7B-Instruct", apiKey: "local" },
  ollama:   { baseUrl: "http://localhost:11434/v1", model: "qwen2.5:7b", apiKey: "ollama" },
  openai:   { baseUrl: "https://api.openai.com/v1", model: "gpt-4o-mini", apiKey: "" },
}

export async function callAi(opts: {
  endpoint: Endpoint
  systemPrompt: string
  messages: Message[]
  apiKey?: string
  baseUrl?: string
  model?: string
}): Promise<string> {
  const { endpoint, systemPrompt, messages, apiKey, baseUrl, model } = opts

  if (endpoint === "anthropic") {
    // Dynamic import — @anthropic-ai/sdk is optional; install it if you need the anthropic endpoint
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const Anthropic = ((await import("@anthropic-ai/sdk" as string)) as any).default
    const client = new Anthropic({ apiKey: apiKey ?? process.env.ANTHROPIC_API_KEY })
    const res = await client.messages.create({
      model: model ?? "claude-haiku-4-5-20251001",
      max_tokens: 2048,
      system: systemPrompt,
      messages,
    })
    return (res.content[0] as { text: string }).text
  }

  const defaults = DEFAULTS[endpoint] ?? DEFAULTS.local
  const client = new OpenAI({
    apiKey: apiKey ?? defaults.apiKey,
    baseURL: baseUrl ?? defaults.baseUrl,
  })
  const res = await client.chat.completions.create({
    model: model ?? defaults.model,
    max_tokens: 2048,
    messages: [{ role: "system", content: systemPrompt }, ...messages],
  })
  return res.choices[0].message.content ?? ""
}
