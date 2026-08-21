# Smart City Traffic Management Dashboard

A live traffic monitoring dashboard for smart-city operations — congestion levels, per-junction status and flow metrics in one place, served as an **Azure Static Web App**.

## Why this exists

Urban traffic is noisy and hard to reason about without good data. This project is a playground for turning raw, high-frequency sensor data into something a control room can actually act on: live congestion, junction health, and flow trends.

## System architecture

The dashboard is the front-end of a full IoT-style data pipeline:

<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/0995fde0-23e7-44b0-81df-0d4be347b790" />



- **Sensors (simulated):** `simulator/sensor.py` emulates intersection sensors, publishing vehicle count, occupancy and average speed at fixed intervals over MQTT (`traffic/#`).
- **Broker:** Eclipse Mosquitto (dockerised) handling publish/subscribe fan-out on `traffic/#`.
- **Ingestion & API:** `ingestion/subscriber.py` subscribes to the topics, keeps the latest reading per junction, and exposes an HTTP API (`/api/traffic`, `/api/health`).
- **Dashboard:** this repo — a single-page app rendering live congestion, per-junction stats and alerts.

## Cloud & networking (Azure)

The dashboard is deployed as an **Azure Static Web App** with CI/CD via GitHub Actions (see `.github/workflows/`), giving you global CDN and managed TLS for free.

For a production deployment of the full pipeline, the design keeps the network boundaries tight:

- **VNet & subnets** — dedicated subnets for the broker tier, ingestion tier and any VM-hosted services, so east-west traffic is contained and auditable.
- **NSGs & network ACLs** — security groups (and NACLs at VNet boundaries) lock ports down to what each tier needs: MQTT (8883) is reachable only from the ingestion subnet, the dashboard talks only to the API.
- **Public exposure** — limited to the static app and API endpoints; the broker and processing tier stay private.
- **Secrets management** — broker credentials and API keys injected via application settings / environment, never committed.

## Repository layout

```
.
├── index.html                       # Dashboard (single page)
├── simulator/                       # MQTT traffic-sensor simulator (Python)
│   └── sensor.py
├── ingestion/                       # MQTT subscriber + HTTP API (Python)
│   └── subscriber.py
├── broker/
│   └── mosquitto.conf               # MQTT broker config
├── docker-compose.yml               # broker + simulator + ingestion
└── .github/workflows/
    └── azure-static-web-apps-*.yml  # Azure SWA CI/CD build & deploy
```

## Run locally

The full pipeline (broker + simulator + ingestion) runs with Docker Compose:

```bash
docker compose up --build
```

- MQTT broker: `localhost:1883` (topics `traffic/#`)
- Ingestion API: `http://localhost:8000/api/traffic`

Or just the dashboard — it's a static single-page app:

```bash
python3 -m http.server 8080
```

## Deployment

Pushing to `main` triggers the Azure Static Web Apps workflow, which builds and publishes the dashboard to Azure. Config lives in `.github/workflows/azure-static-web-apps-*.yml`.

## Roadmap

- [x] MQTT traffic-sensor simulator (Python)
- [x] Broker + ingestion subscriber as a Docker Compose stack
- [ ] Live updates to the dashboard over WebSocket/SSE
- [ ] Time-series storage (e.g. InfluxDB/TimescaleDB) for historical congestion trends
