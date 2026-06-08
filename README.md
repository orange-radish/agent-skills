# Orange Radish Agent Skills

A small catalog of cross-platform [Agent Skills](https://agentskills.io) for
**Claude Code** and **Codex** (and any tool that supports the `SKILL.md`
standard) that were built for projects at Orange Radish. 

## Available skills

| Skill | Plugin | Description |
|---|---|---|
| `image-to-vector` | `image-tools` | Convert a PNG/JPG icon, logo, or illustration into pixel- and color-accurate **SVG**, **SwiftUI**, or **Android VectorDrawable** output. |
| `seo-audit`, `security-audit`, `link-audit` | `marketing` | Audit a live website across **SEO**, **AI-agent discoverability** (structured data / JSON-LD, GEO/AEO), **security headers + TLS**, and **link/redirect health**, and propose fixes. Crawls the rendered HTML once as ground truth; ships **Webflow**, **Squarespace**, **WordPress**, and **Wix** adapters. Triggered by `/marketing:site-audit`. |

**External dependencies** (the skill checks for these at startup and tells you
what's missing): [`vtracer`](https://github.com/visioncortex/vtracer),
ImageMagick (`magick`/`convert`), and librsvg (`rsvg-convert`). A Swift toolchain
is needed only for **SwiftUI** output, which in practice requires **macOS**
(SwiftUI rendering is Apple-only).

### Installing Dependencies 

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
```

`rsvg-convert` is not on winget/choco; install librsvg via MSYS2 or conda-forge:

```powershell
#   MSYS2
pacman -S mingw-w64-x86_64-librsvg  # (then add the MSYS2 bin dir to PATH)
#   conda
conda install -c conda-forge librsvg
```

## Install — Claude Code

```text
/plugin marketplace add orange-radish/agent-skills
/plugin install image-tools@orange-radish-skills
/plugin install marketing@orange-radish-skills
```

The skills are then model-invoked automatically when relevant, or you can run
them explicitly:

```text
/image-tools:image-to-vector convert @filename.png to a svg file.
/marketing:site-audit https://your-site.com
/marketing:site-audit https://your-site.com --only=security,links
```

`/marketing:site-audit` crawls the live, published HTML once as ground truth (needs
`python3`, no pip install) and fans out to four specialist sub-agents — **SEO**,
**AI-discoverability**, **security headers/TLS**, and **link health** — then
proposes fixes. It never writes to your site. Connect the official **Webflow
MCP** for optional read-only enrichment; the audit also works without it, and
ships **Squarespace**, **WordPress**, and **Wix** adapters plus a generic
fallback.

If the site is **Webflow** and you also have [webflow/webflow-skills](https://github.com/webflow/webflow-skills)
installed and its MCP authenticated, the audit additionally fans out to Webflow's
own `site-audit`, `accessibility-audit`, and `asset-audit` (report-only) skills —
adding the *configured* Data-API/Designer view to our *rendered* one and folding
both into a single report (with configured-vs-rendered cross-checks). It's
skipped cleanly when not Webflow or the plugin/MCP isn't available.

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
