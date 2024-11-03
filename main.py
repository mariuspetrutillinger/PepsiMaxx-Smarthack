import uuid

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import httpx
import os
import sqlite3
import pandas as pd
from queue import PriorityQueue
import json
from typing import List, Optional
from uuid import UUID
from collections import defaultdict

app = FastAPI()
BASE_URL = os.getenv("BASE_URL")
API_KEY = os.getenv("API_KEY")
sesh_id = None
conn = sqlite3.connect('file::memory:?cache=shared', uri=True)


def create_in_memory_db():
    global conn
    cursor = conn.cursor()

    with open('data/ddl.sql', 'r') as ddl_file:
        ddl_script = ddl_file.read()

    cursor.executescript(ddl_script)

    conn.commit()
    return conn


def load_data_from_csv(conn, csv_file_path, table_name):
    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_file_path, header=0, sep=';')

    # Load the DataFrame into the SQLite database
    df.to_sql(table_name, conn, index=False, if_exists='append')


@app.on_event("startup")
async def startup_event():
    global conn
    conn = create_in_memory_db()
    load_data_from_csv(conn, 'data/teams.csv', 'team')
    load_data_from_csv(conn, 'data/customers.csv', 'network_node')
    load_data_from_csv(conn, 'data/refineries.csv', 'network_node')
    load_data_from_csv(conn, 'data/tanks.csv', 'network_node')
    load_data_from_csv(conn, 'data/connections.csv', 'network_connection')
    load_data_from_csv(conn, 'data/demands.csv', 'demand')


@app.on_event("shutdown")
async def shutdown_event():
    global conn
    conn.close()
    conn = None


class Movement:
    def __init__(self, id: str, amount: int, connection: 'ConnectionDto'):
        self.id = id
        self.amount = amount
        self.connection = connection


class MovementSchedule:
    def __init__(self, day: int):
        self.day = day
        self.movements: List[Movement] = []

    def add_movement(self, movement: Movement):
        self.movements.append(movement)


class ConnectionManager:
    _instance = None

    def __init__(self):
        self.next_available_day = defaultdict(int)
        self.movement_schedule_list: List[MovementSchedule] = []

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize_schedule(self):
        self.movement_schedule_list = [MovementSchedule(day=i) for i in range(43)]

    def add_movement_to_movement_schedule(self, day: int, movement: Movement):
        schedule = next((s for s in self.movement_schedule_list if s.day == day), None)
        if schedule:
            schedule.add_movement(movement)
        else:
            raise ValueError(f"No MovementSchedule found for the given day: {day}")

    def initialize_connection(self, connection_id: str):
        self.next_available_day[connection_id] = 0

    def is_connection_available(self, connection_id: str, current_day: int) -> bool:
        return current_day >= self.next_available_day[connection_id]

    def schedule_transport(self, connection_id: str, arrival_day: int):
        self.next_available_day[connection_id] = arrival_day


class DayRequestDto(BaseModel):
    day: int
    movements: list


class CustomerDto(BaseModel):
    id: str
    name: str
    max_input: int
    over_input_penalty: float
    late_delivery_penalty: float
    early_delivery_penalty: float
    node_type: str


class DemandDto(BaseModel):
    customer: CustomerDto
    amount: int
    postDay: int
    startDay: int
    endDay: int


class PenaltyDto(BaseModel):
    day: int
    type: str
    message: str
    cost: int
    co2: int


class KpiDto(BaseModel):
    day: int
    cost: int
    co2: int


class DayResponseDto(BaseModel):
    round: int
    demand: list[DemandDto]
    penalties: list[PenaltyDto]
    deltaKpis: KpiDto
    totalKpis: KpiDto


class ErrorResponseSchema(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    properties: dict


class ConnectionDto(BaseModel):
    id: str
    from_id: str
    to_id: str
    distance: int
    lead_time_days: int
    connection_type: str
    max_capacity: int


class RefineryDto(BaseModel):
    id: str
    name: str
    capacity: int
    max_output: int
    production: int
    overflow_penalty: float
    underflow_penalty: float
    over_output_penalty: float
    production_cost: float
    production_co2: float
    initial_stock: int
    node_type: str


class TankDto(BaseModel):
    id: str
    name: str
    capacity: int
    max_output: int
    max_input: int
    overflow_penalty: float
    underflow_penalty: float
    over_output_penalty: float
    over_input_penalty: float
    initial_stock: int
    node_type: str


class MovementDto(BaseModel):
    connection_id: str
    flow: int
    priority: float


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


@app.post("/session/start")
async def start_session():
    global sesh_id
    global API_KEY
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{BASE_URL}/api/v1/session/start",
                headers={"API-KEY": API_KEY}
            )
        response.raise_for_status()
        sesh_id = response.text
        return {"session_id": sesh_id}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)


@app.post("/session/end")
async def stop_session():
    global API_KEY
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{BASE_URL}/api/v1/session/end",
                headers={"API-KEY": API_KEY}
            )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)


@app.post("/play/round")
async def play_round(day_request: DayRequestDto):
    global sesh_id
    global API_KEY
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{BASE_URL}/api/v1/play/round",
                headers={
                    "API-KEY": API_KEY,
                    "SESSION-ID": sesh_id
                },
                json=day_request.dict()
            )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)


def calculate_flow(refinary, tank, connection):
    flow = min(refinary.max_output, tank.max_input, connection.max_capacity)
    return flow


def calculate_priority(refinary, tank, connection):
    refinery_fullness = refinary.initial_stock / refinary.capacity
    tank_fullness = tank.initial_stock / tank.capacity
    priority = refinery_fullness - tank_fullness if connection.connection_type == 'PIPELINE' else (
                                                                                                          refinery_fullness - tank_fullness) / 2
    return priority


@app.get("/solve")
async def solve():
    global sesh_id
    global API_KEY
    global conn
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM network_node where node_type = 'REFINERY'")
    refineries_data = cursor.fetchall()
    refineries = [RefineryDto(**dict(zip([column[0] for column in cursor.description], row))) for row in
                  refineries_data]
    cursor.execute("SELECT * FROM network_node where node_type = 'STORAGE_TANK'")
    tanks_data = cursor.fetchall()
    tanks = [TankDto(**dict(zip([column[0] for column in cursor.description], row))) for row in tanks_data]

    cursor.execute("SELECT * FROM network_node where node_type = 'CUSTOMER'")
    customers_data = cursor.fetchall()
    customers = [CustomerDto(**dict(zip([column[0] for column in cursor.description], row))) for row in customers_data]

    cursor.execute("SELECT * FROM network_connection")
    connections_data = cursor.fetchall()
    connections = [ConnectionDto(**dict(zip([column[0] for column in cursor.description], row))) for row in
                   connections_data]
    connection_manager = ConnectionManager.get_instance()
    connection_manager.initialize_schedule()
    day = 0
    movements = []
    for connection in connections:
        refinery = next((refinery for refinery in refineries if refinery.id == connection.from_id), None)
        tank = next((tank for tank in tanks if tank.id == connection.to_id), None)
        if refinery and tank:
            flow = calculate_flow(refinery, tank, connection)
            priority = calculate_priority(refinery, tank, connection)
            movement = MovementDto(connection_id=connection.id, flow=flow, priority=priority)
            movements.append(movement)

    movements_queue = PriorityQueue()
    for movement in movements:
        movements_queue.put((-movement.priority, movement))
    content = DayRequestDto(day=day, movements=[movement[1] for movement in movements_queue.queue])
    body = {
        "day": content.day,
        "movements": [{"connectionId": movement.connection_id, "amount": movement.flow} for movement in
                      content.movements]
    }
    # body_json = json.dumps(body)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{BASE_URL}/api/v1/play/round",
                headers={
                    "API-KEY": API_KEY,
                    "SESSION-ID": sesh_id
                },
                json=body
            )
        response.raise_for_status()
        result = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)

    data = result

    for day in range(1, 42):
        movements = []
        for connection in connections:
            refinery = next((refinery for refinery in refineries if refinery.id == connection.from_id), None)
            tank = next((tank for tank in tanks if tank.id == connection.to_id), None)
            if refinery and tank:
                flow = calculate_flow(refinery, tank, connection)
                priority = calculate_priority(refinery, tank, connection)
                movement = MovementDto(connection_id=connection.id, flow=flow, priority=priority)
                movements.append(movement)
        movements_queue = PriorityQueue()
        for movement in movements:
            movements_queue.put((-movement.priority, movement))
        content = DayRequestDto(day=day, movements=[movement[1] for movement in movements_queue.queue])
        movements_list = []
        movements_list.extend(
            [{"connectionId": movement.connection_id, "amount": movement.flow} for movement in content.movements])

        demands = []
        for demand in data['demand']:
            cursor.execute("SELECT * FROM network_node WHERE id = ?", (demand['customerId'],))
            customer_data = cursor.fetchone()
            customer = CustomerDto(**dict(zip([column[0] for column in cursor.description], customer_data)))
            demand['customer'] = customer
            demands.append(DemandDto(**demand))

        demands.sort(key=lambda demand: (demand.endDay, demand.startDay))

        for demand in demands:
            customer_connections = [connection for connection in connections if connection.to_id == demand.customer.id]

            # Sort connections by capacity and lead time
            customer_connections.sort(key=lambda c: (min(c.max_capacity, demand.customer.max_input), c.lead_time_days),
                                      reverse=True)

            amount_needed = demand.amount

            for indexday in range(day + 1, demand.endDay + 1):
                if amount_needed <= 0:
                    break

                for connection in customer_connections:
                    if not connection_manager.is_connection_available(connection.id, indexday):
                        continue

                    arrival_day = indexday + connection.lead_time_days

                    if demand.startDay <= arrival_day <= demand.endDay + 2:
                        minimum_possible_needed_amount = min(connection.max_capacity, demand.customer.max_input)
                        send_amount = min(minimum_possible_needed_amount, amount_needed)

                        if send_amount > 0:
                            connection_manager.schedule_transport(connection.id, arrival_day + 1)
                            amount_needed -= send_amount

                            movement = Movement(
                                id=str(uuid.uuid4()),
                                amount=send_amount,
                                connection=connection
                            )
                            connection_manager.add_movement_to_movement_schedule(indexday, movement)

                            if amount_needed <= 0:
                                demands.remove(demand)
                                break

        schedule_opt = next(
            (schedule for schedule in connection_manager.movement_schedule_list if schedule.day == day + 1),
            None)
        next_movements = schedule_opt.movements if schedule_opt else []
        movements_list.extend(
            [{"connectionId": movement.connection.id, "amount": movement.amount} for movement in next_movements])
        body = {
            "day": content.day,
            "movements": movements_list
        }
        # body_json = json.dumps(body)
        # print(body_json)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://{BASE_URL}/api/v1/play/round",
                    headers={
                        "API-KEY": API_KEY,
                        "SESSION-ID": sesh_id
                    },
                    json=body
                )
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)

        data = result
