# NoteLLM 前端 UI 风格设计指南 (UI Style Guide)

这份文档总结了 NoteLLM 现有的全局前端 UI 风格，以便在未来设计或开发新页面时，保持整个项目的视觉一致性。

## 1. 核心设计理念 (Core Concept)
* **复古像素风 (Retro / Pixel Art)**：大量使用锐利的直角、粗线条、无平滑的字体，模拟8-bit/16-bit时代的电子游戏或早期计算机操作系统。
* **终端机与极客感 (Terminal OS)**：标题和标签常带有极客符号（如 `> 标题_`、`BIO.TXT`、`[ADMIN]`），制造一种在操作命令行或复古系统的沉浸感。
* **高对比度 (High Contrast)**：以纯黑色 (`#000000`) 的粗边框和实心阴影作为骨架，内部填充鲜艳的像素风强调色。

## 2. 全局色彩规范 (Color Palette)
项目中所有的颜色定义都在 `src/assets/styles/main.css` 里的 `:root` CSS 变量中，请**务必使用变量**而非硬编码颜色：

* **背景与排版**：
  * `--nl-bg`: `#f8f6f0` (米白色/复古纸张色，作为应用的主背景色)
  * `--nl-bg-grid`: `#e2e2e2` (用于背景上的像素点阵网格模式)
  * `--nl-surface`: `#ffffff` (卡片或弹出窗口的纯白背景)
  * `--nl-border`: `#000000` (统一的极黑粗边框)
* **强调色 (Accent Colors)**：
  * `--nl-primary`: `#4f46e5` (靛蓝色，主色调，用于主要操作)
  * `--nl-secondary`: `#ec4899` (亮粉色，次色调，用于高亮文字或特殊图标)
  * `--nl-accent`: `#10b981` (像素绿，用于表示成功、在线、完成状态)
  * `--nl-warning`: `#f59e0b` (琥珀黄，用于加载中、警告状态)
  * `--nl-danger`: `#ef4444` (警示红，用于错误、删除、离线状态)

## 3. 字体规范 (Typography)
同样定义在 `main.css` 中，针对中文环境进行了后备字体处理：
* `--font-display`: 用于大标题（如 `h1` - `h6`），英文字体采用 "Press Start 2P"。
* `--font-body`: 用于正文阅读，英文字体采用 "VT323"（一种高瘦的终端字体）。
* `--font-ui`: 用于按钮、标签、输入框。
* **特点**：全局禁用了字体平滑 (`-webkit-font-smoothing: none`)，以确保中文回退字体（如宋体 SimSun）在屏幕上展现出锯齿状的“像素感”。

## 4. 组件交互与形状 (Components & Shadows)
* **边框 (Borders)**：全站所有交互元素（卡片、按钮、输入框、头像）均使用直角（`border-radius: 0`）和 `2px` 到 `4px` 的纯黑边框。
* **实心阴影 (Solid Shadows)**：
  * 常规状态：使用无模糊半径的实心黑色阴影，如 `box-shadow: 4px 4px 0px 0px #000000;`
  * 悬浮 (Hover) 状态：元素向左上角偏移 (`translate(-2px, -2px)`)，同时阴影变大 (`6px 6px`)，制造强烈的按压浮动感。
  * 按压 (Active) 状态：元素向右下角按下 (`translate(2px, 2px)`)，阴影消失 (`0px 0px`)。
* **内阴影 (Inset Shadows)**：用于内容展示框、进度条轨道、代码块，模拟屏幕向内凹陷的感觉（例如 `box-shadow: inset 2px 2px 0px rgba(0,0,0,0.1)`）。

## 5. 特色 UI 元素 (Special Elements)
当设计新页面时，可以组合使用以下复古设计：
1. **复古视窗 (Retro Windows)**：卡片顶部带有一条深色（或纯黑）的标题栏，标题栏里写上类似 `> 设置.exe` 的白字，模拟早期 Windows/Mac 视窗。
2. **打字机/闪烁光标**：通过 CSS `@keyframes step-end` 制作光标的闪烁效果（可参考账户页的 `LOADING_PROFILE_DATA...` 提示）。
3. **点阵网格与 CRT 遮罩**：全局已通过 `App.vue` 中的 `.crt-overlay` 增加了屏幕扫描线效果，新页面尽量保持留白，让背景的网格露出来。
4. **进度与加载**：避免使用圆滑的转圈动画，改用区块填充式的进度条（带 `steps()` 过渡），或者方块闪烁。

## 6. 开发建议 (Dev Tips)
* 新建视图 (View) 时，外层通常包裹一个居中的容器。
* 尽量复用全局的 `.card` 和 `.btn` (`.btn-primary`, `.btn-danger` 等) 样式，它们已经内置好了符合此风格的边框和弹跳阴影动画。
* 遇到需要图标的地方，优先使用简单的 ASCII 字符（如 `>`,`_`,`[]`,`X`）、Emoji，或是由直方块画成的 SVG，避免使用现代、圆润的字体图标库。