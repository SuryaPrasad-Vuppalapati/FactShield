# FactShield Edu RAG — Gemini UI Design Specification

This document details the visual design system and signature elements for the FactShield Edu RAG frontend. The goal is to provide a premium, modern, "Gemini-inspired" user experience that feels alive, polished, and extremely high-end.

---

## 1. Color Palette (Gemini-Inspired Dark Mode)

Our core color tokens are defined using modern CSS variables with a dark-mode-first approach:

| Token Name | Value | Purpose |
| :--- | :--- | :--- |
| `--color-bg-base` | `#0f0f11` | Absolute background color (sleek, deep charcoal) |
| `--color-bg-surface` | `#1e1f20` | Cards, input textareas, and elevated panel surfaces |
| `--color-bg-hover` | `#2a2b2d` | Button and card hover background |
| `--color-border` | `#333537` | Subtle borders dividing sections |
| `--color-text-primary` | `#f0f4f9` | High contrast off-white for headings and primary text |
| `--color-text-secondary` | `#c4c7c5` | Soft gray for labels, hints, and body text |
| `--color-spark-blue` | `#4285f4` | Gemini signature blue |
| `--color-spark-purple` | `#9b72cb` | Gemini signature purple |
| `--color-spark-red` | `#d96570` | Gemini signature red/orange |

### The Gemini Spark Gradient:
```css
--gradient-gemini-spark: linear-gradient(
  135deg,
  var(--color-spark-blue) 0%,
  var(--color-spark-purple) 50%,
  var(--color-spark-red) 100%
);
```

---

## 2. Typography & Hierarchy

We pair clean, characterful display typography with highly legible UI body text:

- **Display & Headings**: `Outfit` or `Inter`, sans-serif (light-to-medium weights, loose tracking, large headings).
- **Body Text**: `Inter`, sans-serif (regular weight, high readability).
- **Technical/Code**: `JetBrains Mono` or Consolas (mono-spaced for code fragments, ids, tokens).

---

## 3. Signature Element: The Animated "Gemini Spark" Score Glow

The core feature of this design is the interactive feedback loop. When score cards (TrustBadges) or status fields render:
1. **The Loading Shimmer**: While an API request is in-flight, a smooth, sweeping gradient animation (the Gemini shimmer) passes across the cards.
2. **Glow States**:
   - **Passed/Grounded**: A clean cyan/blue border with a soft matching glow.
   - **Needs Review**: A pulsing golden-amber glow (`rgba(217, 101, 112, 0.45)`) that visually cues the user to pay attention.
   - **Failed**: A subtle dim red alert badge.

---

## 4. UI Layout & Glassmorphism

- **Sleek Sidebar/Top Nav**: A thin, clean header with floating tab controls using subtle background transitions.
- **Form Fields**: Textareas and inputs have a deep background (`#1e1f20`), a soft border (`#333537`), and a glowing border effect on focus that uses the Gemini Spark gradient.
- **Glassmorphism Overlay**: Dialogs and modals use backdrop-filter blurring (`blur(12px)`) with semi-transparent dark overlays.
