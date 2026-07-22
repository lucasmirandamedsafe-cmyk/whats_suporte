# Por que SESSION_GAP_HOURS = 6

`config.SESSION_GAP_HOURS` define o intervalo (em horas) sem mensagens que
marca o início de um novo atendimento/sessão dentro da mesma conversa
(`pipeline/parse.py::assign_sessions`). O valor `6` foi definido desde o
primeiro commit do projeto sem nenhuma análise documentada por trás - só um
default razoável.

Em 2026-07-22, a pedido do usuário, essa escolha foi verificada empiricamente
contra os dados reais de mensagens. Este documento registra o método e o
resultado, para não precisar refazer a análise do zero se a pergunta surgir de
novo (ex.: depois de importar muito mais dados).

## Método

Script: `pipeline/verificar_gap_sessoes.py` (reexecutável a qualquer momento).

Para cada `conversation_id`, ordena as mensagens por `timestamp` e calcula o
intervalo (em horas) entre cada mensagem e a anterior na mesma conversa. Um
bom valor de corte para `SESSION_GAP_HOURS` deve cair num **vale** dessa
distribuição - uma faixa onde quase não há gaps reais - separando:

- gaps pequenos = resposta dentro da mesma conversa corrida;
- gaps grandes = cliente só respondeu no próximo período de atendimento (ex.:
  dia útil seguinte).

Se o valor de corte caísse no meio de uma faixa com muitos gaps, ele estaria
cortando atendimentos no meio (valor baixo demais) ou juntando atendimentos de
dias diferentes em um só (valor alto demais).

## Resultado (5.794 gaps analisados, banco em 2026-07-22)

| Intervalo entre mensagens | % dos gaps |
|---|---|
| ≤ 1h | 91,1% |
| ≤ 2h | 93,1% |
| ≤ 4h | 94,2% |
| **≤ 6h** | **94,4%** |
| ≤ 8h | 94,5% |
| ≤ 10h | 94,5% |
| ≤ 12h | 94,5% |
| ≤ 24h | 95,8% |

Contagem bruta por faixa de 1h entre 5h e 13h (o intervalo que importa):

| Faixa | Nº de gaps |
|---|---|
| 5-6h | 6 |
| **6-7h** | **0** |
| 7-8h | 2 |
| 8-9h | 0 |
| 9-10h | 0 |
| 10-11h | 1 |
| 11-12h | 2 |
| 12-13h | 1 |
| 13-14h | 4 (volume volta a subir) |

## Conclusão

Entre 6h e 13h praticamente não acontece nada (0-2 mensagens por faixa de 1h)
- é um vale real: quase todo cliente responde em até 1h (conversa corrida) ou
só no dia seguinte (13h+, volume volta a subir e cresce). **Qualquer valor
entre 6h e 12h separaria os atendimentos de forma idêntica** nos dados atuais.

`SESSION_GAP_HOURS = 6` cai exatamente nesse vale - não corta conversas no
meio nem junta atendimentos de dias diferentes. **Validado, não precisa
mudar.** Se o padrão de uso mudar no futuro (ex.: suporte passa a operar por
mais horas por dia, ou o gap não aparecer mais tão claro), reexecute
`python pipeline/verificar_gap_sessoes.py` para reverificar.
