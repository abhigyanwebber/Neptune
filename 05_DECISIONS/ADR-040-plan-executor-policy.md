# ADR-040 — Plan Executor: Ordering, Failure Cascade, and Persistence Shape

**Status:** DECISION
**Scope:** Claude A / Planning Contract and Plan Executor (A-007)

## Decision

1. **Execution order is Plan.steps declaration order**, not alphabetical
   or any other implicit sort. `PlanExecutor.select_next_step()` returns
   the first PENDING step (in that declared order) whose dependencies are
   all COMPLETED.
2. **A failed step cascades SKIPPED to every step that depends on it,
   directly or transitively**, by default (`cascade_skip=True` on
   `fail_step()`, overridable per call).
3. **A Plan's steps persist as a single JSON column** (`PlanModel.steps`
   in `infrastructure/persistence/models/orm.py`), not a separate
   per-step table.
4. **Dependency-graph validation reuses
   `core.registry.dependency_resolution.resolve_dependencies()`
   unchanged** rather than a new cycle-detection implementation.

## Rationale

**Why declared order, not alphabetical or insertion-timestamp.** The
brief requires "deterministic ordering" as a testable property. Declared
order is the simplest thing that's deterministic *and* meaningful to
whoever authors a plan -- a human or future planning process writing
`steps=[a, b, c]` almost certainly means "prefer a, then b, then c when
multiple are eligible," not "sort my carefully-ordered list
alphabetically." Alphabetical would have been equally deterministic but
would silently discard authoring intent for no benefit.

**Why cascade the skip by default.** A step whose dependency failed can
mathematically never become executable (its `start_step()` precondition
-- all dependencies COMPLETED -- can no longer be satisfied). Leaving it
PENDING forever would mean `is_complete()` never returns True for that
plan, even though there is nothing left anyone could legitimately do
about it. Cascading SKIPPED is the only choice that lets
`is_complete()` (a required responsibility: "determine plan completion")
give a correct answer without a human manually skipping every downstream
step by hand. This is also the only path that produces
`StepStatus.SKIPPED` at all, since the brief lists it as a required
status without specifying what produces it.

**Why `cascade_skip` is a parameter instead of always-on.** A future
caller (e.g. a smarter driver built on top of this executor, not built in
this task) may want to attempt an alternate step instead of giving up on
everything downstream. Keeping cascade as the *default* behavior (so the
brief's "failed step handling" requirement is satisfied out of the box)
while allowing `cascade_skip=False` avoids hard-coding a policy this task
doesn't have enough information to finalize -- consistent with ADR-038's
precedent of shipping the simplest correct default while leaving room for
a smarter policy later.

**Why steps persist as one JSON column instead of a steps table.** Every
read and write of a Plan's steps in this task happens as a whole --
`select_next_step`, `is_complete`, and every mutation method all need the
full ordered list to make a decision, and nothing in the brief asks for
querying individual steps across plans (e.g. "find all RUNNING steps
system-wide"). A separate table would add join complexity and an
ordering column with no corresponding capability this task needs. This
mirrors the existing precedent of `Turn.tool_calls` (Stage 0/1) and
`Provider.capabilities`/`depends_on` (A-003) -- structured lists that
belong entirely to one parent record persist as JSON on that record.

**Why dependency-graph validation reuses A-003's `resolve_dependencies()`
verbatim.** It is already a generic `dict[str, list[str]] ->
list[str]` topological sort with cycle detection
(`DependencyCycleError`) and missing-reference detection
(`UnresolvedDependencyError`) -- nothing about it is registry-specific.
Reimplementing the same algorithm for PlanStep dependencies would be pure
duplication with no behavioral difference; `PlanExecutor._validate_dependency_graph`
just builds the `step_id -> dependencies` map and re-raises the two
existing exceptions as `PlanValidationError` for a planning-specific error
type.

## Consequences

- A plan with steps that could validly run in parallel (e.g. the diamond
  shape in the tests: `left` and `right` both depend only on `root`) is
  still only ever offered one "next" step at a time via
  `select_next_step()`. This is intentional for this stage -- the brief
  asks for "select next executable step" (singular), not a parallel
  scheduler. A caller that wants to run `left` and `right` concurrently
  can call `select_next_step()` again after starting (not completing) the
  first, since `start_step()` only requires PENDING + satisfied
  dependencies, not "no other step currently RUNNING."
- `PlanExecutor` never calls a provider, runs a tool, or generates a plan
  (the brief's explicit exclusions) -- every test in
  `tests/unit/planning/` and `tests/integration/planning/` constructs
  `Plan`/`PlanStep` objects directly with pre-authored steps, matching
  "This task establishes contracts and execution flow only."

## Validation

Revisit if a future task needs true parallel step execution (multiple
RUNNING steps driven concurrently) or per-step querying across plans --
at that point `select_next_step()` may need to return a list, and the
JSON-column persistence shape may need to become a real steps table.
Neither need exists yet.
