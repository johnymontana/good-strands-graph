"use client";

import { VStack } from "@chakra-ui/react";
import type { BookData } from "@/lib/api";
import { BookCard } from "./BookCard";

interface BookCardListProps {
  books: BookData[];
  onAddToCart?: (bookId: string) => void;
}

export function BookCardList({ books, onAddToCart }: BookCardListProps) {
  return (
    <VStack gap="2" align="stretch" w="full">
      {books.map((book) => (
        <BookCard key={book.bookId} book={book} onAddToCart={onAddToCart} />
      ))}
    </VStack>
  );
}
