# keys-keeper

> **This repo has moved to [kyzdes/keys-keeper-skill](https://github.com/kyzdes/keys-keeper-skill).**

Starting with v0.2.0 the CLI source, the Claude Code skill, and the marketplace plugin all live in a single monolith repo at:

➡️ **<https://github.com/kyzdes/keys-keeper-skill>**

The marketplace URL (`/plugin marketplace add kyzdes/claude-skills`) is unchanged — existing subscribers will auto-update transparently.

## Install

**As Claude Code plugin (recommended):**

```
/plugin marketplace add kyzdes/claude-skills
/plugin install keys-keeper@kyzdes-claude-skills
```

**As CLI:**

```bash
pipx install git+https://github.com/kyzdes/keys-keeper-skill.git
```

## Why this repo is archived

This was the original CLI-only repo. After Windows support landed in v0.2.0, the skill markdown and the CLI source were merged into one repo so contributors only have to update one place. The new repo contains the same code, full history of v0.2.0, and all future releases.

See the [v0.2.0 release notes](https://github.com/kyzdes/keys-keeper/releases/tag/v0.2.0) for the last entry made here, and the new repo for everything since.
