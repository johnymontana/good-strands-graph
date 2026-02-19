"use client";

import {
  Badge,
  Card,
  HStack,
  Separator,
  Text,
  VStack,
} from "@chakra-ui/react";
import { LuCircleCheck, LuPackage } from "react-icons/lu";
import type { OrderData } from "@/lib/api";

interface OrderConfirmationProps {
  order: OrderData;
}

export function OrderConfirmation({ order }: OrderConfirmationProps) {
  return (
    <Card.Root variant="outline" w="full" borderColor="green.200">
      <Card.Body gap="3">
        <HStack gap="2">
          <LuCircleCheck size={20} color="green" />
          <Text textStyle="sm" fontWeight="bold" color="green.600">
            Order Confirmed!
          </Text>
        </HStack>

        <Text textStyle="sm">{order.message}</Text>

        <HStack gap="2">
          <LuPackage size={14} />
          <Text textStyle="xs" color="fg.muted">
            Order ID:
          </Text>
          <Badge size="sm" variant="outline">
            {order.orderId}
          </Badge>
        </HStack>

        <Separator />

        <VStack gap="1" align="stretch">
          {order.items.map((item) => (
            <HStack key={item.bookId} justify="space-between">
              <Text textStyle="xs" lineClamp={1} flex="1">
                {item.title}
                {item.quantity > 1 && ` x${item.quantity}`}
              </Text>
              <Text textStyle="xs" fontWeight="medium">
                ${(item.price * item.quantity).toFixed(2)}
              </Text>
            </HStack>
          ))}
        </VStack>

        <Separator />

        <HStack justify="space-between">
          <Text textStyle="sm" fontWeight="bold">
            Total Charged
          </Text>
          <Text textStyle="md" fontWeight="bold" color="green.600">
            ${order.total.toFixed(2)}
          </Text>
        </HStack>
      </Card.Body>
    </Card.Root>
  );
}
