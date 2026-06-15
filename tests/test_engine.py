"""Engine tests: scoring axes, mode weighting, veto/votes, sequencing arc."""

from setsmith.engine.build import build_setlist
from setsmith.engine.score import score_pool
from setsmith.engine.sequence import sequence_set, target_curve
from setsmith.engine.vibes import get_vibe
from setsmith.models import Song


def _song(title, artist, rank=100000, genre="Pop", year=2010, energy=0.6,
          ease=None, upvotes=0, vetoed=False, dur=210, suggestion=True):
    return Song(title=title, artist=artist, raw_rank=rank, genre=genre, year=year,
                energy_proxy=energy, ease=ease, upvotes=upvotes, vetoed=vetoed,
                duration_s=dur, is_suggestion=suggestion)


def _pool():
    return [
        _song("Hi Pop", "A", rank=900000, genre="Pop", energy=0.6),
        _song("Banger", "B", rank=500000, genre="Dance", energy=0.95),
        _song("Ballad", "C", rank=300000, genre="Folk", energy=0.2),
        _song("Rocker", "D", rank=400000, genre="Rock", energy=0.85),
        _song("Mid", "E", rank=200000, genre="R&B", energy=0.5),
    ]


def test_veto_excluded_and_votes_raise_rank():
    pool = _pool()
    pool[0].vetoed = True            # "Hi Pop" should never appear
    pool[4].upvotes = 10             # "Mid" gets a big member boost
    preset = get_vibe("wedding")
    weights = {"popularity": 0.2, "ease": 0.1, "vibe": 0.1, "member": 0.6}
    scored = score_pool(pool, preset, weights)
    titles = [s.song.title for s in scored]
    assert "Hi Pop" not in titles
    assert titles[0] == "Mid"        # votes dominate under heavy member weight


def test_brainstorm_ignores_member_votes():
    pool = _pool()
    pool[4].upvotes = 50             # would dominate if member axis counted
    sl = build_setlist(pool, mode="brainstorm", vibe="dance_party", target_count=4)
    # member weight is zeroed in brainstorm, so the high-energy/popular songs lead,
    # not the heavily-upvoted mid track by virtue of votes alone
    top_titles = [s.scored.song.title for s in sl.slots]
    assert "Banger" in top_titles    # dance vibe + high energy + popular

def test_target_curve_shape():
    c = target_curve(10)
    assert c[0] >= 0.75              # strong opener
    assert c[-1] >= 0.85            # strong closer
    assert max(c) >= 0.9           # a real peak
    assert min(c[1:-1]) < c[0]     # a dip somewhere in the middle


def test_sequence_sections_and_artist_spacing():
    pool = _pool()
    preset = get_vibe("wedding")
    scored = score_pool(pool, preset, preset.weights)
    sl = sequence_set(scored, preset)
    assert sl.slots[0].section == "opener"
    assert sl.slots[-1].section == "closer"
    # no back-to-back same artist (pool has distinct artists, so guaranteed)
    artists = [s.scored.song.artist for s in sl.slots]
    assert all(artists[i] != artists[i + 1] for i in range(len(artists) - 1))


def test_mix_pins_guaranteed_proposals():
    # one low-popularity band proposal among many strong discovery songs
    proposal = _song("Our Jam", "BandFave", rank=10, genre="Folk", energy=0.3,
                     suggestion=False)
    discovery = [_song(f"Hit{i}", f"Star{i}", rank=900000 - i, genre="Pop")
                 for i in range(20)]
    sl = build_setlist([proposal] + discovery, mode="mix", vibe="wedding",
                       target_count=8, guaranteed_keys={proposal.key})
    titles = [s.scored.song.title for s in sl.slots]
    assert "Our Jam" in titles            # pinned despite low popularity


def test_ranker_uses_only_given_pool_and_length():
    pool = [_song(f"S{i}", chr(65 + i), rank=100000 + i, upvotes=i) for i in range(8)]
    sl = build_setlist(pool, mode="ranker", vibe="dive_bar", target_count=5)
    assert len(sl.slots) == 5
