#!/usr/bin/env python3
"""Ingestion subscriber.

Subscribes to `traffic/#` on the MQTT broker, keeps the latest reading per
junction in memory, and exposes a small HTTP API the dashboard can poll:

    GET /api/traffic   -> latest state for every junction
    GET /api/health    -> liveness + broker connection state

Runs two threads: the MQTT client loop and the Flask API.
"""
import json
import os
import threading
import time

import paho.mqtt.client as mqtt
from flask import Flask, jsonify

BROKER = os.environ.get("MQTT_BROKER", "localhost")
PORT = int(os.environ.get("MQTT_PORT", "1883"))
HOST = os.environ.get("INGEST_HOST", "0.0.0.0")
HTTP_PORT = int(os.environ.get("INGEST_PORT", "8000"))

state: dict = {}
state_lock = threading.Lock()
connected = {"broker": False}

app = Flask(__name__)


def on_connect(client, userdata, flags, rc):
    connected["broker"] = rc == 0
    if connected["broker"]:
        client.subscribe("traffic/#")


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        jid = data.get("junction") or msg.topic.rsplit("/", 1)[-1]
        with state_lock:
            state[jid] = data
    except Exception:
        pass  # malformed message - drop it


@app.get("/api/traffic")
def traffic():
    with state_lock:
        return jsonify({"junctions": list(state.values()), "updated": time.time()})


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "broker_connected": connected["broker"]})


def mqtt_loop():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(BROKER, PORT, keepalive=30)
        client.loop_forever()
    except Exception as exc:  # broker not up yet -> keep trying
        print("mqtt error:", exc)
        connected["broker"] = False


if __name__ == "__main__":
    threading.Thread(target=mqtt_loop, daemon=True).start()
    app.run(host=HOST, port=HTTP_PORT)
