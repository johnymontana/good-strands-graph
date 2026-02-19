"use client";

import { Text, VStack } from "@chakra-ui/react";
import type { ReviewData } from "@/lib/api";
import { ReviewCard } from "./ReviewCard";

interface ReviewListProps {
  reviews: ReviewData[];
}

export function ReviewList({ reviews }: ReviewListProps) {
  if (reviews.length === 0) {
    return (
      <Text textStyle="sm" color="fg.muted">
        No reviews available.
      </Text>
    );
  }

  return (
    <VStack gap="2" align="stretch" w="full">
      <Text textStyle="xs" fontWeight="bold" color="fg.muted">
        Reader Reviews ({reviews.length})
      </Text>
      {reviews.map((review) => (
        <ReviewCard key={review.reviewId} review={review} />
      ))}
    </VStack>
  );
}
