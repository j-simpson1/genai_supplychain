import { AppBar, Toolbar, Typography, Button, Box } from "@mui/material";
import { NavLink, useLocation } from "react-router-dom";
import { memo } from "react";

// Types
interface NavItem {
  readonly label: string;
  readonly path: string;
}

// Navigation configuration
const NAV_LINKS: readonly NavItem[] = [
  // Add your navigation items here
] as const;

// Styles
const headerStyles = {
  logoContainer: {
    display: "flex",
    alignItems: "center",
    textDecoration: "none",
    color: "inherit",
    transition: "opacity 0.2s ease-in-out",
    "&:hover": {
      opacity: 0.8,
    },
    "&:focus-visible": {
      outline: "2px solid",
      outlineColor: "primary.main",
      outlineOffset: "2px",
      borderRadius: 1,
    },
  },
  logoImage: {
    height: 32,
    width: "auto",
    display: "block",
  },
  nav: {
    display: "flex",
    gap: 2,
    alignItems: "center",
  },
  navButton: {
    textTransform: "none" as const,
    minWidth: "auto",
    px: 2,
    py: 1,
    borderRadius: 1,
    transition: "all 0.2s ease-in-out",
    "&:hover": {
      backgroundColor: "action.hover",
      transform: "translateY(-1px)",
    },
    "&:focus-visible": {
      outline: "2px solid",
      outlineColor: "primary.main",
      outlineOffset: "2px",
    },
  },
} as const;

// Component
const Header = memo(() => {
  const { pathname } = useLocation();

  return (
    <AppBar
      position="sticky"
      elevation={0}
      color="default"
      component="header"
      sx={{ backgroundColor: 'grey.200' }}
    >
      <Toolbar sx={{ justifyContent: "space-between" }}>
        {/* Logo */}
        <Box
          component={NavLink}
          to="/"
          sx={headerStyles.logoContainer}
          aria-label="Go to homepage"
        >
          <Box
            component="img"
            src="/supply_iq_logo.svg"
            alt="SupplyIQ"
            sx={headerStyles.logoImage}
          />
        </Box>

        {/* Navigation Links */}
        <Box
          component="nav"
          sx={headerStyles.nav}
          role="navigation"
          aria-label="Main navigation"
        >
          {NAV_LINKS.map(({ label, path }) => {
            const isActive = pathname === path;

            return (
              <Button
                key={path}
                component={NavLink}
                to={path}
                sx={{
                  ...headerStyles.navButton,
                  color: isActive ? "primary.main" : "text.primary",
                  fontWeight: isActive ? 600 : 400,
                }}
                aria-current={isActive ? "page" : undefined}
              >
                {label}
              </Button>
            );
          })}
        </Box>
      </Toolbar>
    </AppBar>
  );
});

Header.displayName = "Header";

export default Header;