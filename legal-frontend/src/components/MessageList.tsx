import type { ChatMessage } from "@/lib/types";

type MessageListProps = {
  messages: ChatMessage[];
  loading: boolean;
};

export function MessageList({ messages, loading }: MessageListProps) {
  return (
    <div className="scrollbar-thin flex-1 overflow-y-auto px-6 py-6">
      <ol className="mx-auto flex max-w-3xl flex-col gap-5">
        {messages.map((message) => (
          <li key={message.id} className={message.role === "user" ? "ml-12" : "mr-8"}>
            <p className="mb-1.5 text-xs tracking-widest text-[var(--muted)]">
              {message.role === "user" ? "你的问题" : "助手回复"}
            </p>
            <div
              className={
                message.role === "user"
                  ? "rounded-2xl rounded-tr-sm bg-[var(--ink)] px-4 py-3 text-[var(--paper)]"
                  : "rounded-2xl rounded-tl-sm bg-white px-4 py-3 shadow-sm"
              }
            >
              <p className="whitespace-pre-wrap text-sm leading-7">{message.content}</p>
              {message.attachments?.length ? (
                <div className="mt-4 space-y-2 border-t border-[var(--line)] pt-3">
                  <p className="text-xs font-medium text-[var(--muted)]">生成文件</p>
                  {message.attachments.map((attachment) => (
                    <a
                      key={attachment.name}
                      href={`data:${attachment.contentType};base64,${attachment.data}`}
                      download={attachment.name}
                      className="flex items-center justify-between rounded-xl border border-[var(--line)] bg-[var(--paper-2)] px-3 py-2 text-sm transition hover:border-[var(--gold)]"
                    >
                      <span className="truncate">{attachment.name}</span>
                      <span className="ml-3 shrink-0 text-xs text-[var(--muted)]">下载</span>
                    </a>
                  ))}
                </div>
              ) : null}
              {message.citations?.length ? (
                <ul className="mt-4 space-y-2 border-t border-[var(--line)] pt-3">
                  {message.citations.map((citation) => (
                    <li key={`${citation.title}-${citation.article}`} className="rounded-xl bg-[var(--paper-2)] px-3 py-2">
                      <p className="text-xs font-medium">
                        《{citation.title}》{citation.article}
                      </p>
                      <p className="mt-1 text-xs leading-5 text-[var(--muted)]">{citation.excerpt}</p>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          </li>
        ))}
        {loading ? (
          <li className="mr-8 text-sm text-[var(--muted)]">正在检索相关规定…</li>
        ) : null}
      </ol>
    </div>
  );
}
