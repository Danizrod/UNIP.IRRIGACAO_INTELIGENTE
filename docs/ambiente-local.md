# Ambiente local

Software verificado em simulação em 12/10/2026. Atuação física bloqueada até montagem e calibração.

## Preparar e executar

Docker Desktop ativo e Python com `cryptography` para configuração inicial:

```powershell
python tools/bootstrap-local.py
docker compose up -d --build
docker compose ps
```

Credenciais em `.env`, certificados em `.local/certs`, dados/modelos locais fora do Git. Configuração inicial preserva arquivos existentes; instalações antigas precisam incluir `APP_DATABASE_PASSWORD` no `.env`. Migrações executam antes da API. Aplicação usa papel restrito; Grafana somente leitura. Dependências e imagens estão fixadas.

| Serviço | Acesso |
| --- | --- |
| API | http://127.0.0.1:8000/docs — Bearer API_TOKEN |
| Grafana | http://127.0.0.1:3000/d/tcc-ingestion — admin/GRAFANA_ADMIN_PASSWORD |
| MQTT | localhost:8883 — TLS, autenticação e ACL por dispositivo |
| PostgreSQL | Rede Docker, sem porta publicada |

Para o ESP32 real, provisionar identidade, ACL e certificado para o endereço do notebook. Não desabilitar TLS. Não remover volumes para reiniciar.

## Verificar software

```powershell
docker compose exec -T backend python -m unittest discover -s tests -v
docker compose --profile simulation run --rm simulator python integration_check.py
docker compose --profile simulation run --rm simulator python control_integration_check.py
docker compose --profile simulation run --rm simulator python automatic_integration_check.py
docker compose --profile simulation run --rm simulator python fallback_integration_check.py
```

Verificados 26 testes unitários e cinco testes adicionais de banco em esquema isolado, além de integrações MQTT/TLS, ACL, duplicidade, expiração, rejeições persistidas, decisões, ciclos e desconexão/retomada. Os cinco testes de banco exigem `TEST_DATABASE_URL` e são ignorados no comando padrão. Simulação usa exclusivamente identidade `sim-01` e origem `simulation`; testes de integração devem executar sequencialmente.

## Simulação e ML

```powershell
docker compose --profile simulation run --rm simulator python tools/ml_fixture.py /data/raw/sim-ml-fixture.csv
docker compose --profile simulation run --rm simulator python -m app.ml /data/raw/sim-ml-fixture.csv /models/active.json --source simulation --allow-simulation
docker compose --profile simulation run --rm simulator python ml_integration_check.py
```

Pipeline compara Ridge, Random Forest, Gradient Boosting e persistência. Separação temporal com expurgo dos alvos de seis horas; modelo JSON versionado, sem carregar pickle. Dados sintéticos verificam integração, não desempenho agronômico. Treinamento físico exige dados preliminares, calibração consistente e revisão antes de aprovação. Alvo é solo observado sob a política coletada, não previsão contrafactual sem irrigação.

Para demonstração contínua: `docker compose --profile simulation run --rm simulator python simulate.py --loop --seconds 120 --state /state/device.json --treatment T2`. Configurar `/control/config` pela API com limites explícitos **simulados**. Serviço opcional `docker compose --profile control up -d controller` avalia novas leituras; configuração desabilitada por padrão. Desligar após demonstração com `docker compose --profile control stop controller`.

Contrato em `backend/app/contracts.py`; decisões, previsões, comandos, eventos remotos/locais e rejeições ficam registrados. PUBACK não comprova atuação. Medições inválidas são null, não zero. Separar sempre origem/experimento nas consultas.

## Backup e firmware

`python tools/backup.py backup-and-verify` cria dump, manifesto SHA-256 e testa restauração em banco temporário isolado. `python tools/backup.py verify CAMINHO.dump` verifica arquivo existente. Restauração testada; banco de trabalho preservado.

`docker compose --profile backup up -d backup` agenda dump diário enquanto Docker estiver ativo. Copiar para local adicional e configurar notebook definitivo. Backup no mesmo equipamento não protege contra sua perda.

[Firmware](../firmware/README.md): compilação ESP-IDF e testes portáteis; drivers, pinagem e provisionamento físico pendentes. Buffer do firmware é volátil e limitado; journal de 128 IDs bloqueia quando cheio. Retenção para operação prolongada ainda precisa ser definida.
