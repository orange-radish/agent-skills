# Orange Radish Agent Skills

A catalog of cross-platform [Agent Skills](https://agentskills.io) for
**Claude Code** and **Codex** (and any tool that supports the `SKILL.md`
standard). Skills are authored once and distributed to both agents.

## Available skills

| Skill | Plugin | Description |
|---|---|---|
| `image-to-vector` | `image-tools` | Convert a PNG/JPG icon, logo, or illustration into pixel- and color-accurate **SVG**, **SwiftUI**, or **Android VectorDrawable** output. |

**External dependencies** (the skill checks for these and tells you what's
missing): [`vtracer`](https://github.com/visioncortex/vtracer), ImageMagick
(`magick`/`convert`), librsvg (`rsvg-convert`), and a Swift toolchain (only for
SwiftUI output).

```sh
brew install vtracer imagemagick librsvg
```

## Install — Claude Code

```text
/plugin marketplace add orange-radish/agent-skills
/plugin install image-tools@orange-radish-skills
```

The skill is then model-invoked automatically when relevant, or you can run it
explicitly:

```text
/image-tools:image-to-vector
```

Update later with `/plugin marketplace update orange-radish-skills`.

## Install — Codex

Codex has no marketplace; it discovers skills from `~/.agents/skills/` (all
projects) or `<your-project>/.agents/skills/` (one project), and follows
symlinks. Clone this repo and copy the skill folder into a skills directory:

```sh
git clone https://github.com/orange-radish/agent-skills.git

# User scope — available in every project:
mkdir -p ~/.agents/skills
cp -R agent-skills/plugins/image-tools/skills/image-to-vector ~/.agents/skills/

# Or repo scope — copy into your own project instead:
# mkdir -p <your-project>/.agents/skills
# cp -R agent-skills/plugins/image-tools/skills/image-to-vector <your-project>/.agents/skills/
```

> Some older Codex builds read skills from `~/.codex/skills/` instead. See the
> [official Codex skills docs](https://developers.openai.com/codex/skills) for
> the paths your version uses.

This repo also ships an `.agents/skills/` directory, so you can run Codex
directly from a clone of it without copying anything.

## Repo layout

```
agent-skills/
├── .claude-plugin/marketplace.json     # Claude Code marketplace catalog
├── plugins/
│   └── image-tools/                    # one plugin per cohesive domain
│       ├── .claude-plugin/plugin.json
│       └── skills/
│           └── image-to-vector/        # the skill (single source of truth)
└── .agents/skills/                     # symlinks for Codex repo-local use
    └── image-to-vector -> ../../plugins/image-tools/skills/image-to-vector
```

### Adding a skill

1. Put it under `plugins/<plugin>/skills/<skill>/` with a `SKILL.md`. Group
   related skills in the same plugin; use a **separate** plugin for an unrelated
   domain so users can install only what they need.
2. If the plugin is new, add an entry to `.claude-plugin/marketplace.json` and
   create its `plugins/<plugin>/.claude-plugin/plugin.json`.
3. Add a matching `.agents/skills/<skill>` symlink so the skill is usable by
   Codex from a clone:
   ```sh
   ln -s ../../plugins/<plugin>/skills/<skill> .agents/skills/<skill>
   ```
4. `SKILL.md` frontmatter must include a portable `name` and `description`. Keep
   the description specific and add a "do not use for…" clause — both agents use
   it to decide when to activate the skill.
5. Validate before pushing: `claude plugin validate .`

## License

[MIT](LICENSE)
