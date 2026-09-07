import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

type ProductBrandProps = {
  compact?: boolean;
};

/**
 * Renders the FinSight product mark and name.
 *
 * @param compact - Uses a smaller mark for application headers.
 */
export default function ProductBrand({
  compact = false,
}: ProductBrandProps) {
  const size = compact ? 38 : 48;

  return (
    <Stack direction="row" spacing={1.5} alignItems="center">
      <Box
        component="svg"
        viewBox="0 0 48 48"
        role="img"
        aria-label="FinSight logo"
        sx={{
          width: size,
          height: size,
          flex: "0 0 auto",
          filter: "drop-shadow(0 6px 12px rgba(23, 105, 224, 0.22))",
        }}
      >
        <defs>
          <linearGradient id="finsight-logo" x1="8" y1="6" x2="40" y2="42">
            <stop offset="0" stopColor="#4f9cff" />
            <stop offset="1" stopColor="#1257c7" />
          </linearGradient>
        </defs>
        <rect width="48" height="48" rx="14" fill="url(#finsight-logo)" />
        <path
          d="M13 32.5V25h5v7.5h-5Zm8.5 0V18h5v14.5h-5Zm8.5 0V11.5h5v21h-5Z"
          fill="#fff"
        />
        <path
          d="m12.5 20.5 8-7 6 3 9-8"
          fill="none"
          stroke="#bfe0ff"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2.5"
        />
      </Box>
      <Box>
        <Typography
          fontWeight={850}
          letterSpacing={-0.7}
          lineHeight={1}
          sx={{ fontSize: compact ? "1.25rem" : "1.5rem" }}
        >
          FinSight
        </Typography>
        {!compact && (
          <Typography
            variant="caption"
            color="text.secondary"
            letterSpacing={0.3}
          >
            Personal finance assistant
          </Typography>
        )}
      </Box>
    </Stack>
  );
}
