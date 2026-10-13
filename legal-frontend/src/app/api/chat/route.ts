import { NextRequest } from "next/server";
import type { ChatAttachment, ChatRequest, ChatResponse } from "@/lib/types";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const body = (await request.json()) as ChatRequest;

  if (!body.message?.trim()) {
    return Response.json({ error: "请输入咨询问题" }, { status: 400 });
  }

  try {
    const upstream = await fetch(`${BACKEND_URL}/chat/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: body.session_id,
        question: body.message,
      }),
    });

    if (!upstream.body) {
      return Response.json({ error: "后端无响应体" }, { status: 502 });
    }

    const contentType = upstream.headers.get("content-type") || "";

    // ---- 分支 A：上游错误 / 非流式 JSON → 保持原有错误包装与兜底逻辑 ----
    if (!upstream.ok || !contentType.includes("text/event-stream")) {
      const payload = await upstream.json().catch(() => ({}));
      if (!upstream.ok || payload?.success === false) {
        return Response.json(
          {
            error:
              payload?.msg ??
              payload?.message ??
              payload?.detail ??
              "咨询请求失败",
          },
          { status: upstream.ok ? payload?.code || 502 : upstream.status },
        );
      }

      const data = payload?.data ?? payload;
      const reply = typeof data?.reply === "string" ? data.reply : data?.answer ?? "";
      const attachments = isDocumentRequest(body.message)
        ? await generateDocumentAttachments(body.message)
        : [];

      return Response.json({
        reply: attachments.length
          ? `${reply}\n\n我已经根据你刚才提供的内容生成了劳动仲裁申请书，文件在下方，可以直接下载。请在提交前核对事实、金额和证据。`
          : reply,
        citations: Array.isArray(data?.citations) ? data.citations : [],
        attachments,
      } satisfies ChatResponse);
    }

    // ---- 分支 B：SSE 流 → 边读边透传，文本结束后再追加文书附件事件 ----
    const needDocs = isDocumentRequest(body.message);

    const stream = new TransformStream({
      transform(chunk, controller) {
        controller.enqueue(chunk);
      },
      async flush(controller) {
        if (needDocs) {
          try {
            const attachments = await generateDocumentAttachments(body.message);
            if (attachments.length) {
              controller.enqueue(
                new TextEncoder().encode(
                  `data: ${JSON.stringify({ type: "attachments", attachments })}\n\n`
                )
              );
            }
          } catch {
            // 附件生成失败不影响已输出的文本
          }
        }
      },
    });

    return new Response(upstream.body.pipeThrough(stream), {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
      },
    });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "无法连接法律咨询后端" },
      { status: 502 },
    );
  }
}

function isDocumentRequest(message: string): boolean {
  return /生成\s*(劳动仲裁|仲裁申请书|仲裁文书)|劳动仲裁.*(生成|申请书)|仲裁申请书/.test(message);
}

function buildDocumentPayload(message: string) {
  return {
    applicant: "待补充申请人",
    respondent: "待补充被申请人",
    province: "全国",
    issue_type: "labor_dispute",
    template_type: "general",
    case_name: "劳动争议仲裁申请书",
    labor_relationship: "请根据用户聊天内容补充劳动关系和用工情况。",
    arbitration_requests: message.trim(),
    facts_and_reasons: message.trim(),
    legal_basis: "依据《劳动争议调解仲裁法》《劳动合同法》及相关规定提出仲裁请求。",
    evidence_list: "请补充劳动合同、工资流水、考勤记录、聊天记录、解除通知等证据。",
    disclaimer: "本文件由 AI 辅助生成，不构成律师执业意见，提交前请核对并咨询专业律师。",
  };
}

async function generateDocumentAttachments(message: string): Promise<ChatAttachment[]> {
  const payload = JSON.stringify(buildDocumentPayload(message));
  const formats = [
    {
      endpoint: "/arbitration/document/download",
      name: "劳动争议仲裁申请书.docx",
      contentType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
    {
      endpoint: "/arbitration/document/download/pdf",
      name: "劳动争议仲裁申请书.pdf",
      contentType: "application/pdf",
    },
  ];

  const attachments = await Promise.all(
    formats.map(async (format) => {
      const response = await fetch(`${BACKEND_URL}${format.endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payload,
      });
      if (!response.ok) return null;

      const bytes = Buffer.from(await response.arrayBuffer());
      return {
        name: format.name,
        contentType: format.contentType,
        data: bytes.toString("base64"),
      } satisfies ChatAttachment;
    }),
  );

  return attachments.filter((attachment): attachment is ChatAttachment => attachment !== null);
}
