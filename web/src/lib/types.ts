// Espelha 1:1 o JSON devolvido por api/routers/suporte.py e api/routers/grupos.py.
// Nao ha calculo nenhum do lado do cliente - so renderizacao do que a API manda.

export type Granularidade = "dia" | "semana" | "mes";

export interface SuporteFiltrosOut {
  has_data: boolean;
  min_date: string | null;
  max_date: string | null;
  categorias: string[];
  categorias_erro: string[];
  tipos_erro: string[];
}

export interface SuporteFiltrosState {
  start?: string;
  end?: string;
  categoria?: string;
  categoriaErro?: string;
  tipoErro?: string;
}

export interface DiaConversas {
  dia: string;
  conversas: number;
}

export interface HoraConversas {
  hora: number;
  conversas: number;
}

export interface PeriodoPico {
  periodo: string;
  pico_simultaneos: number;
}

export interface CategoriaMensagens {
  categoria: string;
  mensagens: number;
}

export interface TipoMensagens {
  tipo: string;
  mensagens: number;
}

export interface MensagemReclamacao {
  timestamp: string;
  conversation_id: string;
  issue_categoria: string | null;
  issue_tipo: string | null;
  content: string;
}

export interface Atendimento {
  started_at: string;
  conversation_id: string;
  categoria: string | null;
  tema: string | null;
  resumo: string | null;
  first_response_seconds: number | null;
}

export interface SuporteDashboardOut {
  kpis: {
    total_sessoes: number;
    tempo_resposta_medio_min: number | null;
    tempo_resposta_medio_min_display: string;
    tempo_resposta_mediano_min: number | null;
    pct_reclamacao: number;
    pct_duvida: number;
    pico_simultaneos: number;
    pct_pouco_clara: number;
    pct_pouco_clara_display: string;
  };
  kpis_reclamacao: {
    total_mensagens_cliente: number;
    total_reclamacoes: number;
    pct_reclamacoes: number;
    pct_reclamacoes_display: string;
  };
  volume_por_dia: DiaConversas[];
  volume_por_hora: HoraConversas[];
  atendimentos_simultaneos: Record<Granularidade, PeriodoPico[]>;
  distribuicao_categoria_erro: CategoriaMensagens[];
  distribuicao_tipo_erro: TipoMensagens[];
  mensagens_reclamacao: MensagemReclamacao[];
  atendimentos: Atendimento[];
}

export interface GruposFiltrosOut {
  has_data: boolean;
  areas: string[];
  min_date: string | null;
  max_date: string | null;
}

export interface GruposFiltrosState {
  areas?: string[];
  start?: string;
  end?: string;
}

export interface AreaProblemas {
  area: string;
  problemas: number;
}

export interface CategoriaIncidentes {
  categoria: string;
  incidentes: number;
}

export interface TipoIncidentes {
  tipo: string;
  incidentes: number;
}

export interface PeriodoProblemas {
  periodo: string;
  problemas: number;
}

export interface GrupoMensagem {
  timestamp: string;
  area: string;
  conversation_id: string;
  sender: string;
  issue_categoria: string | null;
  issue_tipo: string | null;
  issue_tema: string | null;
  content: string;
  is_issue: number | null;
}

export interface GruposDashboardOut {
  is_empty: boolean;
  kpis: {
    total_mensagens: number;
    total_problemas: number;
    pct_problemas: number;
    pct_problemas_display: string;
    pct_erro_app: number;
    pct_erro_app_display: string;
  };
  volume_por_area: AreaProblemas[];
  distribuicao_categoria: CategoriaIncidentes[];
  distribuicao_tipo_erro: TipoIncidentes[];
  problemas_por_periodo: Record<Granularidade, PeriodoProblemas[]>;
  mensagens: GrupoMensagem[];
}
