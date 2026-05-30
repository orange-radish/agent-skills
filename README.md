# Orange Radish Agent Skills

A small catalog of cross-platform [Agent Skills](https://agentskills.io) for
**Claude Code** and **Codex** (and any tool that supports the `SKILL.md`
standard) that were built for projects at Orange Radish. 

## Available skills

| Skill | Plugin | Description |
|---|---|---|
| `image-to-vector` | `image-tools` | Convert a PNG/JPG icon, logo, or illustration into pixel- and color-accurate **SVG**, **SwiftUI**, or **Android VectorDrawable** output. |

**External dependencies** (the skill checks for these at startup and tells you
what's missing): [`vtracer`](https://github.com/visioncortex/vtracer),
ImageMagick (`magick`/`convert`), and librsvg (`rsvg-convert`). A Swift toolchain
is needed only for **SwiftUI** output, which in practice requires **macOS**
(SwiftUI rendering is Apple-only).

`vtracer` is a Rust tool, so the same command works everywhere if you have
[Rust](https://rustup.rs):

```sh
cargo install vtracer
```

**macOS** ([Homebrew](https://brew.sh)):

```sh
brew install vtracer imagemagick librsvg
```

**Linux:**

```sh
# Debian / Ubuntu
sudo apt install imagemagick librsvg2-bin   # + cargo install vtracer

# Fedora
sudo dnf install ImageMagick librsvg2-tools # + cargo install vtracer

# Arch
sudo pacman -S imagemagick librsvg          # + cargo install vtracer
```

**Windows** ([winget](https://learn.microsoft.com/windows/package-manager/) or
[Chocolatey](https://chocolatey.org)):

```powershell
winget install ImageMagick.ImageMagick     # or: choco install imagemagick
cargo install vtracer                       # needs Rust

# rsvg-convert is not on winget/choco; install librsvg via MSYS2 or conda-forge:
#   MSYS2:  pacman -S mingw-w64-x86_64-librsvg   (then add the MSYS2 bin dir to PATH)
#   conda:  conda install -c conda-forge librsvg
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
```

Or repo scope — copy into your own project instead:

```sh
mkdir -p <your-project>/.agents/skills
cp -R agent-skills/plugins/image-tools/skills/image-to-vector <your-project>/.agents/skills/
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

## License

[MIT](LICENSE)
