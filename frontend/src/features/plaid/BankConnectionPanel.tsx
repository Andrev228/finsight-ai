"use client";

import AccountBalanceOutlined from "@mui/icons-material/AccountBalanceOutlined";
import CheckCircleOutline from "@mui/icons-material/CheckCircleOutline";
import ContentCopyOutlined from "@mui/icons-material/ContentCopyOutlined";
import LockOutlined from "@mui/icons-material/LockOutlined";
import ScienceOutlined from "@mui/icons-material/ScienceOutlined";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import { useState } from "react";

import { AccessTokenField } from "@/features/auth/AuthProvider";
import PlaidLinkButton from "@/features/plaid/PlaidLinkButton";

type ConnectionMode = "sandbox" | "real";

const SANDBOX_CREDENTIALS = [
  { label: "Phone number", value: "415-555-0011" },
  { label: "Verification code", value: "123456" },
  { label: "Institution", value: "First Platypus Bank" },
  { label: "Username", value: "user_good" },
  { label: "Password", value: "pass_good" },
];

/**
 * Presents the demo/live Plaid mode choice and guides the Sandbox connection.
 */
export default function BankConnectionPanel() {
  const [mode, setMode] = useState<ConnectionMode>("sandbox");
  const [copiedValue, setCopiedValue] = useState<string>();

  const copyValue = async (value: string) => {
    await navigator.clipboard.writeText(value);
    setCopiedValue(value);
    window.setTimeout(() => setCopiedValue(undefined), 1500);
  };

  return (
    <Paper
      elevation={0}
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 4,
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          px: { xs: 2.5, md: 4 },
          py: 2.5,
          bgcolor: "background.paper",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "stretch", sm: "center" }}
          spacing={2}
        >
          <Box>
            <Typography variant="overline" color="primary" fontWeight={700}>
              Connection mode
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Choose how you want to explore finsight-ai.
            </Typography>
          </Box>
          <ToggleButtonGroup
            exclusive
            fullWidth
            value={mode}
            onChange={(_, value: ConnectionMode | null) => {
              if (value) setMode(value);
            }}
            aria-label="Plaid connection mode"
            sx={{ maxWidth: { sm: 360 } }}
          >
            <ToggleButton value="sandbox">
              <ScienceOutlined sx={{ mr: 1 }} />
              Sandbox demo
            </ToggleButton>
            <ToggleButton value="real">
              <AccountBalanceOutlined sx={{ mr: 1 }} />
              Real bank
            </ToggleButton>
          </ToggleButtonGroup>
        </Stack>
      </Box>

      {mode === "sandbox" ? (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "minmax(0, 1fr) 320px" },
          }}
        >
          <Stack spacing={3} sx={{ p: { xs: 2.5, md: 4 } }}>
            <Stack spacing={1}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Chip
                  icon={<ScienceOutlined />}
                  label="Safe demo data"
                  color="primary"
                  size="small"
                />
                <Chip label="No real money" size="small" variant="outlined" />
              </Stack>
              <Typography variant="h5" fontWeight={750}>
                Connect a sample bank in about a minute
              </Typography>
              <Typography color="text.secondary">
                Plaid creates realistic fake accounts and transactions so you
                can test the complete financial assistant safely.
              </Typography>
            </Stack>

            <Stack spacing={1.5}>
              {[
                "Open Plaid Link",
                "Use the Sandbox details shown on the right",
                "Continue automatically to your financial chat",
              ].map((step, index) => (
                <Stack key={step} direction="row" spacing={1.5}>
                  <Box
                    sx={{
                      width: 28,
                      height: 28,
                      flex: "0 0 auto",
                      borderRadius: "50%",
                      display: "grid",
                      placeItems: "center",
                      bgcolor: "primary.main",
                      color: "primary.contrastText",
                      fontWeight: 700,
                      fontSize: 14,
                    }}
                  >
                    {index + 1}
                  </Box>
                  <Typography sx={{ pt: 0.25 }}>{step}</Typography>
                </Stack>
              ))}
            </Stack>

            <PlaidLinkButton />

            <Accordion disableGutters elevation={0}>
              <AccordionSummary>
                <Typography variant="body2" fontWeight={650}>
                  Advanced: use a JWT access token
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <AccessTokenField />
              </AccordionDetails>
            </Accordion>
          </Stack>

          <Stack
            spacing={2}
            sx={{
              p: { xs: 2.5, md: 3 },
              bgcolor: "background.default",
              borderLeft: { md: "1px solid" },
              borderTop: { xs: "1px solid", md: 0 },
              borderColor: "divider",
            }}
          >
            <Box>
              <Typography variant="subtitle1" fontWeight={750}>
                Sandbox cheat sheet
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Enter these values when Plaid asks for them.
              </Typography>
            </Box>
            <Divider />
            {SANDBOX_CREDENTIALS.map(({ label, value }) => (
              <Box key={label}>
                <Typography variant="caption" color="text.secondary">
                  {label}
                </Typography>
                <Stack
                  direction="row"
                  alignItems="center"
                  justifyContent="space-between"
                  spacing={1}
                >
                  <Typography
                    component="code"
                    fontWeight={700}
                    sx={{ wordBreak: "break-word" }}
                  >
                    {value}
                  </Typography>
                  <Button
                    size="small"
                    onClick={() => copyValue(value)}
                    startIcon={
                      copiedValue === value ? (
                        <CheckCircleOutline />
                      ) : (
                        <ContentCopyOutlined />
                      )
                    }
                    aria-label={`Copy ${label}`}
                  >
                    {copiedValue === value ? "Copied" : "Copy"}
                  </Button>
                </Stack>
              </Box>
            ))}
          </Stack>
        </Box>
      ) : (
        <Stack
          alignItems="center"
          textAlign="center"
          spacing={2}
          sx={{ px: 3, py: { xs: 6, md: 8 } }}
        >
          <Box
            sx={{
              width: 64,
              height: 64,
              display: "grid",
              placeItems: "center",
              borderRadius: "50%",
              bgcolor: "action.hover",
            }}
          >
            <LockOutlined color="action" fontSize="large" />
          </Box>
          <Chip label="Coming soon" size="small" />
          <Typography variant="h5" fontWeight={750}>
            Real bank connections are not enabled
          </Typography>
          <Typography color="text.secondary" maxWidth={520}>
            This portfolio demo intentionally uses Plaid Sandbox. Real
            connections require Plaid Production approval, compliance controls,
            and production credentials.
          </Typography>
          <Alert severity="info" sx={{ maxWidth: 560, textAlign: "left" }}>
            Choose Sandbox demo to explore the complete experience with
            synthetic financial data.
          </Alert>
          <Button variant="outlined" onClick={() => setMode("sandbox")}>
            Back to Sandbox
          </Button>
        </Stack>
      )}
    </Paper>
  );
}
