from onlyask.pwa import DogfoodPWA, MANIFEST, SERVICE_WORKER, _png_icon


def test_manifest_is_installable_shape():
    assert MANIFEST["display"] == "standalone"
    assert MANIFEST["start_url"] == "/"
    assert {i["sizes"] for i in MANIFEST["icons"]} == {"192x192", "512x512"}
    assert "CACHE" in SERVICE_WORKER


def test_generated_icons_are_png():
    assert _png_icon(192).startswith(b"\x89PNG\r\n\x1a\n")
    assert _png_icon(512).startswith(b"\x89PNG\r\n\x1a\n")


def test_pwa_auth_uses_bearer_token():
    app=DogfoodPWA(auth_token="secret")
    assert app.login("wrong") is False
    assert app.login("secret") is True
    assert app.authorized(None) is False
    assert app.authorized("Bearer wrong") is False
    assert app.authorized("Bearer secret") is True
    assert app.authorized(None, f"oa_session={app.session_cookie}") is True
    assert "secret" not in app.session_cookie


def test_uncertain_state_is_visually_flagged():
    from onlyask.pwa import PAGE

    assert ".uncertain{color:var(--d)}" in PAGE
