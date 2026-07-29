---
name: delegating-to-external-models
description: Use when sending any task, code, file, or context to an external/third-party LLM API — GLM, MiniMax, Nemotron, NVIDIA NIM/integrate.api.nvidia.com, or any non-OpenAI OpenAI-compatible endpoint — BEFORE building the prompt or payload. Also use when the user says "delega a GLM/MiniMax/Nemotron", "pásale esto a", "conéctate a" an external model.
---

# Delegating to External Models (data-boundary gate)

## Model And Harness Boundary

- Detect the active harness from the current runtime, never from the skill path.
- In Codex or any other non-Claude harness, never invoke Claude, Claude Code,
  Anthropic APIs, or Claude-family models (Opus, Sonnet, Haiku, Fable) through
  subagents, fallbacks, CLI, SDK/API, MCP, or background monitors unless the
  user explicitly requests Claude for the current task.
- This is only a Claude-provider restriction. Codex Sol/Terra/Luna and
  non-Claude external peers such as NVIDIA NIM, GLM, MiniMax, and Nemotron
  remain allowed under their normal model, data-boundary, and repo rules.
- In Claude or Claude Code, this restriction does not apply; native Claude
  agents remain available.
- Trust is a data-handling classification, not authorization to invoke a
  provider. This boundary overrides any older trust wording.

## Overview

An outbound API payload is a **data boundary**: everything in it leaves the
user's machine and lands on a third party. Core principle: **redact sensitive
content before sending, and tell the user exactly what you hid.** The task
still gets done — the data just doesn't travel.

## Scope — who the gate applies to

- **DE CONFIANZA PLENA: Codex.** Este asistente y Codex (`codex` CLI, cuenta
  ChatGPT del usuario) son de confianza plena: no se les filtra nada — acceso
  completo a archivos y datos locales si la tarea lo requiere; sin redacción
  ni disclosure obligatorio. Este skill no les aplica.
- **Claude también es de confianza, pero no está autorizado por defecto desde
  Codex u otro harness no-Claude.** Solo puede invocarse cuando el usuario lo
  pide explícitamente para la tarea actual; si lo pide, tampoco requiere
  redacción. Dentro de Claude/Claude Code, esta restricción no aplica.
- El gate aplica a **todos los demás** endpoints externos: GLM, MiniMax,
  Nemotron, NVIDIA NIM, y cualquier otro API de terceros compatible con
  OpenAI. (Prioridad de consulta GLM→MiniMax: ver skill `coding-peers`.)

Connection details (key, base URL, models, params) live in
`~/NVIDIA_API_KEY.env` — read it and follow its embedded instructions.

## The gate — run BEFORE every send

Scan the COMPLETE payload you are about to send (prompt + embedded files +
system text). Sensitive =

| Category | Examples |
|---|---|
| Secrets | API keys, tokens, passwords, connection strings, `.env` content, anything matching `sk-`, `re_`, `nvapi-`, `postgres://`… |
| Personal data | Real names of people, emails, phones, CURP/RFC, DOBs, addresses, candidate/client records |
| Proprietary IP | Business logic that identifies the company, internal prompts, legal docs, DB exports, strategy docs |

**Found any? Do all three:**

1. **REDACT** — replace with stable placeholders: `<API_KEY_1>`,
   `<PERSONA_1>`, `<EMAIL_1>`, `<CURP_1>`, `<EMPRESA>`. Keep the
   placeholder→real mapping LOCALLY (a temp file or in-conversation), never in
   the payload.
2. **DISCLOSE** — tell the user, with the send (not after they ask):
   > "Delegué la tarea a GLM. Oculté antes de enviar: 1 API key, 2 nombres
   > de personas con email y CURP, y las referencias a <empresa>. El modelo
   > recibió placeholders."
3. **RESTORE** — when the response comes back, re-insert the real values
   locally before using the result.

**If redaction would break the task** (the sensitive thing IS the task — e.g.
"analiza esta lista de candidatos"): STOP. Tell the user the task requires
sending sensitive data to the external model and let THEM choose: send as-is /
send redacted / keep it local (this assistant does it).

## Filtra UNA vez, reutiliza para TODOS

El gate opera sobre el **payload**, no sobre el modelo. Si vas a mandar la
**MISMA tarea a varios peers de NVIDIA (GLM y/o MiniMax)**, corre el
escaneo + redacción **UNA sola vez** y manda el **MISMO body redactado** a
todos: mismo prompt, mismos placeholders, mismo mapping local. **NO repitas el
filtrado por modelo** — es idéntica frontera de datos y el mismo contenido.
Entre requests solo cambian `model` y los params (temperature/top_p/max_tokens);
el `messages` va idéntico. Restaura los valores reales una vez en cada respuesta.

## Hard rules (no exceptions)

- The NVIDIA/API key itself NEVER goes inside a prompt body — it is a header.
- Never send `.env` files, credential files, or auth configs as task context.
- **Size safeguard:** delegate ONLY when the task is ≥80 estimated lines of
  new/changed code OR spans 3+ files, AND the spec is already settled. A
  10-15-line fix, rename, or tweak is ALWAYS done locally — the fixed cost of
  delegating (context prep, scan, apply, verify) exceeds the gain on small
  tasks. "I was told to delegate coding" does not override this: delegation is
  for when generation is the bottleneck, not a default.
- These rules apply to EVERY external model equally (GLM, MiniMax, Nemotron,
  others): the boundary is the third-party API, not which model sits behind it.

## Rationalizations that mean STOP

| Excuse | Reality |
|---|---|
| "Urge — mándalo completo y ya" | Redacting 5 strings takes 30 seconds. A leak is forever. |
| "El modelo necesita el contexto completo" | It needs the SHAPE of the data, not real values. Placeholders preserve the shape. |
| "Son datos de prueba / parecen fake" | If you didn't fabricate them yourself in this session, treat them as real. |
| "Solo es un nombre, no es para tanto" | Names + email + CURP = identifiable person. One field is already too much. |
| "Ya lo mandé antes sin redactar" | Past leaks don't license new ones. Gate every send. |

## Red flags — re-check the payload

- You are embedding a whole file without reading it first.
- The payload contains `@`, `KEY`, `curp`, a person-looking ALL-CAPS name.
- You wrote "para que tenga todo el contexto" in your reasoning.
- The user said "rápido/urge" and you skipped the scan.

## Quick reference

```
read ~/NVIDIA_API_KEY.env → build prompt → SCAN → redact + map locally
  → (mismo body redactado para GLM/MiniMax: solo cambia model+params)
  → send → disclose to user what was hidden → restore values in the result
```
