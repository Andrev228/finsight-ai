import LockOutlined from "@mui/icons-material/LockOutlined";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Container from "@mui/material/Container";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import BankConnectionPanel from "@/features/plaid/BankConnectionPanel";
import ProductBrand from "@/shared/ui/ProductBrand";

/**
 * Renders the public entry page where a user connects a Plaid Sandbox bank.
 */
export default function Home() {
  return (
    <Box
      component="main"
      sx={{
        minHeight: "100vh",
        py: { xs: 4, md: 7 },
        bgcolor: "background.default",
        backgroundImage:
          "radial-gradient(circle at 10% 0%, rgba(23, 105, 224, 0.16) 0, transparent 34%)",
      }}
    >
      <Container maxWidth="lg">
        <Stack spacing={{ xs: 4, md: 5 }}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            justifyContent="space-between"
            alignItems={{ xs: "flex-start", sm: "center" }}
            spacing={2}
            sx={{ pr: { xs: 7, sm: 8 } }}
          >
            <ProductBrand />
            <Chip
              icon={<LockOutlined />}
              label="Plaid Sandbox demo"
              variant="outlined"
              sx={{ bgcolor: "background.paper" }}
            />
          </Stack>

          <Stack spacing={1.5} maxWidth={760}>
            <Typography
              component="h1"
              variant="h3"
              fontWeight={800}
              letterSpacing={-1.2}
              sx={{ fontSize: { xs: "2rem", sm: "2.5rem", md: "3rem" } }}
            >
              Connect bank data
            </Typography>
            <Typography
              color="text.secondary"
              sx={{ fontSize: { xs: "1rem", md: "1.125rem" } }}
            >
              Use synthetic Plaid accounts to test transaction analytics and
              the grounded financial chat. No real banking data is required.
            </Typography>
          </Stack>

          <BankConnectionPanel />

          <Typography
            variant="caption"
            color="text.secondary"
            textAlign="center"
          >
            Educational budgeting insights only — not financial advice.
          </Typography>
        </Stack>
      </Container>
    </Box>
  );
}
