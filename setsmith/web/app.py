"""setsmith web app: create a gig, propose/vote/veto, generate, print."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..cache import Cache
from ..config import settings
from ..db import DB
from ..engine.build import build_setlist
from ..engine.vibes import VIBE_PRESETS
from ..http import Client
from ..models import Song
from ..sources.deezer import Deezer
from ..sources.discovery import discover
from ..sources.lastfm import LastFM

BASE = Path(__file__).parent
app = FastAPI(title="setsmith")
templates = Jinja2Templates(directory=str(BASE / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")

db = DB(settings.db_path)
_client = Client(settings, Cache(settings.cache_path))
deezer = Deezer(_client)
lastfm = LastFM(_client, settings.lastfm_key)

MODES = [("brainstorm", "Brainstorm, tool builds the set"),
         ("ranker", "Ranker, only our proposed songs"),
         ("mix", "Mix, our songs + suggestions")]


# --- helpers ----------------------------------------------------------------
def _songs_ctx(gig_id: int) -> dict:
    songs = db.get_songs(gig_id)
    songs.sort(key=lambda s: (-(s.upvotes), s.vetoed, s.title.lower()))
    return {"songs": songs, "gig_id": gig_id}


def _gig_or_404(gig_id: int) -> dict:
    g = db.get_gig(gig_id)
    if not g:
        raise KeyError(gig_id)
    return g


# --- pages ------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "vibes": VIBE_PRESETS, "modes": MODES})


@app.post("/gig")
def create_gig(name: str = Form("Gig"), vibe: str = Form("wedding"),
               mode: str = Form("brainstorm"),
               target_count: Optional[int] = Form(15),
               target_minutes: Optional[float] = Form(None)):
    gid = db.create_gig(name or "Gig", vibe, mode, target_count, target_minutes)
    return RedirectResponse(f"/gig/{gid}", status_code=303)


@app.get("/gig/{gig_id}", response_class=HTMLResponse)
def gig_page(request: Request, gig_id: int):
    g = _gig_or_404(gig_id)
    return templates.TemplateResponse(request, "gig.html", {
        "gig": g, "vibes": VIBE_PRESETS, "modes": MODES,
        "setlist": db.get_setlist(gig_id), **_songs_ctx(gig_id)})


@app.get("/gig/{gig_id}/search", response_class=HTMLResponse)
def search(request: Request, gig_id: int, q: str = ""):
    results = deezer.search(q, limit=8) if q.strip() else []
    return templates.TemplateResponse(request, "_results.html", {
        "results": results, "gig_id": gig_id})


@app.post("/gig/{gig_id}/propose", response_class=HTMLResponse)
def propose(request: Request, gig_id: int, title: str = Form(...), artist: str = Form(...),
            source_id: str = Form(None), duration: int = Form(None),
            member: str = Form("Anon")):
    db.add_song(gig_id, Song(
        title=title, artist=artist, source="deezer", source_id=source_id,
        duration_s=duration, proposed_by=member, is_suggestion=False))
    return templates.TemplateResponse(request, "_songs.html", _songs_ctx(gig_id))


@app.post("/gig/{gig_id}/vote", response_class=HTMLResponse)
def vote(request: Request, gig_id: int, song_id: int = Form(...),
         value: int = Form(...), member: str = Form("Anon")):
    db.set_vote(gig_id, song_id, member, value)
    return templates.TemplateResponse(request, "_songs.html", _songs_ctx(gig_id))


@app.post("/gig/{gig_id}/generate", response_class=HTMLResponse)
def generate(request: Request, gig_id: int):
    g = _gig_or_404(gig_id)
    mode, vibe = g["mode"], g["vibe"]
    proposals = db.get_songs(gig_id, only_proposals=True)

    guaranteed = set()
    if mode == "ranker":
        pool = proposals
    else:
        discovered = discover(deezer, vibe, limit=150, lastfm=lastfm)
        if mode == "brainstorm":
            pool = discovered
        else:  # mix: band proposals pinned in, suggestions fill the rest
            seen = {s.key for s in proposals}
            pool = proposals + [s for s in discovered if s.key not in seen]
            guaranteed = {s.key for s in proposals if not s.vetoed}

    setlist = build_setlist(pool, mode=mode, vibe=vibe,
                            target_count=g["target_count"],
                            target_minutes=g["target_minutes"],
                            weights=g.get("weights"), guaranteed_keys=guaranteed)
    snapshot = [{
        "position": slot.position, "section": slot.section,
        "title": slot.scored.song.title, "artist": slot.scored.song.artist,
        "minutes": round(slot.scored.song.duration_min, 1),
        "reason": slot.scored.reason(),
        "is_suggestion": slot.scored.song.is_suggestion,
        "proposed_by": slot.scored.song.proposed_by,
    } for slot in setlist.slots]
    db.save_setlist(gig_id, snapshot)
    return templates.TemplateResponse(request, "_setlist.html", {
        "setlist": snapshot, "gig": g,
        "total_minutes": round(setlist.total_minutes)})


@app.get("/gig/{gig_id}/print", response_class=HTMLResponse)
def print_setlist(request: Request, gig_id: int):
    g = _gig_or_404(gig_id)
    sl = db.get_setlist(gig_id)
    return templates.TemplateResponse(request, "print.html", {
        "gig": g, "setlist": sl,
        "total_minutes": round(sum(s.get("minutes", 0) for s in sl))})


def main():
    import uvicorn
    uvicorn.run("setsmith.web.app:app", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
