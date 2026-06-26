# Design System

## Overview

SAK Ti uses a quiet study-workbench interface: a light gray canvas, white cards, thin borders, and a persistent left navigation rail. The brand expression is practical and calm rather than decorative, with serif headings adding a learning/editorial note and a highly legible sans-serif for UI copy. The homepage is organized around one login hero, quick entry cards, a "核心功能" grid, and a compact CTA band. Motion on the source page is restrained, mostly short fade-ins and hover lifts.

## Colors

- **Canvas**: `#F6F7F8` - page background and negative space.
- **Surface**: `#FFFFFF` - cards, top search, nav blocks.
- **Ink**: `#111827` - primary copy, SAK mark, active buttons.
- **Muted Text**: `#6B7280` - descriptions and metadata.
- **Quiet Border**: `#E5E7EB` - card outlines and separators.
- **Deep Shadow Ink**: `#020617` - soft shadow tint.
- **Mist Accent**: `#4F46E5` - optional theme accent for study focus.
- **Dune Accent**: `#E07A2C` - optional warm CTA pulse.
- **Pine Accent**: `#2DBA7D` - progress/success accent.
- **Celadon Accent**: `#0D9488` - secondary focus accent.

## Typography

- **Heading Serif**: Crimson Pro, weights 400-700. Used for hero and feature titles; should feel academic and readable, not ornamental.
- **UI Sans**: Atkinson Hyperlegible, weights 400 and 700. Used for body, labels, buttons, and stats where clarity matters.
- **Hierarchy**: Video headings should scale the captured hierarchy up: 76-120px for hero statements, 34-44px for feature titles, 22-28px for descriptions, and 18-22px for data labels.

## Elevation

Depth is shallow and functional. Cards use `1px` borders in `#E5E7EB`, white surfaces, rounded corners between 12px and 18px, and soft shadows such as `rgba(2, 6, 23, 0.05) 0px 2px 10px`. The promo can add cinematic parallax and larger device-like frames, but it should preserve the source site's low-noise card depth and avoid heavy drop shadows.

## Components

- **Left Product Rail**: narrow white navigation rail with SAK mark, section labels, and black outline icons.
- **Login Hero Card**: centered white card with Crimson Pro headline, muted explanatory copy, and a dark rounded CTA button.
- **Quick Entry Rows**: full-width white rows for "题库广场" and "搜索", each pairing an icon tile with concise metadata.
- **Core Function Cards**: four white feature cards for 海量题库, 智能错题本, 学习数据, 模拟考试, each with a pale icon tile and restrained text.
- **CTA Band**: bordered rounded band with a dark login/register button, used as the final conversion pattern.
- **Icon System**: simple black stroke SVG icons for home, book, search, data bars, refresh, code, chat, and notifications.

## Do's and Don'ts

### Do's

- Use `#F6F7F8` and `#FFFFFF` as the dominant surfaces.
- Keep card edges thin with `#E5E7EB` and use 12-18px radius.
- Pair Crimson Pro titles with Atkinson Hyperlegible UI labels.
- Use the captured homepage screenshot and SVG icons as real product evidence.
- Let motion feel like a dashboard assembling: slides, draws, counts, and soft zooms.

### Don'ts

- Do not turn the promo into a neon or dark SaaS launch film.
- Do not use generic blue-purple gradients as the main background.
- Do not replace the product UI with abstract stock imagery.
- Do not use heavy glassmorphism, oversized round cards, or nested-card decoration.
- Do not introduce fonts outside the captured brand fonts.
