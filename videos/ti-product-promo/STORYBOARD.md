# Storyboard

**Format:** 1920x1080 landscape
**Audio:** Mandarin voiceover plus soft UI ticks and a restrained low study-pad underscore
**VO direction:** calm, focused, practical; a study tool demo rather than a hype ad
**Style basis:** DESIGN.md, captured SAK Ti homepage, captured fonts and SVG icon system

## Asset Audit

| Asset | Type | Assign to Beat | Role |
| --- | --- | --- | --- |
| `capture/screenshots/scroll-000.png` | Product screenshot | Beat 1, Beat 4 | Full product evidence, device frame, final background |
| `capture/assets/svgs/logo-1535c0d4.svg` | Home icon SVG | Beat 1 | Navigation/entry motif |
| `capture/assets/svgs/svg-da36a5f5.svg` | Book icon SVG | Beat 2 | 题库广场 / 海量题库 icon |
| `capture/assets/svgs/svg-52d41952.svg` | List icon SVG | Beat 2 | Search and resource rows |
| `capture/assets/svgs/svg-246de598.svg` | Star icon SVG | Beat 3 | 收藏 / progress highlight |
| `capture/assets/svgs/svg-580ef70c.svg` | Diamond icon SVG | Beat 3 | 错题复盘 marker |
| `capture/assets/svgs/svg-11626555.svg` | Chart icon SVG | Beat 3 | 学习数据 proof |
| `capture/assets/svgs/svg-111d95ca.svg` | Calendar icon SVG | Beat 3 | Daily learning rhythm |
| `capture/assets/svgs/svg-580c2e9b.svg` | Check icon SVG | Beat 4 | Final action confirmation |

## Beat 1 - Hook: Stop The Scatter (0.00-5.00s)

**VO cue:** "备考，不该被零散资料打断。"

**Concept:** A messy study day snaps into one clean workspace. The viewer starts close to floating fragments of "资料", "错题", "进度", then the captured SAK homepage rises behind them as the organizing center.

**Visual description:** Background uses `#F6F7F8` with a faint paper grid. Three small loose cards drift in the foreground, then a large product screenshot device frame slides in from the right and settles center. The SAK wordmark appears top-left in a compact nav pill. A hand-drawn SVG line circles the login hero card, pointing to the product as the single entry.

**Mood direction:** quiet but decisive; desk-clearing energy, not startup fireworks.

**Assets:** `scroll-000.png` as a device frame, `logo-1535c0d4.svg` as entry icon.

**Animation choreography:** loose cards float and blur, screenshot glides into place, SAK mark stamps in, SVG path draws around the hero area, camera slowly pushes in.

**Transition:** blur-through into Beat 2, with the product screenshot remaining visible until the blur peaks.

**Depth layers:** BG paper grid and accent dots; MG product screenshot; FG loose study fragments and drawn path.

**SFX cues:** soft paper shuffle at 0.2s; clean UI lock tick when the screenshot lands.

## Beat 2 - One Entrance For The Loop (5.00-10.00s)

**VO cue:** "SAK 题库把题库广场、错题复盘、学习数据和模拟考试放到一个入口。"

**Concept:** The product promise becomes an organized system. Four feature cards assemble like the captured homepage's "核心功能" section, each card owning one part of the learning loop.

**Visual description:** A large Crimson Pro headline reads "一个入口，完整备考闭环". Four white feature cards cascade across the lower half: 题库广场, 错题复盘, 学习数据, 模拟考试. Icons sit in pale tiles, while thin connector lines draw between the cards to imply one flow.

**Mood direction:** structured, readable, efficient.

**Assets:** `svg-da36a5f5.svg`, `svg-52d41952.svg`, `svg-11626555.svg`, `svg-111d95ca.svg`.

**Animation choreography:** headline slides up, cards cascade with staggered y movement, icon tiles scale in, connector line draws left to right, a small `#2DBA7D` progress dot travels along the line.

**Transition:** velocity-matched upward into Beat 3.

**Depth layers:** BG grid and subtle radial glow; MG connected cards; FG moving progress dot and headline.

**SFX cues:** four light UI ticks, one per card, then a soft sweep when the connector completes.

## Beat 3 - Every Step Feeds The Score (10.00-15.20s)

**VO cue:** "从搜索题目，到收藏、记录、进度同步，每一步都围着提分展开。"

**Concept:** The workflow becomes measurable progress. Search, collect, answer, and review all feed a live dashboard, turning repeated practice into visible improvement.

**Visual description:** The frame splits into a search rail on the left and a data board on the right. A search pill types "高数 极限", a row moves into 收藏, then into 错题复盘. On the right, three stat counters count up: 收藏, 错题, 正确率. A mini 7-day bar chart rises in `#2DBA7D` and `#0D9488`.

**Mood direction:** analytical, satisfying, tool-like.

**Assets:** `svg-246de598.svg`, `svg-580ef70c.svg`, `svg-11626555.svg`, `svg-580c2e9b.svg`.

**Animation choreography:** search text types on, icons hop from step to step, counters count up, bars grow, a thin path draws from input to chart.

**Transition:** zoom-through into Beat 4, using the data board as the source of the zoom.

**Depth layers:** BG off-white canvas; MG workflow columns; FG counters, animated path, progress markers.

**SFX cues:** keyboard taps under the search phrase; subtle counter clicks.

## Beat 4 - CTA: Start Today (15.20-20.00s)

**VO cue:** "打开 SAK 题库，开始今天的学习。"

**Concept:** Return to the captured product and make the action obvious. The final frame feels like the source homepage, but more cinematic and focused.

**Visual description:** The full screenshot sits in a floating frame, slightly angled, with the CTA band enlarged in the foreground. "SAK 题库" appears as the final brand line, followed by "开始今天的学习". A dark `#111827` button locks into place with "登录 / 注册".

**Mood direction:** confident close, practical conversion.

**Assets:** `scroll-000.png`, `svg-580c2e9b.svg`.

**Animation choreography:** screenshot eases forward, final title rises, check icon draws, CTA button brightens, small accent dots settle into a clean final still. Final half second fades gently to `#F6F7F8`.

**Transition:** final fade only.

**Depth layers:** BG paper canvas; MG product screenshot; FG CTA band and final title.

**SFX cues:** clean chime on CTA lock; underscore resolves.

## Production Architecture

```text
ti-product-promo/
├── index.html
├── DESIGN.md
├── SCRIPT.md
├── STORYBOARD.md
├── narration.txt
├── narration.wav
├── narration.mp3
├── transcript.json
├── capture/
│   ├── screenshots/
│   ├── assets/
│   └── extracted/
└── snapshots/
```
