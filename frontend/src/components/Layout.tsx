import { AppBar, Container, Stack, Toolbar, Typography } from "@mui/material";
import type { ReactNode } from "react";

type LayoutProps = {
  children: ReactNode;
};

export function Layout({ children }: LayoutProps) {
  return (
    <Stack minHeight="100vh" spacing={0}>
      <AppBar position="static" elevation={0}>
        <Toolbar>
          <Typography component="div" variant="h6" fontWeight={700}>
            Fencing Video Research Agent
          </Typography>
        </Toolbar>
      </AppBar>
      <Container component="main" maxWidth="lg" sx={{ py: { xs: 3, md: 5 } }}>
        {children}
      </Container>
    </Stack>
  );
}
