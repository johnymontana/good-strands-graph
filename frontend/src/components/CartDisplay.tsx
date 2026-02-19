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
import { LuShoppingCart, LuTrash2, LuCreditCard } from "react-icons/lu";
import type { CartData } from "@/lib/api";

interface CartDisplayProps {
  cart: CartData;
  onRemoveFromCart?: (bookId: string) => void;
  onCheckout?: () => void;
}

export function CartDisplay({
  cart,
  onRemoveFromCart,
  onCheckout,
}: CartDisplayProps) {
  if (cart.error) {
    return (
      <Card.Root variant="outline" w="full">
        <Card.Body>
          <Text textStyle="sm" color="fg.muted">
            {cart.error}
          </Text>
        </Card.Body>
      </Card.Root>
    );
  }

  if (!cart.items || cart.items.length === 0) {
    return (
      <Card.Root variant="outline" w="full">
        <Card.Body>
          <HStack gap="2">
            <LuShoppingCart size={16} />
            <Text textStyle="sm" color="fg.muted">
              Your cart is empty
            </Text>
          </HStack>
        </Card.Body>
      </Card.Root>
    );
  }

  return (
    <Card.Root variant="outline" w="full">
      <Card.Body gap="3">
        <HStack>
          <LuShoppingCart size={16} />
          <Text textStyle="sm" fontWeight="bold">
            Shopping Cart
          </Text>
          <Badge size="sm" colorPalette="blue">
            {cart.item_count} {cart.item_count === 1 ? "item" : "items"}
          </Badge>
        </HStack>

        {cart.message && (
          <Text textStyle="xs" color="green.600" fontWeight="medium">
            {cart.message}
          </Text>
        )}

        <VStack gap="2" align="stretch">
          {cart.items.map((item) => {
            const hasImage =
              item.imageUrl && !item.imageUrl.includes("nophoto");
            return (
              <HStack key={item.bookId} gap="3" py="1">
                {hasImage && (
                  <Image
                    objectFit="cover"
                    w="40px"
                    h="60px"
                    borderRadius="sm"
                    src={item.imageUrl}
                    alt={item.title}
                  />
                )}
                <Box flex="1">
                  <Text textStyle="xs" fontWeight="medium" lineClamp={1}>
                    {item.title}
                  </Text>
                  <HStack gap="2">
                    <Text textStyle="xs" color="green.600">
                      ${item.price.toFixed(2)}
                    </Text>
                    {item.quantity > 1 && (
                      <Text textStyle="xs" color="fg.muted">
                        x{item.quantity}
                      </Text>
                    )}
                  </HStack>
                </Box>
                {onRemoveFromCart && (
                  <Button
                    size="xs"
                    variant="ghost"
                    colorPalette="red"
                    onClick={() => onRemoveFromCart(item.bookId)}
                  >
                    <LuTrash2 />
                  </Button>
                )}
              </HStack>
            );
          })}
        </VStack>

        <Separator />

        <HStack justify="space-between">
          <Text textStyle="sm" fontWeight="bold">
            Total
          </Text>
          <Text textStyle="md" fontWeight="bold" color="green.600">
            ${cart.total.toFixed(2)}
          </Text>
        </HStack>

        {onCheckout && (
          <Button colorPalette="green" size="sm" onClick={onCheckout} w="full">
            <LuCreditCard />
            Checkout
          </Button>
        )}
      </Card.Body>
    </Card.Root>
  );
}
