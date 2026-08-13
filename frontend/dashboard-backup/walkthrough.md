# Neon Cyberpunk Aesthetic Overhaul

The WSN AI Security Pipeline Dashboard has been fully updated with a visually striking, neon cyberpunk aesthetic. Every aspect of the UI has been tweaked to deliver a premium, high-contrast, glowing experience in dark mode.

## What Changed

### Global Cyberpunk Styling
- **Background**: The dark mode background is now a solid, deep `#0a0a0f` instead of a slate gradient, removing all noise and delivering a clean canvas for glowing elements.
- **Glassmorphism Base**: Dark mode `.glass` cards now use a semi-transparent deep dark background `rgba(10, 10, 15, 0.8)` with a subtle white frosted border to contrast sharply against the neon accents.

### Sidebar Glow
- The sidebar and mobile top bar backgrounds now perfectly match the `#0a0a0f` deep dark hue.
- The sidebar features a highly-requested **neon cyan left border glow** that emanates into the dark background, anchoring the navigation.

### Glowing Typography & Borders
- New custom CSS utility classes power all the glowing text and borders:
  - `neon-text-cyan`, `border-cyan-glow`
  - `neon-text-pink`, `border-danger-glow`
  - `neon-text-green`, `border-success-glow`
  - `neon-text-orange`, `border-warning-glow`
  - `neon-text-purple`, `border-purple-glow`
- All key metrics, such as the `F1 Score`, `Precision`, and `Recall` values across the application now feature vibrant white text with intense neon color drop-shadows.

### Component-Specific Enhancements
- **Attack Detection**: 
  - The XGBoost Confusion Matrix was fully color-coded. Each quadrant uses matching neon text, backgrounds, and intense glowing borders (TP=Green, FN=Orange, FP=Pink, TN=Cyan).
  - Model comparison cards use intense pink and green glowing edges and numbers.
- **Routing Simulation**:
  - The hero subtitle text, "Compromised routes eliminated," now beams with a vibrant neon green glow.
  - The "Baseline Routing" compromised stat blocks are bordered in deep pink glowing borders with pink text, while the "Trust-Aware" 0% stat glows bright neon green.
- **Energy Forecast**:
  - The SVG chart lines now have a custom `<filter>` applied to create a realistic neon blur/glow effect over the data paths.
  - All X/Y axis ticks and labels render as pure white to remain stark and visible against the dark `#0a0a0f` canvas.

> [!TIP]
> Toggle the top-right theme switch to see the contrast between the clean Light Mode design and the intense Cyberpunk Dark Mode!
