"use client";

import { Box, Text, VStack } from "@chakra-ui/react";
import ReactMarkdown from "react-markdown";
import type { ToolResult } from "@/lib/api";
import { ToolResultRenderer } from "./ToolResultRenderer";

interface MessageBubbleProps {
  role: string;
  content: string;
  toolResults?: ToolResult[];
  onAddToCart?: (bookId: string) => void;
  onRemoveFromCart?: (bookId: string) => void;
  onCheckout?: () => void;
}

export function MessageBubble({
  role,
  content,
  toolResults,
  onAddToCart,
  onRemoveFromCart,
  onCheckout,
}: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <Box
      alignSelf={isUser ? "flex-end" : "flex-start"}
      maxW={isUser ? "80%" : "95%"}
      w={isUser ? undefined : "full"}
    >
      <Box
        bg={isUser ? "blue.50" : "gray.50"}
        _dark={{
          bg: isUser ? "blue.900" : "gray.800",
        }}
        px="4"
        py="3"
        borderRadius="lg"
      >
        <Text textStyle="xs" fontWeight="bold" color="fg.muted" mb="1">
          {isUser ? "You" : "Book Agent"}
        </Text>
        {isUser ? (
          <Text textStyle="sm" whiteSpace="pre-wrap">
            {content}
          </Text>
        ) : (
          <Box textStyle="sm" className="markdown-content">
            <ReactMarkdown>{content}</ReactMarkdown>
          </Box>
        )}
      </Box>

      {toolResults && toolResults.length > 0 && (
        <VStack gap="2" mt="2" align="stretch">
          {toolResults.map((result) => (
            <ToolResultRenderer
              key={result.tool_use_id}
              result={result}
              onAddToCart={onAddToCart}
              onRemoveFromCart={onRemoveFromCart}
              onCheckout={onCheckout}
            />
          ))}
        </VStack>
      )}
    </Box>
  );
}
