# 🌩️ Radar-Simulator — Simulador de Radar Meteorológico

Um simulador interativo de radar meteorológico tático baseado no ecossistema do **NWS (National Weather Service)** dos Estados Unidos. Este projeto permite manipular variáveis de células de tempestades em tempo real e gerenciar a emissão de alertas severos baseados em critérios meteorológicos reais.

## 🗺️ Estações NEXRAD e mapa

O simulador inclui um catálogo de estações NEXRAD com identificador, localidade e coordenadas. Use **Escolher radar** para abrir o mapa, filtrar por região e selecionar uma estação. O mapa de fundo usa dados TopoJSON carregados do jsDelivr; se a conexão falhar, os produtos sintéticos do radar continuam funcionando sem as fronteiras.

A estação selecionada define o centro geográfico das fronteiras desenhadas sobre o display. **Importante:** selecionar uma estação não carrega dados meteorológicos reais. Os ecos, velocidades, produtos e alertas continuam sendo gerados pelo modelo sintético local.

## 🕹️ Como o Jogo Funciona

O usuário opera uma interface de radar tri-produto inspirada em softwares profissionais como o GRLevelX (WSR-88D/NEXRAD). Ao alterar os controles deslizantes, a atmosfera se reajusta instantaneamente:

- **Refletividade (dBZ):** Controla a intensidade da precipitação e o núcleo de granizo. Valores altos geram núcleos roxos severos.
- **Velocidade Radial (V):** Altera os vetores de vento. Ao ativar a rotação, o motor gráfico de pixels deforma a célula em uma espiral orgânica, criando um **Eco de Gancho (Hook Echo)** e um par de cores verde/vermelho colados (*Velocity Couplet*).
- **Coeficiente de Correlação (CC):** Mede a uniformidade dos alvos no ar. Em tempestades normais fica totalmente vermelho (chuva uniforme), mas se houver forte rotação e alta refletividade, uma assinatura azul-clara (ciano) surge no centro do gancho, confirmando um **TDS (Tornado Debris Signature)**.

## 🚨 Motor Automatizado de Alertas NWS

O simulador avalia as condições físicas da tempestade em tempo real e emite alertas operacionais oficiais na tela seguindo estes critérios rígidos:

| Alerta Emitido | Critério Meteorológico |
| :--- | :--- |
| **⚠️ Severe Thunderstorm Warning** | Velocidade do vento de 58 mph ou mais, OU refletividade acima de 55 dBZ. |
| **🌊 Flash Flood Warning** | Velocidade de deslocamento do sistema menor que 20 mph (tempestade estacionária). |
| **🌪️ Tornado Warning (Radar Indicated)** | Presença de *Velocity Couplet* ativo com vento abaixo do limiar extremo. |
| **🚨 PDS Tornado Warning (Observed TDS)** | Rotação ativa combinada com ventos de 70+ mph e refletividade de 60+ dBZ, confirmando detritos no solo pelo CC. |

## 🛠️ Tecnologias Utilizadas

- **Vanilla JavaScript (ES6+):** Processamento matemático de matrizes de pixels e lógica dos alertas.
- **HTML5 Canvas:** Renderização gráfica iterativa com efeito clássico de linha giratória de varredura (*Sweep*), anéis de alcance e fronteiras geográficas.
- **CSS3 Dark-Mode:** Interface tática inspirada em centros de meteorologia severa reais.
---
Desenvolvido como um projeto de simulação científica de código aberto. Sinta-se livre para clonar e explorar as dinâmicas físicas!
