export type ChatRole = "user" | "assistant";

export type Citation = {
  title: string;
  article: string;
  excerpt: string;
};

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  citations?: Citation[];
  attachments?: ChatAttachment[];
};

export type ChatAttachment = {
  name: string;
  contentType: string;
  data: string;
};

export type ChatRequest = {
  session_id: string;
  message: string;
};

export type ChatResponse = {
  reply: string;
  citations?: Citation[];
  attachments?: ChatAttachment[];
};
