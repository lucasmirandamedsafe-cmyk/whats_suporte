# Contexto: Piauí Primeira Infância

Base de referência (extraída da Revista Piauí sobre o programa) para classificar
reclamações/temas encontrados nas conversas de grupo em `raw/saude`, `raw/educacao`
e `raw/assistencia`.

## O que é

App/plataforma do Governo do Estado do Piauí para acompanhamento do desenvolvimento
infantil na primeira infância (0 a 6 anos), alinhado ao padrão internacional
**Nurturing Care** (OMS, Banco Mundial, UNICEF). Conecta famílias, profissionais de
saúde/educação e gestão pública em torno do acompanhamento de gestantes e crianças.

Serve a três frentes que espelham as pastas de grupos:

- **Saúde** — cartão vacinal, gestantes e crianças de alto risco, curvas de
  crescimento, caderneta digital da gestante/criança, exames e campanhas.
- **Educação** — indicadores de educação infantil, acesso a recursos educacionais.
- **Assistência (social)** — indicadores de assistência social, redução de pobreza,
  insegurança alimentar, articulação entre Estado/Município/Terceiro Setor.

## Os 6 eixos e 40 indicadores (padrão Nurturing Care)

1. Demografia
2. Saúde
3. Nutrição
4. Parentalidade
5. Segurança e Proteção Infantil
6. Educação Infantil

Toda reclamação/tema tende a cair em algum desses eixos — útil como taxonomia
mais granular que só "saude/educacao/assistencia" se precisar detalhar depois.

## Funcionalidades do app (onde reclamações tendem a se originar)

- Registro/calendário de vacinação digital.
- Caderneta digital da gestante e da criança.
- Ferramentas de monitoramento de crescimento (curvas em tempo real).
- Notificações automáticas/manuais (vacina, exames, atendimentos, campanhas).
- Canal de comunicação entre famílias, profissionais de saúde e educadores.
- Acompanhamento de gestantes de alto risco (rede Alyne).
- Identificação precoce de atrasos no desenvolvimento e de risco (vacinação
  incompleta, triagem neonatal em atraso, consultas com especialistas).

## Quem está por trás

Governo do Estado do Piauí, com parceria/apoio institucional contínuo — os grupos
de WhatsApp scrapeados provavelmente reúnem gestores públicos, profissionais de
saúde/educação/assistência social e equipe do programa, não clientes finais avulsos
(diferente do fluxo de `raw/suporte`, que é atendimento 1:1).

## Como usar isso na análise

Ao classificar mensagens/reclamações dos grupos `saude`, `educacao`, `assistencia`:

- Mapear o tema da reclamação para a pasta (saúde/educação/assistência) e,
  se útil, para o eixo Nurturing Care correspondente.
- Reclamações sobre o **app** em si (bugs, notificação, caderneta digital,
  cadastro) são transversais aos 3 eixos — considerar uma categoria própria
  "app/plataforma" em vez de forçar em uma área.
- Reclamações sobre **processo/política pública** (falta de vacina, atraso de
  atendimento, articulação entre órgãos) tendem a ser assistência/saúde.

Fonte: Revista Piauí Primeira Infância (material institucional, fev/2025).
