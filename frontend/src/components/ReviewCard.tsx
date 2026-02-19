"use client";

import { Box, Card, HStack, Text } from "@chakra-ui/react";
import { LuStar, LuThumbsUp, LuMessageCircle } from "react-icons/lu";
import type { ReviewData } from "@/lib/api";

interface ReviewCardProps {
  review: ReviewData;
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return "";
  try {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}

export function ReviewCard({ review }: ReviewCardProps) {
  return (
    <Card.Root size="sm" variant="subtle">
      <Card.Body gap="1">
        <HStack justify="space-between">
          <HStack gap="1">
            {Array.from({ length: 5 }).map((_, i) => (
              <LuStar
                key={i}
                size={12}
                fill={i < review.rating ? "orange" : "none"}
                color={i < review.rating ? "orange" : "gray"}
              />
            ))}
            {review.rating > 0 && (
              <Text textStyle="xs" fontWeight="medium" ml="1">
                {review.rating}/5
              </Text>
            )}
          </HStack>
          {review.dateAdded && (
            <Text textStyle="xs" color="fg.muted">
              {formatDate(review.dateAdded)}
            </Text>
          )}
        </HStack>

        <Box mt="1">
          <Text textStyle="xs" lineClamp={4}>
            {review.text}
          </Text>
        </Box>

        <HStack gap="3" mt="1">
          {review.nVotes != null && review.nVotes > 0 && (
            <HStack gap="0.5">
              <LuThumbsUp size={10} />
              <Text textStyle="xs" color="fg.muted">
                {review.nVotes} helpful
              </Text>
            </HStack>
          )}
          {review.nComments != null && review.nComments > 0 && (
            <HStack gap="0.5">
              <LuMessageCircle size={10} />
              <Text textStyle="xs" color="fg.muted">
                {review.nComments} comments
              </Text>
            </HStack>
          )}
        </HStack>
      </Card.Body>
    </Card.Root>
  );
}
