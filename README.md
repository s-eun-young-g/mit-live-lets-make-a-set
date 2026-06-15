# setsmith

Build a gig set list in minutes. setsmith weighs **popularity**, **ease**, **event vibe**, and
your **bandmates' votes/vetoes**, then *sequences* the picks into a real set (open strong →
build → peak → breather → big close) — not just a ranked playlist.

Three modes:
- **Brainstorm** — the tool generates a full set from scratch for the vibe.
- **Ranker** — rank/sequence only the songs your band proposed.
- **Mix** — your proposals, supplemented with tool suggestions to fill the gaps.

Members **propose, upvote, and veto** from their phones (a veto removes the song; votes raise it).

## Why it's different
- It **sequences** for an energy arc, with artist spacing and a target length — the part that
  makes a set feel pro.
- **Open discovery + auto-enrichment**: candidates come from all popular music via Deezer's
  **keyless** API (popularity, era, genre, duration); an optional Last.fm key adds mood tags and
  similar-track discovery. (Spotify's audio-features/recommendations were deprecated for new apps,
  so setsmith deliberately doesn't depend on them.)
- **Local-first**: runs on your laptop; bandmates on the same wifi join the gig from their phones —
  no accounts, no cloud needed (hosting is a later upgrade).

## Run it
```bash
git clone https://github.com/s-eun-young-g/mit-live-lets-make-a-set
cd mit-live-lets-make-a-set
uv venv && uv pip install -e .
setsmith            # serves on http://0.0.0.0:8000
```
Open `http://localhost:8000` on your laptop. To let bandmates join from their phones, share your
LAN address (e.g. `http://192.168.1.42:8000`) while on the same wifi.

Optional richer vibe/discovery via Last.fm (free key):
```bash
export LASTFM_API_KEY=your_key
```

## How it works
`sources` (Deezer / optional Last.fm) → `discovery` builds a candidate pool for the vibe →
`engine.score` rates each song on popularity / ease / vibe-fit / member votes →
`engine.sequence` orders them into an arc → web UI for propose/vote/veto/generate/print.
SQLite stores gigs, songs, and votes; a cache keeps API calls fast.

## Develop
```bash
uv pip install -e ".[dev]"
pytest
```

## License
MIT
