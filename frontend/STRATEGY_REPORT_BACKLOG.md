# Strategy Report — 後端 / LLM Payload 待辦

前端 UI 已預留或規劃以下能力，**需後端 schema 與 prompt 擴充後**才能完整呈現。目前報告頁以前端既有欄位推導展示，不捏造資料。

## 1. Today's Pattern 結論卡（結構化）

**現狀：** 使用 `fish_state` 首句 + `confidence_note` + request summary 推導 hero 文案。

**理想 payload（建議新增）：**

```json
{
  "pattern_headline": "Post-Spawn Largemouth",
  "pattern_subline": "Shallow Flats + Windblown Banks",
  "confidence_pct": 82
}
```

或合併為 `todays_pattern: { title, subtitle, confidence_pct }`。

## 2. Likely Holding Zone（魚在哪）

**現狀：** 未顯示。FishSniper 核心差異化尚未在報告中回答「魚在哪」。

**理想 payload：**

```json
{
  "holding_zones": [
    { "label": "Windblown rocky point", "weight_pct": 70 },
    { "label": "First drop outside spawning flat", "weight_pct": 20 },
    { "label": "Isolated wood in 2m depth", "weight_pct": 10 }
  ]
}
```

可選：`holding_zone_diagram_hint`（岸線 / 水深簡圖結構化座標）供前端 SVG 渲染。

## 3. Presentation 分級與 Reason 欄位

**現狀：** 三筆 `recommendations[]` 依序標為 Primary / Backup / Alternate；`retrieve_technique` 顯示為 Reason。

**理想 payload：**

```json
{
  "recommendations": [
    {
      "tier": "primary",
      "lure_type": "Bladed Jig",
      "lure_color": "...",
      "reason": "Cloud cover + low pressure are likely pushing feeding fish onto shallow flats.",
      "retrieve_technique": "..."
    }
  ]
}
```

`reason` 與 `retrieve_technique` 分離後，UI 可更清楚對應戰術報告語彙。

## 4. Conditions 精簡模式

**現狀：** 左欄 compact 列表；使用者已從 mission brief 輸入的 region / temp 等仍顯示供對照。

**可選：** 後端回傳 `conditions_summary_one_liner` 供 hero 或側欄單行摘要，減少重複感。

## 5. 數值 Confidence

**現狀：** 若 `confidence_note` 含 `%` 則提取顯示，否則顯示原文。

**理想：** 固定 `confidence_pct: number` 欄位，避免從 prose 解析。

---

*最後更新：對應 Tactical Readout UI 重構（Field Manual → 戰術報告重心）。*
