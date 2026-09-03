import AccountBalanceWalletOutlined from "@mui/icons-material/AccountBalanceWalletOutlined";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Container from "@mui/material/Container";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

export default function Home() {
  return (
    <Box component="main" sx={{ py: { xs: 6, md: 12 } }}>
      <Container maxWidth="sm">
        <Paper elevation={2} sx={{ p: { xs: 3, md: 5 } }}>
          <Stack spacing={3} alignItems="flex-start">
            <AccountBalanceWalletOutlined color="primary" fontSize="large" />
            <Typography component="h1" variant="h3" fontWeight={700}>
              finsight-ai
            </Typography>
            <Typography color="text.secondary" variant="h6">
              AI-powered personal finance insights. Budgeting and financial
              insights, not licensed financial advice.
            </Typography>
            <Chip label="Phase 0 — Plaid Sandbox" color="primary" />
          </Stack>
        </Paper>
      </Container>
    </Box>
  );
}
