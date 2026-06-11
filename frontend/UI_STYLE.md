# FishSniper 前端 UI 風格說明

本文件以高階語言描述 FishSniper 前端目前實際呈現的視覺與互動風格，供設計、開發與後續頁面擴充時對齊。技術棧為 **React + Tailwind CSS v4**；樣式以 utility class 直接寫在元件中，尚未抽成全域 design token 或 component library。

---

## 1. 產品氣質

FishSniper 是一款 **夜間使用的戰術型釣魚助手**：深色底、高對比、資料導向，帶一點「指揮中心／現場手冊」的語彙，而不是休閒戶外或卡通釣魚 App 的調性。

使用者應感受到：

- **專業、冷靜、可掃讀**：表單與報告都以結構化區塊呈現，標籤多用大寫、寬字距的小標。
- **環境感**：核心功能頁背景有微弱的翠綠、天藍、靛紫 radial glow，暗示天氣、水域與 AI 運算，但不搶內容。
- **行動導向**：主要 CTA 使用實心翠綠（emerald），在深色 UI 中一眼可辨。

品牌主色與 ui-ux-pro-max 對「深色 OLED + 綠色正向指示」的建議一致；背景 `#020617`、CTA `#22C55E` 與現有實作高度吻合。

---

## 2. 雙層視覺架構

前端存在 **兩套互補但刻意分層** 的視覺語言，依頁面職責選用。

### 2.1 應用外殼（App Shell）

**適用**：登入／註冊、Onboarding、Settings、頂部導覽列。

**特徵**：

- 全頁 `gray-950` 純深底，文字 `gray-100`。
- 邊框與分隔以 `gray-800` 為主，圓角偏小（`rounded-md`）。
- 輸入框：`bg-gray-900` + `border-gray-800`，focus 時 `border-emerald-500`。
- 主按鈕：實心 `bg-emerald-500`，hover `emerald-400`，文字 `gray-950`。
- 導覽 active 狀態：半透明翠綠底 `emerald-500/15` + `text-emerald-400`。

這一層 **簡潔、通用、低裝飾**，負責身份、設定與路由，不搶核心功能的「戰術感」。

### 2.2 玻璃控制台（Glass Console）

**適用**：Strategy 表單、My Logs、Strategy Report。

**特徵**：

- 內容區包在 **大圓角容器**（`rounded-[2rem]`）內，底色 `#020617`，外框 `border-white/10`。
- 背景疊加 **多點 radial gradient**（翠綠／天藍／靛紫，低透明度），營造深度但不影響可讀性。
- 卡片使用 **毛玻璃面板**：半透明白底 `bg-white/[0.06]`、`backdrop-blur-2xl`、細白邊 `border-white/15`、深陰影。
- 色彩語彙以 **slate** 為主（`slate-50`～`slate-500`），比 shell 的 gray 更冷、更「儀表板」。

Strategy 與 Logs 共用同一套 panel／input／chip class 常數，視覺上互為姊妹頁；Report 則是同一世界觀下的 **「Field Manual 輸出物」** 變體（見 §5）。

---

## 3. 色彩語意

| 角色 | 典型用途 | 視覺意涵 |
|------|----------|----------|
| **Emerald（翠綠）** | 品牌字、主 CTA、active 導覽、focus ring、推薦序號、Fish state 區塊 | 成功、可行動、AI 正向輸出 |
| **Slate（冷灰）** | 正文、標籤、邊框、muted 說明 | 中性資訊、控制台基調 |
| **Sky（天藍）** | Report 中的 Reference log（RAG）區塊 | 個人歷史紀錄、外部脈絡 |
| **Amber（琥珀）** | Strategy fallback、天氣載入失敗提示 | 可恢復的警告 |
| **Rose（玫瑰）** | Strategy 硬錯誤 banner | 請求失敗 |
| **Fuchsia（品紅）** | My Logs 表單驗證與列表錯誤（含 glow text-shadow） | 強調欄位錯誤，比 rose 更「霓虹」 |
| **Red** | Delete Account 等破壞性操作 | 危險、不可逆 |

**原則**：功能狀態用 **色相區分**，正文仍保持 slate 系；避免用顏色作為唯一資訊載體（錯誤需搭配文字）。

---

## 4. 排版與資訊層級

### 4.1 字體

目前 **未載入自訂 web font**，依賴系統 sans-serif。層級靠 **字級、字重、字距、大小寫** 區分，而非字體家族。

### 4.2 典型層級

| 層級 | 用途 | 風格要點 |
|------|------|----------|
| **Eyebrow / Chip** | 「FishSniper Control Room」、meta 標籤 | 極小字、uppercase、寬 tracking；chip 為圓角 pill + 細邊框 |
| **Section title** | WEATHER SOURCE、Conditions | `text-xs`、semibold、uppercase、`tracking-[0.14em～0.18em]`、`text-slate-300` 或語意色 |
| **Page title** | Bass Strategy Console、Tactical Readout | `text-2xl`～`text-3xl`、semibold/bold、`tracking-tight` |
| **Body** | 說明、表單值、報告段落 | `text-sm`，次要 `text-slate-400` |
| **Footer / meta** | 產生時間、RAG 標記 | `text-xs`、`text-slate-500` |

Report 頁標題區採 **「手冊眉題 + 大標」** 結構：小字 muted eyebrow（FishSniper · Field Manual）+ 主標（Tactical Readout，目前仍帶 uppercase 與較寬 tracking）。

### 4.3 容器寬度

- 頂部導覽與 Settings：`max-w-5xl` 居中。
- Strategy／Logs／Report 外層：`max-w-6xl`。
- Strategy 表單主欄：`max-w-2xl` 居中，避免寬螢幕上欄位過長。
- Report 文件本體：接近 **A4 比例**（`max-w-[210mm]`），強調「可閱讀的戰報」而非全寬儀表板。

---

## 5. 表面、間距與卡片層級

### 5.1 玻璃面板（Hero / 區塊外殼）

- 大面板：`rounded-3xl`、`p-5`、強 blur 與深 shadow。
- 用於頁首 hero、表單 section、log 列表項、loading skeleton。

### 5.2 表單 section（Strategy / Logs）

- Section 與 hero **共用同一套大 glass panel**（`rounded-3xl`、`p-5`、強 blur）。
- Section 標題：`text-xs` uppercase + 寬 tracking。
- 表單欄位以 `space-y-4` 或 `space-y-3.5` 分隔；輸入框本身為 `rounded-xl` slate 深底。
- *規劃中改進*：section 可改為較輕的 `rounded-xl border-white/10 bg-white/5 p-6`，與 hero 大 panel 拉開層級。

### 5.3 報告內嵌面板（Field Manual）

- 較緊湊的 `rounded-xl` 子面板、`px-4 py-3.5`、略深底 `bg-slate-950/55`。
- 推薦項目以 **編號 badge（翠綠方塊）+ 標題 + 副標 + 技法段落** 垂直堆疊。
- 主內容區：**Conditions（左）／Recommended presentations（右）**；目前桌面為約 **38% / 62%** 非等寬雙欄，整份文件接近 A4 寬度。

### 5.4 間距節奏（概略）

- 頁內 section 之間：`space-y-5`。
- 卡片內欄位：`gap-4`。
- 標籤與輸入：`gap-1.5`（field label 縱向 flex）。

---

## 6. 元件與互動模式

### 6.1 表單控制項

- 輸入／select：`rounded-xl`、深底 `bg-slate-950/70`、邊 `border-slate-600/50`。
- Focus：`border-emerald-400` + `ring-emerald-500/25`（無 outline 預設，靠 ring 顯示焦點）。
- Radio 模式切換：可點整列 label 卡片，hover 邊框略亮。

### 6.2 按鈕

- **Primary**：大圓角 `rounded-2xl`、全寬、翠綠底、深色字、帶綠色 glow shadow；disabled 降 opacity。
- **Secondary / ghost**：細邊框、半透明底、hover 邊框轉 emerald。
- Shell 頁 primary 維持較平的 `rounded-md` emerald 實心按鈕。

### 6.3 導覽

- 文字連結 + `transition-colors duration-200`。
- 可點元素加 `cursor-pointer`（列表 expandable card、back link 等）。

### 6.4 載入與空狀態

- Skeleton：`animate-pulse` 灰色條 + 說明文字；Logs 頁尊重 `motion-reduce:animate-none`。
- 空列表：置中 glass panel + muted 文案。

### 6.5 圖示

- 使用 **inline SVG**（如 Settings 齒輪），固定 `viewBox="0 0 24 24"`。
- **不以 emoji 充當 UI 圖示**。

---

## 7. 頁面類型一覽

| 頁面 | 視覺層 | 核心布局 | 語意 |
|------|--------|----------|------|
| Sign-in / Onboarding | Shell | 垂直居中、窄欄 `max-w-md` | 進入產品前的最小摩擦 |
| App Shell 導覽 | Shell | Sticky top bar、`max-w-5xl` | 全局路由與身份 |
| Strategy | Glass Console | Hero + 窄表單 + 全寬 CTA | 「控制室」輸入戰術參數 |
| Strategy Report | Glass Console + Field Manual | Back link + A4 感文件 | 「戰術 readout」輸出 |
| My Logs | Glass Console | Hero + 可展開 log 卡片 + modal 表單 | 與 Strategy 同控制台，錯誤更霓虹 |
| Settings | Shell | 側欄 + 內容，`max-w-5xl` | 設定與破壞性操作分離 |

---

## 8. 文案與語調（UI 文字）

- 英文 UI copy 偏 **簡短、指令式**：Control Room、Tactical Readout、Generate report。
- Section 標題常 **全大寫 + 寬字距**，像儀表或軍規手冊章節名。
- 錯誤訊息具體、可行動（例如天氣 503 時提示改 Manual 或修正 profile region）。

---

## 9. 響應式與無障礙慣例

- 小螢幕：flex-wrap、grid 改單欄；Settings 子導覽改垂直堆疊。
- 可展開 log 卡片：`role="button"`、`tabIndex={0}`、Enter/Space 觸發。
- Report / 表單區塊使用 `aria-label` / `aria-labelledby`。
- 互動過渡集中在 **150–200ms** 的 color transition，避免 layout shift 型 hover。

---

## 10. 刻意避免的方向

與現有 codebase 及 ui-ux-pro-max 檢查清單對齊，新頁面應避免：

- 預設亮色主題或低對比 gray-on-gray 正文。
- 玻璃卡片在淺色底上使用過低 opacity（本產品以深色為主）。
- Emoji 圖示、不一致的 icon 尺寸、缺少 hover/focus 的可點元素。
- 同一功能頁混用 Shell 的 `gray-900` 輸入與 Console 的 slate glass 語言（Settings 除外）。

---

## 11. 實作備註（給開發者）

- 樣式常數目前 **分散在各 page 元件內**（如 `glassPanelClassName`、`inputClassName`），尚未集中至 `src/ui/` 或 CSS variables。
- `index.css` 僅 `@import "tailwindcss"`，無 `@theme` 自訂 token；`text-muted-foreground` 等 shadcn 語意 class **尚未定義**，muted 文字以 `text-slate-400` / `text-gray-500` 代替。
- Strategy Report 資料存於 **sessionStorage 單槽**，Report 頁無資料時 redirect 回 Strategy。

---

## 12. 延伸建議（非現狀，供對齊用）

若後續要統一設計系統，可優先：

1. 將 Glass Console token 抽成共用模組（panel、chip、input、banner）。
2. 為 Report 與 Console 建立 `design-system/pages/` 級別的頁面 override（延續 ui-ux-pro-max persist 模式）。
3. 評估是否引入 **Fira Sans / Fira Code** 以強化「戰術儀表板」字體個性（目前為系統字體）。

---

*文件版本：依 `frontend/src` 現況整理（Strategy、Logs、Report、Shell、Auth）。mock HTML 原型位於 `frontend/public/mock-strategy-report/`，Report 正式 UI 以 Variant B（Field Manual）為準。*
