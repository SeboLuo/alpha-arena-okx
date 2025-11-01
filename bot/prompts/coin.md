### ALL {{.Symbol}} DATA

- current_price: **{{.CurrentPrice}}**
- current_ema20: **{{.CurrentEMA20}}**
- current_macd: **{{.CurrentMACD}}**
- current_rsi (7 period): **{{.CurrentRSI7}}**

In addition, latest {{.Symbol}} open interest and funding rate for perps:

- Open Interest: Latest: **{{.OI_Latest}}**, Average: **{{.OI_Avg}}**
- Funding Rate: **{{.FundingRate}}**

**Intraday series (by minute, oldest → latest):**

Mid prices:

```json
{{ .MidPrices | toJSON }}
```

EMA (20-period):

```json
{{ .EMA20Series | toJSON }}
```

MACD:

```json
{{ .MACDSeries | toJSON }}
```

RSI (7-Period):

```json
{{ .RSI7Series | toJSON }}
```

RSI (14-Period):

```json
{{ .RSI14Series | toJSON }}
```

**Longer‑term context (4‑hour timeframe):**

- 20-Period EMA: **{{.EMA20_4h}}** vs. 50-Period EMA: **{{.EMA50_4h}}**
- 3-Period ATR: **{{.ATR3_4h}}** vs. 14-Period ATR: **{{.ATR14_4h}}**
- Current Volume: **{{.CurrentVolume_4h}}** vs. Average Volume: **{{.AvgVolume_4h}}**

MACD (4h):

```json
{{ .MACD4h | toJSON }}
```

RSI (14-Period, 4h):

```json
{{ .RSI14_4h | toJSON }}
```