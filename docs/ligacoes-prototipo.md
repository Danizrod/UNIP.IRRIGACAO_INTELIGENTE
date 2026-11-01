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
| Comando de saída 1 | 25 | BD135 NPN instalado; borne/polaridade pendentes |
| Comando de saída 2 | 26 | Borne original com LED: pulsos HIGH confirmados visualmente; motores não validados |
| Comando de saída 3 | 27 | BD135 NPN instalado; borne/polaridade pendentes |
| Sensor B / Solo 1 | 32 | Associação identificada pelo usuário |
| Sensor A / Solo 2 | 33 | Associação identificada pelo usuário |
| Sensor C / Solo 3 | 34 | Associação identificada pelo usuário |
| DHT DATA | 18 | Driver DHT22 configurado; leituras recebidas |
| LED auxiliar da placa | 2 | Presente no sketch original; não é saída de bomba |

Não atribuir automaticamente T1/T2/T3 pela posição dos componentes. Falta associar bornes aos GPIOs e canais do INA às cargas. Durante o ensaio, fixar a associação sensor/bomba/tratamento e registrar no provisionamento.

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
2. Observar solo, ambiente, peso e INA pelo painel do sketch atual. Seu endereço observado foi `http://192.168.15.39/`; DHCP pode alterá-lo. O painel temporário não substitui o Grafana do sistema final.
3. Registrar respostas sem tara/calibração por `python tools/bench_monitor.py --ip 192.168.15.39 --samples 3 --interval 2 --output data/raw/diagnostico-led.jsonl`. Usar nome novo em cada coleta; diretório deve existir. O observador consulta somente `/dados` (o sketch limpa a mensagem temporária ao responder), exporta campos permitidos e marca `trial_eligible=false`. A data é de recepção no computador, não horário de aquisição. Falha permanece ausente; flags INA/HX do sketch indicam inicialização, não saúde contínua. NÃO importar esses registros como ensaio nem confirmar calibração com eles.
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

Diagnóstico compilado com Arduino CLI 1.5.1/ESP32 2.0.17 e gravado apenas em app0 (`0x10000`), com hash conferido. O usuário não observou luz no GPIO25 e confirmou o LED piscando no GPIO26. Isso identifica apenas o borne originalmente ocupado; não comprova falha no outro canal nem habilita motores. A aplicação original foi restaurada com hash conferido. A página respondeu novamente em `192.168.15.39` e informou fator 45,47. Como no sketch original há tara automática no boot, não esperar preservação do zero anterior.

Para mapear os outros bornes, desconectar USB e qualquer fonte, etiquetar o borne original como D26 e mover o mesmo LED com seu resistor para outro par de saída, respeitando a polaridade identificada. Não assumir polaridade apenas pela posição dos parafusos. Confirmar a posição antes de energizar se os polos não estiverem identificados. Repetir diagnóstico e registrar a observação, sem conectar motores. Restaurar novamente o programa de sensores ao encerrar.

[Diagrama de diagnóstico](../.archify/workflow-bancada-led-20261101-120000/bancada-led.html): validação de especificação, geração e verificação do artefato passaram. A inspeção automática em navegador falhou por erro do transporte DevTools no Windows; não declarar essa etapa aprovada. Rótulos em português, controles nativos em inglês.
