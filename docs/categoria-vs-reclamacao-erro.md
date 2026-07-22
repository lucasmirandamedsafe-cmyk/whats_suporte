# Por que um atendimento "Dúvida" pode ter reclamações de erro?

No dashboard de Suporte é possível ver atendimentos com `categoria = duvida`
(ou até `elogio`) que aparecem contando mensagens em "Reclamações de erro".
Isso é **esperado, não é bug** - são dois classificadores independentes,
medindo coisas diferentes, sem nenhuma relação de dependência entre eles.

## Os dois classificadores

1. **`categoria` do atendimento** (`duvida` / `reclamacao` / `elogio` /
   `outro`): classifica o **atendimento inteiro** (a sessão), feito pela LLM
   (Groq, em `pipeline/enrich_ai.py`). Julga o tom geral da conversa como um
   todo.
2. **`is_issue` / `issue_tipo`** (reclamação de erro): classifica **mensagem a
   mensagem**, feito por um classificador local por palavra-chave
   (`pipeline/classify_suporte_local.py`). Olha só o texto de cada mensagem
   do cliente, sem nenhum conhecimento da categoria da sessão a que ela
   pertence.

Nenhum dos dois é derivado do outro - `categoria` roda sobre a sessão inteira
via LLM, `is_issue`/`issue_tipo` roda por mensagem via regex/palavra-chave.
É perfeitamente possível uma sessão "dúvida" conter uma mensagem com
`is_issue=1`, e vice-versa.

## Por que isso acontece na prática

O cliente frequentemente **descreve um sintoma técnico como parte de uma
pergunta** ("como resolvo isso?"), então o classificador de mensagem pega a
palavra-chave de problema (ex.: "não consigo", "não aparece", "lento"), mas a
LLM, lendo a conversa inteira, interpreta o tom geral como "tirando uma
dúvida" - não uma reclamação com atrito -, sobretudo quando o suporte resolveu
rápido e sem confronto.

Exemplos reais (sessões com `categoria=duvida` que têm mensagem com
`is_issue=1`):

- *"Não consigo fazer os cursos. Sistema muito lento"* → contém "não
  consigo" + "lento" → classificada como `instabilidade_plataforma`
- *"Os planos de visita não aparece para mim. Só fica os 10 primeiros"* →
  "não aparece" → `visitas_acompanhamento`
- *"Estou com problemas na hora de cadastrar um beneficiário..."* →
  `cadastro_dados`

Levantamento no banco atual: das 299 sessões com `categoria=duvida`, **99
mensagens** dentro delas foram marcadas como reclamação/erro.

## Isso é diferente do bug já corrigido

Não confundir com o bug antigo de vazamento de mensagens: antes,
`api/filters.py::apply_suporte_filters` filtrava mensagens de reclamação por
`conversation_id` + janela de datas, o que vazava mensagens de **outras
sessões do mesmo cliente** para dentro do filtro. Isso já foi corrigido -
hoje o filtro usa `session_id` exato. O comportamento descrito aqui é
diferente: mesmo com o filtro por `session_id` correto, o número de
reclamações "dentro" de uma categoria continua podendo ser não-trivial,
porque as duas classificações realmente medem coisas diferentes.

## Conclusão

Os dois indicadores respondem perguntas diferentes:

- `categoria` → "qual foi o tom geral desse atendimento?"
- reclamação de erro (`is_issue`/`issue_tipo`) → "essa mensagem específica
  descreve um problema técnico?"

Não é esperado que os dois sempre concordem, e não há necessidade de forçar
consistência entre eles - cada um serve a um propósito de análise diferente.
Se no futuro for necessário unificar (ex.: fazer a `categoria` da sessão
levar em conta se ela contém alguma mensagem `is_issue=1`), isso muda a lógica
de classificação existente e deve ser uma decisão explícita, não uma correção
de "bug".
