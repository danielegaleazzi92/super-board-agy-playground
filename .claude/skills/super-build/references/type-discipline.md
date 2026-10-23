# Type-system discipline (code shape, every ticket)

Make the compiler or the schema reject impossible states, mismatched primitives and unhandled
variants. Prefer defining errors and special cases out of existence over adding handlers.
From pstack's `principle-type-system-discipline`; language-agnostic, examples in TypeScript.

| Rule | Do | Not |
|---|---|---|
| Impossible states are unrepresentable | `status: 'pending' \| 'paid' \| 'failed'` as a discriminated union carrying only the fields that state has | `paid: boolean; pending: boolean` (both true at once) |
| Brand semantic primitives | `UserId` and `OrderId` get their own type (branded string, newtype); validate once at creation, trust downstream | two `string` parameters that mean different things |
| External data is untyped until parsed | one parse function at each boundary (request body, JSON, env, CLI args, DB rows, IPC) returns the typed model or a typed error | spreading raw payload fields into the domain |
| Derive from the authoritative schema | types generated from the OpenAPI/GraphQL/protobuf/migration/design-token file the project already owns | a hand-written parallel type that drifts |
| Exhaust variants | a `switch` over the union with a `never` default, so a new variant fails to compile where it is not handled | `default: return null` |
| No `any`, no casts to make it compile | narrow with a parse or a guard; widen the type if the value really can be that | `as unknown as T`, `// @ts-ignore` |

Where it applies in a lane:

- **Builder** (run.md → Builder, step 4): the change follows the rules above in the files it
  touches. It does not retype the codebase: a ticket about one endpoint brands that endpoint's
  ids, parses that endpoint's payload. A broader retype is a `refactor` ticket, filed with
  `/to-tickets`, never smuggled under the size cap.
- **Reviewer** (super-review → "Classify findings"): a new `boolean` pair that can contradict,
  a new `any`/cast, a raw payload crossing into domain code, or an unhandled variant is a
  finding. Class **Bug** when the impossible state can actually be reached (trace the call
  chain), otherwise **Should fix** under maintainability. It never blocks a merge on its own.
- **Tester**: a parse at a boundary gets at least one test with a malformed input; the
  rejected case is an AC-level behaviour, not an implementation detail.

Project conventions win: AGENTS.md's rules for money (`numeric`, integer cents), dates and ids
are the branded types here. A project without TypeScript reads the same table with its own
type system (Kotlin sealed classes, Rust enums, Python `Literal`/`NewType` + a validator at the
boundary).
