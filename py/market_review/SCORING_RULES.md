# Market Review Scoring Rules

This document records the current scoring logic and the recommended next version for
limit-up review, sector strength, advancement candidates, and divergence-to-consensus
signals.

The current implementation lives in `py/market_review/service.py`.

## Current Rules

### Limit-Up Stock Quality Score

Field: `board_quality_score`

Current formula:

```text
score = 45
      + min(consecutive_boards * 6, 24)
      + first_limit_time_bonus
      - min(open_count * 6, 24)
      + seal_amount_bonus
      + turnover_bonus
```

Rules:

- Consecutive boards: +6 per board, capped at +24.
- First limit-up time:
    - Before or at 10:00: +16.
    - Before or at 11:30: +10.
    - After or at 14:30: -10.
- Open-board count: -6 per open, capped at -24.
- Seal amount: logarithmic score, capped at +12.
- Turnover:
    - 3% to 18%: +8.
    - Above 30%: -8.
- Final score is clamped to 0-100.

Current risk tags:

- `炸板偏多`: `open_count >= 3`.
- `尾盘封板`: first limit-up time after or at 14:30.
- `换手过高`: turnover above 30%.
- `板块未知`: missing or unknown industry.

### Sector Strength Score

Field: `strength_score`

Current formula:

```text
score = limit_up_count * 16
      + advanced_count * 12
      + max_consecutive_boards * 8
      + total_seal_amount_bonus
      - min(open_count * 2.5, 18)
```

Rules:

- Limit-up count is the main driver.
- Advanced count means stocks with at least 2 consecutive boards.
- Highest board height contributes directly.
- Total seal amount uses logarithmic scoring, capped at +8.
- Open-board count weakens the sector score.

Current risk tags:

- `炸板偏多`: total open count is greater than or equal to `max(2, limit_up_count)`.
- `板块跟随不足`: only one stock in the sector.

### Advancement Candidate Score

Field: `candidate_score`

Current formula:

```text
score = board_quality_score
      + strength_score * 0.35
      + min(consecutive_boards * 4, 16)
```

Level rules:

- `高关注`: score >= 82 and risk count <= 1.
- `剔除`: score < 55 or risk count >= 3.
- `观察`: all other candidates.

Current positive reasons:

- Sector has at least 3 limit-up stocks.
- Sector has at least 2 advanced stocks.
- Stock first sealed before or at 10:30.
- No open-board event.
- Turnover is between 3% and 18%.

Current extra risks:

- Seal amount is less than 3% of traded amount.
- First limit-up time is after or at 14:30.

### Divergence-To-Consensus Signal Score

Field: `signal_score`

Current additions:

- Open-board and reseal: +8 per open, capped at +24.
- Last limit-up time later than first limit-up time: +10.
- Sector has at least 3 limit-up stocks: +24.
- Sector has at least 2 advanced stocks: +16.
- Seal amount logarithmic bonus, capped at +12.

Current risks:

- `分歧过大`: open-board count >= 4.
- `尾盘一致性待确认`: first limit-up time after or at 14:30.

## Limitations

The current rules are usable as a first-pass heuristic, but they have several issues:

- Absolute seal amount favors large-cap stocks and does not normalize by traded amount or float market value.
- Sector strength is too dependent on limit-up count and board height, but not enough on ladder completeness.
- The same thresholds are used in strong and weak markets.
- Candidate scoring can become too large because sector score is added directly instead of normalized.
- It does not distinguish sector leader, follower, back-row补涨, and isolated limit-up stocks clearly enough.
- It does not account for intraday market risk appetite, such as total turnover, limit-up/down ratio, and broad-market
  breadth.

## Recommended V2 Rules

Keep the output fields unchanged for frontend compatibility, but change the internal scoring to a normalized 0-100
system.

### Market Environment Score

Add an internal market environment score used as a multiplier, not necessarily persisted at first.

Recommended components:

```text
market_env_score =
  turnover_heat_score * 0.30
  + breadth_score * 0.20
  + limit_up_down_score * 0.25
  + advanced_board_height_score * 0.15
  + theme_concentration_score * 0.10
```

Data candidates:

- Total A-share turnover and turnover change versus the previous trading day.
- Rising/falling stock count.
- Limit-up/down count and limit-up/down ratio.
- Highest board height and advanced-board count.
- Top sector concentration: share of limit-up stocks in top 3 sectors.

Usage:

```text
if market_env_score >= 75:
    allow aggressive candidates and raise sector-following weights
elif market_env_score >= 55:
    use normal thresholds
else:
    lower late-board scores and penalize weak seals more strongly
```

### V2 Limit-Up Stock Quality

Recommended formula:

```text
board_quality_score =
  seal_timing_score * 0.22
  + seal_stability_score * 0.18
  + seal_strength_score * 0.20
  + turnover_structure_score * 0.15
  + ladder_position_score * 0.15
  + market_fit_score * 0.10
  - risk_penalty
```

Recommended details:

- Seal timing:
    - 09:25-09:35: strongest, but mark one-word板 risk if成交额 is too small.
    - 09:35-10:00: strong active board.
    - 10:00-11:30: acceptable.
    - 13:00-14:30: weaker unless sector is clearly returning.
    - 14:30-15:00: high risk unless it is a confirmed leader or index resonance.
- Seal stability:
    - No open-board: high score.
    - One open and fast reseal: neutral to positive.
    - Multiple opens: strong penalty.
- Seal strength:
    - Prefer `seal_amount / amount`.
    - Prefer `seal_amount / circulating_market_value`.
    - Use absolute seal amount only as a secondary cap.
- Turnover structure:
    - Use different reasonable turnover bands by float market value.
    - Small-cap can tolerate higher turnover; large-cap should not be judged with the same threshold.
- Ladder position:
    - Add score for market highest board, sector highest board, and only surviving advanced stock.
- Market fit:
    - In high-liquidity markets, tolerate higher turnover.
    - In weak markets, penalize late boards and weak seals more.

### V2 Sector Strength

Recommended formula:

```text
strength_score =
  limit_up_diffusion_score * 0.25
  + ladder_completeness_score * 0.25
  + leader_quality_score * 0.20
  + capital_confirmation_score * 0.15
  + persistence_score * 0.10
  - sector_risk_penalty
```

Recommended details:

- Diffusion: limit-up count, sector limit-up share, number of non-limit-up gainers.
- Ladder completeness: whether the sector has first board, 2-board, 3-board+, and a clear leader.
- Leader quality: best 1-3 stocks by `board_quality_score`, not just raw board height.
- Capital confirmation: total amount, seal/amount ratio, and sector volume expansion.
- Persistence: sector appears in the top ranks for multiple days.
- Risk: high open-board ratio, single-stock contribution too high, or mostly late boards.

### V2 Advancement Candidate

Recommended formula:

```text
candidate_score =
  board_quality_score * 0.42
  + normalized_sector_strength * 0.28
  + ladder_position_score * 0.15
  + next_day_expectation_score * 0.10
  + market_env_adjustment * 0.05
  - risk_penalty
```

Recommended levels:

- `高关注`: score >= 80, risk count <= 1, and not late weak board.
- `观察`: score 60-80 or risk count <= 2.
- `剔除`: score < 60, risk count >= 3, or hard risk triggered.

Hard risks:

- Multiple open-board events plus weak final seal.
- Late board with no sector support.
- Seal/amount ratio too low.
- Turnover extreme versus float size.
- Isolated one-stock sector in a weak market.

### V2 Divergence-To-Consensus

Recommended formula:

```text
signal_score =
  divergence_quality_score * 0.30
  + reseal_strength_score * 0.25
  + sector_return_score * 0.25
  + leader_status_score * 0.10
  + market_env_score * 0.10
  - risk_penalty
```

Recommended details:

- A good divergence-to-consensus signal is not simply "opened and resealed".
- It should show controlled divergence: open-board count is not too high, reseal is fast, and the final seal is
  stronger.
- Give higher scores when the sector also returns at the same time.
- Penalize repeated opens, late weak reseal, and isolated reseal without sector support.

## Implementation Plan

Recommended sequence:

1. Add helper functions in `MarketReviewService`:
    - `_seal_strength_score(stock)`
    - `_turnover_structure_score(stock)`
    - `_ladder_position_score(stock, pool)`
    - `_market_environment_score(pool)`
    - `_sector_ladder_completeness(items)`
2. Keep API schemas unchanged.
3. Recalculate existing fields with V2 logic:
    - `board_quality_score`
    - `strength_score`
    - `candidate_score`
    - `signal_score`
4. Add unit tests with small synthetic pools covering:
    - early one-seal board
    - late weak board
    - strong sector ladder
    - isolated board
    - high-turnover risk
    - divergence then strong reseal
5. Only after test coverage is stable, expose score explanations to the frontend.

## Better Long-Term Approach

The best long-term approach is to move from fixed heuristic scoring to outcome-calibrated scoring.

Store daily features and next-day outcomes:

- Whether a candidate advanced on the next trading day.
- Next-day open, high, close, max drawdown, and whether it hit limit-up.
- Whether the sector stayed active.

Then evaluate each factor by hit rate and risk/reward:

```text
feature -> next_day_advance_rate
feature -> next_day_max_return
feature -> next_day_max_drawdown
feature -> false_positive_rate
```

Use the result to tune weights monthly. This can start as simple historical backtesting before using any ML model.

Avoid jumping directly to a black-box model. A transparent scorecard is easier to debug and more useful for
discretionary review.
