"use client"

import { ChakraProvider, defaultSystem } from "@chakra-ui/react"
import dynamic from "next/dynamic"
import type { ColorModeProviderProps } from "./color-mode"

const ColorModeProvider = dynamic(
  () => import("./color-mode").then((mod) => mod.ColorModeProvider),
  { ssr: false },
)

export function Provider(props: ColorModeProviderProps) {
  return (
    <ChakraProvider value={defaultSystem}>
      <ColorModeProvider {...props} />
    </ChakraProvider>
  )
}
