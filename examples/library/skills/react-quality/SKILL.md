---
name: react-quality
description: Rules and rewrites for correct React — use when writing, reviewing, or refactoring React or Next.js components, hooks, state, effects, or lists.
license: MIT
compatibility: opencode
metadata:
  audience: engineers, reviewers
  stack: react, typescript
---

# React quality

Apply when touching any `.tsx`/`.jsx` file. These are the failure modes coding agents (this one
included) reproduce most often. Each rule: the wrong shape, the right shape, why.

## 1. Effects are for external systems, not derived state
Wrong: `useState` + `useEffect` to compute a value from props/state.
Right: compute during render (`const total = items.reduce(...)`); memoize only if profiling says so.
Why: an effect adds a second render pass, a stale window, and a synchronisation bug you now own.

## 2. If it can be derived, it is not state
Wrong: `filteredItems` in state, resynced on every change.
Right: derive from `items` + `query` during render.
Why: two sources of truth diverge. The bug always arrives.

## 3. Effects that stay must clean up
Every subscription, timer, listener, and observer returns a disposer. Every fetch takes an
`AbortSignal` and ignores `AbortError`. Dependency arrays are complete — never silence the lint
rule; if it fights you, the effect is wrong, not the rule.

## 4. Server state is not client state
Wrong: `useEffect(() => { fetch(...).then(setData) }, [])`.
Right: the framework's data layer (React Query/SWR, route loader, server component). If none
exists, write one small hook that handles loading, error, abort, and race ordering — once.

## 5. Keys are identity, not position
`key={item.id}`. Never `key={index}` for anything reorderable, filterable, or removable.
Why: React reuses the wrong DOM node and state lands on the wrong row.

## 6. Never mutate state
`setItems([...items, next])`, `setUser({ ...user, name })`. No `push`, `splice`, or field
assignment on state or props. Same for nested objects — copy the path you change.

## 7. URL state belongs in the URL
Filters, tabs, pagination, selected id → query params or route segments. Why: shareable,
back-button-correct, survives refresh.

## 8. Memoize on evidence, not reflex
`useMemo`/`useCallback` cost more than they save on cheap values. They matter for: expensive
computation, referential identity feeding a memoized child, and effect dependencies. Otherwise
leave them out.

## 9. Composition beats prop drilling and config props
Pass `children` and slots instead of threading props through three layers or growing a
`variant`/`showX`/`hideY` prop matrix. Context is for genuinely global, rarely-changing values —
not to avoid one level of props.

## 10. Forms: uncontrolled first
Native form + `FormData` for submit-only forms. Reach for controlled inputs only when you need
per-keystroke behaviour. Never `useState` per field by default.

## 11. Accessibility is not optional polish
Real `<button>` for actions, real `<a>` for navigation — never a `div` with `onClick`. Every
input has a `<label htmlFor>`. Icon-only controls have `aria-label`. Focus is visible and
managed on route change and dialog open.

## 12. Next.js App Router
Server Components are the default; `'use client'` goes at the leaf that actually needs
interactivity, not at the top of the tree. Never fetch in a client component when the server
component above it can pass the data down.

## Review checklist
- [ ] no effect that only derives state · [ ] no state that could be derived
- [ ] every effect cleans up and aborts · [ ] complete dependency arrays, lint rule not silenced
- [ ] stable keys · [ ] no mutation of state or props
- [ ] view state that belongs in the URL is in the URL
- [ ] memoization justified · [ ] actions are buttons, labels are wired
- [ ] `'use client'` sits at the leaf, not the root
