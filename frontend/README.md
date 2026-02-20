# Good Strands Graph — Frontend

Next.js 16 (App Router) + Chakra UI v3 chat interface with rich tool result cards for book discovery, reviews, and a simulated purchase flow.

## Getting Started

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The frontend talks to the FastAPI backend at `http://localhost:8000` (configurable via `NEXT_PUBLIC_API_URL`).

## Tech Stack

- **Next.js 16** (App Router) — React 19, Turbopack
- **Chakra UI v3** — component library with dark mode support via `next-themes`
- **react-markdown** — renders agent text responses with markdown formatting
- **react-icons** — icons for star ratings, cart, and UI elements
- **TypeScript** — full type coverage for API responses and component props

## Component Architecture

```
ChatInterface
  ├── AgentConfigPanel                          (collapsible agent config + tools)
  └── MessageBubble
        ├── ReactMarkdown (agent text)
        ├── ToolCallDisplay[]                   (collapsible tool call inspector)
        └── ToolResultRenderer (dispatches by tool_name)
              ├── BookCardList → BookCard[]     (search, popular, similar, recommended)
              ├── BookDetailCard                (single book details)
              ├── ReviewList → ReviewCard[]     (book reviews)
              ├── CartDisplay                   (shopping cart)
              └── OrderConfirmation             (checkout success)
```

### Components

| Component | File | Description |
|-----------|------|-------------|
| `ChatInterface` | `src/components/ChatInterface.tsx` | Main chat UI. Manages messages, session, loading state. Includes `AgentConfigPanel`. Provides `onAddToCart`, `onRemoveFromCart`, `onCheckout` callbacks. |
| `AgentConfigPanel` | `src/components/AgentConfigPanel.tsx` | Collapsible accordion showing model ID, system prompt, and all tools grouped by category. Fetches from `GET /api/chat/config`. |
| `MessageBubble` | `src/components/MessageBubble.tsx` | Renders a single message. User messages as plain text, assistant messages as markdown + collapsible tool calls + tool result cards. |
| `ToolCallDisplay` | `src/components/ToolCallDisplay.tsx` | Single tool call inspector: tool name, status badge (ok/error), input args preview, expandable full input/result JSON. Filters `tool_context`. |
| `ToolResultRenderer` | `src/components/ToolResultRenderer.tsx` | Dispatches a `ToolResult` to the correct card component based on `tool_name`. |
| `BookCard` | `src/components/BookCard.tsx` | Compact horizontal card: cover image, title, publisher, star rating, description snippet, format/year badges, price, "Add to Cart" button. |
| `BookCardList` | `src/components/BookCardList.tsx` | Vertical stack of `BookCard` components for list results. |
| `BookDetailCard` | `src/components/BookDetailCard.tsx` | Expanded book view: full description, all metadata (ISBN, language, format), review stats, Goodreads link, price, purchase button. |
| `ReviewCard` | `src/components/ReviewCard.tsx` | Single review: 5-star visual rating, review text (4-line clamp), helpful votes, comment count, date. |
| `ReviewList` | `src/components/ReviewList.tsx` | List of `ReviewCard` components with count header. |
| `CartDisplay` | `src/components/CartDisplay.tsx` | Shopping cart: item list with thumbnails/prices/remove buttons, total, checkout button. Handles empty and error states. |
| `OrderConfirmation` | `src/components/OrderConfirmation.tsx` | Post-checkout success: order ID, item summary, total charged. Green-themed success card. |

### Tool → Component Mapping

| `tool_name` | Component |
|-------------|-----------|
| `search_books`, `get_popular_books`, `find_similar_books`, `get_books_by_publisher`, `get_recommended_books` | `BookCardList` |
| `get_book_details` | `BookDetailCard` |
| `get_book_reviews` | `ReviewList` |
| `add_to_cart`, `get_cart`, `remove_from_cart` | `CartDisplay` |
| `checkout` | `OrderConfirmation` |

## API Client

`src/lib/api.ts` contains all TypeScript interfaces and API functions:

- **`BookData`** — book properties from Neo4j (bookId, title, averageRating, format, publisher, etc.)
- **`ReviewData`** — review with rating, text, votes, dates
- **`CartItem`**, **`CartData`** — shopping cart state
- **`OrderData`** — checkout confirmation
- **`ToolResult`** — `{tool_name, tool_use_id, data}` from the backend
- **`ToolCallData`** — `{tool_use_id, tool_name, input, result, status}` for tool call transparency
- **`ToolInfo`**, **`AgentConfig`** — agent configuration (model, system prompt, tools)
- **`ChatResponse`** — `{response, session_id, tool_results[], tool_calls[]}`
- **`sendMessage(message, sessionId)`** — `POST /api/chat`
- **`getAgentConfig()`** — `GET /api/chat/config`
- **`getHistory(sessionId)`** — `GET /api/chat/history/{sessionId}`

## Purchase Flow

The purchase experience is driven entirely through the chat interface:

1. User browses books → `BookCard` with "Add to Cart" button
2. Click "Add to Cart" → sends message to agent → agent calls `add_to_cart` tool → `CartDisplay` renders
3. User says "checkout" → agent calls `checkout` tool → `OrderConfirmation` renders
4. Cart actions (remove, view) work the same way — user actions become agent messages

Prices are deterministically generated from `bookId` hash (Hardcover ~$25, Paperback ~$15, ebook ~$10).

## Chakra UI v3 Snippets

Standard Chakra v3 snippet files in `src/components/ui/`:

- `provider.tsx` — wraps `ChakraProvider` with `ColorModeProvider` (loaded via `next/dynamic` with `ssr: false` to avoid hydration mismatch)
- `color-mode.tsx` — `useColorMode`, `ColorModeButton`, `LightMode`/`DarkMode`
- `tooltip.tsx` — Tooltip wrapper with portal
- `toaster.tsx` — Toaster with `createToaster` (bottom-end placement)

## Scripts

```bash
npm run dev       # Start development server (port 3000)
npm run build     # Production build
npm run start     # Start production server
npm run lint      # Run ESLint
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

Set in `.env.local` or as an environment variable.
