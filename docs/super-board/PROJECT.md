# super-board-agy-playground

**What it is.** A tiny shopping-cart module in plain Node (ES modules, no dependencies) whose only job is to give super-board something real to build, test and review while the board runs on Google Antigravity (`run --agy`).

**Shape.** `src/cart.js` exports `createCart`, `addItem`, `removeItem` and `total`; `src/index.js` is a demo; `test/cart.test.js` holds four `node:test` cases. `npm run verify` is the whole check: a syntax check of the two source files plus the tests.

**How cards should look.** One behaviour per card, a few lines of `src/` and one or two tests. No UI, no network, no database: a card that needs any of those is out of scope for this playground.

**Decisions already taken.** Money is a plain number of currency units (no cents type, no rounding library). Quantities are positive integers. Validation throws; it never returns error objects.
