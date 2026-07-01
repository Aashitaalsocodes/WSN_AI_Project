# Neon Cyberpunk Aesthetic Overhaul

This document outlines the changes needed to fully implement the cyberpunk neon glow aesthetic requested for the WSN AI Security Pipeline dashboard.

## Proposed Changes

### 1. Global CSS (`src/index.css`)
- **Background**: Update `.dark .bg-dashboard` and Sidebar background to `#0a0a0f`. Remove existing background gradients/noise in favor of the clean dark background.
- **Text & Contrast**: Ensure no black text is present in dark mode. Elevate `text-surface-900` to pure white `#ffffff` and `text-surface-800` to `#f1f5f9`. Add global utility classes for glowing text (`neon-text-cyan`, `neon-text-green`, `neon-text-pink`, `neon-text-orange`, `neon-text-purple`).
- **Cards & Panels**: Update `.dark .glass` base styling to support neon `box-shadow` borders. Add specific utility classes for neon borders:
  - Cyan: `#00fff7`
  - Purple: `#bf00ff`
  - Green: `#00ff88`
  - Pink: `#ff006e`
  - Orange/Red: Alert states.
- **Interactivity**: Add hover states for buttons and nav links that intensify the neon glow (`hover-glow`). Add a subtle neon cyan left border glow to the sidebar in dark mode.

### 2. Sidebar (`src/components/Sidebar.jsx`)
#### [MODIFY] [Sidebar.jsx](file:///c:/Users/Aashita/Downloads/dashboard/dashboard/src/components/Sidebar.jsx)
- Update the background color of the `<aside>` element to match `#0a0a0f` in dark mode.
- Add a neon cyan `box-shadow` (e.g., `shadow-[-4px_0_15px_#00fff7]`) to the left border of the sidebar, or simply `border-l border-cyan-400 shadow-[inset_4px_0_15px_rgba(0,255,247,0.3)]` since it's on the left side of the screen (or right border if it's a standard sidebar, but we will make it glow).
- Update NavLinks to use neon hover effects.

### 3. Attack Detection (`src/pages/AttackDetection.jsx`)
#### [MODIFY] [AttackDetection.jsx](file:///c:/Users/Aashita/Downloads/dashboard/dashboard/src/pages/AttackDetection.jsx)
- **Confusion Matrix**: Update `matrixCells` array:
  - TP: Green text and border with `neon-text-green` and green glow box-shadow.
  - FP: Pink text and border with `neon-text-pink` and pink glow box-shadow.
  - FN: Orange text and border with `neon-text-orange` and orange glow box-shadow.
  - TN: Cyan text and border with `neon-text-cyan` and cyan glow box-shadow.
- **Metrics**: Ensure F1, Precision, and Recall numbers use white text with the respective neon `text-shadow`.

### 4. Routing Simulation (`src/pages/RoutingSimulation.jsx`)
#### [MODIFY] [RoutingSimulation.jsx](file:///c:/Users/Aashita/Downloads/dashboard/dashboard/src/pages/RoutingSimulation.jsx)
- **Hero Banner**: Change the "Compromised routes eliminated" text to use a bright neon green glow (`neon-text-green`).
- **Comparison Cards**: Make the compromised blocks (e.g., the 23% baseline) highly visible with bright red/pink neon glows. Update the safe routes (0%) with bright green neon glows.

### 5. Energy Forecast (`src/pages/EnergyForecast.jsx`)
#### [MODIFY] [EnergyForecast.jsx](file:///c:/Users/Aashita/Downloads/dashboard/dashboard/src/pages/EnergyForecast.jsx)
- **Charts**: Update `AreaChart` stroke colors to be neon. Add CSS filters (`filter: drop-shadow(0 0 8px currentColor)`) to SVG elements for chart lines to make them glow.
- **Axes**: Ensure all axis labels and ticks are bright white/slate in dark mode.

## User Review Required

> [!IMPORTANT]
> The exact neon colors to be used:
> - Cyan: `#00fff7`
> - Purple: `#bf00ff`
> - Green: `#00ff88`
> - Pink: `#ff006e`
> - Orange: `#ffaa00` (for FN)
> Please confirm if these exact hex codes meet your expectations for the Cyberpunk aesthetic.

## Verification Plan

### Manual Verification
- Toggle to dark mode.
- Verify background color is exactly `#0a0a0f`.
- Verify sidebar blends in and has the requested cyan glow.
- Verify no black text exists on dark backgrounds across all pages.
- Verify XGBoost confusion matrix colors (Green, Pink, Orange, Cyan) are applied correctly.
- Verify chart lines and numbers have glowing effects.
