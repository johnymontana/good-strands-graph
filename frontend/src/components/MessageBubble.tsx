"use client";

import { Box, Text } from "@chakra-ui/react";

interface MessageBubbleProps {
  role: string;
  content: string;
}

export function MessageBubble({ role, content }: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <Box
      alignSelf={isUser ? "flex-end" : "flex-start"}
      maxW="80%"
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
      <Text textStyle="sm" whiteSpace="pre-wrap">
        {content}
      </Text>
    </Box>
  );
}
