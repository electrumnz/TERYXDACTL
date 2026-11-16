import asyncio
import json

from teryx.dash.gateway import Gateway
from teryx.dash.server import build_app
from teryx.sim.runner import Simulator


async def test_websocket_streams_state_and_takes_requests(aiohttp_client, bus_spec):
    sim = Simulator(bus_spec, "idle").start()
    gw = Gateway(bus_spec).start()
    try:
        client = await aiohttp_client(build_app(gw, sim))
        assert (await client.get("/")).status == 200
        assert (await client.get("/sim")).status == 200
        assert (await client.get("/virtual")).status == 200
        assert (await client.get("/virtual-static/virtual.js")).status == 200
        assert (await client.get("/vendor/three/three.module.min.js")).status == 200
        assert (await client.get("/vendor/three/OrbitControls.js")).status == 200
        canmap = await (await client.get("/api/canmap")).json()
        assert any(m["id"] == "0x710" for m in canmap["messages"])

        ws = await client.ws_connect("/ws")
        await ws.send_str(json.dumps({"type": "request", "id": "light.interior", "value": 90}))
        await ws.send_str(json.dumps({"type": "request", "id": "nope", "value": 1}))
        got_error = got_light = False
        for _ in range(100):
            msg = json.loads((await ws.receive(timeout=2)).data)
            if msg["type"] == "error":
                got_error = True
            elif msg["type"] == "state" and msg["state"].get("light.interior") == 90:
                got_light = True
                assert msg["state"]["sim.scenario"] == "idle"
            if got_error and got_light:
                break
        assert got_error and got_light

        r = await client.post("/api/sim", json={"scenario": "reversing"})
        assert (await r.json())["scenario"] == "reversing"
        r = await client.post("/api/sim", json={"scenario": "nope"})
        assert r.status == 400
        await ws.close()
    finally:
        gw.stop()
        sim.stop()
        await asyncio.sleep(0)
