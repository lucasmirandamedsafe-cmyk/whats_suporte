// Traducao dos valores "enum" (snake_case) vindos do backend para rotulos
// legiveis em portugues - so apresentacao, o VALOR usado em filtros/API
// continua sendo o original (ver uso de `value`/`option` vs `label` nos
// componentes de filtro).

export const CATEGORIA_ATENDIMENTO_LABELS: Record<string, string> = {
  duvida: "Dúvida",
  reclamacao: "Reclamação",
  elogio: "Elogio",
  outro: "Outro",
};

export const TIPO_ERRO_LABELS: Record<string, string> = {
  acesso_login: "Acesso e login",
  cadastro_dados: "Cadastro de dados",
  visitas_acompanhamento: "Visitas e acompanhamento",
  cursos_certificados: "Cursos e certificados",
  vinculos_aprovacoes: "Vínculos e aprovações",
  instabilidade_plataforma: "Instabilidade da plataforma",
  outro: "Outro",
};

export const CATEGORIA_ERRO_LABELS: Record<string, string> = {
  erro_app: "Erro no aplicativo",
  processo_publico: "Processo administrativo",
  outro: "Outro",
};

export const AREA_LABELS: Record<string, string> = {
  saude: "Saúde",
  educacao: "Educação",
  assistencia: "Assistência",
};

export const SENTIMENTO_LABELS: Record<string, string> = {
  positivo: "Positivo",
  neutro: "Neutro",
  negativo: "Negativo",
};

/** Traduz um valor via dicionario; se nao encontrar, devolve o valor original. */
export function translateLabel(value: string | null | undefined, dict: Record<string, string>): string {
  if (value === null || value === undefined) return "—";
  return dict[value] ?? value;
}
