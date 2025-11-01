# Market Snapshot

It has been **{{.MinutesElapsed}} minutes** since you started trading. The current time is **{{.CurrentTime}}** and you've been invoked **{{.InvocationCount}} times**.

Below is a snapshot containing state data, price data, predictive signals, and account information (value, performance, positions).

**NOTE:** ALL OF THE PRICE OR SIGNAL DATA BELOW IS ORDERED: OLDEST → NEWEST

**Timeframes note:** Unless stated otherwise in a section title, intraday series are provided at **3‑minute intervals**. If a coin uses a different interval, it is explicitly stated in that coin’s section.

---

## CURRENT MARKET STATE FOR ALL COINS

{{.CoinSection}}

---

## ACCOUNT INFORMATION & PERFORMANCE

- **Current Total Return (percent):** {{.CurrentTotalReturnPercent}}
- **Available Cash:** {{.AvailableCash}}
- **Current Account Value:** {{.CurrentAccountValue}}

### Current live positions & performance

Each position is shown as JSON (symbol, quantity, entry_price, current_price, liquidation_price, unrealized_pnl, leverage, exit_plan, confidence, risk_usd, notional_usd):

```json
{{ .Positions | toJSON }}
```, 