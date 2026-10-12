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

`core/controller.hpp` contém proteção portátil, histerese, retomada explícita e buffer FIFO limitado. O journal persiste IDs **antes** de qualquer acionamento; 128 IDs ocupados bloqueiam novos comandos, sem expulsar IDs antigos silenciosamente. Definir retenção/provisionamento antes de uso contínuo.

`main/main.cpp` prepara conexão Wi-Fi/MQTT com CA, autenticação e identificação por dispositivo, a partir do namespace NVS `settings`: `device`, `experiment`, `unit`, `broker` (mqtts), `username`, `password`, `ca`, `ssid`, `wifi_password`, `ntp` (servidor de horário). MQTT só inicia após obter horário UTC via SNTP. Nenhum segredo é versionado. ACL do broker deve limitar `irrigation/v1/{device}/commands` e tópicos de saída do dispositivo.

O modo `IRRIGATION_SIMULATION` habilita somente fixtures sintéticas (solo, reservatório e bomba virtual), exigindo dispositivo/experimento `sim-`. Publica telemetria identificada a cada cinco segundos. Limites simulados não são recomendações de calibração. A configuração padrão não amostra nem publica sensores físicos fictícios.

Retomada exige conexão, SUBACK da assinatura, UTC válido, buffer esvaziado e ausência de ciclo ativo. Comandos remotos durante essa barreira são rejeitados. Publicação QoS1 só libera o buffer no PUBACK, sem tratar isso como prova de atuação. Eventos conservam UUID/horário original nos reenvios; medições ausentes são null/inválidas. O journal guarda término máximo conservador para preservar intervalo após reboot.

Pendentes: drivers físicos, calibração, integração física das medições e provisionamento seguro dos segredos no dispositivo. Watchdog ESP-IDF reinicia o dispositivo; corte elétrico seguro durante reset depende do circuito real. Buffer volátil perde eventos ao reboot; capacidade 32 rejeita novos itens ao transbordar e incrementa contador. UTC/SNTP, NVS, TLS e entrega MQTT precisam de ensaio no ESP32. PUBACK confirma broker, não persistência no backend. Não houve teste físico.

Os testes portáteis usam bomba/sensores simulados. Não comprovam GPIO, TLS em ESP32, consumo, calibração ou funcionamento físico.
