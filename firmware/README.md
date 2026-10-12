# Firmware preparado

Projeto ESP-IDF para ESP32, sem pinagem ou acionamento físico. O boot permanece desligado; sensores e calibração inválidos impedem atuação. Não gravar como firmware funcional de bancada. `IRRIGATION_PHYSICAL_ENABLED` falha a compilação propositalmente até revisão dos drivers.

## Compilar

Na pasta firmware, com ESP-IDF 5.5.1:

```sh
idf.py set-target esp32
idf.py build
g++ -std=c++17 -Wall -Wextra -Werror -Icore tests/safety_test.cpp -o /tmp/safety-test
/tmp/safety-test
# Compila padrão + simulação em diretório temporário separado:
bash tests/build_check.sh
```

`core/controller.hpp` contém proteção portátil, histerese e retomada explícita. O journal persiste IDs **antes** de qualquer acionamento. Seus 128 slots retêm comandos até a expiração (TTL máximo 300 s); slots vencidos só são reaproveitados no checkpoint que também persiste o piso UTC. Regressão do relógio bloqueia comandos. Observações atualizam o piso em RAM; a persistência ocorre em mutações, sem escrita por segundo. IDs legados sem expiração recebem quarentena conservadora de 300 s a partir do primeiro horário confiável; reboot pode prolongá-la. Estado corrompido, versão desconhecida ou falha de gravação bloqueia atuação sem apagar dados.

`main/main.cpp` prepara conexão Wi-Fi/MQTT com CA, autenticação e identificação por dispositivo, a partir do namespace NVS `settings`: `device`, `experiment`, `unit`, `broker` (mqtts), `username`, `password`, `ca`, `ssid`, `wifi_password`, `ntp` (servidor de horário). MQTT só inicia após obter horário UTC via SNTP. Nenhum segredo é versionado. ACL do broker deve limitar `irrigation/v1/{device}/commands` e tópicos de saída do dispositivo.

O modo `IRRIGATION_SIMULATION` habilita somente fixtures sintéticas (solo, reservatório e bomba virtual), exigindo dispositivo/experimento `sim-`. Publica telemetria identificada a cada cinco segundos. Limites simulados não são recomendações de calibração. A configuração padrão não amostra nem publica sensores físicos fictícios.

Retomada exige conexão, SUBACK da assinatura, UTC válido, buffer esvaziado e ausência de ciclo ativo. Comandos remotos durante essa barreira são rejeitados. Publicação QoS1 só libera o buffer no PUBACK, sem tratar isso como prova de atuação. Eventos conservam UUID/horário original nos reenvios; medições ausentes são null/inválidas. O journal guarda término máximo conservador para preservar intervalo após reboot.

Eventos usam fila NVS durável de 32 posições, com UUID e horário preservados após reboot. Antes de ligar a bomba virtual, `accepted` já está persistido e três posições estão reservadas para accepted/started/terminal; rejeições concorrentes não consomem essa reserva. Erro na persistência interrompe/bloqueia atuação. PUBACK libera a fila persistindo o novo estado; queda de energia entre PUBACK e checkpoint pode reenviar a mesma mensagem, exigindo deduplicação no backend. Snapshots gravam somente o prefixo usado; testes físicos de desgaste/heap/queda de energia permanecem pendentes. Telemetria usa buffer separado **volátil**, limitado a 32 mensagens, com perdas contabilizadas.

`partitions.csv` mantém a NVS legada e o aplicativo nos offsets anteriores e acrescenta partições separadas de journal, events e provision. A tabela cabe em 2 MiB, mas capacidade e modelo da placa devem ser conferidos antes de qualquer gravação. Não houve flash/erase. Configuração da identidade usa somente `provision`; não apagar journal/events ao reprovisionar. Antes de trocar device/experimento/unidade, drenar e reconciliar eventos pendentes, que conservam a identidade original.

Pendentes: drivers físicos, calibração, integração física das medições e provisionamento no dispositivo. Watchdog ESP-IDF reinicia o dispositivo; corte elétrico seguro durante reset depende do circuito real. UTC/SNTP, NVS, TLS, RAM e entrega MQTT precisam de ensaio no ESP32. PUBACK confirma broker, não persistência no backend. Após queda de energia durante um ciclo pode haver accepted/started sem terminal; a bomba não retoma automaticamente e o backend pode exigir reconciliação manual para desbloquear o dispositivo. Nenhuma água/energia/conclusão é inventada para encerrar esse ciclo. Não houve teste físico.

Os testes portáteis usam bomba/sensores simulados. Não comprovam GPIO, TLS em ESP32, consumo, calibração ou funcionamento físico.
