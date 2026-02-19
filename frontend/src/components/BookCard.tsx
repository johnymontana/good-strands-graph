"use client";

import {
  Badge,
  Box,
  Card,
  HStack,
  Image,
  RatingGroup,
  Text,
} from "@chakra-ui/react";

export interface BookData {
  bookId: string;
  title: string;
  averageRating?: number;
  ratingsCount?: number;
  numPages?: number;
  publicationYear?: number;
  imageUrl?: string;
  description?: string;
  shelves?: string[];
  authorIds?: string[];
}

export function BookCard({ book }: { book: BookData }) {
  const rating = book.averageRating ?? 0;
  const hasImage =
    book.imageUrl && !book.imageUrl.includes("nophoto");

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
      <Box>
        <Card.Body gap="1">
          <Card.Title textStyle="sm">{book.title}</Card.Title>
          <HStack gap="2" mt="1">
            <RatingGroup.Root
              readOnly
              allowHalf
              defaultValue={rating}
              count={5}
              size="xs"
              colorPalette="orange"
            >
              <RatingGroup.HiddenInput />
              <RatingGroup.Control />
            </RatingGroup.Root>
            <Text textStyle="xs" color="fg.muted">
              {rating.toFixed(2)}
            </Text>
            {book.ratingsCount != null && (
              <Text textStyle="xs" color="fg.muted">
                ({book.ratingsCount.toLocaleString()} ratings)
              </Text>
            )}
          </HStack>
          {book.description && (
            <Text textStyle="xs" color="fg.muted" lineClamp={3} mt="1">
              {book.description}
            </Text>
          )}
          <HStack gap="1" mt="1" flexWrap="wrap">
            {book.numPages != null && (
              <Badge size="sm" variant="subtle">
                {book.numPages} pages
              </Badge>
            )}
            {book.publicationYear != null && (
              <Badge size="sm" variant="subtle">
                {book.publicationYear}
              </Badge>
            )}
            {book.shelves?.slice(0, 3).map((shelf) => (
              <Badge key={shelf} size="sm" variant="outline">
                {shelf}
              </Badge>
            ))}
          </HStack>
        </Card.Body>
      </Box>
    </Card.Root>
  );
}
