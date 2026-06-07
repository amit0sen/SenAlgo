"""
Pine Script v6 Generator — SenAlgo by Amit Kumar Sen

Generates complete, compilable TradingView Pine Script v6 code for:
- Indicators (SMC, ICT, Elliott Wave, Volume Profile, Order Flow, ORB, CRT, etc.)
- Strategy scripts with entry/exit logic
- Multi-timeframe scripts
- Alert conditions

All generated scripts target //@version=6 syntax.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Strategy / Indicator templates
# ---------------------------------------------------------------------------
TEMPLATES: Dict[str, str] = {}


def _register(name: str, code: str) -> None:
    TEMPLATES[name] = code


# ---------------------------------------------------------------------------
# Template: SMC Order Block indicator
# ---------------------------------------------------------------------------
_register("smc_order_blocks", '''
//@version=6
indicator("SenAlgo — SMC Order Blocks", overlay=true, max_boxes_count=50)

// ── Inputs ──────────────────────────────────────────────────────────────────
swingLen    = input.int(5, "Swing Length", minval=2, maxval=20)
showBullOB  = input.bool(true, "Show Bullish OB")
showBearOB  = input.bool(true, "Show Bearish OB")
obExtend    = input.int(20, "OB Extend Bars")
bullColor   = input.color(color.new(color.green, 80), "Bullish OB Color")
bearColor   = input.color(color.new(color.red, 80),   "Bearish OB Color")

// ── Swing detection ─────────────────────────────────────────────────────────
var float swingHighPrice = na
var float swingLowPrice  = na
var int   swingHighBar   = na
var int   swingLowBar    = na

isSwingHigh = ta.pivothigh(high, swingLen, swingLen)
isSwingLow  = ta.pivotlow(low,  swingLen, swingLen)

if not na(isSwingHigh)
    swingHighPrice := isSwingHigh
    swingHighBar   := bar_index[swingLen]

if not na(isSwingLow)
    swingLowPrice := isSwingLow
    swingLowBar   := bar_index[swingLen]

// ── Structure: BOS / CHOCH ───────────────────────────────────────────────────
var bool bullishBias = false
bosUp   = close > swingHighPrice[1] and not na(swingHighPrice[1])
bosDown = close < swingLowPrice[1]  and not na(swingLowPrice[1])

if bosUp
    bullishBias := true
if bosDown
    bullishBias := false

// ── Order Block detection ────────────────────────────────────────────────────
// Bearish OB = last up-close candle before a BOS down
// Bullish OB = last down-close candle before a BOS up
var box[] bearBoxes = array.new<box>()
var box[] bullBoxes = array.new<box>()

if bosDown and showBearOB
    b = box.new(bar_index[1], high[1], bar_index[1] + obExtend, low[1],
                border_color=color.red, bgcolor=bearColor, extend=extend.right)
    array.push(bearBoxes, b)

if bosUp and showBullOB
    b = box.new(bar_index[1], high[1], bar_index[1] + obExtend, low[1],
                border_color=color.green, bgcolor=bullColor, extend=extend.right)
    array.push(bullBoxes, b)

// ── Labels ───────────────────────────────────────────────────────────────────
if bosUp
    label.new(bar_index, low, "BOS ↑", style=label.style_label_up,
              color=color.green, textcolor=color.white, size=size.small)
if bosDown
    label.new(bar_index, high, "BOS ↓", style=label.style_label_down,
              color=color.red, textcolor=color.white, size=size.small)

// ── Alerts ───────────────────────────────────────────────────────────────────
alertcondition(bosUp,   "SenAlgo BOS Up",   "Bullish BOS detected — SenAlgo")
alertcondition(bosDown, "SenAlgo BOS Down", "Bearish BOS detected — SenAlgo")

plotshape(bosUp,   style=shape.triangleup,   location=location.belowbar,
          color=color.green, size=size.small)
plotshape(bosDown, style=shape.triangledown, location=location.abovebar,
          color=color.red,   size=size.small)
''')


# ---------------------------------------------------------------------------
# Template: ICT Kill Zones + OTE
# ---------------------------------------------------------------------------
_register("ict_kill_zones", '''
//@version=6
indicator("SenAlgo — ICT Kill Zones & OTE", overlay=true)

// ── Inputs ──────────────────────────────────────────────────────────────────
showAsia      = input.bool(true,  "Show Asia KZ")
showLondon    = input.bool(true,  "Show London KZ")
showNewYork   = input.bool(true,  "Show New York KZ")
asiaColor     = input.color(color.new(color.orange, 85), "Asia Color")
londonColor   = input.color(color.new(color.blue,   85), "London Color")
nyColor       = input.color(color.new(color.purple, 85), "New York Color")
otelevel1     = input.float(0.620, "OTE Level 1 (Fib)")
otelevel2     = input.float(0.786, "OTE Level 2 (Fib)")
swingLen      = input.int(20, "OTE Swing Length")

// ── Kill Zone shading ────────────────────────────────────────────────────────
// UTC offsets — adjust timezone() to match your chart
inAsia(t)    => hour(t, "UTC") >= 20 and hour(t, "UTC") < 24
inLondon(t)  => hour(t, "UTC") >= 2  and hour(t, "UTC") < 5
inNY(t)      => hour(t, "UTC") >= 7  and hour(t, "UTC") < 10

bgColor = showAsia   and inAsia(time)   ? asiaColor   :
          showLondon and inLondon(time) ? londonColor :
          showNewYork and inNY(time)    ? nyColor     : na

bgcolor(bgColor)

// ── OTE Zone (Fibonacci 62–78.6% retracement) ───────────────────────────────
swingHigh = ta.highest(high, swingLen)
swingLow  = ta.lowest(low,  swingLen)
rng       = swingHigh - swingLow

oteHigh = swingLow + rng * (1 - otelevel1)  // 38% from high
oteLow  = swingLow + rng * (1 - otelevel2)  // 21.4% from high

plot(oteHigh, "OTE Upper", color=color.new(color.yellow, 50), linewidth=1, style=plot.style_linebr)
plot(oteLow,  "OTE Lower", color=color.new(color.yellow, 50), linewidth=1, style=plot.style_linebr)
linefill.new(
    plot(oteHigh, display=display.none),
    plot(oteLow,  display=display.none),
    color=color.new(color.yellow, 90)
)

// Kill zone labels
if ta.change(inLondon(time) ? 1 : 0) > 0 and showLondon
    label.new(bar_index, high, "London Open", style=label.style_label_down,
              color=color.blue, textcolor=color.white, size=size.small)
if ta.change(inNY(time) ? 1 : 0) > 0 and showNewYork
    label.new(bar_index, high, "NY Open", style=label.style_label_down,
              color=color.purple, textcolor=color.white, size=size.small)
''')


# ---------------------------------------------------------------------------
# Template: Elliott Wave count
# ---------------------------------------------------------------------------
_register("elliott_wave", '''
//@version=6
indicator("SenAlgo — Elliott Wave Counter", overlay=true)

// ── Inputs ──────────────────────────────────────────────────────────────────
swingLen     = input.int(5, "Swing Sensitivity", minval=2, maxval=30)
showFib      = input.bool(true, "Show Fibonacci Levels")
showLabels   = input.bool(true, "Show Wave Labels")
impulseColor = input.color(color.blue,  "Impulse Wave Color")
correctColor = input.color(color.orange,"Corrective Wave Color")

// ── Swing highs/lows ─────────────────────────────────────────────────────────
swH = ta.pivothigh(high, swingLen, swingLen)
swL = ta.pivotlow(low,  swingLen, swingLen)

// Store last 6 swings for wave identification
var float[] swingPrices = array.new<float>(6, na)
var int[]   swingBars   = array.new<int>(6, na)
var bool[]  swingIsHigh = array.new<bool>(6, false)

if not na(swH)
    array.shift(swingPrices)
    array.push(swingPrices, swH)
    array.shift(swingBars)
    array.push(swingBars, bar_index[swingLen])
    array.shift(swingIsHigh)
    array.push(swingIsHigh, true)

if not na(swL)
    array.shift(swingPrices)
    array.push(swingPrices, swL)
    array.shift(swingBars)
    array.push(swingBars, bar_index[swingLen])
    array.shift(swingIsHigh)
    array.push(swingIsHigh, false)

// ── Wave labels ──────────────────────────────────────────────────────────────
waveLabels = array.from("1", "2", "3", "4", "5")

if barstate.islast and showLabels
    for i = 0 to 4
        px = array.get(swingPrices, i + 1)
        bx = array.get(swingBars,   i + 1)
        ih = array.get(swingIsHigh, i + 1)
        if not na(px) and not na(bx)
            lbl = array.get(waveLabels, i)
            label.new(bx, px, lbl,
                      style = ih ? label.style_label_down : label.style_label_up,
                      color = impulseColor,
                      textcolor = color.white,
                      size = size.normal)

// ── Fibonacci projections ────────────────────────────────────────────────────
if barstate.islast and showFib and not na(array.get(swingPrices, 0))
    w1s = array.get(swingPrices, 1)
    w1e = array.get(swingPrices, 2)
    rng = math.abs(w1e - w1s)
    fib618  = w1e + rng * 1.618
    fib1000 = w1e + rng * 1.000
    fib2618 = w1e + rng * 2.618
    line.new(bar_index - 10, fib618,  bar_index + 10, fib618,  color=color.new(color.yellow, 50), style=line.style_dashed)
    line.new(bar_index - 10, fib1000, bar_index + 10, fib1000, color=color.new(color.green,  50), style=line.style_dashed)
    line.new(bar_index - 10, fib2618, bar_index + 10, fib2618, color=color.new(color.red,    50), style=line.style_dashed)
    label.new(bar_index + 10, fib618,  "W3 1.618", style=label.style_label_left, color=color.yellow, textcolor=color.black, size=size.tiny)
    label.new(bar_index + 10, fib1000, "W5 1.000", style=label.style_label_left, color=color.green,  textcolor=color.black, size=size.tiny)
''')


# ---------------------------------------------------------------------------
# Template: Volume Profile + VWAP
# ---------------------------------------------------------------------------
_register("volume_profile_vwap", '''
//@version=6
indicator("SenAlgo — Volume Profile & VWAP", overlay=true)

// ── Inputs ──────────────────────────────────────────────────────────────────
vpBars      = input.int(100, "Volume Profile Lookback", minval=20)
numBins     = input.int(24,  "Price Bins", minval=10, maxval=50)
showVAH     = input.bool(true, "Show VAH")
showVAL     = input.bool(true, "Show VAL")
showPOC     = input.bool(true, "Show POC")
showVWAP    = input.bool(true, "Show VWAP")
showSD      = input.bool(true, "Show Std Dev Bands")
pocColor    = input.color(color.yellow, "POC Color")
vahColor    = input.color(color.blue,   "VAH Color")
valColor    = input.color(color.blue,   "VAL Color")
vwapColor   = input.color(color.orange, "VWAP Color")
sdColor     = input.color(color.new(color.orange, 70), "Std Dev Color")

// ── VWAP ─────────────────────────────────────────────────────────────────────
var float  cumPV  = 0.0
var float  cumVol = 0.0
var float  cumPV2 = 0.0
var int    dayStart = na

isNewDay = ta.change(dayofweek) != 0
if isNewDay
    cumPV   := 0.0
    cumVol  := 0.0
    cumPV2  := 0.0

tp = (high + low + close) / 3
cumPV   += tp * volume
cumVol  += volume
cumPV2  += tp * tp * volume

vwap_val = cumPV / cumVol
variance = (cumPV2 / cumVol) - vwap_val * vwap_val
sigma    = math.sqrt(math.max(variance, 0))

vwap1U = vwap_val + sigma
vwap1D = vwap_val - sigma
vwap2U = vwap_val + sigma * 2
vwap2D = vwap_val - sigma * 2
vwap3U = vwap_val + sigma * 3
vwap3D = vwap_val - sigma * 3

plot(showVWAP ? vwap_val : na, "VWAP",  color=vwapColor, linewidth=2)
p1u = plot(showSD ? vwap1U : na, "+1σ", color=sdColor, linewidth=1)
p1d = plot(showSD ? vwap1D : na, "-1σ", color=sdColor, linewidth=1)
p2u = plot(showSD ? vwap2U : na, "+2σ", color=sdColor, linewidth=1, style=plot.style_circles)
p2d = plot(showSD ? vwap2D : na, "-2σ", color=sdColor, linewidth=1, style=plot.style_circles)
p3u = plot(showSD ? vwap3U : na, "+3σ", color=color.new(color.red, 60), linewidth=1)
p3d = plot(showSD ? vwap3D : na, "-3σ", color=color.new(color.red, 60), linewidth=1)

fill(p1u, p1d, color=color.new(vwapColor, 95))

// ── Alerts ───────────────────────────────────────────────────────────────────
alertcondition(close > vwap3U, "Above +3σ VWAP", "SenAlgo: Price above 3σ VWAP — extreme")
alertcondition(close < vwap3D, "Below -3σ VWAP", "SenAlgo: Price below -3σ VWAP — extreme")
alertcondition(ta.crossover(close, vwap_val),  "VWAP Cross Up",   "SenAlgo: VWAP cross up")
alertcondition(ta.crossunder(close, vwap_val), "VWAP Cross Down", "SenAlgo: VWAP cross down")
''')


# ---------------------------------------------------------------------------
# Template: Opening Range Breakout strategy
# ---------------------------------------------------------------------------
_register("orb_strategy", '''
//@version=6
strategy("SenAlgo — Opening Range Breakout", overlay=true,
         default_qty_type=strategy.percent_of_equity, default_qty_value=10,
         commission_type=strategy.commission.percent, commission_value=0.05)

// ── Inputs ──────────────────────────────────────────────────────────────────
orbMinutes  = input.int(15, "ORB Duration (minutes)", options=[5, 15, 30, 60])
atrMult     = input.float(1.5, "ATR Stop Multiplier", step=0.1)
targetMult  = input.float(2.0, "Target R:R Multiplier", step=0.1)
sessionStr  = input.session("0915-1530", "Session (Exchange time)")
atrLen      = input.int(14, "ATR Length")

// ── ORB High/Low ─────────────────────────────────────────────────────────────
var float orbHigh = na
var float orbLow  = na
var bool  orbSet  = false
var bool  longFilled  = false
var bool  shortFilled = false

inSession = not na(time(timeframe.period, sessionStr))
isFirstBar = inSession and not inSession[1]

orbTime = isFirstBar ? time : na
orbEndBar = ta.barssince(isFirstBar) <= (orbMinutes / timeframe.multiplier)

if isFirstBar
    orbHigh := high
    orbLow  := low
    orbSet  := false
    longFilled  := false
    shortFilled := false

if orbEndBar and not orbSet
    orbHigh := math.max(orbHigh, high)
    orbLow  := math.min(orbLow,  low)

if not orbEndBar and not orbSet
    orbSet := true

// ── Entry signals ────────────────────────────────────────────────────────────
atr   = ta.atr(atrLen)
longEntry  = orbSet and ta.crossover(close, orbHigh)  and not longFilled
shortEntry = orbSet and ta.crossunder(close, orbLow)  and not shortFilled

if longEntry
    strategy.entry("ORB Long", strategy.long)
    strategy.exit("ORB Long Exit", "ORB Long",
                  stop   = orbHigh - atr * atrMult,
                  limit  = orbHigh + atr * atrMult * targetMult)
    longFilled := true

if shortEntry
    strategy.entry("ORB Short", strategy.short)
    strategy.exit("ORB Short Exit", "ORB Short",
                  stop   = orbLow + atr * atrMult,
                  limit  = orbLow - atr * atrMult * targetMult)
    shortFilled := true

// ── Visuals ──────────────────────────────────────────────────────────────────
plot(orbSet ? orbHigh : na, "ORB High", color=color.green, linewidth=2, style=plot.style_linebr)
plot(orbSet ? orbLow  : na, "ORB Low",  color=color.red,   linewidth=2, style=plot.style_linebr)

alertcondition(longEntry,  "ORB Long",  "SenAlgo ORB: Bullish breakout!")
alertcondition(shortEntry, "ORB Short", "SenAlgo ORB: Bearish breakdown!")
''')


# ---------------------------------------------------------------------------
# Template: CRT (Candle Range Theory)
# ---------------------------------------------------------------------------
_register("crt_indicator", '''
//@version=6
indicator("SenAlgo — Candle Range Theory (CRT)", overlay=true)

// ── Inputs ──────────────────────────────────────────────────────────────────
htfTF       = input.timeframe("60", "Higher TimeFrame")
raidThresh  = input.float(0.3, "Raid Threshold %", step=0.1) / 100
showSetups  = input.bool(true, "Show CRT Setups")
bullColor   = input.color(color.new(color.green, 80), "Bullish Setup")
bearColor   = input.color(color.new(color.red,   80), "Bearish Setup")

// ── HTF data ─────────────────────────────────────────────────────────────────
htfHigh  = request.security(syminfo.tickerid, htfTF, high[1],  lookahead=barmerge.lookahead_on)
htfLow   = request.security(syminfo.tickerid, htfTF, low[1],   lookahead=barmerge.lookahead_on)
htfClose = request.security(syminfo.tickerid, htfTF, close[1], lookahead=barmerge.lookahead_on)

htfRange = htfHigh - htfLow

// ── Raid detection ────────────────────────────────────────────────────────────
raidedHigh = high > htfHigh * (1 + raidThresh) and close < htfHigh
raidedLow  = low  < htfLow  * (1 - raidThresh) and close > htfLow

// CRT bearish: price raids the HTF high then closes back inside → expect drop
// CRT bullish: price raids the HTF low then closes back inside → expect rally
bearSetup = raidedHigh and showSetups
bullSetup = raidedLow  and showSetups

bgcolor(bearSetup ? bearColor : bullSetup ? bullColor : na)

plotshape(bearSetup, "CRT Bear", shape.triangledown, location.abovebar,
          color=color.red, size=size.small)
plotshape(bullSetup, "CRT Bull", shape.triangleup, location.belowbar,
          color=color.green, size=size.small)

// ── Entry/SL/TP labels ────────────────────────────────────────────────────────
if bearSetup
    tp = htfLow
    sl = high * 1.002
    label.new(bar_index, high, "CRT ↓\\nSL:" + str.tostring(sl, "#.##") + " TP:" + str.tostring(tp, "#.##"),
              style=label.style_label_down, color=color.red, textcolor=color.white, size=size.small)

if bullSetup
    tp = htfHigh
    sl = low * 0.998
    label.new(bar_index, low, "CRT ↑\\nSL:" + str.tostring(sl, "#.##") + " TP:" + str.tostring(tp, "#.##"),
              style=label.style_label_up, color=color.green, textcolor=color.white, size=size.small)

alertcondition(bearSetup, "CRT Bear Setup", "SenAlgo CRT: Bearish setup — HTF high raided")
alertcondition(bullSetup, "CRT Bull Setup", "SenAlgo CRT: Bullish setup — HTF low raided")
''')


# ---------------------------------------------------------------------------
# Main generator class
# ---------------------------------------------------------------------------
@dataclass
class PineScriptResult:
    name: str
    version: int
    code: str
    description: str
    file_name: str

    def save(self, path: str) -> str:
        """Save Pine Script to a .pine file."""
        import os
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            f.write(self.code)
        return path


class PineScriptGenerator:
    """
    Generate TradingView Pine Script v6 code.

    Usage:
        gen = PineScriptGenerator()
        result = gen.generate("smc_order_blocks")
        print(result.code)

        # Or generate custom strategy from parameters
        result = gen.generate_custom(
            name="My RSI Strategy",
            script_type="strategy",
            indicators=["rsi", "ema"],
            entry_rules="rsi < 30 and close > ema200",
            exit_rules="rsi > 70",
        )
    """

    VERSION = 6

    def __init__(self):
        self.templates = TEMPLATES

    def list_templates(self) -> list[str]:
        return list(self.templates.keys())

    def generate(self, template_name: str) -> PineScriptResult:
        """Generate Pine Script from a named template."""
        if template_name not in self.templates:
            raise ValueError(
                f"Unknown template '{template_name}'. "
                f"Available: {', '.join(self.templates.keys())}"
            )
        code = self.templates[template_name].strip()
        return PineScriptResult(
            name=template_name,
            version=self.VERSION,
            code=code,
            description=f"SenAlgo {template_name} — Pine Script v{self.VERSION}",
            file_name=f"senalgo_{template_name}.pine",
        )

    def generate_custom(
        self,
        name: str,
        script_type: str = "indicator",          # "indicator" | "strategy"
        indicators: Optional[list] = None,
        entry_rules: str = "",
        exit_rules: str = "",
        timeframe: str = "",
        overlay: bool = True,
        extra_logic: str = "",
    ) -> PineScriptResult:
        """
        Generate a custom Pine Script v6 from high-level parameters.
        The LLM agent uses this to create bespoke strategies on demand.
        """
        indicators = indicators or []
        header = f"//@version={self.VERSION}"

        if script_type == "strategy":
            decl = (
                f'strategy("{name} — SenAlgo", overlay={str(overlay).lower()}, '
                'default_qty_type=strategy.percent_of_equity, default_qty_value=10, '
                'commission_type=strategy.commission.percent, commission_value=0.05)'
            )
        else:
            decl = f'indicator("{name} — SenAlgo", overlay={str(overlay).lower()})'

        # Build indicator blocks
        ind_code = self._build_indicators(indicators)

        # Entry/exit
        entry_exit = ""
        if script_type == "strategy" and entry_rules:
            entry_exit = (
                f"\n// ── Entry / Exit ────────────────────────────────────────────\n"
                f"longCond  = {entry_rules}\n"
                f"shortCond = {exit_rules if exit_rules else 'not longCond'}\n\n"
                "if longCond\n"
                '    strategy.entry("Long", strategy.long)\n'
                "if shortCond\n"
                '    strategy.entry("Short", strategy.short)\n'
            )

        code = "\n".join(filter(None, [header, decl, ind_code, extra_logic, entry_exit]))

        return PineScriptResult(
            name=name,
            version=self.VERSION,
            code=code,
            description=f"Custom: {name}",
            file_name=f"senalgo_custom_{name.lower().replace(' ', '_')}.pine",
        )

    def _build_indicators(self, indicators: list) -> str:
        blocks = ["\n// ── Indicators ───────────────────────────────────────────────"]
        for ind in indicators:
            ind = ind.lower()
            if ind == "rsi":
                blocks.append(
                    "rsiLen = input.int(14, 'RSI Length')\n"
                    "rsiVal = ta.rsi(close, rsiLen)\n"
                    "plot(rsiVal, 'RSI', color=color.purple)"
                )
            elif ind in ("ema", "ema200", "ema20", "ema50"):
                n = ind.replace("ema", "") or "200"
                blocks.append(
                    f"ema{n} = ta.ema(close, {n})\n"
                    f"plot(ema{n}, 'EMA {n}', color=color.orange, linewidth=2)"
                )
            elif ind == "macd":
                blocks.append(
                    "[ macdLine, signalLine, histLine ] = ta.macd(close, 12, 26, 9)\n"
                    "plot(histLine, 'MACD Hist', style=plot.style_histogram, color=histLine > 0 ? color.green : color.red)"
                )
            elif ind == "bollinger" or ind == "bb":
                blocks.append(
                    "bbLen = input.int(20, 'BB Length')\n"
                    "bbMult = input.float(2.0, 'BB Multiplier')\n"
                    "[bbMid, bbUpper, bbLower] = ta.bb(close, bbLen, bbMult)\n"
                    "plot(bbMid, 'BB Mid', color=color.gray)\n"
                    "p_up = plot(bbUpper, 'BB Upper', color=color.blue)\n"
                    "p_dn = plot(bbLower, 'BB Lower', color=color.blue)\n"
                    "fill(p_up, p_dn, color=color.new(color.blue, 95))"
                )
            elif ind == "vwap":
                blocks.append(
                    "[vwapVal, upper1, lower1] = ta.vwap(hlc3, true, 1)\n"
                    "plot(vwapVal, 'VWAP', color=color.orange, linewidth=2)"
                )
            elif ind == "atr":
                blocks.append(
                    "atrLen = input.int(14, 'ATR Length')\n"
                    "atrVal = ta.atr(atrLen)"
                )
        return "\n".join(blocks)
