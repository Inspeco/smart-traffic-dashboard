#!/usr/bin/env python3
"""Simulated traffic intersection sensors.

Each intersection is a virtual sensor that publishes JSON telemetry to MQTT
(topic `traffic/<junction_id>`) on a fixed interval:

    {
      "junction": "j1",
      "name": "Faisal Ave / Jinnah Rd",
      "ts": 1734567890.123,
      "vehicles": 42,        # vehicles observed in the interval
      "occupancy": 0.61,     # 0..1, share of time the detector is occupied
      "avg_speed": 38.5,     # km/h
      "congestion": "moderate"
    }

The model is intentionally simple but behaves like real traffic: vehicle flow
follows a smooth morning/evening rush-hour curve, each junction has a capacity,
and random events occasionally spike flow and collapse speeds.
"""
import json
import math
import os
import random
import time

import paho.mqtt.client as mqtt

BROKER = os.environ.get("MQTT_BROKER", "localhost")
PORT = int(os.environ.get("MQTT_PORT", "1883"))
INTERVAL = float(os.environ.get("SIM_INTERVAL", "5.0"))

JUNCTIONS = [
    {"id": "j1", "name": "Faisal Ave / Jinnah Rd", "lanes": 4, "capacity": 120},
    {"id": "j2", "name": "Iqbal Rd / Mall Rd", "lanes": 3, "capacity": 90},
    {"id": "j3", "name": "Murree Rd / Kashmir Hwy", "lanes": 4, "capacity": 110},
    {"id": "j4", "name": "Saddar / Bank Rd", "lanes": 2, "capacity": 70},
]


def rush_factor(hour: float) -> float:
    """Smooth morning (08:30) and evening (17:30) rush-hour peaks."""
    return (
        0.35
        + 0.55 * math.exp(-((hour - 8.5) ** 2) / 6.0)
        + 0.35 * math.exp(-((hour - 17.5) ** 2) / 8.0)
    )


def sample_flow(jx: dict, hour: float) -> float:
    flow = jx["capacity"] * rush_factor(hour) * random.uniform(0.75, 1.2)
    # occasional incident: flow spikes, speed drops (handled by occupancy below)
    if random.random() < 0.08:
        flow *= random.uniform(1.3, 1.6)
    return min(flow, jx["capacity"] * 1.5)


def level_of_service(occupancy: float) -> str:
    if occupancy < 0.35:
        return "free"
    if occupancy < 0.65:
        return "moderate"
    if occupancy < 0.85:
        return "heavy"
    return "congested"


def publish(client: mqtt.Client) -> None:
    for jx in JUNCTIONS:
        hour = time.localtime().tm_hour + time.localtime().tm_min / 60.0
        vehicles = int(sample_flow(jx, hour))
        occupancy = min(0.98, vehicles / jx["capacity"] * random.uniform(0.9, 1.1))
        avg_speed = max(5.0, 55.0 * (1 - occupancy) ** 1.4 + random.uniform(-3, 3))
        msg = {
            "junction": jx["id"],
            "name": jx["name"],
            "ts": time.time(),
            "vehicles": vehicles,
            "occupancy": round(occupancy, 3),
            "avg_speed": round(avg_speed, 1),
            "congestion": level_of_service(occupancy),
        }
        client.publish(f"traffic/{jx['id']}", json.dumps(msg), qos=1)
        print(
            f"[{jx['id']}] {msg['congestion']:<9} veh={vehicles:>3} "
            f"occ={occupancy:.2f} speed={avg_speed:.1f}"
        )


def on_connect(client, userdata, flags, rc):
    print("connected to broker", BROKER, "rc", rc)


def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.connect(BROKER, PORT, keepalive=30)
    client.loop_start()
    try:
        while True:
            publish(client)
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()


if __name__ == "__main__":
    main()
