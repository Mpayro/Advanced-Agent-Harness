# Tutorial — day-to-day use

## Human-gated end to end

```text
end-to-end coding session: add pagination to /orders
```

The workflow first scans the real repo, then shows a compact alignment
checklist: outcome, scope, non-goals, assumptions, constraints, acceptance
evidence, and any ambiguity that changes behavior or authority.

Confirm the interpretation and choose persistent continuation or a single run.
The workflow recommends persistence for long, complex, interruption-prone work
and a single run for a simple bounded one, but it waits for your choice. No product files are edited
yet.

Next it writes and adversarially reviews a living plan. You get at most five
plain-language bullets plus the saved plan path. Say `implement` only when the
plan is right.

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

Automatic requires an explicit persistent-continuation or single-run choice plus
isolated-branch auto-commit consent. It recommends persistence for long/complex
work and a single run for simple/bounded work. It refuses tasks whose intent, source
freshness, proof, isolation, or production boundary is unresolved.

For an eligible task:

- fresh reviewers get up to ten attempts to approve the latest corrected plan;
- implementation and verification run without a plan checkpoint;
- a fresh reviewer gets up to three attempts to approve the exact patch;
- you still choose once whether to run heavy Peer Bug Review;
- only the accepted patch is staged and committed to the isolated branch.

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

1. Bootstrap one controlled run and record baseline state.
2. Inventory modules, symbols, business flows, UI journeys, jobs, persistence,
   tests, deployment, and observability surfaces.
3. Run disjoint discovery lanes; explorers report candidates, never bugs.
4. Blindly verify and classify every candidate.
5. Write and adversarially attack one plan per confirmed bug.
6. In repair mode, reproduce RED and fix the smallest shared seam.
7. Verify the assembled product and run a fresh integration adversary.
8. Close only when coverage and candidate state are accounted for honestly.

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
