# Optional NVIDIA peers

## Why

The harness can use outside models for an explicitly requested external opinion.
They run on NVIDIA's hosted inference (`build.nvidia.com`, also called NIM),
which exposes an OpenAI-compatible API.

- **GLM-5.2** — the default peer. Strong at reasoning-heavy code. Slow (~20
  tokens/sec) but takes enormous input and doesn't get cut off.
- **MiniMax-M3** — the one that can **see**. Screenshots, mockups, diagrams,
  video frames. Use it first whenever the task carries an image.

You do not need a key for the normal workflows. `coding-peers`,
`end-to-end-coding-session`, and `peer-bug-review` use permitted Codex reviewers
by default. Configure NVIDIA only when you want to request a named external
peer.

## Steps

1. **Go to <https://build.nvidia.com>** and sign in (or create an NVIDIA
   account — free, email + password).

2. **Open a model page.** Search for `glm` and open the **GLM-5.2** page, or go
   straight to a model page from the catalog. This matters: generate the key
   **from a model page**, not from the generic NGC account settings. Keys made
   in NGC without entitlement come back `403` even though they look valid.

3. **Click "Get API Key"** (the button sits near the code sample on the right;
   it may read "Build with this NIM" / "Generate API Key" depending on the page
   version). Confirm.

4. **Copy the key immediately.** It looks like:
   ```
   nvapi-XxXxXx-XxXxXx_XxXx--XxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXx
   ```
   ~70 characters, starts with `nvapi-`, contains dashes AND underscores, and
   usually a **double dash** somewhere in the middle. You will not be shown it
   again — if you lose it, generate a new one.

5. **Verify MiniMax is covered by the same key.** Open the **MiniMax-M3** page
   and check the code sample; the same `nvapi-` key works for every model in the
   catalog. You do not need a second key.

6. **Save the file.** Copy `NVIDIA_API_KEY.env.template` from this folder to
   your home directory as `~/NVIDIA_API_KEY.env`, and paste your key in on the
   `NVIDIA_API_KEY=` line, replacing `nvapi-PASTE_YOUR_OWN_KEY_HERE`.

   The path matters — `delegating-to-external-models` looks for exactly
   `~/NVIDIA_API_KEY.env`. If you want it somewhere else, change that skill's
   configured path.

7. **Smoke test.** In a terminal:
   ```bash
   export NVIDIA_API_KEY=$(grep -E '^NVIDIA_API_KEY='  ~/NVIDIA_API_KEY.env | head -1 | cut -d= -f2-)
   export NVIDIA_BASE_URL=$(grep -E '^NVIDIA_BASE_URL=' ~/NVIDIA_API_KEY.env | head -1 | cut -d= -f2-)
   curl -s -o /dev/null -w 'HTTP %{http_code}\n' "$NVIDIA_BASE_URL/chat/completions" \
     -H "Authorization: Bearer $NVIDIA_API_KEY" -H "Content-Type: application/json" \
     -d '{"model":"z-ai/glm-5.2","messages":[{"role":"user","content":"hi"}],"max_tokens":4}'
   ```
   It must print exactly `HTTP 200`.

## When the smoke test doesn't say 200

| What you see | What it actually is |
|---|---|
| `HTTP 403` | **99% of the time the key got mangled during extraction, not a dead key.** Print it: `echo ${#NVIDIA_API_KEY}` — it should be ~70. If it says 8, your regex cut at the first dash. Never split the key on `-`. Take the whole line after the first `=`. |
| `HTTP 403` with a full-length key | The key was generated in NGC account settings without model entitlement. Regenerate it **from the model's own page**. |
| `HTTP 000`, hangs ~60s | Cold start or HTTP/2 negotiation. Add `--http1.1` and raise the timeout (`-m 120`). Not a key problem. |
| `curl: (16) HTTP2 framing layer` | Same thing — add `--http1.1`. |
| `HTTP 200` but the reply content is empty | The endpoint does this under load. Retry once; if it repeats, make the request smaller. Treat empty as a failure, never as a valid answer. |

## Cost

Signing up gives you a pool of free credits. It's enough to use these models as
occasional peer reviewers for a long while — a plan review or a diff review is
one call, not a chat session. If you burn through them, NVIDIA has paid tiers,
but the harness never *needs* the external peers to function.

## The rule that comes with the key

Everything you send to these models leaves your machine and lands on a third
party. The `delegating-to-external-models` skill enforces this: before every
send, the active agent scans the payload, replaces secrets / real names / client
data with placeholders, tells you exactly what it hid, and restores the real
values in the answer. If redaction would break the task, it stops and asks you
instead.

That gate is not optional and not decoration — it's the reason it's safe to have
outside models reviewing your real code.
