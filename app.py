from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
import math
import os
import psycopg2
from psycopg2 import sql
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

# --- FastAPI app --------------------------------------------
app = FastAPI(
    title="WasteWatch Smart Bin Dashboard API",
    description="Provides bin locations, KPIs, history, forecasts, alerts, and route optimization",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic models ---------------------------------------
class Location(BaseModel):
    lat: float
    lng: float

class RouteRequest(BaseModel):
    locations: List[Location] = Field(..., min_items=2)

class RouteResponse(BaseModel):
    route_order: List[int]
    route: List[Location]

class BinInfo(BaseModel):
    id: str
    latitude: float
    longitude: float

class KPI(BaseModel):
    current_fill: float
    next_pickup: datetime
    ch4: float
    nh3: float

class ForecastPoint(BaseModel):
    timestamp: datetime
    fill: float
    ch4: float
    nh3: float
    type: str  # 'forecast'

class HistoryPoint(BaseModel):
    timestamp: datetime
    fill: float
    ch4: float
    nh3: float
    type: str  # 'sensor'

class AlertResponse(BaseModel):
    alerts: List[str]

# --- Utility functions ------------------------------------
def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        port=os.environ.get("DB_PORT"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        dbname=os.environ.get("DB_NAME")
    )

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def build_distance_matrix(coords: List[Location]):
    n = len(coords)
    mat = [[0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                mat[i][j] = haversine(
                    coords[i].lat, coords[i].lng,
                    coords[j].lat, coords[j].lng
                )
    return mat

def solve_tsp(dist_matrix):
    n = len(dist_matrix)
    manager = pywrapcp.RoutingIndexManager(n, 1, 0)
    routing = pywrapcp.RoutingModel(manager)
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node   = manager.IndexToNode(to_index)
        return int(dist_matrix[from_node][to_node] * 1000)
    idx = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(idx)
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    solution = routing.SolveWithParameters(params)
    if not solution:
        return None
    index = routing.Start(0)
    route = []
    while not routing.IsEnd(index):
        route.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))
    route.append(manager.IndexToNode(index))
    return route

# --- Route Optimization Endpoint ---------------------------
@app.post("/optimize-route", response_model=RouteResponse, summary="Optimize pickup route")
def optimize_route(req: RouteRequest):
    coords = req.locations
    dist_matrix = build_distance_matrix(coords)
    order = solve_tsp(dist_matrix)
    if order is None:
        raise HTTPException(status_code=500, detail="No route solution found")
    ordered = [coords[i] for i in order]
    return RouteResponse(route_order=order, route=ordered)

# --- Dashboard Data Endpoints -----------------------------
@app.get("/bins", response_model=List[BinInfo], summary="List all bin locations")
def list_bins():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT lokasi_id, latitude, longitude FROM sensor_data")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [BinInfo(id=r[0], latitude=r[1], longitude=r[2]) for r in rows]

@app.get("/bins/{bin_id}/kpi", response_model=KPI, summary="Current KPIs for a bin")
def get_kpi(bin_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(sql.SQL(
        "SELECT fill_percentage, ch4, nh3 FROM sensor_data WHERE lokasi_id=%s ORDER BY timestamp DESC LIMIT 1"
    ), (bin_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Bin not found")
    current_fill, ch4, nh3 = row
    cur.execute(sql.SQL(
        "SELECT prediction_time FROM predictions WHERE lokasi_id=%s AND need_pickup=TRUE ORDER BY prediction_time ASC LIMIT 1"
    ), (bin_id,))
    nxt = cur.fetchone()
    cur.close()
    conn.close()
    if not nxt:
        raise HTTPException(status_code=404, detail="No pickup scheduled")
    return KPI(current_fill=current_fill, next_pickup=nxt[0], ch4=ch4, nh3=nh3)

@app.get("/bins/{bin_id}/forecast", response_model=List[ForecastPoint], summary="7-day forecast")
def get_forecast(bin_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(sql.SQL(
        "SELECT prediction_time, fill_percentage, ch4, nh3 FROM predictions WHERE lokasi_id=%s ORDER BY prediction_time ASC"
    ), (bin_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [ForecastPoint(timestamp=r[0], fill=r[1], ch4=r[2], nh3=r[3], type="forecast") for r in rows]

@app.get("/bins/{bin_id}/history", response_model=List[HistoryPoint], summary="Recent sensor readings")
def get_history(bin_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(sql.SQL(
        "SELECT timestamp, fill_percentage, ch4, nh3 FROM sensor_data WHERE lokasi_id=%s ORDER BY timestamp DESC LIMIT 100"
    ), (bin_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [HistoryPoint(timestamp=r[0], fill=r[1], ch4=r[2], nh3=r[3], type="sensor") for r in rows]

@app.get("/bins/{bin_id}/alerts", response_model=AlertResponse, summary="Active alerts for a bin")
def get_alerts(bin_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(sql.SQL(
        "SELECT 'Pickup needed' FROM predictions WHERE lokasi_id=%s AND need_pickup=TRUE UNION "
        "SELECT 'Gas threshold exceeded' FROM predictions WHERE lokasi_id=%s AND gas_exceeded_threshold=TRUE"
    ), (bin_id, bin_id))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return AlertResponse(alerts=[r[0] for r in rows])

# --- Run with Uvicorn ---------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

