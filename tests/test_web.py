"""Tests for the web API and static server."""
import json
import threading
import urllib.request

import pytest

from nexus.web import server


def test_routes_pure_functions():
    assert server._api_detect({"input": "SGVsbG8="})["candidates"]
    assert server._api_hash({"input": "hello"})["hashes"]["md5"].startswith("5d41402")
    assert server._api_hash_id({"input": "5d41402abc4b2a76b9719d911017c592"})["candidates"][0]["name"] == "MD5"
    assert server._api_code_id({"input": "def f(): pass"})["candidates"][0]["language"] == "Python"
    assert server._api_ports({"input": "443"})["matches"][0]["service"] == "https"
    assert server._api_iocs({"input": "go http://x.com 1.2.3.4"})["ioc_total"] >= 2
    assert server._api_defang({"input": "http://x.com"})["output"] == "hxxp[://]x[.]com"


def test_decode_route_auto_and_named():
    auto = server._api_decode({"input": "Uryyb", "codec": "auto"})
    assert auto["candidates"][0]["recipe"] == ["rot13"]
    named = server._api_decode({"input": "SGk=", "codec": "base64"})
    assert named["output"] == "Hi"


@pytest.fixture()
def live_server():
    httpd = server.serve("127.0.0.1", 0)  # ephemeral port
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


def test_static_and_api_over_http(live_server):
    index = urllib.request.urlopen(live_server + "/").read().decode()
    assert "Nexus Console" in index
    meta = json.load(urllib.request.urlopen(live_server + "/api/meta"))
    assert "version" in meta

    req = urllib.request.Request(
        live_server + "/api/crypt/detect",
        data=json.dumps({"input": "SGVsbG8="}).encode(),
        headers={"Content-Type": "application/json"},
    )
    body = json.load(urllib.request.urlopen(req))
    assert body["candidates"]


def test_path_traversal_blocked(live_server):
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(live_server + "/../server.py")
    assert exc.value.code == 404
