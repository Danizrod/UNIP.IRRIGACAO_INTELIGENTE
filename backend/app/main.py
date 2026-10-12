import os
import secrets

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.contracts import Telemetry
from app.store import MessageConflict, connect, save

app = FastAPI(title='TCC Irrigação — base de integração', version='0.1.0')
bearer = HTTPBearer()


def authorize(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not secrets.compare_digest(credentials.credentials, os.environ['API_TOKEN']):
        raise HTTPException(status_code=401, detail='Credencial inválida')


@app.get('/health')
def health():
    try:
        with connect() as conn:
            conn.execute('SELECT 1 FROM telemetry LIMIT 1')
        return {'status': 'ready', 'actuation_enabled': False}
    except psycopg.Error:
        raise HTTPException(status_code=503, detail='Banco indisponível')


@app.post('/telemetry', dependencies=[Depends(authorize)])
def ingest(item: Telemetry):
    try:
        inserted = save(item)
        return {'status': 'stored' if inserted else 'duplicate'}
    except MessageConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except psycopg.Error:
        raise HTTPException(status_code=503, detail='Persistência indisponível; reenviar')


@app.get('/telemetry', dependencies=[Depends(authorize)])
def latest(experiment_id: str = Query(min_length=1, max_length=48),
           source: str = Query(pattern='^(physical|simulation)$'),
           limit: int = Query(default=50, ge=1, le=500)):
    with connect() as conn:
        rows = conn.execute(
            '''SELECT payload, received_at FROM telemetry
               WHERE experiment_id=%s AND source=%s
               ORDER BY received_at DESC LIMIT %s''', (experiment_id, source, limit),
        ).fetchall()
    return rows
