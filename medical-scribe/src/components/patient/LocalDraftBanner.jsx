import { Badge, Flex, HStack, Text, useColorMode } from "@chakra-ui/react";
import { useEffect, useState } from "react";
import { FaCloud, FaLock } from "react-icons/fa";
import { colors } from "../../theme/colors";
import { universalFetch } from "../../utils/helpers/apiHelpers";
import { buildApiUrl } from "../../utils/helpers/apiConfig";

const LocalDraftBanner = () => {
  const { colorMode } = useColorMode();
  const c = colors[colorMode];
  const [isLocal, setIsLocal] = useState(false);

  useEffect(() => {
    let active = true;

    const loadMode = async () => {
      try {
        const response = await universalFetch(await buildApiUrl("/api/config/global"));
        if (!response.ok) return;
        const config = await response.json();
        if (active) setIsLocal(config?.LLM_PROVIDER === "local");
      } catch (error) {
        console.error("Could not load inference mode:", error);
      }
    };

    loadMode();
    return () => {
      active = false;
    };
  }, []);

  const scheme = isLocal ? "green" : "blue";

  return (
    <Flex
      align={{ base: "flex-start", md: "center" }}
      justify="space-between"
      direction={{ base: "column", md: "row" }}
      gap={3}
      px={4}
      py={3}
      border="1px solid"
      borderColor={
        colorMode === "dark" ? `${scheme}.700` : `${scheme}.200`
      }
      bg={colorMode === "dark" ? `${scheme}.900` : `${scheme}.50`}
      borderRadius="lg"
      role="status"
    >
      <HStack spacing={3}>
        <Flex
          align="center"
          justify="center"
          boxSize="32px"
          borderRadius="full"
          bg={colorMode === "dark" ? `${scheme}.700` : `${scheme}.100`}
          color={colorMode === "dark" ? `${scheme}.100` : `${scheme}.700`}
          flexShrink={0}
        >
          {isLocal ? <FaLock aria-hidden="true" /> : <FaCloud aria-hidden="true" />}
        </Flex>
        <Text color={c.textPrimary} fontWeight="700">
          {isLocal ? "Runs locally" : "Gemma via OpenRouter"}
        </Text>
        <Text color={c.textSecondary} fontSize="sm">
          {isLocal
            ? "Audio and notes stay on this device."
            : "Transcription via Groq. Review before use."}
        </Text>
      </HStack>
      <Badge colorScheme={scheme} variant="subtle" px={2} py={1}>
        Synthetic demo data only
      </Badge>
    </Flex>
  );
};

export default LocalDraftBanner;
