# keys-keeper

Personal macOS-first secrets manager for one developer who runs many AI agents and many servers. Stores API keys, SSH keys, server credentials, and domain info in the macOS Keychain, with a Claude skill that prevents secret values from ever entering an agent's transcript.

**Status:** v0.1 — single-user, macOS only.

## Install

```bash
pipx install /path/to/keys-keeper
keys doctor                              # creates ~/.config/keys-keeper/, probes keychain
echo 'export KEYS_KEEPER_ALLOW_REVEAL=1' >> ~/.zshrc   # optional, lets shell users print plaintext
./scripts/install_skill.sh               # copies the Claude skill
```

## Quick start

```bash
# save a secret without typing the value into an AI chat
pbcopy <<<"sk-or-v1-..."
keys add openrouter-cline --type api_key --from-clipboard --tag llm

# get it into a file
keys inject openrouter-cline --file .env --as OPENROUTER_API_KEY

# open the local admin to browse 50+ entries
keys serve
```

## Output-safe command surface

| For Claude (safe) | For shell (gated) |
|---|---|
| `keys add NAME --from-clipboard` | `keys reveal NAME` (requires `KEYS_KEEPER_ALLOW_REVEAL=1`) |
| `keys list / info / audit` | |
| `keys copy NAME` (clipboard, auto-clear 30s) | |
| `keys inject NAME --file F --as ENV` | |
| `keys resolve FILE` (substitute `__KEYS:name__`) | |
| `keys ssh NAME` | |

The skill markdown forbids Claude from running `reveal`. The CLI default surface is built so even a misbehaving agent can't extract plaintext into the transcript.

## See also

- [`docs/superpowers/specs/2026-05-04-keys-keeper-design.md`](docs/superpowers/specs/2026-05-04-keys-keeper-design.md) — full design
- [`ux-spec-2026-05-04-keys-keeper-admin.md`](ux-spec-2026-05-04-keys-keeper-admin.md) — admin UX spec
- [`keys-keeper-admin-canvas.html`](keys-keeper-admin-canvas.html) — interactive design canvas

## License

Private project. No license granted.
