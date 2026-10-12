"""Verificação local do dashboard e da consulta PostgreSQL sem exibir credenciais."""
from pathlib import Path
import base64
import json
from urllib.request import Request, urlopen

root = Path(__file__).resolve().parents[1]
env = dict(line.split('=', 1) for line in (root / '.env').read_text().splitlines() if '=' in line)
token = base64.b64encode(('admin:' + env['GRAFANA_ADMIN_PASSWORD']).encode()).decode()


def request(path, payload=None):
    headers = {'Authorization': 'Basic ' + token}
    if payload is not None:
        headers['Content-Type'] = 'application/json'
    req = Request('http://127.0.0.1:3000' + path, headers=headers,
                  data=None if payload is None else json.dumps(payload).encode())
    with urlopen(req, timeout=15) as response:
        return json.load(response)


dashboard = request('/api/dashboards/uid/tcc-ingestion')
assert dashboard['dashboard']['uid'] == 'tcc-ingestion'
result = request('/api/ds/query', {'from': 'now-1h', 'to': 'now', 'queries': [{
    'refId': 'A', 'datasource': {'uid': 'irrigation-postgres', 'type': 'postgres'},
    'format': 'table', 'rawSql': "SELECT count(*) AS messages FROM telemetry WHERE source='simulation'",
    'intervalMs': 1000, 'maxDataPoints': 100}]})
assert not result['results']['A'].get('error'), 'Consulta Grafana falhou'
frames = result['results']['A']['frames']
assert frames and frames[0]['data']['values'][0][0] > 0
print('PASS: dashboard provisionado e consulta PostgreSQL pelo Grafana retornou fixtures simuladas.')
