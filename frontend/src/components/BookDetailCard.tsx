"use client";

import {
  Badge,
  Box,
  Button,
  Card,
  HStack,
  Image,
  Separator,
  Text,
  VStack,
} from "@chakra-ui/react";
import { LuShoppingCart, LuStar, LuExternalLink } from "react-icons/lu";
import type { BookData } from "@/lib/api";

interface BookDetailCardProps {
  book: BookData & {
    titleWithoutSeries?: string;
    languageCode?: string;
    isbn13?: string;
    asin?: string;
    kindleAsin?: string;
    isEbook?: boolean;
    link?: string;
    publisherName?: string;
    reviewCount?: number;
    avgUserRating?: number;
    textReviewsCount?: number;
  };
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

export function BookDetailCard({ book, onAddToCart }: BookDetailCardProps) {
  const rating = book.averageRating ?? 0;
  const hasImage = book.imageUrl && !book.imageUrl.includes("nophoto");
  const price = generatePrice(book.bookId);
  const publisher = book.publisher || book.publisherName;

  return (
    <Card.Root overflow="hidden" variant="outline" w="full">
      <Card.Body gap="3">
        <HStack align="start" gap="4">
          {hasImage && (
            <Image
              objectFit="cover"
              maxW="120px"
              minW="120px"
              borderRadius="md"
              src={book.imageUrl}
              alt={book.title}
            />
          )}
          <VStack align="start" gap="1" flex="1">
            <Card.Title textStyle="md">{book.title}</Card.Title>

            {publisher && (
              <Text textStyle="sm" color="fg.muted">
                Published by {publisher}
              </Text>
            )}

            <HStack gap="3" mt="1">
              <HStack gap="0.5">
                <LuStar size={14} fill="orange" color="orange" />
                <Text textStyle="sm" fontWeight="medium">
                  {rating.toFixed(2)}
                </Text>
              </HStack>
              {book.ratingsCount != null && (
                <Text textStyle="xs" color="fg.muted">
                  {book.ratingsCount.toLocaleString()} ratings
                </Text>
              )}
              {book.reviewCount != null && (
                <Text textStyle="xs" color="fg.muted">
                  {book.reviewCount} reviews
                </Text>
              )}
            </HStack>

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
              {book.languageCode && (
                <Badge size="sm" variant="outline">
                  {book.languageCode}
                </Badge>
              )}
              {book.isbn && (
                <Badge size="sm" variant="outline">
                  ISBN: {book.isbn}
                </Badge>
              )}
            </HStack>

            <HStack gap="3" mt="2">
              <Text textStyle="xl" fontWeight="bold" color="green.600">
                ${price.toFixed(2)}
              </Text>
              {onAddToCart && (
                <Button
                  size="sm"
                  colorPalette="blue"
                  onClick={() => onAddToCart(book.bookId)}
                >
                  <LuShoppingCart />
                  Add to Cart
                </Button>
              )}
            </HStack>
          </VStack>
        </HStack>

        {book.description && (
          <>
            <Separator />
            <Box>
              <Text textStyle="xs" fontWeight="bold" mb="1">
                Description
              </Text>
              <Text textStyle="sm" color="fg.muted">
                {book.description}
              </Text>
            </Box>
          </>
        )}

        {book.link && (
          <HStack>
            <Button
              size="xs"
              variant="ghost"
              asChild
            >
              <a href={book.link} target="_blank" rel="noopener noreferrer">
                <LuExternalLink />
                View on Goodreads
              </a>
            </Button>
          </HStack>
        )}
      </Card.Body>
    </Card.Root>
  );
}
