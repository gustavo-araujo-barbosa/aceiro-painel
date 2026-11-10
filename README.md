# Aceiro: boletim de fogo e seca para a agricultura familiar do Pará

Protótipo funcional do **Aceiro**, projeto do grupo **Raiz de Dados** para a Global Solution 2026/2 da FIAP (tema CitizenTech).

O Aceiro transforma dados públicos de fogo, seca e El Niño num boletim semanal por município, em linguagem simples. O boletim traz o nível de alerta, o motivo em uma frase e a ação da semana, como abrir o aceiro. Ele chega por WhatsApp, SMS, rádio comunitário ou visita do técnico da Emater.

## O que dá para fazer no painel

| Página | O que mostra |
|---|---|
| **Início** | O problema, a solução e como usar o protótipo |
| **Visão do agricultor** | O boletim de um município no WhatsApp, no SMS e no rádio, como chegaria ao produtor |
| **Painel do técnico** | Mapa do Pará por nível de alerta e fila de revisão dos alertas vermelhos. O técnico aprova ou muda o nível, com motivo obrigatório para baixar |
| **Sobre os dados** | Fontes, a regra usada para o nível e os limites do protótipo |

## O que é real e o que é demonstração

- **Dados reais:** focos de calor do INPE (satélite de referência AQUA_M-T, de agosto a outubro de 2026), municípios do IBGE (Censo 2022 e Censo Agropecuário 2017), cobertura 4G da Anatel e índice RONI da NOAA.
- **Regra de demonstração:** o nível de alerta usa o número de focos na semana (verde 0, amarelo 1 a 4, laranja 5 a 19, vermelho 20 ou mais). Com El Niño forte, nenhum município fica verde. O modelo estatístico do projeto é testado à parte e não roda aqui.
- **Simulação:** a revisão do técnico não grava nem envia nada.
- **Rascunho:** as ações recomendadas precisam de revisão técnica da Emater antes de qualquer uso real.
- **Validação:** o uso do painel ainda não foi testado com agricultores e técnicos. Isso fica para a próxima etapa.

Foco de calor não é incêndio confirmado nem dano às famílias. O alerta é por município: o Aceiro não sabe onde fica cada propriedade.

## Como rodar no seu computador

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/streamlit run app/painel.py
```

Os dados agregados já estão em `app/dados/` (cerca de 0,8 MB). O `app/preparar_dados.py` mostra como eles foram gerados a partir dos dados públicos.

## Equipe

Grupo Raiz de Dados, FIAP, turma 1TSCPW: Gustavo de Araujo Barbosa e Jonatas Menezes da Silva.

Protótipo acadêmico. Não envia mensagens reais e não substitui os alertas oficiais da Defesa Civil.
