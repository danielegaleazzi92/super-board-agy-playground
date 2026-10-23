# QA Report — Issue #3: cart clearCart empties the cart and drops its discount

## Verdict
✅ Pass

## Acceptance Criteria Verification
- [x] after `clearCart(cart)` on a cart with two items and a 10% discount, `cart.items` is empty and `total(cart)` is 0
  ↳ verified: `test/cart.test.js:63` passes (items cleared and total returns 0)
- [x] after `clearCart`, adding an item worth 20.00 gives `total(cart)` of 20.00: no discount survives
  ↳ verified: `test/cart.test.js:71` passes (subsequent purchases calculate total without previous discount)
- [x] `clearCart(cart)` returns the same object (`===`) so `addItem(clearCart(cart), …)` works
  ↳ verified: `test/cart.test.js:79` passes (returns original cart reference, method chaining functions correctly)
- [x] `clearCart` on an empty cart is a no-op that does not throw
  ↳ verified: `test/cart.test.js:87` passes (`doesNotThrow` passes, items remain empty and total is 0)
- [x] each criterion above has its own `node:test` case in `test/cart.test.js`, and `npm run verify` is green
  ↳ verified: full suite passes cleanly with 14 passing tests, lint checks pass

## Test Gaps & Additional Coverage
- Added test case verifying `clearCart` on a cart with items but no discount empties items cleanly and ensures no discount property remains (`test/cart.test.js:93`).

## Evidence
- Command: `npm run verify`
- Log: `docs/super-board/runs/issue-3-qa-v1/test.log`
