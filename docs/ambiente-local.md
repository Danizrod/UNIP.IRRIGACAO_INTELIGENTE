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

[Firmware](../firmware/README.md): drivers, pinagem e provisionamento físico pendentes. Journal limitado reutiliza slots após expiração segura; relógio regressivo e falhas de armazenamento bloqueiam atuação. Eventos têm fila persistente separada de 32 registros; telemetria continua volátil. Validar NVS, desgaste e cortes de energia na placa. Um ciclo interrompido pode exigir reconciliação do estado no backend, sem inventar conclusão ou consumo.

## Preparar provisionamento do ESP32

`tools/provision-device.py` gera CSV/bin NVS privados usando o gerador oficial ESP-IDF; não grava dispositivo. Criar `.local/device-settings.json` com `device`, `experiment`, `unit`, `broker` (`mqtts://endereco-do-notebook:8883`), `username`, `ssid`, `ntp` e `ca_file` (caminho do certificado em `.local`). Senhas MQTT/Wi-Fi ausentes são solicitadas sem eco. Modo simulado exige identidades `sim-`; modo físico mantém drivers/atuação bloqueados.

```powershell
python tools/provision-device.py --settings .local/device-settings.json --output .local/provision-01 --mode simulation --csv-only
# Em terminal ESP-IDF ativo, remover --csv-only para gerar settings.bin.
```

CSV/bin contêm segredos em texto claro; no Windows, chmod não configura ACL: manter `.local` privada, fora do Git e de pastas compartilhadas. O script preserva arquivos existentes. Manifesto registra tamanho/offset/hash da tabela e firmware disponível; isso não comprova firmware já instalado.

Antes de mudar identidade ou contexto de um dispositivo já usado, drenar/reconciliar eventos pendentes com a configuração antiga. O script não migra histórico entre identidades. Ainda não há suporte operacional completo a três vasos no firmware/configuração; o provisionamento atual prepara uma unidade.

Imagem destinada **somente à partição `provision`** de `firmware/partitions.csv`. Conferir capacidade real e atualizar tabela/firmware compatíveis antes de qualquer gravação manual. Não apagar nem sobrescrever `nvs`, `journal` ou `events`; eles guardam histórico que evita reexecução. Não há flash automático, gravação de eFuses ou alteração do broker. Revisar endereço do notebook, SAN do certificado do broker e CA confiável e ACL por dispositivo antes da conexão; provisionamento/flash ainda exigem ensaio na placa. Gerador oficial ESP-IDF 5.5.1 verificado com credenciais sintéticas: imagem de 65.536 bytes; seis testes unitários aprovados. [Gerador oficial NVS](https://docs.espressif.com/projects/esp-idf/en/v5.5/esp32/api-reference/storage/nvs_partition_gen.html).
