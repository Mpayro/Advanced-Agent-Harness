# Tutorial — day-to-day use

## Human-gated end to end

```text
end-to-end coding session: add pagination to /orders
```

The workflow first scans the real repo, then shows a compact alignment
checklist: outcome, scope, non-goals, assumptions, constraints, acceptance
evidence, and any ambiguity that changes behavior or authority.

It asks you for one thing only: which release steps, if any, this work reaches.
Nothing later in the run can grant that authority, which is why it cannot wait.
Everything else it decides and tells you — who reviews, how it will verify — so
you only speak up to override. No product files are edited yet.

Next it writes and adversarially reviews a living plan, then puts it in front of
you for approval. Say `implement` only when the plan is right.

Implementation then runs continuously in an isolated worktree:

- failing evidence first;
- smallest shared root-cause change;
- targeted verification;
- isolated Chrome smoke with a temporary profile and remote debugging for UI;
- fresh adversarial review of the exact saved patch.

At the end it asks once:

```text
¿Quieres correr ahora Peer Bug Review pesado antes del commit?
```

Answer yes or no. After that choice is resolved, the workflow reports the
verified result and stops before commit.

## Automatic end to end

```text
end-to-end coding session automatic: migrate the email renderer
```

Automatic requires isolated-branch auto-commit consent up front, and any release
step has to be named in that same consent or it never runs. It refuses tasks
whose intent, source freshness, proof, isolation, or production boundary is
unresolved, handing those back to the human-gated skill.

For an eligible task:

- a fresh reviewer approves the plan in your place, and rejects it outright if it
  carries a production step your consent never named;
- implementation and verification run without a plan checkpoint, but the work is
  committed to the isolated branch as it goes, so a killed turn loses nothing;
- a fresh reviewer approves the exact patch;
- a UI change whose browser check failed or was unavailable blocks the landing and
  every release step after it;
- you still choose once whether to run heavy Peer Bug Review;
- the accepted bytes are committed, that commit's sha is recorded, and exactly that
  sha lands.

That last point is the part worth understanding, because the branch and the
delivery stop being the same thing. Checkpoints and living-plan updates keep
arriving on the branch, so its tip is usually ahead of what was reviewed. The
handoff names the landed sha and says how far ahead the tip is; anything past that
sha is not delivered work and is not reported as such.

Automatic never pushes or merges.

## Peer Bug Review

Read-only audit is the default:

```text
peer bug review: audit this repository
```

To authorize repairs, say so explicitly:

```text
peer bug review: prove and fix the reported invoice bug end to end
```

The eight stages are:

1. Bootstrap one controlled run and record baseline state — including proof that
   the gates can fail. An unpopulated baseline, a test glob matching no file, a
   declared assertion no code reads: each makes every green behind it meaningless,
   and none can be found by probing the product.
2. Inventory modules, symbols, business flows, UI journeys, jobs, persistence,
   tests, deployment, and observability surfaces, starting from auth, secrets,
   money, destructive operations, audit history, and date/unit/rounding.
3. Run disjoint discovery lanes; explorers report candidates, never bugs.
4. Blindly verify and classify every candidate.
5. Write and adversarially attack one plan per confirmed bug.
6. In repair mode, reproduce RED and fix the smallest shared seam.
7. Verify the assembled product and run a fresh integration adversary.
8. Close only when coverage and candidate state are accounted for honestly.

One thing the lanes hunt deserves naming, because it is what a code review cannot
see: a test that passes without meaning anything. Three shapes recur. A **dead
anchor** compares output against a frozen fixture or snapshot, so green means
nothing has changed since the freeze, not that the behaviour is right. An
**uncompared twin** is one fact resolved by two paths, each with its own green
test and nothing asserting they agree — the defect lives in the gap, where no test
that stays inside one path can reach it. **Borrowed authority** is a test whose
name claims it compares against a document it never opens. A passing test is not
evidence a candidate is harmless until you have broken what it protects and
watched it go red.

A state ledger holds the run by default and records what was covered, what was
classified, and what is still open. It is not bookkeeping: it is what lets a run
survive losing its context, and skipping it is what leaves a long run with
duplicated branches and work nobody can account for.

For UI audits, every enumerated action is exercised in isolated Chrome with a
temporary profile and remote debugging. Audit mode does not authorize source or
production mutations.

## Lightweight review

For one settled plan, diff, shared seam, or generated artifact:

```text
coding peers: review this exact patch
```

This is read-only by default, uses one fresh Luna reviewer, freezes the exact
artifact and SHA-256 identity, and verifies every finding locally. It does not
create a goal, branch, or commit.

## Minimalism

```text
ponytail: implement the smallest correct fix
ponytail-review
ponytail ultra
stop ponytail
```

Ponytail looks for an existing helper, standard-library solution, native
platform feature, or installed dependency before adding code. It never
simplifies away validation, data-loss prevention, security, accessibility, or
an explicit requirement.

## Reading progress

End-to-end updates start with:

```text
Skill step <N>/8 - <name>: <status>.
```

Peer Bug Review updates start with:

```text
Peer Bug Review step <N>/8 - <name>: <status>.
```

Retries stay inside the failed stage. Reaching a limit produces a documented
blocker; it never silently becomes approval.

## Which workflow to choose

| Request | Workflow |
|---|---|
| Small review or second opinion | `coding-peers` |
| Multi-stage implementation with human plan approval | `end-to-end-coding-session` |
| Deterministic isolated-branch auto-commit | `end-to-end-coding-session-automatic` |
| Unknown, disputed, or whole-product bug surface | `peer-bug-review` |
| Simple bounded edit | normal Codex + Ponytail |

Use named external GLM, MiniMax, Nemotron, or NVIDIA peers only when you want
that external perspective. The data-boundary skill redacts sensitive payloads
before anything leaves the machine.
