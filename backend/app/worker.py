import logging
import os

import paho.mqtt.client as mqtt
import psycopg
from pydantic import ValidationError

from app.contracts import Telemetry
from app.store import MessageConflict, save

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('ingestion')


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        raise RuntimeError('MQTT rejeitou conexão')
    client.subscribe('irrigation/v1/+/telemetry', qos=1)
    log.info('MQTT conectado; assinatura solicitada')


def on_message(client, userdata, message):
    try:
        if len(message.payload) > 8192:
            raise ValueError('payload excede limite')
        item = Telemetry.model_validate_json(message.payload)
        if message.topic != f'irrigation/v1/{item.device_id}/telemetry':
            raise ValueError('dispositivo diverge do tópico')
        inserted = save(item)
        log.info('telemetria %s: %s', item.message_id, 'stored' if inserted else 'duplicate')
    except (ValidationError, ValueError, MessageConflict):
        log.warning('telemetria rejeitada no tópico %s', message.topic)
    except psycopg.Error:
        # Encerrar sem ACK; a sessão persistente permite reentrega na reconexão.
        log.error('Banco indisponível; encerrando sem confirmar mensagem')
        os._exit(1)
    client.ack(message.mid, message.qos)


def make_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='tcc-ingestion-v1',
                         clean_session=False, manual_ack=True)
    client.username_pw_set('backend', os.environ['MQTT_BACKEND_PASSWORD'])
    client.tls_set(ca_certs='/certs/ca.crt')
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(1, 30)
    return client


if __name__ == '__main__':
    client = make_client()
    client.connect(os.environ.get('MQTT_HOST', 'mosquitto'), 8883, keepalive=30)
    client.loop_forever()
