"use client";

import {
  Badge,
  Box,
  Button,
  Card,
  HStack,
  Image,
  Text,
} from "@chakra-ui/react";
import { LuShoppingCart, LuStar } from "react-icons/lu";
import type { BookData } from "@/lib/api";

interface BookCardProps {
  book: BookData;
  onAddToCart?: (bookId: string) => void;
}

function generatePrice(bookId: string): number {
  let hash = 0;
  for (let i = 0; i < bookId.length; i++) {
    hash = (hash << 5) - hash + bookId.charCodeAt(i);
    hash |= 0;
  }
  const base = Math.abs(hash) % 20;
  return 9.99 + base * 0.5;
}

export function BookCard({ book, onAddToCart }: BookCardProps) {
  const rating = book.averageRating ?? 0;
  const hasImage = book.imageUrl && !book.imageUrl.includes("nophoto");
  const price = generatePrice(book.bookId);

  return (
    <Card.Root
      flexDirection="row"
      overflow="hidden"
      maxW="xl"
      size="sm"
      variant="outline"
    >
      {hasImage && (
        <Image
          objectFit="cover"
          maxW="100px"
          minW="100px"
          src={book.imageUrl}
          alt={book.title}
        />
      )}
      <Box flex="1">
        <Card.Body gap="1">
          <Card.Title textStyle="sm">{book.title}</Card.Title>

          {book.publisher && (
            <Text textStyle="xs" color="fg.muted">
              {book.publisher}
            </Text>
          )}

          <HStack gap="2" mt="1">
            <HStack gap="0.5">
              <LuStar size={12} fill="orange" color="orange" />
              <Text textStyle="xs" fontWeight="medium">
                {rating.toFixed(2)}
              </Text>
            </HStack>
            {book.ratingsCount != null && (
              <Text textStyle="xs" color="fg.muted">
                ({book.ratingsCount.toLocaleString()} ratings)
              </Text>
            )}
          </HStack>

          {book.description && (
            <Text textStyle="xs" color="fg.muted" lineClamp={2} mt="1">
              {book.description}
            </Text>
          )}

          <HStack gap="1" mt="1" flexWrap="wrap">
            {book.format && (
              <Badge size="sm" variant="subtle">
                {book.format}
              </Badge>
            )}
            {book.numPages != null && (
              <Badge size="sm" variant="subtle">
                {book.numPages} pages
              </Badge>
            )}
            {book.publicationYear != null && (
              <Badge size="sm" variant="outline">
                {book.publicationYear}
              </Badge>
            )}
          </HStack>
        </Card.Body>
        <Card.Footer gap="2" pt="0">
          <Text textStyle="md" fontWeight="bold" color="green.600">
            ${price.toFixed(2)}
          </Text>
          {onAddToCart && (
            <Button
              size="xs"
              variant="subtle"
              colorPalette="blue"
              onClick={() => onAddToCart(book.bookId)}
            >
              <LuShoppingCart />
              Add to Cart
            </Button>
          )}
        </Card.Footer>
      </Box>
    </Card.Root>
  );
}
