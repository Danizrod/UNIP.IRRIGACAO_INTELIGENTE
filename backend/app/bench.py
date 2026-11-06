"""Painel local da bancada: leituras ao vivo e testes guiados de pesagem.

Somente leitura do banco. Sessões de teste (etapas com horário do servidor) ficam em arquivos JSON
fora do Git; os resultados são calculados das contagens HX711 da telemetria, nunca gravados na placa.
"""
import json
import os
import statistics
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.store import connect

DEVICE = os.environ.get('BENCH_DEVICE', 'esp32-01')
SESSIONS = Path(os.environ.get('BENCH_SESSIONS', '/sessions'))
PAGE = Path(__file__).with_name('bench_static') / 'index.html'
# Readings right after a load change are discarded: settling plus telemetry delivery delay.
SETTLE_S = 15
KINDS = ('calibration', 'withdrawal', 'press')

app = FastAPI(title='TCC — painel de bancada', version='0.1.0')


def now():
    return datetime.now(timezone.utc)


def iso(value):
    return value.astimezone(timezone.utc).isoformat()


# ---------- análise (funções puras) ----------

def step_counts(step, samples, settle_s=SETTLE_S):
    """Contagens HX711 dentro da etapa, descartando o início (acomodação)."""
    start = datetime.fromisoformat(step['started_at']) + timedelta(seconds=settle_s)
    end = datetime.fromisoformat(step['ended_at'])
    return [s['counts'] for s in samples if start <= s['at'] <= end and s['counts'] is not None]


def summarize(steps, samples, settle_s=SETTLE_S):
    out = []
    for step in steps:
        if not step.get('ended_at'):
            continue
        counts = step_counts(step, samples, settle_s)
        out.append(dict(index=step['index'], load=step['load'], label=step['label'], n=len(counts),
                        median=statistics.median(counts) if counts else None,
                        spread=(max(counts) - min(counts)) if counts else None))
    return out


def calibration(summary, mass_g):
    """Fator por etapa carregada contra a média das etapas vazias vizinhas (cancela deriva linear)."""
    factors = []
    for i, step in enumerate(summary):
        if step['load'] != 'loaded' or step['median'] is None:
            continue
        before = next((s for s in reversed(summary[:i]) if s['load'] == 'empty' and s['median'] is not None), None)
        after = next((s for s in summary[i + 1:] if s['load'] == 'empty' and s['median'] is not None), None)
        if not before or not after:
            continue
        base = (before['median'] + after['median']) / 2
        factors.append(dict(step=step['index'], delta_counts=step['median'] - base,
                            factor=(step['median'] - base) / mass_g, empty_drift_counts=after['median'] - before['median']))
    empties = [s for s in summary if s['load'] == 'empty' and s['median'] is not None]
    if not factors or not empties:
        return dict(ok=False, reason='Etapas válidas insuficientes (é preciso vazio antes e depois de cada carga).', factors=factors)
    values = [f['factor'] for f in factors]
    factor = statistics.mean(values)
    # Repeatability in grams of the reference mass across the loaded repetitions.
    spread_g = (max(values) - min(values)) * mass_g / abs(factor) if len(values) > 1 and factor else 0.0
    # The current platform reads ~20 counts/g; a factor far from that means the load was not applied.
    plausible = 2 <= abs(factor) <= 200
    return dict(ok=plausible, factor=factor, offset=empties[-1]['median'], repeats=len(values),
                repeatability_g=spread_g, factors=factors, mass_g=mass_g,
                reason=None if plausible else 'Fator implausível: confira se o peso foi colocado e retirado nas etapas indicadas.')


def withdrawal(summary, mass_g, factor):
    """Cada par com peso → sem peso é uma retirada; erro contra a massa de referência."""
    reps = []
    for i, step in enumerate(summary):
        if step['load'] != 'loaded' or step['median'] is None:
            continue
        nxt = next((s for s in summary[i + 1:] if s['load'] == 'empty'), None)
        if not nxt or nxt['median'] is None:
            continue
        removed = (step['median'] - nxt['median']) / factor
        reps.append(dict(step=step['index'], removed_g=removed, error_g=removed - mass_g))
    passed = sum(1 for r in reps if abs(r['error_g']) <= 2)
    return dict(ok=bool(reps), reps=reps, within_2g=passed, total=len(reps),
                approved=len(reps) >= 10 and passed >= 9, mass_g=mass_g, factor=factor)


def press(summary, factor):
    """Volta ao mesmo valor após apertar? Diferença de cada etapa solta contra a primeira base."""
    bases = [s for s in summary if s['load'] == 'empty' and s['median'] is not None]
    if len(bases) < 2:
        return dict(ok=False, returns=[])
    first = bases[0]['median']
    returns = [dict(step=s['index'], diff_g=(s['median'] - first) / factor) for s in bases[1:]]
    return dict(ok=True, returns=returns, max_abs_g=max(abs(r['diff_g']) for r in returns))


# ---------- dados ----------

def scale_samples(since):
    with connect() as conn:
        rows = conn.execute(
            """SELECT DISTINCT ON (collected_at) collected_at, (payload->>'scale_counts')::bigint AS counts,
                      (payload->>'reservoir_mass_g')::float AS mass, (payload->>'temperature_c')::float AS temp
               FROM telemetry WHERE device_id=%s AND source='physical' AND collected_at>=%s
               ORDER BY collected_at, unit_id""", (DEVICE, since)).fetchall()
    return [dict(at=r['collected_at'], counts=r['counts'], mass=r['mass'], temp=r['temp']) for r in rows]


def provisional_factor():
    """Fator gravado na placa, deduzido de duas leituras: massa = (contagens - zero) / fator."""
    with connect() as conn:
        rows = conn.execute(
            """SELECT DISTINCT (payload->>'scale_counts')::float AS c, (payload->>'reservoir_mass_g')::float AS m
               FROM telemetry WHERE device_id=%s AND source='physical' AND payload->>'scale_counts' IS NOT NULL
               AND payload->>'reservoir_mass_g' IS NOT NULL AND collected_at > now() - interval '1 hour'
               LIMIT 50""", (DEVICE,)).fetchall()
    for a in rows:
        for b in rows:
            if abs(a['c'] - b['c']) >= 50 and a['m'] != b['m']:
                return (a['c'] - b['c']) / (a['m'] - b['m'])
    return None


@app.get('/')
def page():
    # no-store: an updated page must replace an open, cached copy on the next reload.
    return FileResponse(PAGE, headers={'Cache-Control': 'no-store'})


@app.get('/api/live')
def live(minutes: int = 15):
    minutes = max(1, min(minutes, 120))
    with connect() as conn:
        latest = conn.execute(
            """SELECT DISTINCT ON (unit_id) unit_id, treatment, collected_at, received_at, payload
               FROM telemetry WHERE device_id=%s AND source='physical' ORDER BY unit_id, collected_at DESC""", (DEVICE,)).fetchall()
    series = scale_samples(now() - timedelta(minutes=minutes))
    return dict(server_time=iso(now()), device=DEVICE,
                units=[dict(unit_id=r['unit_id'], treatment=r['treatment'], collected_at=iso(r['collected_at']),
                            age_s=(now() - r['received_at']).total_seconds(), payload=r['payload']) for r in latest],
                series=[dict(at=iso(s['at']), mass=s['mass'], counts=s['counts'], temp=s['temp']) for s in series],
                factor=provisional_factor(), calibration=latest_calibration())


class SessionStart(BaseModel):
    kind: str = Field(pattern='^(calibration|withdrawal|press)$')
    mass_g: float | None = Field(default=None, gt=0, le=5000)
    factor: float | None = None
    note: str | None = Field(default=None, max_length=300)


class StepMark(BaseModel):
    index: int = Field(ge=0, le=200)
    load: str = Field(pattern='^(empty|loaded|press)$')
    label: str = Field(max_length=120)
    planned_s: int = Field(gt=0, le=1800)


def path_for(session_id):
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(404, 'Sessão inexistente')
    path = SESSIONS / f'{session_id}.json'
    if not path.exists():
        raise HTTPException(404, 'Sessão inexistente')
    return path


def load(session_id):
    return json.loads(path_for(session_id).read_text(encoding='utf-8'))


def store(session):
    SESSIONS.mkdir(parents=True, exist_ok=True)
    (SESSIONS / f"{session['id']}.json").write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding='utf-8')


def close_open_step(session, at):
    if session['steps'] and not session['steps'][-1].get('ended_at'):
        session['steps'][-1]['ended_at'] = iso(at)


def all_sessions():
    return [json.loads(p.read_text(encoding='utf-8')) for p in SESSIONS.glob('*.json')] if SESSIONS.exists() else []


def latest_calibration():
    done = [s for s in all_sessions() if s.get('calibration')]
    return max(done, key=lambda s: s['started_at'])['calibration'] if done else None


@app.post('/api/sessions')
def start(body: SessionStart):
    # A page reload leaves the previous session running; it can no longer be finished.
    for old in all_sessions():
        if old['status'] == 'running':
            old['status'] = 'abandoned'
            store(old)
    session = dict(id=str(uuid.uuid4()), kind=body.kind, mass_g=body.mass_g, factor=body.factor, note=body.note,
                   device=DEVICE, started_at=iso(now()), status='running', steps=[],
                   trial_eligible=False, purpose='diagnóstico/calibração da bancada; não é dado do ensaio')
    store(session)
    return session


@app.post('/api/sessions/{session_id}/steps')
def mark(session_id: str, body: StepMark):
    session = load(session_id)
    if session['status'] != 'running':
        raise HTTPException(409, 'Sessão encerrada')
    at = now()
    close_open_step(session, at)
    session['steps'].append(dict(index=body.index, load=body.load, label=body.label, planned_s=body.planned_s, started_at=iso(at)))
    store(session)
    return dict(ok=True, started_at=iso(at))


@app.post('/api/sessions/{session_id}/finish')
def finish(session_id: str, cancelled: bool = False):
    session = load(session_id)
    if session['status'] == 'running':
        close_open_step(session, now())
        session['status'] = 'cancelled' if cancelled else 'completed'
        session['finished_at'] = iso(now())
        store(session)
    return session


@app.get('/api/sessions')
def sessions():
    items = all_sessions()
    items.sort(key=lambda s: s['started_at'], reverse=True)
    return [dict(id=s['id'], kind=s['kind'], status=s['status'], started_at=s['started_at'], mass_g=s.get('mass_g')) for s in items[:30]]


@app.get('/api/sessions/{session_id}/result')
def result(session_id: str):
    session = load(session_id)
    if not session['steps']:
        raise HTTPException(409, 'Sessão sem etapas')
    samples = scale_samples(datetime.fromisoformat(session['started_at']) - timedelta(seconds=30))
    summary = summarize(session['steps'], samples)
    factor = session.get('factor') or provisional_factor()
    if session['kind'] == 'calibration':
        analysis = calibration(summary, session['mass_g'])
        if analysis['ok'] and session['status'] == 'completed' and not session.get('calibration'):
            session['calibration'] = dict(factor=analysis['factor'], offset=analysis['offset'],
                                          repeatability_g=analysis['repeatability_g'], computed_at=iso(now()))
            store(session)
    elif not factor:
        raise HTTPException(409, 'Fator indisponível')
    elif session['kind'] == 'withdrawal':
        analysis = withdrawal(summary, session['mass_g'], factor)
    else:
        analysis = press(summary, factor)
    temps = [s['temp'] for s in samples if s['temp'] is not None and s['at'] >= datetime.fromisoformat(session['started_at'])]
    return dict(session=session, steps=summary, analysis=analysis,
                temperature=dict(min=min(temps), max=max(temps)) if temps else None)
