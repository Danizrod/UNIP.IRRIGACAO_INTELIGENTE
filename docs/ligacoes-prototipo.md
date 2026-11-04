# Ligações e diagnóstico da bancada

Estado em **01/11/2026**: sensores e um LED com resistor conectado a uma saída de acionamento. **Bombas desconectadas; circuito de potência não validado.** O LED não comprova capacidade de acionar motores. A pinagem vem do sketch do usuário; fotos e leituras complementam a identificação, sem validar continuidade de todas as trilhas.

## Mapa identificado

Placa ESP32 de 30 pinos, família ESP32 clássica/WROOM; revisão exata não identificada. Dxx na serigrafia corresponde ao GPIOxx neste mapa. GPIO não é posição física na fileira.

| Componente/sinal | GPIO | Identificação |
| --- | --- | --- |
| HX711 DOUT/DT | 5 | Configuração do sketch |
| HX711 SCK | 4 | Configuração do sketch |
| Quatro sensores de carga | Sem GPIO direto | Conjunto ligado a E+, E−, A− e A+ do mesmo HX711 |
| INA3221 SDA | 21 | I²C, endereço configurado 0x40 |
| INA3221 SCL | 22 | I²C |
| Comando de saída 1 | 25 | Segundo borne testado: três pulsos no LED confirmados pelo usuário |
| Comando de saída 2 | 26 | Borne original com LED: pulsos HIGH confirmados visualmente; motores não validados |
| Comando de saída 3 | 27 | Último borne testado: três pulsos no LED confirmados pelo usuário |
| Sensor B / Solo 1 | 32 | Associação identificada pelo usuário |
| Sensor A / Solo 2 | 33 | Associação identificada pelo usuário |
| Sensor C / Solo 3 | 34 | Associação identificada pelo usuário |
| DHT DATA | 18 | Driver DHT22 configurado; leituras recebidas |
| LED auxiliar da placa | 2 | Presente no sketch original; não é saída de bomba |

Não atribuir automaticamente T1/T2/T3 pela posição dos componentes. Os três bornes foram associados aos GPIOs por teste com LED; falta associar canais do INA às cargas. Durante o ensaio, fixar a associação sensor/bomba/tratamento e registrar no provisionamento.

## Componentes e pendências

- INA3221 substitui INA219/INA226. Fotos mostram três resistores R100, coerentes com 0,1 Ω usados no sketch; confirmar continuidade do caminho de corrente e calibrar antes de integrar energia por ciclo. Um chip de três canais não comprova que cada saída passa pelo canal esperado.
- Três BD135 NPN substituem a hipótese de MOSFET. Resistores de base, corrente, dissipação e proteção indutiva precisam de conferência. Diodos não foram identificados; não presumir ausência nem proteção existente.
- As três bombas são do mesmo modelo segundo o usuário, sem inscrição. Anúncio encontrado por semelhança cita 3–6 V e ~200 mA; são dados provisórios, não identificação nem corrente máxima/partida comprovada.
- Alimentação atual por USB. Tensões efetivas de VCC e dos sinais ainda não medidas. Fonte externa de 5 V é intenção, sem capacidade confirmada. Não conectar fonte e USB simultaneamente sem conferir o circuito.
- Pesagem real: **quatro sensores de carga de três fios**, tipo balança, ligados a **um HX711** nos terminais E+, E−, A− e A+, conforme relato do usuário. Formam um conjunto de medição, não quatro leituras separadas. A combinação elétrica dos doze fios ainda não foi verificada; não presumir ligação em paralelo nem deduzir função pela cor. Capacidade individual e total desconhecidas; não somar capacidades presumidas nem testar por sobrecarga. Conferir plataforma, distribuição da carga e resposta em cada apoio com massa conhecida e pequena antes da calibração final.
- Índice de solo do sketch usa limites comuns de ar/água: não é calibração individual no substrato nem umidade volumétrica. Peso e energia exibidos ainda não têm exatidão comprovada.

GPIO5 participa da configuração de inicialização do ESP32; validar boot/reset com o HX711 conectado. GPIO34 é somente entrada, adequado ao sinal analógico. Verificar níveis de 3,3 V, pull-ups e alimentação dos módulos antes de modificar ligações. A célula se liga ao HX711, não diretamente ao ESP32; motores se ligam ao circuito de potência, nunca aos GPIOs.

## O que pode ser feito agora

1. Manter motores desconectados, LED com resistor e etiquetas A/B/C nos sensores.
2. Observar solo, ambiente, peso e INA pelo painel do sketch atual. Endereço observado em 04/11: `http://192.168.15.30/`; DHCP pode alterá-lo. O painel temporário não substitui o Grafana do sistema final.
3. Registrar respostas sem tara/calibração por `python tools/bench_monitor.py --ip 192.168.15.30 --samples 3 --interval 2 --output data/raw/diagnostico-led.jsonl`. Usar nome novo em cada coleta; diretório deve existir. O observador consulta somente `/dados` (o sketch limpa a mensagem temporária ao responder), exporta campos permitidos e marca `trial_eligible=false`. A data é de recepção no computador, não horário de aquisição. Falha permanece ausente; flags INA/HX do sketch indicam inicialização, não saúde contínua. NÃO importar esses registros como ensaio nem confirmar calibração com eles.
4. Depois da preservação do programa atual, usar o diagnóstico sequencial abaixo para identificar o borne com LED. Etiquetar o borne com GPIO25, 26 ou 27 conforme a observação. O teste não identifica os outros bornes sem mover a carga ou medir continuidade.
5. Com alimentação desligada, completar continuidade/identificação dos canais e verificar fonte, proteções e célula. Após validação, implementar drivers no ESP-IDF e calibrar antes de ensaio físico.

## Diagnóstico sequencial preparado, ainda não gravado

Arquivo: `firmware/diagnostics/led_channels/led_channels.ino`; mapa em `firmware/core/bench_pins.hpp`. É um sketch Arduino separado, sem rede, sem alteração de EEPROM e sem sensores; o programa atual deixa de fornecer a página web enquanto esse diagnóstico estiver gravado. Não confundir compilação Arduino com o build ESP-IDF do projeto. No Arduino CLI, incluir `firmware/core` em `compiler.cpp.extra_flags` usando `-I` e um caminho curto para evitar o limite do Windows.

**Antes de gravar:** preservar o fonte atual fora do Git se contiver credenciais, registrar o fator de calibração do painel, identificar flash/partições e fazer backup verificado da memória para restauração. Backup de flash pode conter senhas: guardar em `.local/`, nunca versionar. Não executar apagamento de flash. Nenhuma gravação ou backup é realizado automaticamente por esta documentação.

1. Confirmar motores fisicamente desconectados; o diagnóstico só admite LED com resistor. LOW é estado de teste, não polaridade de motor validada.
2. Compilar no ambiente Arduino para a placa confirmada. Ainda requer compilação e verificação física.
3. Após gravação deliberada, abrir serial a 115200 baud com final de linha newline.
4. Enviar `LED_ONLY`: libera testes por 60 s; não liga saída automaticamente.
5. Enviar `1`, `2` ou `3`, separadamente: pulso HIGH no GPIO25, 26 ou 27 por até 1 s no funcionamento normal do loop. As demais saídas ficam LOW. Observar o LED e registrar o GPIO correspondente ao borne. Não há corte independente de hardware contra travamento.
6. Enviar `OFF` para desarmar. Entrada desconhecida/longa desarma; sessão expira e reboot volta desarmado. Comandos recebidos durante pulso encerram o anterior antes de qualquer novo teste.
7. Restaurar o programa preservado para voltar à página de sensores. Não usar esse diagnóstico para motores ou coleta dos 30 dias.

O firmware ESP-IDF final mantém o bloqueio de atuação física até integração e revisão dos drivers. O ensaio aprovado permanece um ESP32, três vasos e 30 dias simultâneos; testes com LED não são ciclos de irrigação. A janela originalmente proposta para novembro não está comprovadamente iniciada e precisa ser replanejada após preparação.

Referências técnicas: [ESP32](https://documentation.espressif.com/esp32_datasheet_en.html), [INA3221](https://www.ti.com/lit/ds/symlink/ina3221.pdf) e [BD135](https://www.st.com/resource/en/datasheet/bd135.pdf). Conferir fabricante/revisão da peça antes de usar qualquer pinagem de encapsulamento.

Quatro sensores de três fios podem ser combinados em ponte para um HX711; a foto isolada não comprova a ligação atual. Referência: [guia SparkFun](https://learn.sparkfun.com/tutorials/load-cell-amplifier-hx711-breakout-hookup-guide). Não é necessário adquirir placa combinadora para documentar ou testar a montagem existente.

## Verificações desta atualização

Em 01/11/2026, três respostas reais de `/dados` foram registradas em `data/raw/diagnostico-led-20261101.jsonl` (arquivo local ignorado pelo Git). São respostas de bancada, com calibração não verificada; o fator informado foi 45,47. Quatro testes do observador HTTP e o teste C++ com adaptador de GPIO/tempo passaram.

Backup completo de 4 MB realizado e comparado com a flash por `esptool verify-flash`: digest correspondente. Chip identificado como ESP32-D0WD-V3, revisão 3.1. Backup e fonte fornecido com credenciais ficam somente em `.local/backups/esp32-com5-20261101/`, ignorados pelo Git. Manifesto contém SHA-256 e partições; não publicar o binário nem o fonte com senhas.

Diagnóstico compilado com Arduino CLI 1.5.1/ESP32 2.0.17 e gravado apenas em app0 (`0x10000`), com hash conferido. O usuário não observou luz no GPIO25 e confirmou o LED piscando no GPIO26. Na primeira posição, isso identificou o borne originalmente ocupado; depois o usuário moveu o mesmo LED com resistor e confirmou três pulsos no GPIO25 no segundo borne e no GPIO27 no último. Os três bornes estão identificados por ordem de teste, sem presumir posição esquerda/direita. Os testes não validam corrente de motor, proteções nem mapeamento dos canais INA. A aplicação original foi restaurada com hash conferido. A página respondeu novamente em `192.168.15.39` e informou fator 45,47. Como no sketch original há tara automática no boot, não esperar preservação do zero anterior.

Para repetir a identificação em outra montagem, desconectar USB e qualquer fonte, etiquetar o borne original como D26 e mover o mesmo LED com seu resistor para outro par de saída, respeitando a polaridade identificada. Não assumir polaridade apenas pela posição dos parafusos. Confirmar a posição antes de energizar se os polos não estiverem identificados. Repetir diagnóstico e registrar a observação, sem conectar motores. Restaurar novamente o programa de sensores ao encerrar.

[Diagrama de diagnóstico](../.archify/workflow-bancada-led-20261101-120000/bancada-led.html): validação de especificação, geração e verificação do artefato passaram. A inspeção automática em navegador falhou por erro do transporte DevTools no Windows; não declarar essa etapa aprovada. Rótulos em português, controles nativos em inglês.

Resultado final dos bornes: **original = D26; segundo testado = D25; último testado = D27**. Etiquetar fisicamente antes de montar os ramos dos vasos; T1/T2/T3 ainda precisam de associação explícita.


## Revisão da pesagem em 04/11/2026

IP confirmado por MAC e página: `http://192.168.15.30/`; DHCP pode alterá-lo. `/dados` informou fator **20,00**, HX inicializado e leituras de peso; o flag não comprova saúde contínua nem calibração. O fator 45,47 nos backups anteriores é histórico: não restaurar dados antigos sobre a calibração atual.

O usuário informou referência de celular de 221 g, cantos 228/220/223/222 g e repetições centrais 223,67/225,08/224,48/225,10/227,73 g. A origem da referência não foi aferida por nós. Relatou deriva sem carga após reposicionar a plataforma: 11,36/14,31/15,37/15,83/19,59 g aos 1/3/5/10/15 min. São observações relatadas, sem aquisição sincronizada; a pesagem não está validada para pequenos volumes. Não corrigir a deriva por taras repetidas ou ajuste do fator.

Revisão do sketch web fornecido e do exemplo serial enviado pelo usuário:

- `getData()` já retorna média filtrada da HX711_ADC. `pesoRaw` do painel não é ADC bruto. A média externa de dez amostras acrescenta atraso, não explica sozinha a deriva por 15 min. Para comparar, usar uma só camada de filtro e não aplicar zona morta ao dado registrado.
- O exemplo serial isola Wi-Fi, DHT, INA e alternância de saídas, sendo uma base melhor para diagnóstico; não é um firmware final e ainda contém bloqueios.
- No código-fonte público consultado, `start(t, ...)` compara `millis()` com `t + 400` como tempo absoluto desde o boot. Se chamado após a espera pelo Wi-Fi, pode pular a fase de estabilização. A versão efetivamente compilada no sketch original não é conhecida. Preferir estabilização própria por diferença de tempos, mantendo `update()` ativo, e tara explícita após estabilização.
- `while (!LoadCell.update())` não tem prazo; no serial, espera por fator e por confirmação de gravação não chama `update()`. Calibração/tara devem ser estados com prazo, cancelamento e aquisição contínua, sem espera infinita por entrada serial nem `parseFloat()` bloqueante.
- Validar massa positiva e finita, fator finito e não nulo (sinal pode depender da orientação), retorno de `EEPROM.begin/commit` e tamanho/versão da configuração. Não reinstalar automaticamente o fator 31,79 se faltar calibração válida. `getNewCalibration()` já aplica o fator na biblioteca consultada: não é falta de `setCalFactor()` no exemplo serial.
- Atualizar saúde por idade da última amostra, timeouts e finitude; durante tara/dados vencidos, publicar valor ausente/estado inválido. Registrar uptime, idade, taxa observada, fator, offset, início/fim de tara e eventual reconexão. Não rotular leitura filtrada como dado bruto.
- Interrupções podem alongar SCK e interferir no HX711; conferir configuração/versão e temporização. Remover Wi-Fi e outras tarefas em teste controlado pode ajudar a isolar a causa, mas não demonstra interferência elétrica nem defeito mecânico por si só.

Próximo ensaio proposto: pesagem isolada por serial, sem rede nem alternância de saídas, fator 20,00 preservado, filtro da biblioteca explícito, sem segunda média/zona morta/autozero; aquisição contínua, tara manual única após estabilização e registro por 15 min sem tocar na montagem. Antes de gravar, fazer novo backup completo: o backup de 01/11 contém fator antigo. Manter motores desconectados. Não trocar programa, fazer tara ou gravar EEPROM automaticamente nesta revisão.

### Resultado do diagnóstico isolado (04/11/2026, à noite)

Novo backup completo em `.local/backups/esp32-com5-20261104-fator20/`: bootloader/tabela, otadata, app0 e restante conferidos; NVS relida e conferida com o chip parado no bootloader (mudou após reboot por Wi-Fi/PHY). Fator gravado: **19,9955** (painel mostra 20,00). Diagnóstico `firmware/diagnostics/hx711_drift` gravado só em app0; app0 do backup restaurado depois, com hash e página conferidos.

Fotos do usuário: quatro sensores sobre suportes plásticos nas extremidades da tampa, placa fina de compensado (~280 g, estimado ao levantá-la) apoiada nos quatro, sem cabos encostando. Ligação aparenta o arranjo padrão em ponte (pares preto/branco entre sensores vizinhos, quatro vermelhos em E+/E−/A−/A+), sem continuidade medida. DHT22 estava na saída de ar quente do notebook (36,6 °C) e foi afastado.

Balança vazia, sem toque, uma série de cada condição (n=1, não há repetição):

| Condição | Duração | Variação | Ruído (dp) |
| --- | --- | --- | --- |
| Sketch web, horas após boot, DHT a 36 °C, antes de mexer na placa | 5 min | +2,8 g (+0,9 g/min) | — |
| Sketch web, após recolocar a placa | 7 min | +16,5 g (+1,5 g/min) | — |
| Diagnóstico serial sem Wi-Fi, após tara única | 15 min | −5,4 g | 1,1 g |
| Sketch web logo após boot (tara automática) | 15 min | +2,9 g | 0,9 g |

Leitura: logo após o boot, os dois programas ficaram dentro de cerca de ±6 g em 15 min; a subida de ~1 g/min e o acúmulo de 11 para 87 g ocorreram com horas de operação, calor do notebook e manuseio. O Wi-Fi não aparece como causa dominante; a causa da deriva maior continua não isolada (temperatura e acomodação mecânica são hipóteses). A alternância das saídas alterou o peso em ~0,3 g. Às 19:19 o INA3221 retornou leitura inválida (−0,01 V; 1638 mA) com o painel ainda "OPERACIONAL": o firmware final deve rejeitar leituras I²C inconsistentes. Canal 3 do INA acompanha o LED (~21 mA quando GPIO25/27 em HIGH). Dados: `data/raw/deriva-vazio-20261104.jsonl`, `hx711-serial-20261104.log`, `deriva-web-pos-boot-20261104.jsonl` (fora do Git, `trial_eligible=false`).

Próximo passo: registro longo (1–2 h ou noturno) com o DHT22 junto ao HX711/sensores e notebook afastado, para relacionar deriva e temperatura; depois, massa conhecida estável por tempo equivalente a um ciclo (fluência sob carga). A pesagem segue não validada.

Fontes: [implementação HX711_ADC](https://github.com/olkal/HX711_ADC/blob/master/src/HX711_ADC.cpp), [API](https://github.com/olkal/HX711_ADC/blob/master/src/HX711_ADC.h), [configuração](https://github.com/olkal/HX711_ADC/blob/master/src/config.h). O código consultado não comprova a versão instalada no firmware original.
