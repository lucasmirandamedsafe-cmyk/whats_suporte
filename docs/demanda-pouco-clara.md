# Como é calculada a "% Demanda pouco clara"

Métrica exibida no dashboard (página Suporte WhatsApp). Vem de
`pipeline/metrics.py::demandas_pouco_claras()` - uma heurística **local, sem
IA/LLM**, que marca um atendimento como `demanda_pouco_clara = True` se
**qualquer um** de dois sinais aparecer.

## 1. Mensagem inicial "vaga"

Junta **todas as mensagens do cliente antes da 1ª resposta do suporte**
naquela sessão em um texto só - não olha só a primeira mensagem isolada,
porque "Bom dia" antes de explicar o problema é um padrão normal de conversa,
não sinal de demanda confusa.

Esse texto junto é considerado **vago** se:

- **não** contém nenhuma destas palavras-chave de problema (radicais, então
  "cadastr" pega "cadastro"/"cadastrar" etc.):
  `senha, erro, cpf, cadastr, cai, trava, não consig[o], não aparece, não
  abre, não funciona, invalid[o], exclu[ir], vincul[ar], sumi[u],
  bloque[ado], não entra, não carrega, não salva, bug`
- **e** tem **menos de 5 palavras** (números como CPF não contam como
  palavra).

Ou seja: se o cliente já usa uma palavra de problema, a mensagem NUNCA é
considerada vaga, mesmo curta - "não abre" já basta. Só é vaga quando é curta
**e** sem nenhum sinal de problema (ex.: só "oi bom dia", ou mensagem vazia).

## 2. Suporte pediu esclarecimento

Depois da 1ª resposta, se em qualquer mensagem do **suporte** aparecer uma
frase do tipo "não entendi", "pode explicar melhor", "não ficou claro", "em
que parte exatamente", "o que você quer dizer" (regex, case-insensitive) -
isso conta como sinal de que a demanda não veio clara, independente do texto
do cliente.

## Fórmula final

```
demanda_pouco_clara = mensagem_inicial_vaga OR pelo_menos_1_pedido_de_esclarecimento
```

```
% Demanda pouco clara = (nº de atendimentos com demanda_pouco_clara=True no filtro atual)
                         / (total de atendimentos no filtro atual) × 100
```

Calculado sobre as sessões já filtradas por período/categoria do atendimento
(mesmo recorte usado nos outros KPIs da página) - mas, assim como o "% msgs
com reclamação", **não** é afetado pelos filtros de "Categoria de erro"/"Tipo
de erro", que só mexem na seção "Reclamações de erro" (ver
`api/filters.py::apply_suporte_filters`).

## Ressalva

Marcar um atendimento como "pouco clara" não significa necessariamente que a
demanda foi ruim - só que faltou detalhe de cara. É uma heurística de texto,
não uma classificação semântica: vale conferir manualmente os casos
limítrofes antes de tirar conclusões fortes a partir desse número.
