import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Stack from "@mui/material/Stack";

import RequireBankConnection from "@/features/auth/RequireBankConnection";
import FinanceChat from "@/features/chat/FinanceChat";
import ProductBrand from "@/shared/ui/ProductBrand";

/**
 * Renders the protected financial chat page for users with a connected bank.
 */
export default function ChatPage() {
  return (
    <Box component="main" sx={{ py: { xs: 4, md: 8 } }}>
      <Container maxWidth="xl">
        <RequireBankConnection>
          <Stack spacing={3}>
            <Box sx={{ pr: 7 }}>
              <ProductBrand compact />
            </Box>
            <FinanceChat />
          </Stack>
        </RequireBankConnection>
      </Container>
    </Box>
  );
}
