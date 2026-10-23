"""Smoke-Tests fuer alle oeffentlichen Ansichten.

Diese Tests sichern ab, dass beim Umbauen keine Zuschauer-Ansicht kaputtgeht.
"""
import pytest


def test_landing_zeigt_turniere(client, simple_tournament):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Simple Cup" in resp.data


def test_landing_ohne_turniere(client):
    assert client.get("/").status_code == 200


@pytest.mark.parametrize("pfad", ["/", "/speisekarte", "/t/", "/phone/", "/tv/",
                                  "/phone/speisekarte", "/tv/speisekarte"])
def test_globale_seiten_erreichbar(client, simple_tournament, menu_items, pfad):
    resp = client.get(pfad)
    assert resp.status_code == 200, f"{pfad} antwortet {resp.status_code}"


@pytest.mark.parametrize("suffix", ["/", "/tv/", "/phone/"])
def test_turnieransichten_erreichbar(client, simple_tournament, suffix):
    slug = simple_tournament["tournament"].slug
    resp = client.get(f"/t/{slug}{suffix}")
    assert resp.status_code == 200, f"{suffix} antwortet {resp.status_code}"


@pytest.mark.parametrize("suffix", ["/", "/tv/", "/phone/"])
def test_unbekanntes_turnier_404(client, suffix):
    assert client.get(f"/t/gibt-es-nicht{suffix}").status_code == 404


def test_speisekarte_zeigt_preise(client, menu_items):
    resp = client.get("/speisekarte")
    assert b"Bratwurst" in resp.data
    assert b"3,00" in resp.data


def test_api_state_struktur(client, simple_tournament):
    slug = simple_tournament["tournament"].slug
    resp = client.get(f"/t/{slug}/api/state")
    assert resp.status_code == 200
    data = resp.get_json()

    for key in ("tournament", "live_match", "live_matches", "past_matches",
                "upcoming_matches", "final_matches", "standings_by_group",
                "groups", "settings"):
        assert key in data, f"Feld {key} fehlt in /api/state"

    assert data["tournament"]["slug"] == slug
    assert data["live_match"] is None
    assert len(data["past_matches"]) == 6
    assert len(data["groups"]) == 1

    gid = str(simple_tournament["group"].id)
    standings = data["standings_by_group"][gid]["standings"]
    assert standings[0]["team"]["name"] == "Alpha"


def test_api_state_unbekanntes_turnier(client):
    resp = client.get("/t/gibt-es-nicht/api/state")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "not found"
