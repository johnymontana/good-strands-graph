const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ChatResponse {
  response: string;
  session_id: string;
}

export interface ConversationMessage {
  role: string;
  content: string;
  timestamp?: string;
}

export async function sendMessage(
  message: string,
  sessionId: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}

export async function getHistory(
  sessionId: string
): Promise<ConversationMessage[]> {
  const res = await fetch(`${API_BASE}/api/chat/history/${sessionId}`);
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}
