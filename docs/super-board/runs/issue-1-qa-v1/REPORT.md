# QA Report — Issue #1: cart percentage discount applied to total

## Verdict
✅ Pass

## Acceptance Criteria Verification
- [x] `applyDiscount(cart, 10)` then `total(cart)` on items worth 20.00 returns 18.00
  ↳ verified: `test/cart.test.js:28` passes (total correctly calculates 20 * (1 - 0.10) = 18.00)
- [x] a second `applyDiscount` replaces the first: 10 then 25 on items worth 20.00 gives 15.00
  ↳ verified: `test/cart.test.js:34` passes (replaces discount on cart object, calculates 20 * (1 - 0.25) = 15.00)
- [x] `applyDiscount(cart, -1)`, `applyDiscount(cart, 101)` and `applyDiscount(cart, 1.5)` each throw an `Error` whose message contains `percent`
  ↳ verified: `test/cart.test.js:41` passes (input validation enforces integer 0-100)
- [x] `total(cart)` on a cart with no discount is unchanged and the four existing tests still pass
  ↳ verified: `test/cart.test.js:5-26` all pass unchanged
- [x] each criterion above has its own `node:test` case in `test/cart.test.js`, and `npm run verify` is green
  ↳ verified: full suite passes cleanly with 9 passing tests, lint checks pass

## Test Gaps & Additional Coverage
- Added boundary tests for 0% and 100% discount calculations (`test/cart.test.js:48`).
- Added type validation tests for non-integer / non-number inputs (`'10'`, `null`, `NaN`) (`test/cart.test.js:55`).

## Evidence
- Command: `npm run verify`
- Log: `docs/super-board/runs/issue-1-qa-v1/test.log`
