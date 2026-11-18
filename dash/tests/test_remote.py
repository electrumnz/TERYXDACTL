"""4G remote texts (docs/remote-access.md): who gets an answer, what each command does."""

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from teryx_dash import remote as R
from teryx_dash.remote import (FakeModem, MmcliModem, RemoteConfig, RemoteRules, RemoteService, Sms,
                               normalise_number, parse_mm_time, where_text)

OWNER = "021 123 4567"


def cfg(enabled=True):
    c = RemoteConfig(enabled=enabled, numbers=[normalise_number(OWNER)])
    c.set_code("4821")
    return c


def test_numbers_normalise_to_plus64():
    for raw in ("021 123 4567", "0211234567", "+64 21 123 4567", "0064211234567", "+64-21-123-4567"):
        assert normalise_number(raw) == "+64211234567"
    assert normalise_number("") == "" and normalise_number("hello") == ""


def test_code_is_hashed_never_kept(tmp_path):
    c = cfg()
    assert c.check_code("4821") and not c.check_code("4822") and not c.check_code("")
    p = tmp_path / "remote.json"
    c.save(p)
    text = p.read_text()
    assert "4821" not in text and c.code_hash in text
    assert (p.stat().st_mode & 0o777) == 0o600
    back = RemoteConfig.load(p)
    assert back.check_code("4821") and back.numbers == ["+64211234567"]
    assert "code_hash" not in back.public() and back.public()["code_set"]
    with pytest.raises(ValueError):
        c.set_code("12")
    with pytest.raises(ValueError):
        c.set_code("12ab")


def test_only_listed_number_with_code_gets_a_command():
    r = RemoteRules(cfg())
    assert r.handle(Sms("+64 27 999 9999", "WHERE 4821", 0), 1).ignored == "number not on the list"
    assert r.handle(Sms(OWNER, "where", 0), 1).ignored == "wrong code"
    assert r.handle(Sms(OWNER, "hello 4821", 0), 1).ignored == "not a command"
    for text in ("WHERE 4821", "where 4821", "Where? 4821", "lock 4821", "CAMS 4821", "off 4821", "help 4821"):
        assert r.handle(Sms(OWNER, text, 0), 1).command == text.split()[0].strip("?").lower()


def test_off_when_disabled_and_old_texts_dropped():
    assert RemoteRules(cfg(enabled=False)).handle(Sms(OWNER, "WHERE 4821", 0), 1).ignored == "remote access is off"
    r = RemoteRules(cfg())
    assert r.handle(Sms(OWNER, "LOCK 4821", 0), R.MAX_AGE_S + 1).ignored == "too old"


def test_five_wrong_codes_blocks_everyone_for_an_hour():
    r = RemoteRules(cfg())
    for i in range(R.WRONG_CODE_LIMIT):
        assert r.handle(Sms(OWNER, "LOCK 1111", 0), 10 + i).ignored == "wrong code"
    assert r.handle(Sms(OWNER, "LOCK 4821", 0), 20).ignored == "blocked after wrong codes"
    assert r.handle(Sms(OWNER, "LOCK 4821", 0), 20 + R.WRONG_CODE_BLOCK_S).command == "lock"


def test_reply_limit_still_locks_but_stays_quiet():
    r = RemoteRules(cfg())
    for i in range(R.MAX_REPLIES_PER_HOUR):
        assert r.handle(Sms(OWNER, "WHERE 4821", 0), i).command == "where"
    o = r.handle(Sms(OWNER, "WHERE 4821", 0), 50)
    assert o.command is None and o.ignored == "reply limit"
    o = r.handle(Sms(OWNER, "LOCK 4821", 0), 51)
    assert o.command == "lock" and o.ignored == "reply limit"
    assert r.handle(Sms(OWNER, "WHERE 4821", 0), 3700).command == "where"


def test_where_text():
    st = {"pi.gps.fix": True, "pi.gps.lat": -36.84846, "pi.gps.lon": 174.76334, "mc.online": True, "mc.speed": 23.4,
          "in.ignition": True, "lock.state": "unlocked", "an.aux_12v": 12.71}
    t = where_text(st, 0)
    assert "https://maps.google.com/?q=-36.84846,174.76334" in t and "23 km/h" in t and "key ON" in t
    assert "12V 12.7V" in t and "—" not in t
    assert "No GPS fix yet" in where_text({}, 0)
    t = where_text({"remote.last_fix": (-36.8, 174.7, 0), "lock.pending": True}, 600)
    assert "Last at" in t and "10 min ago" in t and "lock waiting to stop" in t


class Gw:
    def __init__(self):
        self.locks = []
        self.state = {"lock.state": "unlocked", "in.ignition": False}

    def lock(self, cmd, digits=None):
        self.locks.append(cmd)

    def snapshot(self):
        return dict(self.state)


async def test_service_end_to_end(tmp_path):
    gw, modem, now = Gw(), FakeModem(), [1000.0]
    svc = RemoteService(modem, tmp_path / "remote.json", gw, gw.snapshot, clock=lambda: now[0], rules=RemoteRules(cfg()))
    # A stranger gets nothing at all.
    modem.inbox.append(Sms("+6427000000", "LOCK 4821", now[0]))
    await svc.poll()
    assert modem.sent == [] and gw.locks == []
    # The owner locks: the Pi asks the control box for a REMOTE lock (never "lock now").
    modem.inbox.append(Sms(OWNER, "LOCK 4821", now[0]))
    await svc.poll()
    assert gw.locks == ["remote"]
    assert modem.sent[-1][0] == OWNER and "never while moving" in modem.sent[-1][1]
    # CAMS turns data on, and it goes off again by itself.
    modem.inbox.append(Sms(OWNER, "cams 4821", now[0]))
    await svc.poll()
    assert modem.data_on and "Tailscale" in modem.sent[-1][1]
    now[0] += 29 * 60
    await svc.poll()
    assert modem.data_on
    now[0] += 2 * 60
    await svc.poll()
    assert not modem.data_on
    # No PIN set: say so instead of pretending.
    gw.state["lock.state"] = "off"
    modem.inbox.append(Sms(OWNER, "LOCK 4821", now[0]))
    await svc.poll()
    assert "No PIN set" in modem.sent[-1][1] and gw.locks == ["remote"]
    # The log never has the code in it.
    assert all("4821" not in str(entry) for entry in svc.log)
    # Never texts on its own: polling with nothing in the inbox sends nothing.
    n = len(modem.sent)
    for _ in range(5):
        now[0] += 3600
        await svc.poll()
    assert len(modem.sent) == n


async def test_routes(tmp_path):
    gw = Gw()
    app = web.Application()
    modem = FakeModem()
    R.setup_remote_routes(app, gw, lambda: tmp_path, gw.snapshot, modem=modem, poll_s=3600)
    c = TestClient(TestServer(app))
    await c.start_server()
    try:
        d = await (await c.get("/api/remote")).json()
        assert d["simulated"] and not d["enabled"] and not d["code_set"]
        r = await c.put("/api/remote", json={"enabled": True})
        assert r.status == 400   # number and code first
        r = await c.put("/api/remote", json={"numbers": [OWNER], "code": "4821", "enabled": True})
        assert r.status == 200 and (await r.json())["enabled"]
        assert "4821" not in (tmp_path / "remote.json").read_text()
        r = await c.post("/api/remote/sim-text", json={"from": OWNER, "text": "WHERE 4821"})
        assert "lock: unlocked" in (await r.json())["replies"][0]
        gw.state["lock.state"] = "locked"
        r = await c.put("/api/remote", json={"code": "9999"})
        assert r.status == 403   # can't change it while locked
    finally:
        await c.close()


async def test_mmcli_modem_reads_and_deletes(monkeypatch):
    calls = []
    outputs = {
        ("mmcli", "-m", "any", "--messaging-list-sms", "-K"):
            "modem.messaging.sms.length : 2\nmodem.messaging.sms.value[1] : /org/freedesktop/ModemManager1/SMS/3\n"
            "modem.messaging.sms.value[2] : /org/freedesktop/ModemManager1/SMS/4\n",
        ("mmcli", "-s", "3", "-K"): "sms.content.number : +64211234567\nsms.content.text : WHERE 4821\n"
                                    "sms.properties.state : received\nsms.properties.timestamp : 2026-11-18T19:04:11+13\n",
        ("mmcli", "-s", "4", "-K"): "sms.content.number : +64211234567\nsms.content.text : old\nsms.properties.state : sent\n",
    }

    async def run(*args, timeout=20):
        calls.append(args)
        if args[:4] == ("mmcli", "-m", "any", "--messaging-create-sms=number='+64211234567',text='Hi there  ok'"):
            return "Successfully created new SMS: /org/freedesktop/ModemManager1/SMS/9\n"
        return outputs.get(args, "")

    m = MmcliModem(run=run)
    msgs = await m.read_sms()
    assert len(msgs) == 1 and msgs[0].text == "WHERE 4821" and msgs[0].sender == "+64211234567"
    assert abs(msgs[0].when - parse_mm_time("2026-11-18T19:04:11+13:00")) < 1
    assert ("mmcli", "-m", "any", "--messaging-delete-sms=3") in calls
    await m.send_sms("021 123 4567", "Hi there, ok")
    assert ("mmcli", "-s", "9", "--send") in calls
    await m.set_data(True)
    assert calls[-1] == ("nmcli", "connection", "up", "teryx-4g")


async def test_phone_app_link(tmp_path):
    """The phone app texts ONLINE, connects over Tailscale, then keeps the link up or drops it with the code."""
    gw = Gw()
    app = web.Application()
    modem = FakeModem()
    svc = R.setup_remote_routes(app, gw, lambda: tmp_path, gw.snapshot, modem=modem, poll_s=3600)
    svc.rules = RemoteRules(cfg())
    c = TestClient(TestServer(app))
    await c.start_server()
    try:
        assert (await (await c.get("/api/remote/link")).json())["up"] is False
        r = await c.post("/api/remote/sim-text", json={"from": OWNER, "text": "ONLINE 4821"})
        assert (await r.json())["data_on"] and "Tailscale" in (await r.json())["replies"][0]
        link = await (await c.get("/api/remote/link")).json()
        assert link["up"] and link["minutes_left"] > 29 and "code" not in str(link)
        assert (await c.post("/api/remote/link", json={"code": "0000", "minutes": 60})).status == 403
        r = await c.post("/api/remote/link", json={"code": "4821", "minutes": 60})
        assert r.status == 200 and (await r.json())["minutes_left"] > 59
        r = await c.post("/api/remote/link", json={"code": "4821", "off": True})
        assert (await r.json())["up"] is False and not modem.data_on
        # Wrong codes on the app count toward the same block as texts.
        for _ in range(R.WRONG_CODE_LIMIT - 1):
            await c.post("/api/remote/link", json={"code": "1111"})
        await c.post("/api/remote/sim-text", json={"from": OWNER, "text": "WHERE 1111"})   # the fifth, by text
        assert (await c.post("/api/remote/link", json={"code": "4821"})).status == 403
        r = await c.post("/api/remote/sim-text", json={"from": OWNER, "text": "WHERE 4821"})
        assert (await r.json())["replies"] == []
    finally:
        await c.close()
