# setsmith

A local web tool that builds a gig set list. It scores songs on popularity, ease, event vibe,
and member votes, then orders the picks into an energy arc (strong open, build, peak, breather,
strong close) rather than a flat ranked list.

Three modes:

- Brainstorm: the tool generates a full set for the vibe.
- Ranker: rank and order only the songs the band proposed.
- Mix: keep the band's proposals and fill the rest with suggestions.

Members propose, upvote, and veto from their phones. A veto removes a song; upvotes raise it.

## Details

- Candidates come from Deezer's keyless API (popularity, era, genre, duration). An optional
  Last.fm key adds mood tags. setsmith does not use Spotify audio-features or recommendations,
  which were deprecated for new apps.
- Local-first: it runs on your laptop, and bandmates on the same wifi join from their phones. No
  accounts or cloud required. Hosting is a later option.

## Run it

```bash
git clone https://github.com/s-eun-young-g/mit-live-lets-make-a-set
cd mit-live-lets-make-a-set
uv venv && uv pip install -e .
setsmith            # serves on http://0.0.0.0:8000
```

Open `http://localhost:8000` on your laptop. For bandmates to join from their phones, share your
LAN address (for example `http://192.168.1.42:8000`) while on the same wifi.

Optional Last.fm enrichment (free key):
```bash
export LASTFM_API_KEY=your_key
```

## How it works

The `sources` (Deezer and optional Last.fm) feed `discovery`, which builds a candidate pool for
the vibe. `engine.score` rates each song on popularity, ease, vibe-fit, and member votes, and
`engine.sequence` orders the chosen songs into an arc. The web UI handles propose, vote, veto,
generate, and print. SQLite stores gigs, songs, and votes; an HTTP cache keeps API calls fast.

## Develop

```bash
uv pip install -e ".[dev]"
pytest
```

## License

MIT
