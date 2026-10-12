# Ambiente local

Base de integração verificada com dados simulados em 12/10/2026. Ainda não controla bombas nem executa ML.

## Executar e testar

Na raiz do projeto, com Docker Desktop ativo:

```powershell
docker compose up -d --build
docker compose ps
docker compose exec -T backend python -m unittest discover -s tests -v
docker compose --profile simulation run --rm simulator python integration_check.py
docker compose logs --tail 30 ingestion
docker compose stop
```

Os testes gravam dados identificados como simulados. Foram verificados validação, autenticação, duplicidade, conflito, persistência MQTT/TLS, reinicialização do broker e consulta do Grafana. Não são testes físicos.

## Acessos

| Serviço | Endereço ou acesso |
| --- | --- |
| API/Swagger | http://127.0.0.1:8000/docs — Bearer com API_TOKEN |
| Prontidão | http://127.0.0.1:8000/health |
| Grafana | http://127.0.0.1:3000/d/tcc-ingestion — admin e GRAFANA_ADMIN_PASSWORD |
| MQTT | localhost:8883, TLS, autenticação e ACL |
| PostgreSQL | Apenas rede Docker, sem porta publicada |

Credenciais em `.env`; certificados em `.local/certs`. Ambos fora do Git. Não remover volumes para reiniciar: contêm os dados. Backup e restauração ainda devem ser preparados.

## Backup

Com Python 3 disponível no notebook, executar `python tools/backup.py backup-and-verify`. O script cria um dump consistente e um manifesto SHA-256 em `.local/backups/`, restaura em banco temporário isolado e verifica as tabelas. O banco de trabalho não é substituído. Para verificar um dump existente: `python tools/backup.py verify CAMINHO.dump`.

Restauração isolada verificada em 12/10/2026. Copiar backups para um local adicional antes do experimento; a cópia no mesmo notebook não protege contra perda do equipamento. O agendamento diário ainda deve ser configurado no notebook definitivo.

## Configuração e dados

Python 3.12 no container; dependências fixadas em backend/requirements.lock.txt. Imagens da infraestrutura ainda usam tags; congelar antes do experimento. Em configuração nova, tools/bootstrap-local.py exige Python/cryptography, gera credenciais/certificados e preserva configurações existentes. Scripts SQL de inicialização só executam em volume vazio; mudanças posteriores exigem migração.

Para ESP32 pela rede local, configurar identidade/ACL, endereço do notebook e certificado correspondente. Os acessos atuais ficam restritos a localhost; não desabilitar validação TLS. Separar usuário da aplicação com permissões mínimas antes da operação física; Grafana já usa usuário somente de leitura.

Contrato: backend/app/contracts.py. Tópico: `irrigation/v1/<device_id>/telemetry`. Identificar dispositivo, vaso, experimento, tratamento, origem e calibração; registrar horário de coleta e recebimento. Deduplicação por dispositivo/message_id. Índice de solo é relativo; ausência de leitura não é zero. Rejeições MQTT atualmente ficam em log; registro durável ainda pendente.

Filtrar sempre origem e experimento. Fixtures sim-* não entram na análise física ou treinamento real. Buffer, confirmação de atuação e fallback no ESP32 ainda não foram implementados.
