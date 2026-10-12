import os

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.contracts import Telemetry


class MessageConflict(ValueError):
    pass


def connect():
    return psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row)


def save(item: Telemetry) -> bool:
    payload = item.model_dump(mode='json')
    with connect() as conn:
        row = conn.execute(
            '''INSERT INTO telemetry (device_id, message_id, collected_at, experiment_id,
               unit_id, treatment, source, sensor_valid, soil_index, payload)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (device_id, message_id) DO NOTHING RETURNING message_id''',
            (item.device_id, item.message_id, item.collected_at, item.experiment_id,
             item.unit_id, item.treatment, item.source, item.sensor_valid, item.soil_index,
             Jsonb(payload)),
        ).fetchone()
        if row:
            return True
        existing = conn.execute(
            'SELECT payload FROM telemetry WHERE device_id=%s AND message_id=%s',
            (item.device_id, item.message_id),
        ).fetchone()
        if existing['payload'] != payload:
            raise MessageConflict('Identificador reutilizado com outro conteúdo')
        return False
