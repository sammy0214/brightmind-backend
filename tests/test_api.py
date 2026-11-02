from tests.conftest import auth

REG = {"email": "mum@example.com", "password": "a-long-password", "region": "africa",
       "consent_given": True, "consent_policy_version": "2026-01"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "region": "africa"}


def test_registration_requires_consent_and_correct_region(client):
    assert client.post("/auth/register", json={**REG, "consent_given": False}).status_code == 400
    assert client.post("/auth/register", json={**REG, "region": "eu_br_in"}).status_code == 409


def test_full_flow(client):
    token = client.post("/auth/register", json=REG).json()["access_token"]
    assert client.post("/auth/register", json=REG).status_code == 409  # duplicate

    child = client.post("/children", headers=auth(token), json={
        "display_name": "Thandi", "birth_year": 2016, "grade": 4, "language": "zu"}).json()

    # child device token cannot use parent-only endpoints
    ctoken = client.post(f"/children/{child['id']}/device-token",
                         headers=auth(token)).json()["access_token"]
    assert client.get("/children", headers=auth(ctoken)).status_code == 403

    sess = client.post("/sessions", headers=auth(ctoken), json={"subject": "maths"}).json()
    r1 = client.post(f"/sessions/{sess['id']}/turns", headers=auth(ctoken),
                     data={"text": "What is 6 x 7?", "attempted_first": "true"})
    r2 = client.post(f"/sessions/{sess['id']}/turns", headers=auth(ctoken),
                     data={"text": "I don't know", "attempted_first": "false", "hint_level": "2"})
    assert r1.status_code == r2.status_code == 201
    assert client.post(f"/sessions/{sess['id']}/end", headers=auth(ctoken)).status_code == 200

    summary = client.get(f"/dashboard/children/{child['id']}/summary",
                         headers=auth(token)).json()
    assert summary["sessions"] == 1 and summary["turns"] == 2
    assert summary["independence_score"] == 0.5

    # revoking consent locks everything out immediately
    assert client.post("/auth/consent/revoke", headers=auth(token)).status_code == 204
    assert client.get("/children", headers=auth(token)).status_code == 403
    assert client.get("/children", headers=auth(ctoken)).status_code == 403
