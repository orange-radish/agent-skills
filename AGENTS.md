# Repository guide for coding agents

This repo is a **distribution catalog of Agent Skills** for Claude Code and
Codex. It is not an application — there is nothing to build or run. Your job here
is to author and package skills correctly.

## Layout

- Skills live at `plugins/<plugin>/skills/<skill>/`, each with a `SKILL.md`. A
  plugin may ship **multiple peer skills** plus `commands/` and `agents/`.
- A plugin may also have a plugin-level shared dir (e.g. `marketing/core/` with
  `tools/`, `procedures/`, `adapters/`) reused by several skills/agents/commands.
  Reference it via `${CLAUDE_PLUGIN_ROOT}/core/...` from commands/agents and a
  relative `../../core/...` from a skill's `SKILL.md`. Such a plugin is meant to
  be installed whole — copying one skill folder in isolation won't include the
  shared `core/`.
- `plugins/<plugin>/.claude-plugin/plugin.json` is the plugin manifest.
- `.claude-plugin/marketplace.json` (repo root) is the Claude Code catalog and
  must list every plugin.
- `.agents/skills/<skill>` symlinks point into the canonical skill folders so
  Codex can discover them when running from a clone of this repo (one symlink
  per skill, including each peer skill in a multi-skill plugin).

The skill folder under `plugins/<plugin>/skills/` is the **single source of
truth**. Do not create duplicate copies — `.agents/skills/` entries are symlinks,
never copies.

## Conventions

- Group related skills in one plugin; put an unrelated domain in a **separate**
  plugin so users can install only what they need.
- `SKILL.md` frontmatter needs a portable `name` and `description`. Make the
  description specific and include a "do not use for…" clause — both Claude Code
  and Codex use it to decide when to activate the skill.
- Omit `version` from manifests during active development (the git commit SHA is
  used). Add an explicit `version` only for tagged releases, and set it in just
  one place (`plugin.json` wins over the marketplace entry).

## When adding or changing a skill

1. Edit/add files only under `plugins/<plugin>/skills/<skill>/`.
2. New plugin → add it to `.claude-plugin/marketplace.json` and create its
   `plugins/<plugin>/.claude-plugin/plugin.json`. The marketplace entry's
   `category` must be one of Claude Code's fixed values — `database`,
   `deployment`, `design`, `development`, `learning`, `location`, `math`,
   `monitoring`, `productivity`, `security`, `testing`. An unrecognized
   category makes the loader **silently drop the plugin** (it won't appear for
   `/plugin install`), and `claude plugin validate` does **not** catch it.
3. New skill → add a matching symlink:
   `ln -s ../../plugins/<plugin>/skills/<skill> .agents/skills/<skill>`.
4. Validate before committing: `claude plugin validate .` and
   `claude plugin validate ./plugins/<plugin>`.
