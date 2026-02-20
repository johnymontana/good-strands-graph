"use client";

import { Badge, Box, Code, Collapsible, Flex, HStack, Text } from "@chakra-ui/react";
import { LuChevronDown, LuChevronRight, LuWrench } from "react-icons/lu";
import type { ToolCallData } from "@/lib/api";

function formatArgsPreview(args: Record<string, unknown>): string {
  const entries = Object.entries(args).filter(
    ([key]) => key !== "tool_context"
  );
  if (entries.length === 0) return "";
  const parts = entries.slice(0, 2).map(([key, val]) => {
    const str = typeof val === "string" ? val : JSON.stringify(val);
    const truncated = str.length > 30 ? str.slice(0, 27) + "..." : str;
    return `${key}: ${truncated}`;
  });
  if (entries.length > 2) parts.push("...");
  return parts.join(", ");
}

interface ToolCallDisplayProps {
  toolCall: ToolCallData;
  isExpanded: boolean;
  onToggle: () => void;
}

export function ToolCallDisplay({
  toolCall,
  isExpanded,
  onToggle,
}: ToolCallDisplayProps) {
  const isError = toolCall.status === "error";
  const argsPreview = formatArgsPreview(toolCall.input);

  return (
    <Box borderWidth="1px" borderRadius="md" overflow="hidden">
      <Flex
        as="button"
        onClick={onToggle}
        w="full"
        align="center"
        gap="2"
        px="3"
        py="2"
        bg="gray.50"
        _dark={{ bg: "gray.800" }}
        _hover={{ bg: "gray.100", _dark: { bg: "gray.700" } }}
        cursor="pointer"
        textAlign="left"
      >
        <Box color="fg.muted" flexShrink={0}>
          <LuWrench size={14} />
        </Box>
        <Text textStyle="xs" fontWeight="semibold" flexShrink={0}>
          {toolCall.tool_name}
        </Text>
        <Badge
          size="xs"
          colorPalette={isError ? "red" : "green"}
          variant="subtle"
          flexShrink={0}
        >
          {isError ? "error" : "ok"}
        </Badge>
        {argsPreview && (
          <Text textStyle="xs" color="fg.muted" truncate flex="1">
            {argsPreview}
          </Text>
        )}
        <Box color="fg.muted" flexShrink={0} ml="auto">
          {isExpanded ? (
            <LuChevronDown size={14} />
          ) : (
            <LuChevronRight size={14} />
          )}
        </Box>
      </Flex>

      <Collapsible.Root open={isExpanded}>
        <Collapsible.Content>
          <Box px="3" py="2" borderTopWidth="1px">
            {Object.keys(toolCall.input).filter(k => k !== "tool_context").length > 0 && (
              <Box mb="2">
                <Text textStyle="xs" fontWeight="semibold" color="fg.muted" mb="1">
                  Input
                </Text>
                <Code
                  display="block"
                  whiteSpace="pre-wrap"
                  p="2"
                  borderRadius="sm"
                  textStyle="xs"
                  overflow="auto"
                  maxH="200px"
                >
                  {JSON.stringify(
                    Object.fromEntries(
                      Object.entries(toolCall.input).filter(
                        ([k]) => k !== "tool_context"
                      )
                    ),
                    null,
                    2
                  )}
                </Code>
              </Box>
            )}
            {toolCall.result != null && (
              <Box>
                <Text textStyle="xs" fontWeight="semibold" color="fg.muted" mb="1">
                  Result
                </Text>
                <Code
                  display="block"
                  whiteSpace="pre-wrap"
                  p="2"
                  borderRadius="sm"
                  textStyle="xs"
                  overflow="auto"
                  maxH="300px"
                >
                  {typeof toolCall.result === "string"
                    ? toolCall.result
                    : JSON.stringify(toolCall.result, null, 2)}
                </Code>
              </Box>
            )}
          </Box>
        </Collapsible.Content>
      </Collapsible.Root>
    </Box>
  );
}
