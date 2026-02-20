"use client";

import { useState, useCallback } from "react";
import { Box, Collapsible, HStack, Text, VStack } from "@chakra-ui/react";
import { LuChevronDown, LuChevronRight, LuWrench } from "react-icons/lu";
import ReactMarkdown from "react-markdown";
import type { ToolResult, ToolCallData } from "@/lib/api";
import { ToolResultRenderer } from "./ToolResultRenderer";
import { ToolCallDisplay } from "./ToolCallDisplay";

interface MessageBubbleProps {
  role: string;
  content: string;
  toolResults?: ToolResult[];
  toolCalls?: ToolCallData[];
  onAddToCart?: (bookId: string) => void;
  onRemoveFromCart?: (bookId: string) => void;
  onCheckout?: () => void;
}

export function MessageBubble({
  role,
  content,
  toolResults,
  toolCalls,
  onAddToCart,
  onRemoveFromCart,
  onCheckout,
}: MessageBubbleProps) {
  const isUser = role === "user";
  const [toolCallsOpen, setToolCallsOpen] = useState(false);
  const [expandedTools, setExpandedTools] = useState<Record<string, boolean>>(
    {}
  );

  const toggleTool = useCallback((toolUseId: string) => {
    setExpandedTools((prev) => ({
      ...prev,
      [toolUseId]: !prev[toolUseId],
    }));
  }, []);

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

      {/* Tool call details (collapsible debug view) */}
      {toolCalls && toolCalls.length > 0 && (
        <Box mt="2">
          <Collapsible.Root
            open={toolCallsOpen}
            onOpenChange={(e) => setToolCallsOpen(e.open)}
          >
            <Collapsible.Trigger asChild>
              <HStack
                as="button"
                gap="1"
                px="2"
                py="1"
                cursor="pointer"
                borderRadius="md"
                _hover={{ bg: "gray.100", _dark: { bg: "gray.700" } }}
              >
                <LuWrench size={12} />
                <Text textStyle="xs" color="fg.muted">
                  {toolCalls.length} tool call{toolCalls.length > 1 ? "s" : ""}
                </Text>
                <Box color="fg.muted">
                  {toolCallsOpen ? (
                    <LuChevronDown size={12} />
                  ) : (
                    <LuChevronRight size={12} />
                  )}
                </Box>
              </HStack>
            </Collapsible.Trigger>
            <Collapsible.Content>
              <VStack gap="1" mt="1" align="stretch">
                {toolCalls.map((tc) => (
                  <ToolCallDisplay
                    key={tc.tool_use_id}
                    toolCall={tc}
                    isExpanded={expandedTools[tc.tool_use_id] ?? false}
                    onToggle={() => toggleTool(tc.tool_use_id)}
                  />
                ))}
              </VStack>
            </Collapsible.Content>
          </Collapsible.Root>
        </Box>
      )}

      {/* Rich tool result cards */}
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
