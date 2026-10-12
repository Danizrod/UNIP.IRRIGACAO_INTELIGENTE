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

# Safe to run on an existing volume; PostgreSQL serializes concurrent migration calls.
def migrate():
    if os.environ.get('AUTO_MIGRATE', 'true') != 'true':
        return
    from pathlib import Path
    path = Path(os.environ.get('CONTROL_MIGRATION_PATH', '/app/migrations/003-control.sql'))
    if not path.exists():
        path = Path(__file__).resolve().parents[2] / 'infra/postgres/003-control.sql'
    with connect() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(41926012)')
        conn.execute(path.read_text(encoding='utf-8'))


def save_command(item):
    from datetime import datetime, timezone
    if item.source != 'simulation' or os.environ.get('SIMULATION_CONTROL_ENABLED') != 'true':
        raise ValueError('Atuação física bloqueada; habilite explicitamente simulação')
    payload = item.model_dump(mode='json')
    with connect() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (item.device_id,))
        existing = conn.execute('SELECT payload FROM commands WHERE command_id=%s FOR UPDATE', (item.command_id,)).fetchone()
        if existing:
            if existing['payload'] != payload:
                raise MessageConflict('command_id reutilizado com outro conteúdo')
            return False
        now = datetime.now(timezone.utc)
        if not item.issued_at <= now < item.expires_at:
            raise ValueError('Comando futuro ou vencido')
        # A per-device transactional lock prevents overlapping commands across API/worker.
        conn.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (item.device_id,))
        active = conn.execute("SELECT 1 FROM commands WHERE device_id=%s AND status IN ('queued','published','accepted','started') AND (expires_at>now() OR status='started')", (item.device_id,)).fetchone()
        if active:
            raise ValueError('Há um comando ativo para o dispositivo')
        from app.contracts import DecisionConfiguration
        from app.control import decide, configuration_key, hysteresis_state
        cfgrow = conn.execute('SELECT payload FROM control_configs WHERE device_id=%s', (item.device_id,)).fetchone()
        if not cfgrow:
            raise ValueError('Configuração ausente')
        cfg = DecisionConfiguration.model_validate(cfgrow['payload'])
        if (item.experiment_id,item.unit_id,item.treatment,item.source) != (cfg.experiment_id,cfg.unit_id,cfg.treatment,cfg.source):
            raise ValueError('Contexto diverge da configuração')
        if item.max_duration_s > cfg.max_duration_s or item.target_volume_ml > cfg.target_volume_ml:
            raise ValueError('Comando excede limites configurados')
        tr = conn.execute('SELECT payload FROM telemetry WHERE device_id=%s AND experiment_id=%s AND source=%s ORDER BY collected_at DESC LIMIT 1', (item.device_id,item.experiment_id,item.source)).fetchone()
        telemetry = Telemetry.model_validate(tr['payload']) if tr else None
        # Manual simulation commands still obey sensor/reservoir/calibration/cooldown guards.
        last = conn.execute("SELECT issued_at FROM commands WHERE device_id=%s AND status!='rejected' ORDER BY issued_at DESC LIMIT 1", (item.device_id,)).fetchone()
        allowed, reason = decide(cfg,telemetry,now,last['issued_at'] if last else None,simulation_enabled=True)
        if reason in ('control_disabled','missing_telemetry','telemetry_context_mismatch','stale_telemetry','invalid_or_uncalibrated_sensor','insufficient_or_unknown_reservoir','cooldown','soil_at_or_above_high'):
            raise ValueError(reason)
        conn.execute('INSERT INTO commands(command_id,device_id,source,issued_at,expires_at,payload) VALUES(%s,%s,%s,%s,%s,%s)', (item.command_id,item.device_id,item.source,item.issued_at,item.expires_at,Jsonb(payload)))
        conn.execute('INSERT INTO command_outbox(command_id) VALUES(%s)', (item.command_id,))
        return True


TRANSITIONS = {'queued': {'accepted','rejected'}, 'published': {'accepted','rejected'}, 'accepted': {'started','failed'}, 'started': {'completed','failed'}, 'completed': set(), 'rejected': set(), 'failed': set(), 'expired': set()}


def save_event(item):
    if item.origin == 'local':
        return save_local_event(item)
    payload = item.model_dump(mode='json')
    with connect() as conn:
        command = conn.execute('SELECT * FROM commands WHERE command_id=%s FOR UPDATE', (item.command_id,)).fetchone()
        if not command:
            raise ValueError('Comando desconhecido')
        previous = conn.execute('SELECT payload FROM command_events WHERE event_id=%s', (item.event_id,)).fetchone()
        if previous:
            from app.contracts import CommandEvent
            if CommandEvent.model_validate(previous['payload']).model_dump(mode='json') != payload:
                raise MessageConflict('event_id reutilizado')
            return False
        if item.device_id != command['device_id'] or item.source != command['source']:
            raise ValueError('Evento diverge do comando')
        latest = conn.execute('SELECT occurred_at FROM command_events WHERE command_id=%s ORDER BY occurred_at DESC LIMIT 1', (item.command_id,)).fetchone()
        if item.occurred_at < command['issued_at'] or (latest and item.occurred_at < latest['occurred_at']):
            raise ValueError('Evento fora de ordem temporal')
        if item.status not in TRANSITIONS[command['status']]:
            raise ValueError('Transição inválida')
        if item.status in ('accepted','started') and item.occurred_at >= command['expires_at']:
            raise ValueError('Comando vencido')
        if item.duration_s is not None and item.duration_s > command['payload']['max_duration_s'] + 1:
            raise ValueError('Duração excede limite do comando')
        conn.execute('INSERT INTO command_events(event_id,command_id,occurred_at,status,payload) VALUES(%s,%s,%s,%s,%s)', (item.event_id,item.command_id,item.occurred_at,item.status,Jsonb(payload)))
        conn.execute('UPDATE commands SET status=%s WHERE command_id=%s', (item.status,item.command_id))
        return True


def save_local_event(item):
    """Ledger auditado de ciclos autônomos; não cria outbox/comando remoto."""
    if item.source != 'simulation':
        raise ValueError('Ciclos físicos ainda não habilitados')
    payload = item.model_dump(mode='json')
    with connect() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (str(item.command_id),))
        old = conn.execute('SELECT payload FROM local_cycle_events WHERE event_id=%s', (item.event_id,)).fetchone()
        if old:
            if old['payload'] != payload:
                raise MessageConflict('event_id local reutilizado')
            return False
        if conn.execute('SELECT 1 FROM commands WHERE command_id=%s', (item.command_id,)).fetchone():
            raise ValueError('Ciclo local não pode reutilizar comando remoto')
        previous = conn.execute('SELECT status,occurred_at,payload FROM local_cycle_events WHERE command_id=%s ORDER BY received_at DESC LIMIT 1', (item.command_id,)).fetchone()
        if previous:
            original = previous['payload']
            if any(payload[k] != original[k] for k in ('device_id','experiment_id','unit_id','source')):
                raise ValueError('Contexto local divergente')
            if item.occurred_at < previous['occurred_at'] or item.status not in TRANSITIONS[previous['status']]:
                raise ValueError('Evento local fora de ordem/transição')
        elif item.status not in ('accepted','rejected'):
            raise ValueError('Ciclo local sem evento inicial')
        conn.execute('INSERT INTO local_cycle_events(event_id,command_id,device_id,occurred_at,status,payload) VALUES(%s,%s,%s,%s,%s,%s)',
                     (item.event_id,item.command_id,item.device_id,item.occurred_at,item.status,Jsonb(payload)))
        return True


def save_rejection(topic, payload, reason):
    with connect() as conn:
        conn.execute('INSERT INTO rejected_messages(topic,reason,payload) VALUES(%s,%s,%s)',
                     (topic[:256], reason[:300], payload[:8192]))


def evaluate(device_id, request_id):
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4
    from app.contracts import DecisionConfiguration, IrrigationCommand, Prediction
    from app.control import decide, configuration_key, hysteresis_state
    with connect() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (device_id,))
        old = conn.execute('SELECT payload FROM decisions WHERE request_id=%s', (request_id,)).fetchone()
        if old:
            if old['payload']['device_id'] != device_id:
                raise MessageConflict('request_id reutilizado para outro dispositivo')
            return old['payload']
        row = conn.execute('SELECT payload FROM control_configs WHERE device_id=%s', (device_id,)).fetchone()
        if not row:
            raise ValueError('Configuração ausente')
        config = DecisionConfiguration.model_validate(row['payload'])
        row = conn.execute('SELECT payload FROM telemetry WHERE device_id=%s AND experiment_id=%s AND source=%s ORDER BY collected_at DESC LIMIT 1', (device_id,config.experiment_id,config.source)).fetchone()
        telemetry = Telemetry.model_validate(row['payload']) if row else None
        row = conn.execute('SELECT payload FROM predictions WHERE device_id=%s ORDER BY predicted_at DESC LIMIT 1', (device_id,)).fetchone()
        prediction = Prediction.model_validate(row['payload']) if row else None
        previous = conn.execute("SELECT issued_at FROM commands WHERE device_id=%s AND status!='rejected' ORDER BY issued_at DESC LIMIT 1", (device_id,)).fetchone()
        active = conn.execute("SELECT 1 FROM commands WHERE device_id=%s AND status IN ('queued','published','accepted','started') AND (expires_at>now() OR status='started')", (device_id,)).fetchone()
        now = datetime.now(timezone.utc)
        config_key = configuration_key(config)
        last_decision = conn.execute('SELECT payload FROM decisions WHERE device_id=%s ORDER BY created_at DESC LIMIT 1', (device_id,)).fetchone()
        prior_latch = bool(last_decision and last_decision['payload'].get('configuration_key') == config_key and last_decision['payload'].get('hysteresis_latched', False))
        # Stale data cannot change state; valid high readings release the latch even during cooldown.
        fresh = telemetry is not None and 0 <= (now-telemetry.collected_at).total_seconds() <= config.max_telemetry_age_s
        latch = hysteresis_state(config,telemetry,prior_latch) if fresh else prior_latch
        act, reason = decide(config,telemetry,now,previous['issued_at'] if previous else None,prediction,bool(active),os.environ.get('SIMULATION_CONTROL_ENABLED') == 'true', latch)
        result = {'request_id': str(request_id), 'device_id':device_id, 'reason':reason, 'actuate':act, 'telemetry_message_id':str(telemetry.message_id) if telemetry else None, 'prediction_id':str(prediction.prediction_id) if prediction else None, 'command_id':None, 'configuration_key':config_key, 'hysteresis_latched':latch}
        if act:
            command = IrrigationCommand(command_id=uuid4(),decision_id=request_id,device_id=device_id,experiment_id=config.experiment_id,unit_id=config.unit_id,treatment=config.treatment,source=config.source,issued_at=now,expires_at=now+timedelta(seconds=60),target_volume_ml=config.target_volume_ml,max_duration_s=config.max_duration_s,reason=reason,model_version=prediction.model_version if prediction and config.treatment=='T3' and reason=='prediction_below_low' else None)
            conn.execute('INSERT INTO commands(command_id,device_id,source,issued_at,expires_at,payload) VALUES(%s,%s,%s,%s,%s,%s)', (command.command_id,device_id,command.source,now,command.expires_at,Jsonb(command.model_dump(mode='json'))))
            conn.execute('INSERT INTO command_outbox(command_id) VALUES(%s)', (command.command_id,))
            result['command_id'] = str(command.command_id)
        conn.execute('INSERT INTO decisions(request_id,device_id,payload) VALUES(%s,%s,%s)', (request_id,device_id,Jsonb(result)))
        return result
