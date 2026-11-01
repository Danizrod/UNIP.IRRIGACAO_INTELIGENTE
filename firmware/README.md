# Firmware preparado para três unidades

Projeto ESP-IDF para um ESP32 e três canais, com mapa de GPIOs documentado e sem drivers de acionamento físico integrados. Todos os canais ficam desligados no boot; sensores e calibração inválidos impedem atuação. Não gravar como firmware funcional de bancada. `IRRIGATION_PHYSICAL_ENABLED` falha a compilação propositalmente até revisão dos drivers.

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

`main/main.cpp` prepara Wi-Fi/MQTT com CA, autenticação e identidade por dispositivo. Namespace NVS `settings` na partição `provision`: `device`, `experiment`, `unit1`, `unit2`, `unit3`, `broker` (mqtts), `username`, `password`, `ca`, `ssid`, `wifi_password`, `ntp`. `unit1/unit2/unit3` correspondem a T1/T2/T3 fixos e precisam ser distintos; `unit` legado pode substituir apenas `unit1`. Sem as três identidades, o runtime fica desligado. MQTT inicia após sincronização UTC/SNTP. Nenhum segredo é versionado; ACL limita tópicos por dispositivo.

`IRRIGATION_SIMULATION` habilita fixtures sintéticas de três solos e bombas virtuais, com reservatório comum; exige dispositivo/experimento `sim-`. Padrão de provisionamento: `sim-01`, experimento `sim-three-pots`, unidades `sim-pot-01/T1`, `sim-pot-02/T2`, `sim-pot-03/T3`. Publica uma leitura por unidade a cada cinco segundos, com calibração `sim-fixture-{unit_id}`. DHT/reservatório são valores comuns, não três medições independentes. Fixtures recomeçam no boot e não representam ensaio físico. O modo padrão não publica sensores físicos fictícios.

`core/shared_rig.hpp` mantém executor global: uma bomba por vez, pesagem estabilizada antes/depois, intervalo global e término somente após estabilização. Comandos durante outro ciclo/estabilização são rejeitados, sem começar outro canal. Fallback seleciona unidades em rodízio e não se sobrepõe ao remoto; a fila remota justa fica no backend. Eventos preservam unidade/tratamento. Valores **apenas sintéticos**: limite 50 mL/10 s, intervalo 20 s e estabilização 2 s; não importar para a bancada. Medições dos eventos permanecem null/inválidas até implementação dos drivers e integração calibrada.

Retomada exige conexão, SUBACK da assinatura, UTC válido, buffer esvaziado e ausência de ciclo ativo. Comandos remotos durante essa barreira são rejeitados. Publicação QoS1 só libera o buffer no PUBACK, sem tratar isso como prova de atuação. Eventos conservam UUID/horário original nos reenvios; medições ausentes são null/inválidas. O journal guarda término máximo conservador para preservar intervalo após reboot.

Eventos usam fila NVS durável de 32 posições, com UUID e horário preservados após reboot. Antes de ligar a bomba virtual, `accepted` já está persistido e três posições estão reservadas para accepted/started/terminal; rejeições concorrentes não consomem essa reserva. Erro na persistência interrompe/bloqueia atuação. PUBACK libera a fila persistindo o novo estado; queda de energia entre PUBACK e checkpoint pode reenviar a mesma mensagem, exigindo deduplicação no backend. Snapshots gravam somente o prefixo usado; testes físicos de desgaste/heap/queda de energia permanecem pendentes. Telemetria usa buffer separado **volátil**, limitado a 32 mensagens, com perdas contabilizadas.

`partitions.csv` preserva a NVS legada em `0x9000` e o início do aplicativo em `0x10000`, ampliando-o para 1,5 MiB. Novos offsets: journal `0x190000`, events `0x1a0000`, provision `0x1b0000` (64 KiB cada). A tabela termina em `0x1c0000` e cabe em 2 MiB; conferir capacidade/placa e hash do mapa antes de qualquer gravação. **Este mapa não pode substituir automaticamente um mapa anteriormente gravado:** os offsets de journal/events/provision mudaram. Preservar e migrar dados antes de qualquer alteração, sem erase automático. Nenhum flash/erase foi executado.

Configuração usa somente `provision`; não apagar journal/events ao reprovisionar. Antes de trocar device/experimento/unidades, drenar e reconciliar eventos pendentes, que conservam a identidade original. Tratamentos/parâmetros/modelos reais devem permanecer congelados durante os 30 dias, conforme protocolo; dias/leituras não são réplicas independentes.

Pendentes: drivers físicos, calibração, integração física das medições e provisionamento no dispositivo. Watchdog ESP-IDF reinicia o dispositivo; corte elétrico seguro durante reset depende do circuito real. UTC/SNTP, NVS, TLS, RAM e entrega MQTT precisam de ensaio no ESP32. PUBACK confirma broker, não persistência no backend. Após queda de energia durante um ciclo pode haver accepted/started sem terminal; a bomba não retoma automaticamente e o backend pode exigir reconciliação manual para desbloquear o dispositivo. Nenhuma água/energia/conclusão é inventada para encerrar esse ciclo. Não houve teste físico.

Os testes portáteis usam bomba/sensores simulados. Não comprovam GPIO, TLS em ESP32, consumo, calibração ou funcionamento físico.


## Diagnóstico isolado com LED

`core/bench_pins.hpp` registra os GPIOs do sketch do usuário e sensores A/B/C. Não define tratamento, borne, polaridade ou circuito de potência validado. `diagnostics/led_channels/led_channels.ino` é um sketch Arduino separado, sem Wi-Fi, credenciais ou escrita de calibração; não faz parte do build ESP-IDF e não foi gravado automaticamente. Ele testa GPIO25/26/27 individualmente por até 1 s, após `LED_ONLY`, com sessão de 60 s. Estado LOW não é confirmação de motor desligado: usar exclusivamente com motores fisicamente desconectados. Instruções e preservação do programa atual em [ligações](../docs/ligacoes-prototipo.md).

Verificação local: `g++ -std=c++17 -Wall -Wextra -Werror -Itests/arduino_stub tests/led_channels_test.cpp -o /tmp/led-test && /tmp/led-test`, na pasta `firmware/`. O adaptador simula serial, tempo e níveis; verifica bloqueio inicial, exclusão entre canais, pulso, expiração, entrada inválida e rollover. Não comprova compilação Arduino/ESP32, temporização física ou circuito elétrico. Quatro sensores de carga compartilham um HX711; não há quatro canais de massa.
