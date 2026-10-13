"use client";

import { FormEvent, KeyboardEvent, useRef, useState } from "react";
import type { ChatMessage } from "@/lib/types";
import { MessageList } from "@/components/MessageList";
import { Composer } from "@/components/Composer";

const STARTERS = [
  "劳动合同到期不续签，有没有经济补偿？",
  "网购商品七天无理由退货，运费谁承担？",
  "房东提前收房，租客可以主张哪些权利？",
];

function createId() {
  return crypto.randomUUID();
}

function buildClarifyingReply(message: string): string {
  const text = message.trim();
  return [
    `我先帮你梳理一下这个问题。为了判断是否适用法律规则，我想先确认 3 个关键点：`,
    "",
    `1. 发生在什么时间、地点？`,
    "2. 具体事实是什么？例如工资、合同、解除关系、赔偿等细节。",
    "3. 你最关心的是责任认定、赔偿金额，还是后续处理方式？",
    "",
    text ? `你现在提的内容是：${text}` : "请先简单描述一下你的情况。",
    "",
    "把这些信息发给我，我能继续给你更准确的判断和建议。",
  ].join("\n");
}

export function ChatApp() {
  const [sessionId, setSessionId] = useState(() => createId());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const hasMessages = messages.length > 0;
  const canSend = draft.trim().length > 0 && !loading;

  async function send(text: string) {
    const content = text.trim();
    if (!content || loading) return;

    const userMessage: ChatMessage = { id: createId(), role: "user", content };
    setMessages((prev) => [...prev, userMessage]);
    setDraft("");
    setError("");
    setLoading(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({ session_id: sessionId, message: content }),
      });

      const contentType = response.headers.get("content-type") || "";

      // ---- 分支 A：非 SSE（老接口/报错 JSON）→ 保持原来一次性渲染 ----
      if (!contentType.includes("text/event-stream")) {
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data?.error || "咨询请求失败");
        }
        setMessages((prev) => [...prev, {
          id: createId(),
          role: "assistant",
          content: typeof data.reply === "string" ? data.reply : buildClarifyingReply(content),
          citations: Array.isArray(data.citations) ? data.citations : [],
          attachments: Array.isArray(data.attachments) ? data.attachments : [],
        }]);
        return;
      }

      // ---- 分支 B：SSE 流式 → 先插入空消息，再逐块填充 ----
      const assistantId = createId();
      setMessages((prev) => [...prev, { id: assistantId, role: "assistant", content: "" }]);

      const reader = response.body!.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let acc = "";
      let citations: any[] = [];
      let attachments: any[] = [];

      let scheduled = false;
      const flush = () => {
        scheduled = false;
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, content: acc } : m))
        );
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";

        for (const evt of events) {
          for (const line of evt.split("\n")) {
            if (!line.startsWith("data:")) continue;
            const payloadStr = line.slice(5).trim();
            if (!payloadStr || payloadStr === "[DONE]") continue;
            let payload: any;
            try {
              payload = JSON.parse(payloadStr);
            } catch {
              continue;
            }
            if (payload.type === "delta" && payload.content) {
              acc += payload.content;
              if (!scheduled) {
                scheduled = true;
                requestAnimationFrame(flush);
              }
            } else if (payload.type === "done") {
              citations = Array.isArray(payload.citations) ? payload.citations : [];
              attachments = Array.isArray(payload.attachments) ? payload.attachments : [];
            } else if (payload.type === "attachments") {
              attachments = Array.isArray(payload.attachments) ? payload.attachments : [];
            }
          }
        }
      }

      if (scheduled) {
        scheduled = false;
        flush();
      }

      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: acc, citations, attachments }
            : m
        )
      );
    } catch (e) {
      // 用户主动中止（点"新会话"）不算错误
      if (controller.signal.aborted) return;
      const fallback: ChatMessage = {
        id: createId(),
        role: "assistant",
        content: buildClarifyingReply(content),
      };
      setMessages((prev) => [...prev, fallback]);
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void send(draft);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send(draft);
    }
  }

  function newChat() {
    abortRef.current?.abort();
    setSessionId(createId());
    setMessages([]);
    setDraft("");
    setError("");
    setLoading(false);
  }

  return (
    <div className="flex min-h-dvh flex-col bg-[#f5f5f5] text-[#111827]">
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#111827] text-sm font-semibold text-white">
              法
            </div>
            <div>
              <div className="text-[10px] font-medium uppercase tracking-[0.28em] text-slate-500">Legal AI</div>
              <div className="font-serif text-xl font-semibold text-slate-900">衡法咨询</div>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-4 py-6 sm:px-6">
        <section className="mb-4 flex items-center justify-between">
          <div className="text-sm text-slate-500">法律咨询助手</div>
          <button
            type="button"
            onClick={newChat}
            className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-slate-300"
          >
            新会话
          </button>
        </section>

        <section className="min-h-0 flex-1 overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-[0_12px_32px_rgba(15,23,42,0.06)]">
          <div className="flex h-full flex-col">
            <div className="flex-1 overflow-y-auto px-4 py-4 sm:px-6">
              {hasMessages ? (
                <MessageList messages={messages} loading={loading} />
              ) : (
                <div className="flex h-full flex-col items-center justify-center text-center">
                  <div className="mb-6 text-4xl">💬</div>
                  <h2 className="mb-2 text-2xl font-semibold text-slate-900">先把关键事实说清楚，我来帮你判断</h2>
                  <p className="max-w-xl text-sm leading-6 text-slate-500">
                    我会先用追问方式确认事实、时间、地点和你最关心的权益，再给出参考意见。
                  </p>
                  <div className="mt-6 grid w-full max-w-2xl gap-2 sm:grid-cols-2">
                    {STARTERS.map((starter) => (
                      <button
                        key={starter}
                        type="button"
                        onClick={() => void send(starter)}
                        className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 text-left text-sm text-slate-700 transition hover:border-slate-300 hover:bg-white"
                      >
                        {starter}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="border-t border-slate-200 bg-white px-4 py-4 sm:px-6">
              {error ? <p className="mb-3 text-sm text-red-600">{error}</p> : null}
              <Composer
                value={draft}
                loading={loading}
                canSend={canSend}
                onChange={setDraft}
                onSubmit={onSubmit}
                onKeyDown={onKeyDown}
              />
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
