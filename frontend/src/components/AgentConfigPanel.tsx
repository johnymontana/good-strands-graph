"use client";

import { useEffect, useState } from "react";
import {
  Accordion,
  Badge,
  Box,
  Code,
  HStack,
  Span,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import { LuBot, LuBrain, LuShoppingCart, LuWrench } from "react-icons/lu";
import { getAgentConfig } from "@/lib/api";
import type { AgentConfig, ToolInfo } from "@/lib/api";

const CATEGORY_LABELS: Record<string, { label: string; icon: React.ReactNode }> = {
  book_discovery: { label: "Book Discovery", icon: <LuBot size={14} /> },
  commerce: { label: "Commerce", icon: <LuShoppingCart size={14} /> },
  memory: { label: "Memory", icon: <LuBrain size={14} /> },
};

function groupTools(tools: ToolInfo[]): Record<string, ToolInfo[]> {
  const groups: Record<string, ToolInfo[]> = {};
  for (const tool of tools) {
    if (!groups[tool.category]) groups[tool.category] = [];
    groups[tool.category].push(tool);
  }
  return groups;
}

export function AgentConfigPanel() {
  const [config, setConfig] = useState<AgentConfig | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAgentConfig()
      .then(setConfig)
      .catch((err) => console.error("Failed to load agent config:", err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <HStack gap="2" px="4" py="2" justify="center">
        <Spinner size="xs" />
        <Text textStyle="xs" color="fg.muted">Loading agent config...</Text>
      </HStack>
    );
  }

  if (!config) return null;

  const toolGroups = groupTools(config.tools);

  return (
    <Box w="full" borderWidth="1px" borderRadius="lg" overflow="hidden">
      <Accordion.Root collapsible size="sm" variant="enclosed">
        <Accordion.Item value="config">
          <Accordion.ItemTrigger px="4" py="2">
            <HStack flex="1" gap="2">
              <LuBot size={16} />
              <Span textStyle="sm" fontWeight="semibold">Agent Configuration</Span>
              <Badge size="xs" variant="subtle" colorPalette="blue">
                {config.tools.length} tools
              </Badge>
            </HStack>
            <Accordion.ItemIndicator />
          </Accordion.ItemTrigger>
          <Accordion.ItemContent>
            <Accordion.ItemBody px="0" py="0">
              {/* Nested accordion for config sections */}
              <Accordion.Root collapsible multiple size="sm" variant="plain">
                {/* Model Info */}
                <Accordion.Item value="model">
                  <Accordion.ItemTrigger px="4" py="2">
                    <Span flex="1" textStyle="xs" fontWeight="semibold">Model</Span>
                    <Accordion.ItemIndicator />
                  </Accordion.ItemTrigger>
                  <Accordion.ItemContent>
                    <Accordion.ItemBody px="4" py="2">
                      <HStack gap="2" flexWrap="wrap">
                        <Badge size="sm" variant="outline">{config.model_id}</Badge>
                        <Badge size="sm" variant="outline">{config.aws_region}</Badge>
                      </HStack>
                    </Accordion.ItemBody>
                  </Accordion.ItemContent>
                </Accordion.Item>

                {/* System Prompt */}
                <Accordion.Item value="prompt">
                  <Accordion.ItemTrigger px="4" py="2">
                    <Span flex="1" textStyle="xs" fontWeight="semibold">System Prompt</Span>
                    <Accordion.ItemIndicator />
                  </Accordion.ItemTrigger>
                  <Accordion.ItemContent>
                    <Accordion.ItemBody px="4" py="2">
                      <Code
                        display="block"
                        whiteSpace="pre-wrap"
                        p="3"
                        borderRadius="md"
                        textStyle="xs"
                        overflow="auto"
                        maxH="300px"
                      >
                        {config.system_prompt}
                      </Code>
                    </Accordion.ItemBody>
                  </Accordion.ItemContent>
                </Accordion.Item>

                {/* Tools by Category */}
                <Accordion.Item value="tools">
                  <Accordion.ItemTrigger px="4" py="2">
                    <HStack flex="1" gap="2">
                      <Span textStyle="xs" fontWeight="semibold">
                        Tools ({config.tools.length})
                      </Span>
                    </HStack>
                    <Accordion.ItemIndicator />
                  </Accordion.ItemTrigger>
                  <Accordion.ItemContent>
                    <Accordion.ItemBody px="4" py="2">
                      <VStack gap="3" align="stretch">
                        {Object.entries(toolGroups).map(([category, tools]) => {
                          const meta = CATEGORY_LABELS[category] || {
                            label: category,
                            icon: <LuWrench size={14} />,
                          };
                          return (
                            <Box key={category}>
                              <HStack gap="1" mb="1">
                                {meta.icon}
                                <Text textStyle="xs" fontWeight="semibold" color="fg.muted">
                                  {meta.label}
                                </Text>
                              </HStack>
                              <VStack gap="1" align="stretch" pl="5">
                                {tools.map((tool) => (
                                  <HStack key={tool.name} gap="2" align="baseline">
                                    <Code textStyle="xs" flexShrink={0}>
                                      {tool.name}
                                    </Code>
                                    <Text textStyle="xs" color="fg.muted">
                                      {tool.description}
                                    </Text>
                                  </HStack>
                                ))}
                              </VStack>
                            </Box>
                          );
                        })}
                      </VStack>
                    </Accordion.ItemBody>
                  </Accordion.ItemContent>
                </Accordion.Item>
              </Accordion.Root>
            </Accordion.ItemBody>
          </Accordion.ItemContent>
        </Accordion.Item>
      </Accordion.Root>
    </Box>
  );
}
