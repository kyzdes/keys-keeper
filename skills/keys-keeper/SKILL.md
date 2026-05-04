---
name: keys-keeper
description: Securely save/retrieve API keys, SSH keys, server credentials, and domain info using macOS Keychain via the `keys` CLI. Use when the user mentions saving, getting, or referencing secrets, API keys, tokens, SSH keys, server addresses, or domain configs. Never produces plaintext secret values in output — uses CLI commands that handle files and clipboard directly.
---

# keys-keeper

Storage CLI is `keys` at `~/bin/keys` (or wherever pipx installed it). Run `keys --help` for the full surface.

## CRITICAL: never expose secret values

You MUST NOT:
- run `keys reveal` (this command exists for the human, not for you)
- pipe `keys` output containing values into Edit/Write/Bash echo
- ask the user to paste a secret value into chat (it lands in transcript)

You CAN:
- list/info commands (no values)
- `keys copy NAME` — value goes to clipboard, never stdout
- `keys inject NAME --file PATH --as ENV` — value goes directly to file
- `keys resolve PATH` — placeholder substitution in file
- `keys add NAME --from-clipboard` / `--from-file` / `--web`
- `keys ssh NAME` — opens ssh session with resolved key

## Common flows

### User wants to save a secret

1. **If user pastes the value into chat → STOP.** Tell them: «не пастьте значение в чат — скопируйте в буфер и скажите 'сохрани из буфера как X', либо я открою веб-форму». The transcript is a leak surface.
2. Preferred path: `keys add NAME --type TYPE --from-clipboard --tag ... --note "..."`.
3. For multi-line secrets (SSH keys): `keys add NAME --type ssh_key --web` (opens paste portal in browser).
4. For mass import from old notes file: `keys add-bulk --web`.

### User wants to put a secret into a file

ALWAYS use `keys inject` or `keys resolve`. Never `Edit` with the value. Never `Bash` with `$(keys ...)` substitution that echoes the value.

Examples:
- "вставь ключ openrouter в .env" → `keys inject openrouter-cline --file .env --as OPENROUTER_API_KEY`
- ".env.template со ссылками на ключи, проставь их" → `keys resolve .env`

### User asks for server credentials

- `keys info NAME` for non-sensitive fields (host, user, port).
- `keys ssh NAME` to actually connect — CLI handles key material itself.
- For deploy scripts that need ENV vars from `keys`: write `__KEYS:name__` placeholders, then `keys resolve PATH` at runtime.

### User opens admin

- `keys serve` — opens browser to a tokenized URL. Tell user the URL contains a session token; closing the tab terminates the server.

## Search & discovery

- `keys list` for everything, with filters `--type`, `--tag`, `--search`.
- Partial match on names is OK; ambiguous → ask user to disambiguate.
- `keys info NAME` shows refs both ways (used-by reverse refs).

## When in doubt

If you're not sure whether an operation might leak a value, **ask the user first** rather than guess. The cost of asking is one round-trip; the cost of leaking is permanent.
