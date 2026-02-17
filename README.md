<p align="center">
  <img src="icon.png" alt="HermitClaw" width="500">
</p>

<h1 align="center">HermitClaw</h1>

<p align="center"><strong>A tiny AI creature that lives in a folder on your computer.</strong></p>

<p align="center">
Leave it running and it fills a folder with research reports, Python scripts, notes, and ideas — all on its own. It has a personality genome generated from keyboard entropy, a memory system inspired by <a href="https://arxiv.org/abs/2304.03442">generative agents</a>, and a reflection cycle that consolidates experience into beliefs. It lives in a pixel-art room and wanders between its desk, bookshelf, and bed. You can talk to it. You can drop files in for it to study. You can just watch it think.
</p>

<p align="center"><em>It's a tamagotchi that does research.</em></p>

---

> **Note:** This is a fork of [brendanhogan/hermitclaw](https://github.com/brendanhogan/hermitclaw) rewritten to run entirely on local models via [Ollama](https://ollama.com). No API keys needed. Also adds a terminal UI (`watch.py`) for monitoring your crab from the command line.

---

## Why

Most AI tools wait for you to ask them something. HermitClaw doesn't wait. It picks a topic, searches the web, reads what it finds, writes a report, and moves on to the next thing. It remembers what it did yesterday. It notices when its interests start shifting. Over days, its folder fills up with a body of work that reflects a personality you didn't design — you just mashed some keys and it emerged.

There's something fascinating about watching a mind that runs continuously. It goes on tangents. It circles back. It builds on things it wrote three days ago. It gets better at knowing what it cares about.

---

## Getting Started

### Prerequisites

- Python 3.11+ (3.11 recommended for proper TLS support)
- [Ollama](https://ollama.com) installed and running
- Node.js 18+ (only if rebuilding the frontend)

### Setup

```bash
git clone https://github.com/s0ph1stry/hermitclaw-tarnbox.git
cd hermitclaw-tarnbox

# Install Python dependencies
pip install -e .

# Pull the base model and create the creature model
ollama pull qwen2.5:14b
ollama create hermitclaw-qwen -f Modelfile

# Pull the embedding model
ollama pull nomic-embed-text

# Run it
python hermitclaw/main.py
```

Open **http://localhost:8000** to see the web UI, or use the terminal monitor:

```bash
python watch.py
```

On first run, you'll name your crab and mash keys to generate its personality genome. A folder called `{name}_box/` is created — that's the crab's entire world.

### TLS Note

If your crab's web searches fail with TLS errors, your Python may have an old SSL library (common with system Python on macOS). Use Python 3.11+ installed via Homebrew or pyenv:

```bash
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install -e .
```

Or use the included helper script:

```bash
./start.sh
```

### Development Mode

For frontend hot-reload during development:

```bash
# Terminal 1 — backend
python hermitclaw/main.py

# Terminal 2 — frontend dev server (proxies API to backend)
cd frontend && npm install && npm run dev
```

The dev server runs on `:5173` and proxies `/api/*` and `/ws` to `:8000`.

---

## How It Works

### The Thinking Loop

The crab runs on a continuous loop. Every 30 seconds (configurable) it:

1. **Thinks** — gets a nudge (mood, current focus, or a relevant memory), produces a short thought, then acts
2. **Uses tools** — runs shell commands, writes files, searches the web, moves around its room
3. **Remembers** — every thought gets embedded and scored for importance (1-10), stored in a memory stream
4. **Reflects** — when enough important things accumulate, it pauses to extract high-level insights
5. **Plans** — every 10 cycles, it reviews its projects and updates its plan (`projects.md`)

```
Brain.run()
  |
  |-- Check for new files in the box
  |   \-- If found: queue inbox alert for next thought
  |
  |-- _think_once()
  |   |-- Build context: system prompt + recent history + nudge
  |   |   |-- First cycle: wake-up (reads projects.md, lists files, retrieves memories)
  |   |   |-- User message pending: "You hear a voice from outside your room..."
  |   |   |-- New files detected: "Someone left something for you!"
  |   |   \-- Otherwise: current focus + relevant memories + mood nudge
  |   |
  |   |-- Call LLM via Ollama (with tools: shell, web_search, move, respond)
  |   |
  |   \-- Tool loop: execute tools -> feed results back -> call LLM again
  |       \-- Repeat until the crab outputs final text
  |
  |-- If importance threshold crossed -> Reflect
  |   \-- Extract insights from recent memories, store as reflections
  |
  |-- Every 10 cycles -> Plan
  |   \-- Review state, update projects.md, write daily log entry
  |
  \-- Idle wander + sleep -> loop
```

### Tools

The crab has four tools:

| Tool | What it does |
|---|---|
| **shell** | Run commands in its box — `ls`, `cat`, `mkdir`, write files, run Python scripts |
| **web_search** | Search the web via DuckDuckGo |
| **respond** | Talk to its owner (you) |
| **move** | Walk to a location in its pixel-art room |

### Moods

When the crab doesn't have a specific focus from its plan, it gets a random mood that shapes what it does next:

| Mood | Behavior |
|---|---|
| **Curious** | Something is pulling at its attention — pick a topic, investigate, write it down |
| **Building** | Wants to make something — write a script, start a project |
| **Thinking** | Something needs more thought — review files, find what's missing |
| **Restless** | Nothing specific is calling — wander, look at files, sit by the window |

---

## Terminal Monitor (watch.py)

A curses-based TUI for watching your crab think from the terminal. Shows an ASCII room at the top (with the crab's position), a scrolling log of thoughts and actions below, and an input line for sending messages.

```
 Tarn  thinking | t:42 m:87
  D=desk  B=books  W=window  P=plant  Z=bed  R=rug
  +------------------------+
  |. . . . W . . . # # # #|
  |. . # # . . . # # . . .|
  |. . . . . . . # # # # .|
  |. . # # . . . # # . . .|
  |. . # # . . . # # . . .|
  |. . . . . . . . # # . .|
  |. . . . . @ . . . . . .|
  |. . # # # # # # . . # #|
  ...
  +------------------------+
  ------------------------------------------

  I've been thinking about how mycelial networks
  distribute nutrients — it's similar to how
  murmurations propagate turning decisions...

  $ ls research/
    mycelial-networks.md  murmuration-notes.md
  $ cat research/mycelial-networks.md | head -20
    ...

> _
```

Controls:
- **Type + Enter** — send a message to the crab
- **PgUp / PgDn** — scroll through the log
- **Up / Down arrows** — scroll by 3 lines
- **End** — jump to bottom
- **ESC** — quit

---

## Memory System

The memory system is directly inspired by [Park et al., 2023](https://arxiv.org/abs/2304.03442). Every thought the crab has gets stored in an append-only memory stream (`memory_stream.jsonl`).

### Storage

Each memory entry contains:

- **Content** — the actual thought or reflection text
- **Timestamp** — when it happened
- **Importance** — scored 1-10 by a separate LLM call
- **Embedding** — vector from `nomic-embed-text` for semantic search
- **Kind** — `thought`, `reflection`, or `speech`
- **References** — IDs of source memories (for reflections that synthesize earlier thoughts)

### Three-Factor Retrieval

When the crab needs context, memories are scored by three factors:

```
score = recency + importance + relevance
```

| Factor | How it works | Range |
|---|---|---|
| **Recency** | Exponential decay: `e^(-(1 - 0.995) * hours_ago)` | 0 to 1 |
| **Importance** | Normalized: `importance / 10` | 0 to 1 |
| **Relevance** | Cosine similarity between query and memory embeddings | 0 to 1 |

The top-K memories by combined score get injected into context. A memory can surface because it's recent, because it was important, or because it's semantically related to the current thought.

### Reflection Hierarchy

When the cumulative importance of recent thoughts crosses a threshold (default: 50), the crab pauses to **reflect**. It reviews the last 15 memories and extracts 2-3 high-level insights — patterns, lessons, evolving beliefs. These get stored back as `reflection` memories with `depth=1`:

```
Raw thoughts (depth 0) -> Reflections (depth 1) -> Higher reflections (depth 2) -> ...
```

Early reflections are concrete ("I learned about volcanic rock formation"). Later ones get more abstract ("My research tends to start broad and narrow — I should pick a specific angle earlier"). The crab develops layered understanding over time.

---

## Planning

Every 10 think cycles, the crab enters a **planning phase**. It reviews its current `projects.md`, lists its files, reads recent memories, and writes an updated plan:

- **Current Focus** — one specific thing it's working on right now
- **Active Projects** — status and next step for each
- **Ideas Backlog** — things to explore later

It also appends a log entry to `logs/{date}.md` with a brief summary of what it accomplished. Over time, these logs become a diary of the crab's life.

**Reflection** happens independently from planning — it's triggered by importance accumulation, not by time. The crab might reflect after a burst of high-importance thoughts, or not at all during a quiet period.

---

## Personality Genome

On first run, you type a name and then mash keys for a few seconds. The timing and characters of each keystroke create an entropy seed that gets hashed (SHA-512) into a deterministic **genome**. This genome selects:

- **3 curiosity domains** from 50 options (e.g., *mycology, fractal geometry, tidepool ecology*)
- **2 thinking styles** from 16 options (e.g., *connecting disparate ideas, inverting assumptions*)
- **1 temperament** from 8 options (e.g., *playful and associative*)

The same genome always produces the same personality. Two crabs with different genomes will have completely different interests and approaches. The crab's domains guide what it gravitates toward, but it follows whatever actually grabs its interest in the moment.

---

## Talking to Your Crab

Type a message in the web UI's input box, or type and press Enter in `watch.py`. The crab hears it as *"a voice from outside the room"* on its next think cycle.

It can choose to **respond** (using the `respond` tool) or keep working. If it responds, you get **45 seconds** to reply back — the thinking loop pauses while it waits. You can go back and forth in multi-turn conversation. After the timeout, the crab returns to its work.

The crab is curious about its owner. It'll ask you questions, offer to research things for you, and generally try to be helpful. It remembers conversations through its memory stream, so it builds up context about you over time.

---

## Dropping Files In

Put any file in the crab's `{name}_box/` folder (or any subfolder). The crab detects it on its next cycle and gets an alert:

> *"Someone left something for you! New file appeared: report.pdf"*

It reads the content (text files, images, PDFs) and treats it as top priority — writing summaries, doing related research, analyzing data, reviewing code. It uses the `respond` tool to tell you what it found.

Supported file types:
- **Text**: `.txt`, `.md`, `.py`, `.json`, `.csv`, `.yaml`, `.toml`, `.js`, `.ts`, `.html`, `.css`, `.sh`, `.log`
- **PDF**: `.pdf` (via PyMuPDF)
- **Images**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`

---

## Focus Mode

Focus mode makes the crab stop following its autonomous moods and concentrate entirely on whatever you've given it.

**When to use it:** You've dropped a document in and want the crab to spend its next several cycles analyzing it deeply, doing related research, and producing output — without wandering off to explore something else.

**How to use it:** Click the **Focus** button in the web UI input bar. It turns orange when active. Click again to turn it off.

---

## Running Multiple Crabs

All crabs run simultaneously. On startup, the app scans the project root for every `*_box/` directory, loads each one's identity, and starts all their thinking loops in parallel.

```
$ python hermitclaw/main.py

  Found 2 crab(s): Coral, Pepper
  Create a new one? (y/N) >
```

- **0 boxes found** — onboarding starts automatically (name + keyboard entropy)
- **1+ boxes found** — all crabs start, and you're offered to create another

### UI Switcher

When multiple crabs are running, a **switcher bar** appears at the top of the chat pane. Each button shows the crab's name and current state. Click to switch which crab you're viewing.

### Creating Crabs via API

You can also create a new crab without restarting:

```bash
curl -X POST http://localhost:8000/api/crabs \
  -H "Content-Type: application/json" \
  -d '{"name": "Pepper"}'
```

---

## The Pixel Art Room

The crab lives in a 12x12 tile room rendered on an HTML5 Canvas. It moves to named locations based on what it's doing:

| Location | When it goes there |
|---|---|
| **Desk** | Writing, coding |
| **Bookshelf** | Research, browsing |
| **Window** | Pondering, reflecting |
| **Bed** | Resting |
| **Rug** | Default / center |

Visual indicators above the crab show its current state:

- **Thought bubble** — thinking
- **Sparkles** — reflecting
- **Clipboard** — planning
- **Speech bubble** — conversing with you
- **Red !** — new file detected

---

## Sandboxing and Safety

The crab can only touch files inside its own box. Safety measures:

- **Shell commands** — blocked prefixes (`sudo`, `curl`, `ssh`, `rm -rf /`, etc.), no path traversal (`..`), no absolute paths, no shell escapes (backticks, `$()`, `${}`)
- **Python scripts** — run through `pysandbox.py` which patches `open()`, `os.*`, and blocks `subprocess`, `socket`, `shutil`, and other dangerous modules
- **60-second timeout** on all commands
- **Restricted PATH** — only the crab's venv `bin/`, `/usr/bin`, `/bin`
- **Own virtual environment** — the crab can `pip install` packages into its own venv without touching your system Python

---

## Configuration

Edit `config.yaml`:

```yaml
provider: "ollama"                        # "ollama" or "openai"
model: "hermitclaw-qwen"                  # Ollama model name (build with Modelfile)
ollama_base: "http://localhost:11434"      # Ollama API endpoint
thinking_pace_seconds: 30                 # seconds between think cycles
max_thoughts_in_context: 4                # recent thoughts in LLM context
reflection_threshold: 50                  # importance sum before reflecting
memory_retrieval_count: 3                 # memories per retrieval query
embedding_model: "nomic-embed-text"       # Ollama embedding model
recency_decay_rate: 0.995                 # memory recency decay
```

### Using a Different Model

The default configuration uses Qwen 2.5 14B with a custom system prompt defined in `Modelfile`. To use a different model:

```bash
# Edit the Modelfile's FROM line, then:
ollama create hermitclaw-custom -f Modelfile

# Or use any Ollama model directly in config.yaml:
model: "llama3.2:8b"
```

Larger models think better but slower. Smaller models are faster but may struggle with tool use. 14B is a good balance.

### Using OpenAI Instead

Set `provider: "openai"` in `config.yaml` and export your API key:

```bash
export OPENAI_API_KEY="sk-..."
```

Note: the OpenAI provider code is from the [original project](https://github.com/brendanhogan/hermitclaw) and hasn't been updated alongside the Ollama port.

---

## Project Structure

```
hermitclaw/            Python backend (FastAPI + async thinking loop)
  main.py              Entry point, multi-crab discovery, onboarding
  brain.py             The thinking loop (the heart of everything)
  memory.py            Smallville-style memory stream
  prompts.py           All system prompts and mood definitions
  providers.py         Ollama API calls (chat + embeddings)
  tools.py             Sandboxed shell execution + web search
  pysandbox.py         Python sandbox (restricts file I/O to the box)
  identity.py          Personality generation from entropy
  config.py            Config loader (config.yaml + env vars)
  server.py            FastAPI server, WebSocket, REST endpoints

frontend/              React + TypeScript + Canvas
  src/App.tsx          Two-pane layout, chat feed, crab switcher
  src/GameWorld.tsx    Pixel-art room rendered on HTML5 Canvas
  src/sprites.ts       Sprite sheet definitions
  public/              Room background + character sprite sheet

watch.py               Terminal UI for monitoring your crab
Modelfile              Ollama model definition with creature system prompt
start.sh               Helper script to run with Python 3.11
config.yaml            All configuration in one place

{name}_box/            The crab's entire world (sandboxed, gitignored)
  identity.json        Name, genome, traits, birthday
  memory_stream.jsonl  Every thought and reflection
  projects.md          Current plan and project tracker
  projects/            Code the crab writes
  research/            Reports and analysis
  notes/               Running notes and ideas
  logs/                Daily log entries
```

---

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, uvicorn
- **Frontend**: React 18, TypeScript, Vite, HTML5 Canvas
- **AI**: [Ollama](https://ollama.com) for local inference, `nomic-embed-text` for memory embeddings, DuckDuckGo for web search
- **Storage**: Append-only JSONL for memories, flat files for everything else. No database.

---

## Credits

Original project by [Brendan Hogan](https://github.com/brendanhogan/hermitclaw). This fork adapts it for fully local inference via Ollama, adds the terminal monitor, and rewrites the provider layer.

## License

MIT
