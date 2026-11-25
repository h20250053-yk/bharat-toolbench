"""Gujarati station aliases (environment/data/stations.json, key "gu").

Adding Gujarati names must (a) make every station resolvable from its Gujarati base name, (b) mirror the existing
ambiguity rules (Delhi -> NDLS + NZM), (c) keep inflected forms unresolvable, exactly like Hindi/Marathi, and
(d) change nothing for the existing four languages or the mutable environment state.
"""
import json
import unicodedata
from pathlib import Path

import pytest

from environment import RailwayEnv
from environment.state import normalize_name

DATA = Path(__file__).resolve().parent.parent / "environment" / "data"
STATIONS = json.loads((DATA / "stations.json").read_text(encoding="utf-8"))["stations"]
OLD_LANGS = ("en", "hinglish", "hi", "mr")

# Mutable-state fingerprint (seats + bookings) before the Gujarati aliases were added. Aliases are static data,
# so it must not change; env_hash_before in all existing run files stays comparable.
# 3.0: the snapshot gained the (empty) cancellations / waitlist lists; bookings and seats are unchanged (2.x: 2ee9740c...a29e0)
BASELINE_STATE_HASH = "2584c4a8964d6d43460e8b3fef5e71c47dd3442e46d8d4b20506679df740bd84"

GU_EXPECTED = {
    "નવી દિલ્હી": ["NDLS"], "હઝરત નિઝામુદ્દીન": ["NZM"], "નિઝામુદ્દીન": ["NZM"], "જયપુર": ["JP"],
    "અમદાવાદ": ["ADI"], "અહમદાબાદ": ["ADI"], "મુંબઈ": ["MMCT"], "મુંબઈ સેન્ટ્રલ": ["MMCT"], "પુણે": ["PUNE"],
    "નાગપુર": ["NGP"], "બેંગલુરુ": ["SBC"], "બેંગ્લોર": ["SBC"], "બેંગલોર": ["SBC"], "લખનઉ": ["LKO"],
    "લખનૌ": ["LKO"], "કોલકાતા": ["HWH"], "હાવડા": ["HWH"],
}


@pytest.fixture(scope="module")
def env():
    return RailwayEnv()


def _codes(env, name):
    r = env.call("resolve_station", {"name": name})
    return r["ok"], (sorted(c["code"] for c in r["data"]["candidates"]) if r["ok"] else r["error"]["code"])


def test_every_station_has_gujarati_aliases_in_gujarati_script():
    for st in STATIONS:
        forms = st["aliases"].get("gu")
        assert forms, f"{st['code']} has no gu aliases"
        for f in forms:
            assert f == unicodedata.normalize("NFC", f)
            assert all(ch == " " or 0x0A80 <= ord(ch) <= 0x0AFF for ch in f), f


@pytest.mark.parametrize("name,codes", sorted(GU_EXPECTED.items()))
def test_gujarati_base_names_resolve(env, name, codes):
    assert _codes(env, name) == (True, codes)


def test_gujarati_delhi_is_ambiguous_like_hindi_and_marathi(env):
    assert _codes(env, "દિલ્હી") == (True, ["NDLS", "NZM"])
    assert _codes(env, "दिल्ली") == (True, ["NDLS", "NZM"])
    r = env.call("resolve_station", {"name": "દિલ્હી"})
    assert r["data"]["ambiguous"] is True


@pytest.mark.parametrize("inflected", ["અમદાવાદથી", "મુંબઈથી", "પુણેમાં", "જયપુરથી", "દિલ્હીથી"])
def test_gujarati_inflected_forms_do_not_resolve(env, inflected):
    """Same design as Hindi/Marathi: no fuzzy matching; the agent must pass the base name."""
    assert _codes(env, inflected) == (False, "STATION_NOT_FOUND")


def test_existing_language_resolutions_unchanged(env):
    """Every alias of the four original languages resolves exactly as it did without the gu key."""
    index = {}
    for st in STATIONS:
        forms = {st["code"], st["name"], st["city"]}
        for lang in OLD_LANGS:
            forms.update(st["aliases"][lang])
        for f in forms:
            index.setdefault(normalize_name(f), set()).add(st["code"])
    for form, codes in index.items():
        assert env.state.alias_index[form] == sorted(codes), form


def test_gujarati_aliases_never_collide_with_other_scripts(env):
    gu_keys = {normalize_name(f) for st in STATIONS for f in st["aliases"]["gu"]}
    old_keys = {normalize_name(f) for st in STATIONS for lang in OLD_LANGS for f in st["aliases"][lang]}
    assert not gu_keys & old_keys


def test_mutable_state_fingerprint_unchanged(env):
    env.reset()
    assert env.state_hash() == BASELINE_STATE_HASH
