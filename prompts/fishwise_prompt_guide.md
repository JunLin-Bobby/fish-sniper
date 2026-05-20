# FishSniper — 產品技術規格文件

> 版本：v1.3
> 產品定位：針對 Bass 路亞釣魚愛好者的 AI 策略助手。使用者輸入當日釣場環境條件，AI 結合個人歷史釣魚 log 與即時天氣，生成針對 Bass 的具體路亞選擇與操作策略。

---

## 技術棧總覽

| 層級 | 技術 | 部署 | 費用 |
|------|------|------|------|
| 前端 | React + Tailwind CSS | Cloudflare Pages | 免費 |
| 後端 | Python + FastAPI | Railway | 免費 tier |
| AI Agent | LangGraph + Gemini API | Railway（同後端） | ~$3–5/月 |
| 向量資料庫 | Pinecone | 雲端 SaaS | 免費 tier |
| 關聯式資料庫 | Supabase (PostgreSQL) | 雲端 SaaS | 免費 tier |
| 天氣 API | OpenWeatherMap | 雲端 SaaS | 免費 tier |
| Email 發送 | Resend | 雲端 SaaS | 免費 tier |
| AI Tracing | Langfuse | 雲端 SaaS | 免費 tier |
| CI/CD | GitHub Actions | GitHub | 免費 |

---

## 功能模組索引

1. [AUTH — Email OTP 認證](#1-auth--email-otp-認證)
2. [ONBOARDING — 首次設定](#2-onboarding--首次設定)
3. [WEATHER — 即時天氣擷取](#3-weather--即時天氣擷取)
4. [AGENT — LangGraph 七步驟策略生成](#4-agent--langgraph-七步驟策略生成)
5. [RAG — 釣魚 Log 向量搜尋](#5-rag--釣魚-log-向量搜尋)
6. [LOG — 釣魚 Log CRUD](#6-log--釣魚-log-crud)
7. [STRATEGY — 策略主頁面](#7-strategy--策略主頁面)
8. [TRACING — Langfuse 可觀測性](#8-tracing--langfuse-可觀測性)

---

## 1. AUTH — Email OTP 認證

### 功能描述
使用者以 email 收取一次性驗證碼（OTP）完成註冊與登入，無需密碼。

### API 規格

**POST /auth/send-otp**
```json
Request:
{ "email": "user@example.com" }

Response 200:
{ "message": "OTP sent" }

Response 429:
{ "error": "Too many requests, please wait 60 seconds" }
```

**POST /auth/verify-otp**
```json
Request:
{ "email": "user@example.com", "otp": "482910" }

Response 200:
{
  "access_token": "eyJhbGci...",
  "is_new_user": true
}

Response 400:
{ "error": "Invalid or expired OTP" }
```

### 後端邏輯
- OTP 使用 `secrets.randbelow(1000000)` 生成，補零格式化為 6 位字串
- 存入 Supabase `otp_codes` 表，`expires_at` = 當前時間 + 10 分鐘
- 同一 email 60 秒內只能發送一次（rate limit）
- 驗證成功後立即刪除該筆 OTP 記錄
- 驗證成功後，若 `users` 表無此 email 則新增用戶，回傳 JWT

### Supabase 資料表

**users**
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**otp_codes**
```sql
CREATE TABLE otp_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL,
  code TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### Resend 整合
```python
resend.Emails.send({
  "from": "FishSniper <no-reply@yourdomain.com>",
  "to": user_email,
  "subject": f"Your FishSniper verification code: {otp}",
  "text": f"""
Hi there,

Your FishSniper verification code is: {otp}

This code expires in 10 minutes.
If you didn't request this, you can safely ignore this email.

— The FishSniper Team
  """
})
```

### 前端畫面規格

**Step 1 — Email 輸入**
- 標題：「Sign in to FishSniper」
- 副標題：「Enter your email to receive a verification code」
- Email input（type=email，autofocus），placeholder：`you@example.com`
- 按鈕：「Send code」
- 錯誤提示：`Please enter a valid email address`

**Step 2 — OTP 輸入**
- 標題：「Check your email」
- 副標題：`We sent a 6-digit code to {email}`
- 6 個獨立 input 格（每格一位數，自動跳格）
- 按鈕：「Verify」
- 重新發送連結：`Resend code`（60 秒倒數後才可點擊）
- 錯誤提示：`Invalid or expired code. Please try again.`

---

## 2. ONBOARDING — 首次設定

### 功能描述
新用戶首次登入後完成一次性基本設定，儲存後進入主畫面。

### API 規格

**POST /users/preferences**
```json
Request Header: Authorization: Bearer {token}

Request:
{
  "region": "Boston"
}

Response 200:
{ "message": "Preferences saved" }
```

**GET /users/preferences**
```json
Response 200:
{
  "region": "Boston",
  "onboarding_completed": true
}
```

### Supabase 資料表

**user_preferences**
```sql
CREATE TABLE user_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  region TEXT NOT NULL,
  onboarding_completed BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### 前端畫面規格
- 頁面標題：「Set up your fishing profile」
- **地區欄位**：text input，placeholder `City name, e.g. Boston`
- **確認按鈕**：「Start sniping」，地區為必填

---

## 3. WEATHER — 即時天氣擷取

### 功能描述
根據用戶儲存的地區，從 OpenWeatherMap API 取得當前天氣資料，供 Agent Step 2 使用。

### API 規格

**GET /weather/current**
```json
Response Header: Authorization: Bearer {token}

Response 200:
{
  "temperature_c": 18.5,
  "condition": "Cloudy",
  "condition_code": "cloudy",
  "wind_speed_ms": 3.2,
  "pressure_hpa": 1008,
  "humidity_pct": 72,
  "fetched_at": "2026-04-24T08:30:00Z"
}

Response 503:
{ "error": "Weather service unavailable" }
```

### 後端邏輯
- Endpoint：`https://api.openweathermap.org/data/2.5/weather?q={region}&units=metric&appid={key}`
- FishSniper 使用的欄位對應：

| OpenWeatherMap 欄位 | FishSniper 欄位 |
|---------------------|----------------|
| `main.temp` | `temperature_c` |
| `main.pressure` | `pressure_hpa` |
| `wind.speed` | `wind_speed_ms` |
| `weather[0].id` | → 對應 `condition_code` |

- weather id 對應表：

| OpenWeatherMap code | condition_code |
|---------------------|----------------|
| 800 | `sunny` |
| 801–804 | `cloudy` |
| 500–531 | `rainy` |
| 200–232 | `stormy` |
| 600–622 | `snowy` |

- 結果快取 30 分鐘（in-memory dict + timestamp）
- API 失敗時回傳 503，Agent Step 2 收到 503 時使用使用者手動輸入的天氣資料繼續

---

## 4. AGENT — LangGraph 七步驟策略生成

### 功能描述
FishSniper 的核心 AI 功能。以 LangGraph 編排七個步驟，結合使用者輸入、即時天氣、個人釣魚 log，生成針對 Bass 路亞釣魚的具體策略。

### LangGraph State 格式

```python
from typing import TypedDict, Optional

class FishSniperAgentState(TypedDict):
    # ── 使用者輸入（前端傳入）──
    user_id: str
    fishing_location: str         # 釣場名稱，用於顯示與 RAG filter
    water_depth_m: float
    target_species: str           # 固定 "bass"
    fishing_scene: str            # "river" | "lake" | "reservoir" | "pond"

    # ── Step 2 從 user_preferences 讀取並補齊 ──
    region: str                   # 從 user_preferences 自動帶入，不由前端傳入

    # ── Step 2 補齊的天氣資料 ──
    temperature_c: float
    pressure_hpa: int
    wind_speed_ms: float
    condition_code: str           # "sunny" | "cloudy" | "rainy" | "stormy"

    # ── Step 3 RAG 搜尋結果 ──
    retrieved_log_count: int
    retrieved_logs: list[dict]    # 最多 3 筆

    # ── Step 4 組裝的 prompt ──
    system_prompt: str
    has_personal_log: bool

    # ── Step 5/6 LLM 輸出 ──
    raw_llm_output: str
    retry_count: int              # 最多重試 2 次
    llm_output_valid: bool

    # ── Step 7 最終結果 ──
    lure_type: str
    lure_color: str
    retrieve_speed: str
    target_zone: str
    time_window: str
    confidence_note: str          # 有 log 時說明參考了哪些記錄
    fallback: bool                # True 時代表 LLM 驗證失敗，回傳降級訊息
```

### API 規格

**POST /agent/strategy**
```json
Request Header: Authorization: Bearer {token}

Request:
{
  "fishing_location": "Charles River",  // user-entered spot name, used for display and RAG filter
  "water_depth_m": 3.0,
  "fishing_scene": "river",
  "target_species": "bass",

  // Optional — only required if user chooses to enter weather manually
  // or as fallback when OpenWeatherMap returns 503
  "manual_weather": {
    "temperature_c": 18.5,
    "condition_code": "cloudy",
    "wind_speed_ms": 2.1,
    "pressure_hpa": 1008
  }
}

// Note: `region` is NOT included in this request.
// The backend reads `region` from user_preferences automatically to fetch weather.

Response 200（成功）:
{
  "lure_type": "Soft plastic swimbait",
  "lure_color": "Green pumpkin",
  "retrieve_speed": "Slow, 1 rotation per 2 seconds",
  "target_zone": "Rocky bottom near submerged structure",
  "time_window": "Early morning 05:30–07:30",
  "confidence_note": "Based on 2 past logs with similar pressure and depth",
  "battle_plan_summary": "## Fish Condition & Behavior\n\nAt 18.5°C...(markdown content)",
  "weather_snapshot": {
    "temperature_c": 18.5,
    "pressure_hpa": 1008,
    "wind_speed_ms": 2.1,
    "condition_code": "cloudy"
  },
  "rag_logs_used": 2,
  "generated_at": "2026-04-24T08:00:00Z",
  "fallback": false
}

Response 200（fallback，LLM 驗證失敗）:
{
  "fallback": true,
  "message": "Could not generate a confident strategy. Try again or adjust your input.",
  "generated_at": "2026-04-24T08:00:00Z"
}
```

### LangGraph 七步驟流程

**Step 1 — validate_user_input**
- 檢查 `fishing_location`、`water_depth_m`、`fishing_scene`、`target_species` 是否完整
- 任一欄位缺失 → 直接回傳 400，不進入 Agent 流程

**Step 2 — fetch_weather_data（Tool Call）**
- 從 `user_preferences.region` 讀取城市名稱（不從 request body 傳入）
- 呼叫 `/weather/current` 取得天氣資料
- 寫入 State：`temperature_c`、`pressure_hpa`、`wind_speed_ms`、`condition_code`
- 失敗時 → 從 request body 的 `manual_weather` 取用（若有提供），否則回傳 503

**Step 3 — search_fishing_log（RAG）**
- 以使用者輸入的條件組合 query 文字，搜尋 Pinecone
- Filter：`user_id`（僅自己的 log）**且** `fishing_location`（metadata 欄位名與 DB 欄位名一致）等於本次請求 body 的 `fishing_location`（字串需與建立 log 時相同才會命中）
- `top_k = 3`，結果寫入 `retrieved_logs`
- 若無命中（`retrieved_log_count == 0`）→ 設定 `has_personal_log = false`，**不強化個人化**，改走一般最佳實務 prompt，流程繼續

**Step 4 — build_system_prompt**
- 有 log（`has_personal_log == true`）：
```
You are an expert Bass lure fishing coach.
The angler has fished in similar conditions before. Here are their past records:

{retrieved_logs}

Use these records to personalize your strategy. If a past record shows success, reinforce that approach.
If a past record shows failure, explicitly warn against it.
```
- 無 log（`has_personal_log == false`）：
```
You are an expert Bass lure fishing coach specializing in lure selection and retrieval techniques.
The angler has no past records for similar conditions.
Provide a general best-practice strategy based on the environmental conditions provided.
```
- User prompt（兩種情況共用）：
```
Environmental conditions:
- Weather region (from profile): {region}
- Fishing spot (today): {fishing_location}
- Fishing scene: {fishing_scene}
- Water depth: {water_depth_m}m
- Temperature: {temperature_c}°C
- Pressure: {pressure_hpa} hPa
- Wind speed: {wind_speed_ms} m/s
- Weather: {condition_code}
- Target species: Bass

Respond ONLY with a valid JSON object containing exactly these fields:
{
  "lure_type": "...",
  "lure_color": "...",
  "retrieve_speed": "...",
  "target_zone": "...",
  "time_window": "...",
  "confidence_note": "..."
}
Do not include any explanation outside the JSON.
```

**Step 5 — generate_lure_strategy（LLM Call）**
- 呼叫 **Gemini API**（例如 `gemini-2.5-flash`，與 Langfuse 追蹤設定一致），傳入 Step 4 組裝的 system prompt 和 user prompt
- 將原始回應寫入 `raw_llm_output`

**Step 6 — validate_llm_output**
- 嘗試 `json.loads(raw_llm_output)`
- 驗證必填欄位：`lure_type`、`lure_color`、`retrieve_speed`、`target_zone`、`time_window`、`confidence_note` 全部存在且為非空字串
- 驗證失敗 → `retry_count += 1`，回到 Step 5 重試
- `retry_count >= 2` → 設定 `fallback = true`，跳到 Step 7

**Step 7 — format_final_response**
- `fallback == true`：回傳降級訊息，跳過 summary 生成
- `fallback == false`：
  - 先組裝結構化欄位（`lure_type`、`lure_color` 等）
  - 接著發起第二次 LLM 呼叫（**Gemini API**，與 Step 5 相同設定原則），生成 `battle_plan_summary`
  - 兩者組裝完成後一次性回傳前端

**Step 7 — Second LLM Call：battle_plan_summary 生成**

System prompt：
```
You are an expert Bass fishing coach writing a shore fishing battle plan.
Write in the style of an experienced angler briefing a student before a session —
confident, specific, and educational. Use markdown formatting with clear section headers.

The angler's conditions today:
- Fishing spot: {fishing_location}
- Temperature: {temperature_c}°C
- Weather: {condition_code}
- Wind: {wind_speed_ms} m/s
- Fishing scene: {fishing_scene}
- Water depth: {water_depth_m}m

The AI has already determined the optimal strategy:
- Lure: {lure_type} in {lure_color}
- Retrieve: {retrieve_speed}
- Target zone: {target_zone}
- Best time window: {time_window}

Write a structured battle plan with EXACTLY these four sections:
1. Fish condition & behavior (1 paragraph, explain WHY bass behave this way today)
2. Target terrain features (3 numbered points, each with terrain name and reason)
3. Recommended depth (split by morning vs afternoon)
4. Lure selection & technique (focus on the recommended lure, explain how to work it
   in these conditions. Add one alternative if appropriate)

Language: English
Tone: Like a knowledgeable fishing buddy — direct, practical, enthusiastic
Do NOT use emoji anywhere in the response.
```

回傳欄位：`battle_plan_summary`（markdown 格式字串）

---

## 5. RAG — 釣魚 Log 向量搜尋

### Embedding 文字格式
```
On {date}, fished at {fishing_location} ({fishing_scene}) for Bass using {lure_type} in {lure_color}.
Water depth: {water_depth_m}m. Weather: {condition_code}, {temperature_c}°C,
wind {wind_speed_ms} m/s, pressure {pressure_hpa} hPa.
Result: {caught_count} bass caught. Notes: {notes}
```

### Pinecone 設定
- Index name：`fishsniper-logs`
- Dimension：768（Gemini `text-embedding-004` model）
- Metric：cosine
- Metadata：`user_id`、`fishing_scene`、`log_id`、**`fishing_location`**（與該筆 log 的 `fishing_logs.fishing_location` 相同，供策略頁 RAG 篩選）

### 搜尋邏輯
```python
query_text = (
    f"Bass lure fishing in {fishing_scene}, "
    f"water depth {water_depth_m}m, "
    f"{condition_code} weather, temperature {temperature_c}°C, "
    f"pressure {pressure_hpa} hPa"
)
results = pinecone_index.query(
    vector=embed(query_text),
    top_k=3,
    filter={
        "user_id": {"$eq": current_user_id},
        "fishing_location": {"$eq": fishing_location},
    },
    include_metadata=True
)
```

---

## 6. LOG — 釣魚 Log CRUD

### API 規格

**POST /logs**（新增 log）
```json
Request Header: Authorization: Bearer {token}

Request:
{
  "date": "2026-04-24",
  "fishing_location": "Charles River",
  "fishing_scene": "river",
  "water_depth_m": 3.0,
  "lure_type": "Soft plastic swimbait",
  "lure_color": "Green pumpkin",
  "retrieve_speed": "Slow",
  "caught_count": 2,
  "weight_kg": 1.4,
  "length_cm": 38.0,
  "weather_auto": true,
  "temperature_c": 18.5,
  "condition_code": "cloudy",
  "wind_speed_ms": 2.1,
  "pressure_hpa": 1008,
  "notes": "Best action near the bridge pillars at 6am"
}

Response 201:
{ "log_id": "uuid", "message": "Log saved" }
```

**GET /logs**（取得所有 log）
```json
Response 200:
{
  "logs": [
    {
      "log_id": "uuid",
      "date": "2026-04-24",
      "fishing_location": "Charles River",
      "fishing_scene": "river",
      "lure_type": "Soft plastic swimbait",
      "caught_count": 2,
      "created_at": "2026-04-24T09:00:00Z"
    }
  ]
}
```

**GET /logs/{log_id}**（取得單筆完整 log）

### Supabase 資料表

**fishing_logs**
```sql
CREATE TABLE fishing_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  fishing_location TEXT NOT NULL,
  fishing_scene TEXT NOT NULL,
  water_depth_m DECIMAL(4,1),
  lure_type TEXT,
  lure_color TEXT,
  retrieve_speed TEXT,
  caught_count INTEGER DEFAULT 0,
  weight_kg DECIMAL(5,2),
  length_cm DECIMAL(5,1),
  temperature_c DECIMAL(4,1),
  condition_code TEXT,
  wind_speed_ms DECIMAL(4,1),
  pressure_hpa INTEGER,
  notes TEXT,
  pinecone_synced BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### 前端畫面規格

**新增 Log 表單**
- 日期選擇器（預設今天）
- 釣場（`fishing_location`）：自由輸入，placeholder `e.g. Charles River`
- 釣場類型：單選 tag（River / Lake / Reservoir / Pond）
- 水深（m）：數字輸入
- 路亞類型：自由輸入，placeholder `e.g. Soft plastic swimbait`
- 路亞顏色：自由輸入，placeholder `e.g. Green pumpkin`
- 操作速度：自由輸入，placeholder `e.g. Slow retrieve`
- 釣獲數：整數輸入
- 重量（kg）：小數輸入
- 長度（cm）：小數輸入
- 天氣：Radio「Auto-fill」/ 「Manual」，手動時填氣溫、天氣狀況、風速、氣壓
- 備註：多行文字
- 按鈕：「Save log」

**Log 列表**
- 依日期降冪排列
- 每列顯示：日期、釣場（`fishing_location`）、路亞類型、釣獲數
- 點擊展開完整資訊

---

## 7. STRATEGY — 策略主頁面

### 功能描述
使用者輸入當日環境條件，觸發 Agent 生成 Bass 路亞策略。

### 頁面結構

**輸入區塊**
- 釣場地點（自由輸入，placeholder `e.g. Charles River`）— 對應 `fishing_location`
- 釣場類型（單選 tag）— 對應 `fishing_scene`
- 水深（數字輸入，單位 m）— 對應 `water_depth_m`
- 天氣資訊：Radio「Auto-fetch」（預設）/ 「Enter manually」
  - 手動時顯示：氣溫、天氣狀況下拉、風速、氣壓 → 對應 `manual_weather`
- 按鈕：「Snipe it」→ 觸發 POST /agent/strategy
- 地區（`region`）由後端從 `user_preferences` 自動讀取，**不在此頁面顯示或輸入**

**天氣摘要列（自動顯示）**
- 氣溫、天氣狀況、風速、氣壓
- 小字：`Updated at {time}`

**策略結果區塊（AI 生成）**

| 欄位 | Header |
|------|--------|
| `lure_type` | Lure |
| `lure_color` | Color |
| `retrieve_speed` | Retrieve |
| `target_zone` | Target zone |
| `time_window` | Best window |
| `confidence_note` | Based on |

**空白狀態（尚未產生過策略）**
- 結果區塊顯示提示文案（例）：`Enter your spot and tap Snipe it for today's strategy.`
- 可加次要說明（例）：`After you fish, save a log to personalize recommendations for this spot.`

**Loading 狀態**
- Skeleton loading，小字：`Analyzing conditions...`

**Fallback 狀態**
- 顯示：`Could not generate a strategy. Try adjusting your input.`

**底部導覽列**
- Tab 1：`Strategy`
- Tab 2：`My Logs`
- 右下角浮動按鈕「＋」：快速新增 log

---

## 8. TRACING — Langfuse 可觀測性

### 整合方式

```python
trace = langfuse.trace(
    name="bass-lure-strategy-generation",
    user_id=user_id,
    metadata={
        "region": region,
        "fishing_location": fishing_location,
        "fishing_scene": fishing_scene,
        "water_depth_m": water_depth_m
    }
)

# Step 2
span_weather = trace.span(name="fetch-weather-data")
span_weather.end(output=weather_data)

# Step 3
span_rag = trace.span(name="search-fishing-log")
span_rag.end(output={"retrieved_log_count": count, "log_ids": ids})

# Step 4
span_prompt = trace.span(name="build-system-prompt")
span_prompt.end(output={"has_personal_log": has_log})

# Step 5
gen_llm = trace.generation(
    name="generate-lure-strategy",
    input={"system_prompt": system_prompt},
    model="gemini-2.5-flash"
)
gen_llm.end(output=raw_output, usage=token_usage)

# Step 6
span_validate = trace.span(name="validate-llm-output")
span_validate.end(output={"valid": is_valid, "retry_count": retry_count})

trace.update(
    output=final_response,
    status="success" if not fallback else "fallback"
)
```

### 監控指標

| 指標 | 目標值 |
|------|--------|
| Agent 平均回應時間 | < 8 秒 |
| LLM token 用量 / 次 | < 2,000 tokens |
| Agent 成功率（非 fallback） | > 90% |
| RAG 命中 log 數 | 若該釣場字串（`fishing_location`）已有歷史 log，預期 ≥ 1 筆 |
| LLM 驗證首次通過率 | > 85% |

---

## 程式碼規範（每個提示詞的強制約束）

```
Code quality constraints (apply to all generated code):

1. NEVER expose API keys in frontend code. All external API calls must go through the FastAPI backend.
2. All async operations must have strict TypeScript interfaces. No `any` types.
3. Handle timeouts and errors gracefully. Provide fallback UI when AI generation fails.
4. Use functional components and separate business logic into custom hooks.
5. All environment variables must be read from `.env` files. Never hardcode secrets.
6. All Python functions must have type hints. Use Pydantic for all request/response validation.
7. Each LangGraph node must log its execution via Langfuse span or generation.
8. Database operations must handle connection errors and return meaningful HTTP status codes.
9. CORS must only allow the configured frontend origin, not wildcard `*`.
10. Generated code must be compatible with Docker multi-stage build and Railway deployment.
11. All code comments must be written in English.
12. All naming must follow Document as Code principles — names must be specific and self-explanatory.
    - Functions: describe the exact action and subject (e.g. `embedFishingLogToVector` not `embed`, `fetchCurrentWeatherByRegion` not `getWeather`, `generateBassLureStrategy` not `generate`)
    - Variables: reflect the exact data they hold (e.g. `retrievedFishingLogList` not `data`, `agentRetryCount` not `count`, `pineconeUpsertResult` not `result`)
    - React hooks: prefix with `use` and describe the resource (e.g. `useBassLureStrategy` not `useData`, `useFishingLogList` not `useLogs`)
    - API route handlers: name after the operation and resource (e.g. `handleCreateFishingLog` not `handleCreate`, `handleGenerateBassStrategy` not `handleStrategy`)
    - Avoid all generic names: `data`, `result`, `item`, `info`, `temp`, `obj`, `handle`, `process`, `manage`
```