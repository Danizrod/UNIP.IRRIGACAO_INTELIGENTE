"""Estatística descritiva do ensaio contínuo; metades e período pós-modelo não são réplicas."""
import json
import math
from datetime import datetime, timezone
from pathlib import Path


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Horário sem fuso')
    return result


def windows(plan):
    # Janela real registrada no protocolo (decisões de 04/11, 22/11 e 26/11: menos de 30 dias).
    start, end = timestamp(plan['starts_at']), timestamp(plan['ends_at'])
    if end <= start or plan['analysis_periods_are_replicates'] or plan['independent_units_per_treatment'] != 1:
        raise ValueError('Protocolo exige janela contínua, n=1 e períodos sem replicação')
    units = plan['units']
    if len(units) != 3 or len({u['unit_id'] for u in units}) != 3 or {u['treatment'] for u in units} != {'T1','T2','T3'}:
        raise ValueError('Exige três unidades/tratamentos distintos')
    middle = start + (end - start) / 2
    result = {'total':(start,end), 'primeira_metade':(start,middle), 'segunda_metade':(middle,end)}
    if plan.get('t3_model_frozen_at'):
        frozen = timestamp(plan['t3_model_frozen_at'])
        if not start <= frozen < end:
            raise ValueError('Congelamento do modelo fora da janela')
        result['pos_modelo_t3'] = (frozen, end)
    return result


def dosed_ml(unit, terminal):
    """Água pela dose calibrada (vazão em copo), pois a pesagem por diferença não foi aprovada.

    Retorna (mínimo, máximo): ciclo completo com duração conhecida é exato pela calibração; ciclo
    que falhou sem duração (reinício, leitura inválida) pode ter aplicado de 0 até a dose inteira."""
    dose, seconds = unit['dose_ml'], unit['dose_s']
    duration = terminal.get('duration_s')
    if terminal['status'] == 'completed' and isinstance(duration,(int,float)) and math.isfinite(duration) and duration >= 0:
        value = dose * min(duration, seconds) / seconds
        return value, value
    return 0.0, float(dose)


def saving(baseline, other):
    """Faixa de economia 100×(1−Tx/T1) com os extremos de água incerta; None se T1 pode ser zero."""
    if not baseline['dosed_water_ml_min'] or baseline['dosed_water_ml_min'] <= 0:
        return None
    low = 100 * (1 - other['dosed_water_ml_max'] / baseline['dosed_water_ml_min'])
    high = 100 * (1 - other['dosed_water_ml_min'] / baseline['dosed_water_ml_max'])
    return [low, high]


def describe(plan, events, readings, as_of=None):
    as_of = as_of or datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        raise ValueError('as_of sem fuso')
    intervals = windows(plan)
    units = {u['unit_id']:u for u in plan['units']}
    result = {'design':plan['design'], 'source':plan['source'], 'starts_at':plan['starts_at'], 'ends_at':plan['ends_at'],
              'independent_units_per_treatment':1, 'analysis_periods_are_replicates':False, 'inferential_claims':False,
              'water_basis':'dose calibrada; pesagem por diferença apenas complementar', 'as_of':as_of.isoformat(), 'periods':{}}
    def compatible(row):
        unit = units.get(row.get('unit_id'))
        return row.get('source') == plan['source'] and row.get('experiment_id') == plan['experiment_id'] and unit is not None and row.get('treatment') == unit['treatment']
    unique_events = {}
    for event in events:
        if not compatible(event):
            continue
        if event['event_id'] in unique_events and unique_events[event['event_id']] != event:
            raise ValueError('event_id conflitante')
        unique_events[event['event_id']] = event
    cycles = {}
    for event in unique_events.values():
        cycles.setdefault(event['command_id'], []).append(event)
    unit_readings = {}
    for r in readings:
        if compatible(r):
            unit_readings.setdefault(r['unit_id'], {})[r['message_id']] = r
    for period, (start,end) in intervals.items():
        reports = {}
        stop = min(as_of, end)
        elapsed = max(0, (stop-start).total_seconds())
        expected = math.ceil(elapsed / plan['sampling_interval_s'])
        for unit_id, unit in units.items():
            observed = [r for r in unit_readings.get(unit_id, {}).values() if start <= timestamp(r['collected_at']) < stop]
            valid = [r for r in observed if r.get('sensor_valid') is True and r.get('soil_index') is not None]
            covered_slots = {int((timestamp(r['collected_at'])-start).total_seconds()//plan['sampling_interval_s']) for r in valid}
            in_range = sum(plan['soil_low'] <= r['soil_index'] <= plan['soil_high'] for r in valid)
            completed = failed = unresolved = measured = 0
            water_min = water_max = scale_ml = 0.0
            energy = []
            for cycle in cycles.values():
                if cycle[0]['unit_id'] != unit_id:
                    continue
                terminals = [e for e in cycle if e['status'] in ('completed','failed')]
                if len(terminals) > 1:
                    raise ValueError('Mais de um resultado terminal no ciclo')
                terminal = terminals[0] if terminals else None
                # Ciclos pertencem ao período do resultado, sem contar duas vezes.
                anchor = timestamp(terminal['occurred_at'] if terminal else min(e['occurred_at'] for e in cycle))
                if not start <= anchor < stop:
                    continue
                if not terminal:
                    if any(e['status'] in ('accepted','started','unconfirmed') for e in cycle):
                        unresolved += 1
                        water_max += unit['dose_ml']
                    continue
                if not any(e['status'] == 'started' for e in cycle):
                    continue  # falhou antes de ligar a bomba: sem água
                completed += terminal['status'] == 'completed'
                failed += terminal['status'] == 'failed'
                low, high = dosed_ml(unit, terminal)
                water_min += low
                water_max += high
                volume = terminal.get('volume_ml')
                if terminal.get('measurements_valid') is True and isinstance(volume,(int,float)) and math.isfinite(volume) and volume >= 0:
                    measured += 1
                    scale_ml += volume
                    if isinstance(terminal.get('energy_wh'),(int,float)) and math.isfinite(terminal['energy_wh']) and terminal['energy_wh'] >= 0:
                        energy.append(terminal['energy_wh'])
            reports[unit['treatment']] = dict(unit_id=unit_id, cycles_completed=completed, cycles_failed_after_start=failed,
                cycles_unresolved=unresolved, dosed_water_ml_min=water_min, dosed_water_ml_max=water_max,
                scale_measured_cycles=measured, scale_water_ml=scale_ml if measured else None,
                pump_energy_wh=sum(energy) if energy else None, cycles_with_energy=len(energy),
                valid_readings=len(valid), unique_readings=len(observed), expected_readings_until_snapshot=expected,
                valid_reading_coverage=len(covered_slots)/expected if expected else None,
                in_range_pct_of_valid=100*in_range/len(valid) if valid else None,
                window_finished=as_of>=end, water_saving_pct_range=None)
        baseline = reports['T1']
        for treatment in ('T2','T3'):
            if as_of >= end:
                reports[treatment]['water_saving_pct_range'] = saving(baseline, reports[treatment])
        result['periods'][period]=reports
    return result


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',default='/app/config/experiment.json')
    parser.add_argument('--output',required=True)
    parser.add_argument('--as-of',help='Instantâneo ISO com fuso (padrão: agora)')
    args=parser.parse_args()
    from app.store import connect
    plan=json.loads(Path(args.plan).read_text(encoding='utf-8'))
    with connect() as conn:
        events=conn.execute("SELECT e.payload || jsonb_build_object('source',c.source,'experiment_id',c.payload->>'experiment_id','unit_id',c.payload->>'unit_id','treatment',c.payload->>'treatment') AS payload FROM command_events e JOIN commands c USING(command_id) WHERE c.source=%s AND c.payload->>'experiment_id'=%s UNION ALL SELECT payload FROM local_cycle_events WHERE payload->>'source'=%s AND payload->>'experiment_id'=%s",(plan['source'],plan['experiment_id'],plan['source'],plan['experiment_id'])).fetchall()
        readings=conn.execute('SELECT payload FROM telemetry WHERE source=%s AND experiment_id=%s',(plan['source'],plan['experiment_id'])).fetchall()
        # Estado derivado do ledger: identifica comandos sem resultado, sem inventar atuação.
        # 'expired' nunca foi publicado (fila), portanto não é ciclo pendente.
        unresolved=conn.execute("SELECT payload,command_id FROM commands WHERE source=%s AND payload->>'experiment_id'=%s AND status NOT IN ('completed','failed','rejected','expired')",(plan['source'],plan['experiment_id'])).fetchall()
    for row in unresolved:
        item=row['payload']
        events.append({'payload':dict(item,event_id='ledger-'+str(row['command_id']),command_id=str(row['command_id']),status='unconfirmed',occurred_at=item['issued_at'])})
    as_of=timestamp(args.as_of) if args.as_of else None
    report=describe(plan,[e['payload'] for e in events],[r['payload'] for r in readings],as_of)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as out:
        json.dump(report,out,ensure_ascii=False,indent=2,allow_nan=False)
    print('Relatório descritivo criado. Períodos não são réplicas; ausência não é consumo zero.')
