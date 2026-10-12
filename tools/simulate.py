"""Fixture de transporte MQTT. Não simula dinâmica agronômica nem liga bombas."""
import os
from datetime import datetime, timezone
from uuid import uuid4

import paho.mqtt.client as mqtt

from app.contracts import Telemetry


def sample():
    return Telemetry(schema_version=1, message_id=uuid4(), device_id='sim-01',
        experiment_id='sim-integration', unit_id='sim-pot-01', treatment='T1',
        source='simulation', collected_at=datetime.now(timezone.utc),
        calibration_id='sim-fixture-v1', soil_raw=2000, soil_index=50,
        sensor_valid=True, temperature_c=24, humidity_pct=60, reservoir_mass_g=1500,
        pump_voltage_v=0, pump_current_a=0)


def publish_fixture(item):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='tcc-simulator')
    client.username_pw_set('sim-01', os.environ['MQTT_SIM_PASSWORD'])
    client.tls_set(ca_certs='/certs/ca.crt')
    client.connect(os.environ.get('MQTT_HOST', 'mosquitto'), 8883)
    client.loop_start()
    # Mesmo identificador e conteúdo: testar idempotência de forma explícita.
    for _ in range(2):
        result = client.publish('irrigation/v1/sim-01/telemetry', item.model_dump_json(), qos=1)
        result.wait_for_publish(timeout=10)
        if not result.is_published():
            raise RuntimeError('Publicação não confirmada pelo broker')
    client.disconnect()
    client.loop_stop()
    return item


if __name__ == '__main__':
    item = publish_fixture(sample())
    print(f'Fixture simulada enviada duas vezes: {item.message_id}. ACK MQTT não comprova persistência.')
