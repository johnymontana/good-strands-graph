const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- Book & Review Types ---

export interface BookData {
  bookId: string;
  title: string;
  averageRating?: number;
  ratingsCount?: number;
  numPages?: number;
  publicationYear?: number;
  imageUrl?: string;
  description?: string;
  format?: string;
  isbn?: string;
  publisher?: string;
  score?: number;
  similarityScore?: number;
  recommendationScore?: number;
}

export interface ReviewData {
  reviewId: string;
  rating: number;
  text: string;
  dateAdded?: string;
  nVotes?: number;
  nComments?: number;
  userId?: string;
}

// --- Commerce Types ---

export interface CartItem {
  bookId: string;
  title: string;
  price: number;
  quantity: number;
  imageUrl?: string;
}

export interface CartData {
  items: CartItem[];
  total: number;
  item_count: number;
  message?: string;
  error?: string;
}

export interface OrderData {
  orderId: string;
  items: CartItem[];
  total: number;
  item_count: number;
  status: string;
  message: string;
}

// --- Tool Result Types ---

export interface ToolResult {
  tool_name: string;
  tool_use_id: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any;
}

// --- API Types ---

export interface ChatResponse {
  response: string;
  session_id: string;
  tool_results: ToolResult[];
}

export interface ConversationMessage {
  role: string;
  content: string;
  timestamp?: string;
}

// --- API Functions ---

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
