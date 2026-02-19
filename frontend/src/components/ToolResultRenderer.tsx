"use client";

import type { ToolResult, BookData, ReviewData, CartData, OrderData } from "@/lib/api";
import { BookCardList } from "./BookCardList";
import { BookDetailCard } from "./BookDetailCard";
import { ReviewList } from "./ReviewList";
import { CartDisplay } from "./CartDisplay";
import { OrderConfirmation } from "./OrderConfirmation";

// Tool names that render as book lists
const BOOK_LIST_TOOLS = new Set([
  "search_books",
  "get_popular_books",
  "find_similar_books",
  "get_books_by_publisher",
  "get_recommended_books",
]);

// Tool names that render as cart
const CART_TOOLS = new Set(["add_to_cart", "get_cart", "remove_from_cart"]);

interface ToolResultRendererProps {
  result: ToolResult;
  onAddToCart?: (bookId: string) => void;
  onRemoveFromCart?: (bookId: string) => void;
  onCheckout?: () => void;
}

export function ToolResultRenderer({
  result,
  onAddToCart,
  onRemoveFromCart,
  onCheckout,
}: ToolResultRendererProps) {
  const { tool_name, data } = result;

  if (!data) return null;

  // Book list tools
  if (BOOK_LIST_TOOLS.has(tool_name)) {
    const books: BookData[] = Array.isArray(data) ? data : [data];
    if (books.length === 0) return null;
    return <BookCardList books={books} onAddToCart={onAddToCart} />;
  }

  // Single book detail
  if (tool_name === "get_book_details") {
    if (data.error) return null;
    return <BookDetailCard book={data} onAddToCart={onAddToCart} />;
  }

  // Reviews
  if (tool_name === "get_book_reviews") {
    const reviews: ReviewData[] = Array.isArray(data) ? data : [];
    return <ReviewList reviews={reviews} />;
  }

  // Cart operations
  if (CART_TOOLS.has(tool_name)) {
    const cartData = data as CartData;
    return (
      <CartDisplay
        cart={cartData}
        onRemoveFromCart={onRemoveFromCart}
        onCheckout={onCheckout}
      />
    );
  }

  // Checkout / order confirmation
  if (tool_name === "checkout") {
    if (data.error) return null;
    const orderData = data as OrderData;
    return <OrderConfirmation order={orderData} />;
  }

  return null;
}
