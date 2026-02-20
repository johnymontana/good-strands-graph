"use client";

import { useEffect, useRef, useState } from "react";
import {
  Box,
  Button,
  Container,
  Heading,
  HStack,
  Input,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import { sendMessage } from "@/lib/api";
import type { ToolResult, ToolCallData } from "@/lib/api";
import { MessageBubble } from "./MessageBubble";
import { AgentConfigPanel } from "./AgentConfigPanel";

interface Message {
  role: string;
  content: string;
  toolResults?: ToolResult[];
  toolCalls?: ToolCallData[];
}

function generateSessionId(): string {
  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(generateSessionId);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSendText(text: string) {
    if (!text.trim() || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      const res = await sendMessage(text, sessionId);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.response,
          toolResults: res.tool_results,
          toolCalls: res.tool_calls,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error: ${err instanceof Error ? err.message : "Something went wrong"}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleSend() {
    handleSendText(input.trim());
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleAddToCart(bookId: string) {
    handleSendText(`Add book ${bookId} to my cart`);
  }

  function handleRemoveFromCart(bookId: string) {
    handleSendText(`Remove book ${bookId} from my cart`);
  }

  function handleCheckout() {
    handleSendText("I'd like to checkout and complete my purchase");
  }

  return (
    <Container maxW="3xl" h="100vh" py="4">
      <VStack h="full" gap="4">
        {/* Header */}
        <Box textAlign="center">
          <Heading size="lg">Good Strands Graph</Heading>
          <Text textStyle="sm" color="fg.muted">
            AI-powered book recommendations &amp; shopping
          </Text>
        </Box>

        {/* Agent config panel */}
        <AgentConfigPanel />

        {/* Messages area */}
        <Box
          flex="1"
          w="full"
          overflowY="auto"
          borderWidth="1px"
          borderRadius="lg"
          p="4"
        >
          <VStack gap="3" align="stretch">
            {messages.length === 0 && (
              <Box textAlign="center" py="12">
                <Text color="fg.muted" textStyle="lg">
                  Ask me for book recommendations!
                </Text>
                <Text color="fg.muted" textStyle="sm" mt="2">
                  Try: &quot;Show me popular books&quot; or &quot;Find books
                  about space exploration&quot;
                </Text>
              </Box>
            )}
            {messages.map((msg, i) => (
              <MessageBubble
                key={i}
                role={msg.role}
                content={msg.content}
                toolResults={msg.toolResults}
                toolCalls={msg.toolCalls}
                onAddToCart={handleAddToCart}
                onRemoveFromCart={handleRemoveFromCart}
                onCheckout={handleCheckout}
              />
            ))}
            {loading && (
              <HStack alignSelf="flex-start" gap="2" px="4" py="3">
                <Spinner size="sm" />
                <Text textStyle="sm" color="fg.muted">
                  Thinking...
                </Text>
              </HStack>
            )}
            <div ref={messagesEndRef} />
          </VStack>
        </Box>

        {/* Input area */}
        <HStack w="full" gap="2">
          <Input
            flex="1"
            placeholder="Search for books, ask for recommendations, or manage your cart..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <Button onClick={handleSend} disabled={loading || !input.trim()}>
            Send
          </Button>
        </HStack>
      </VStack>
    </Container>
  );
}
