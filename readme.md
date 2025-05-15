# WasteWatch Smart Bin Dashboard API

**Course**: SI5038701 - Cloud and Fog Computing in the Internet of Things

**Provides bin locations, KPIs, history, forecasts, alerts, and route optimization**

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Locally](#running-locally)
- [Running with Docker](#running-with-docker)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [CORS](#cors)
- [License](#license)

## Features

- **List Bin Locations**: Retrieve all smart bin locations with latitude and longitude.
- **Current KPIs**: Get the latest fill level and gas sensor readings for a specific bin, plus next scheduled pickup.
- **7-Day Forecast**: View predicted fill levels and gas readings over the next seven days.
- **Sensor History**: Access the most recent 100 sensor data points for a bin.
- **Active Alerts**: Check alerts for pickup needs or gas threshold breaches.
- **Route Optimization**: Calculate the optimal pickup route using OR‑Tools.

## Algorithm

The route optimization functionality models the pickup locations as nodes in a Vehicle Routing Problem (VRP). We leverage Google's OR-Tools CP-SAT solver, which uses a constraint programming approach to minimize total travel distance and time. The algorithm:

1. Constructs a distance matrix between all bin locations.
2. Defines routing constraints (e.g., start/end at the depot, visit each bin once).
3. Uses the CP-SAT solver to find an optimal or near-optimal route.

This approach ensures scalable and efficient route planning for IoT-enabled smart bins.

## Tech Stack

- **Python** 3.11
- **FastAPI** for building the RESTful API
- **Uvicorn** as the ASGI server
- **PostgreSQL** for data storage
- **psycopg2** for PostgreSQL connectivity
- **python-dotenv** for environment variable management
- **OR‑Tools** for route optimization
- **Pydantic** for data validation

## Installation

1. **Clone the repository**

   ```bash
   git clone git@github.com:satyaadhiyaksaardy/CFiot-web-backend.git
   cd CFiot-web-backend
   ```

2. **Create and activate a virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install --no-cache-dir -r requirements.txt
   ```

## Configuration

Create a `.env` file in the `backend` directory with the following variables:

```
DB_HOST=<your-db-host>
DB_PORT=<your-db-port>
DB_USER=<your-db-user>
DB_PASSWORD=<your-db-password>
DB_NAME=<your-db-name>
```

## Running Locally

Start the API server with Uvicorn:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Open your browser and navigate to:

- Interactive docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Running with Docker

Build the Docker image:

```bash
docker build -t wastewatch-backend .
```

Run the container:

```bash
docker run -d -p 8000:8000 \
  -e DB_HOST=<db-host> \
  -e DB_PORT=<db-port> \
  -e DB_USER=<db-user> \
  -e DB_PASSWORD=<db-password> \
  -e DB_NAME=<db-name> \
  wastewatch-backend
```

## API Endpoints

### `GET /bins`

Returns a list of all smart bin locations.

**Response Example**

```json
[
  {
    "id": "bin1",
    "latitude": 12.345678,
    "longitude": 98.765432
  }
]
```

### `GET /bins/{bin_id}/kpi`

Retrieve current KPIs for a specific bin.

- **Path Parameters**
  - `bin_id` (string): Identifier of the bin.

**Response Model**

```json
{
  "current_fill": 65.2,
  "next_pickup": "2025-05-17T08:00:00Z",
  "ch4": 0.03,
  "nh3": 0.01
}
```

### `GET /bins/{bin_id}/forecast`

7-day forecast of fill levels and gas readings.

**Response Model**

```json
[
  {
    "timestamp": "2025-05-16T00:00:00Z",
    "fill": 70.1,
    "ch4": 0.04,
    "nh3": 0.02,
    "type": "forecast"
  }
]
```

### `GET /bins/{bin_id}/history`

Recent sensor readings (limit 100).

**Response Model**

```json
[
  {
    "timestamp": "2025-05-15T12:00:00Z",
    "fill": 64.5,
    "ch4": 0.03,
    "nh3": 0.02,
    "type": "sensor"
  }
]
```

### `GET /bins/{bin_id}/alerts`

Active alerts for a bin.

**Response Model**

```json
{
  "alerts": ["Pickup needed", "Gas threshold exceeded"]
}
```

### `POST /optimize-route`

Optimize pickup route given a list of locations.

- **Request Body**

  ```json
  {
    "locations": [
      { "lat": 12.345678, "lng": 98.765432 },
      { "lat": 12.346, "lng": 98.7659 }
    ]
  }
  ```

- **Response Model**
  ```json
  {
    "route_order": [0, 1],
    "route": [
      { "lat": 12.345678, "lng": 98.765432 },
      { "lat": 12.346, "lng": 98.7659 }
    ]
  }
  ```

## Database Schema

Ensure the following tables exist in your PostgreSQL database:

```sql
CREATE TABLE sensor_data (
  lokasi_id TEXT,
  latitude FLOAT,
  longitude FLOAT,
  timestamp TIMESTAMP,
  fill_percentage FLOAT,
  ch4 FLOAT,
  nh3 FLOAT
);

CREATE TABLE predictions (
  lokasi_id TEXT,
  prediction_time TIMESTAMP,
  fill_percentage FLOAT,
  ch4 FLOAT,
  nh3 FLOAT,
  need_pickup BOOLEAN,
  gas_exceeded_threshold BOOLEAN
);
```

## CORS

CORS is configured to allow all origins.

## License

This project is licensed under the MIT License.
