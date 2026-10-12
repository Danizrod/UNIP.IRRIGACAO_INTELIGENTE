"""Avaliação automática opcional, exclusivamente para dispositivos simulados."""
import logging
import time
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from app.contracts import DecisionConfiguration
from app.control import configuration_key
from app.ml_api import PredictionRequest, predict
from app.store import connect, evaluate

log = logging.getLogger('control')


def tick_once():
    with connect() as conn:
        configurations = conn.execute('SELECT payload FROM control_configs').fetchall()
    count = 0
    for row in configurations:
        config = DecisionConfiguration.model_validate(row['payload'])
        if not config.enabled or config.source != 'simulation':
            continue
        with connect() as conn:
            reading = conn.execute('SELECT message_id FROM telemetry WHERE device_id=%s AND experiment_id=%s AND source=%s ORDER BY collected_at DESC LIMIT 1',
                                  (config.device_id,config.experiment_id,config.source)).fetchone()
            if not reading:
                continue
            request_id = uuid5(NAMESPACE_URL, configuration_key(config) + str(reading['message_id']))
            if conn.execute('SELECT 1 FROM decisions WHERE request_id=%s', (request_id,)).fetchone():
                continue
        if config.treatment == 'T3':
            try:
                predict(PredictionRequest(device_id=config.device_id,telemetry_message_id=reading['message_id']))
            except HTTPException as exc:
                log.warning('Previsão indisponível: %s', exc.detail)
        evaluate(config.device_id, request_id)
        count += 1
    return count


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            tick_once()
        except Exception:
            log.exception('Avaliação falhou; nenhum comando é presumido como executado')
        time.sleep(2)
