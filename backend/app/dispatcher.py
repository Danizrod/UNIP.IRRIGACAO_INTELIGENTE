"""Transactional at-least-once command delivery. Device must deduplicate command_id."""
import logging
import os
import time
from app.store import connect, migrate
from app.worker import make_client

log = logging.getLogger('dispatcher')


def dispatch_once(client):
    with connect() as conn:
        row = conn.execute('''SELECT c.command_id,c.device_id,c.expires_at,c.payload,c.status
            FROM command_outbox o JOIN commands c USING(command_id)
            WHERE o.published_at IS NULL ORDER BY c.issued_at
            FOR UPDATE OF o SKIP LOCKED LIMIT 1''').fetchone()
        if not row:
            return False
        from datetime import datetime, timezone
        if row['expires_at'] <= datetime.now(timezone.utc) or row['status'] not in ('queued','published'):
            conn.execute('UPDATE command_outbox SET published_at=now() WHERE command_id=%s',(row['command_id'],))
            if row['status'] == 'queued':
                conn.execute("UPDATE commands SET status='expired' WHERE command_id=%s",(row['command_id'],))
            return True
        if row['payload']['source'] != 'simulation' or os.environ.get('SIMULATION_CONTROL_ENABLED') != 'true':
            return False
        import json
        result = client.publish(f"irrigation/v1/{row['device_id']}/commands",json.dumps(row['payload']),qos=1,retain=False)
        result.wait_for_publish(timeout=10)
        if not result.is_published():
            raise RuntimeError('Publicação MQTT não confirmada')
        conn.execute('UPDATE command_outbox SET published_at=now(),attempts=attempts+1 WHERE command_id=%s',(row['command_id'],))
        conn.execute("UPDATE commands SET status='published' WHERE command_id=%s AND status='queued'",(row['command_id'],))
        return True


if __name__ == '__main__':
    migrate()
    client = make_client(client_id='tcc-dispatcher-v1')
    client.on_message = None
    client.on_connect = None
    client.connect(os.environ.get('MQTT_HOST','mosquitto'),8883,keepalive=30)
    client.loop_start()
    while True:
        if not dispatch_once(client):
            time.sleep(0.5)
