"use client";
import { useState } from "react";

import { BarChartCard } from "@/components/charts/BarChartCard";
import { BarLineChartCard } from "@/components/charts/BarLineChartCard";
import { HeatmapCard } from "@/components/charts/HeatmapCard";
import { HorizontalBarChartCard } from "@/components/charts/HorizontalBarChartCard";
import { CATEGORICAL } from "@/components/charts/chartTheme";
import { DateRangePicker } from "@/components/filters/DateRangePicker";
import { GranularidadeToggle } from "@/components/filters/GranularidadeToggle";
import { SingleSelect } from "@/components/filters/SingleSelect";
import { KpiCard } from "@/components/kpi/KpiCard";
import { KpiRow } from "@/components/kpi/KpiRow";
import { EmptyState } from "@/components/layout/EmptyState";
import { InfoNote } from "@/components/layout/InfoNote";
import { PageHeader } from "@/components/layout/PageHeader";
import { SectionHeader } from "@/components/layout/SectionHeader";
import { DataTable } from "@/components/tables/DataTable";
import { useSuporteDashboard } from "@/hooks/useSuporteDashboard";
import { useSuporteFiltros } from "@/hooks/useSuporteFiltros";
import { formatDateTime, formatSeconds } from "@/lib/formatters";
import { CATEGORIA_ATENDIMENTO_LABELS, TIPO_ERRO_LABELS, translateLabel } from "@/lib/labels";
import type { Granularidade, PeriodoConversas, PeriodoMensagens, SuporteFiltrosState } from "@/lib/types";

// Mesma ordem canonica de pipeline/metrics.py::volume_por_dia_semana_hora
// (_DIAS_SEMANA_PT / _FAIXAS_HORA_ORDEM) - o backend sempre devolve as 7x8
// combinacoes, entao so precisamos da ordem de exibicao aqui.
const DIAS_SEMANA_ORDEM = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"];
const FAIXAS_HORA_ORDEM = [
  "Fora do horário",
  "06h–08h",
  "08h–10h",
  "10h–12h",
  "12h–14h",
  "14h–16h",
  "16h–18h",
];

interface VolumeCombinado {
  periodo: string;
  conversas: number;
  mensagens: number;
}

// Junta as duas series (atendimentos e mensagens) por periodo - vem de duas
// queries separadas no backend (sessoes x mensagens), entao mesclamos aqui
// so pra desenhar no mesmo grafico, sem nenhum calculo alem do merge.
function mesclarVolume(atendimentos: PeriodoConversas[], mensagens: PeriodoMensagens[]): VolumeCombinado[] {
  const porPeriodo = new Map<string, VolumeCombinado>();
  for (const r of atendimentos) {
    porPeriodo.set(r.periodo, { periodo: r.periodo, conversas: r.conversas, mensagens: 0 });
  }
  for (const r of mensagens) {
    const existente = porPeriodo.get(r.periodo);
    if (existente) existente.mensagens = r.mensagens;
    else porPeriodo.set(r.periodo, { periodo: r.periodo, conversas: 0, mensagens: r.mensagens });
  }
  return Array.from(porPeriodo.values()).sort((a, b) => a.periodo.localeCompare(b.periodo));
}

export default function SuportePage() {
  const { data: filtrosOut, loading: loadingFiltros } = useSuporteFiltros();
  const [filters, setFilters] = useState<SuporteFiltrosState>({});
  const [granularidade, setGranularidade] = useState<Granularidade>("dia");
  const { data, loading, error } = useSuporteDashboard(filters);

  if (loadingFiltros) {
    return <EmptyState message="Carregando..." />;
  }

  if (!filtrosOut?.has_data) {
    return (
      <EmptyState message="Nenhum dado encontrado. Rode `python pipeline/sync_data.py` antes de abrir o dashboard." />
    );
  }

  const tipoErroChartData = data?.distribuicao_tipo_erro.map((r) => ({
    tipo: translateLabel(r.tipo, TIPO_ERRO_LABELS),
    mensagens: r.mensagens,
  }));

  const volumeCombinado = data
    ? mesclarVolume(data.volume_atendimentos[granularidade], data.volume_mensagens[granularidade])
    : [];

  const paramsRelatorio = new URLSearchParams();
  if (filters.start) paramsRelatorio.set("start", filters.start);
  if (filters.end) paramsRelatorio.set("end", filters.end);
  if (filters.categoria) paramsRelatorio.set("categoria", filters.categoria);
  if (filters.tipoErro) paramsRelatorio.set("tipo_erro", filters.tipoErro);
  const hrefRelatorio = `/api/suporte/relatorio-pdf?${paramsRelatorio.toString()}`;

  return (
    <div>
      <div className="flex items-start justify-between gap-4">
        <PageHeader title="Suporte WhatsApp" />
        {data ? (
          <a
            href={hrefRelatorio}
            className="shrink-0 rounded-md border border-[#e1e0d9] bg-white px-4 py-2 text-sm font-medium text-[#0b0b0b] hover:bg-[#f5f4f0]"
          >
            Exportar PDF
          </a>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-4 mb-6 rounded-lg border border-[#e1e0d9] bg-white p-4">
        <DateRangePicker
          start={filters.start}
          end={filters.end}
          minDate={filtrosOut.min_date}
          maxDate={filtrosOut.max_date}
          onChange={(start, end) => setFilters((f) => ({ ...f, start, end }))}
        />
        <SingleSelect
          label="Categoria do atendimento"
          value={filters.categoria}
          onChange={(categoria) => setFilters((f) => ({ ...f, categoria }))}
          options={filtrosOut.categorias}
          sentinel="Todas"
          labels={CATEGORIA_ATENDIMENTO_LABELS}
        />
        <SingleSelect
          label="Tipo de erro"
          value={filters.tipoErro}
          onChange={(tipoErro) => setFilters((f) => ({ ...f, tipoErro }))}
          options={filtrosOut.tipos_erro}
          sentinel="Todos"
          labels={TIPO_ERRO_LABELS}
        />
      </div>

      {error ? <InfoNote message={`Erro ao carregar dados: ${error}`} /> : null}
      {loading || !data ? (
        <EmptyState message="Carregando..." />
      ) : (
        <>
          <KpiRow>
            <KpiCard
              label="Conversas na base"
              value={data.kpis.total_conversas_display}
              help="Quantidade de conversas (números/contatos) distintos por trás dos atendimentos do período filtrado. Uma mesma conversa pode gerar mais de 1 atendimento."
            />
            <KpiCard
              label="Atendimentos"
              value={data.kpis.total_sessoes}
              help="Total de sessões de atendimento no período filtrado. Cada sessão agrupa as mensagens de uma mesma conversa com até 6h de intervalo entre elas."
            />
            <KpiCard
              label="Média de atendimentos por hora"
              value={data.kpis.media_por_hora_display}
              help="Desconsidera fins de semana. Total de atendimentos em dias úteis dividido pelas horas de expediente disponíveis (8h/dia) somadas só nos dias úteis que tiveram pelo menos 1 atendimento."
            />
            <KpiCard
              label="Média de mensagens por hora"
              value={data.kpis.media_msgs_por_hora_display}
              help="Mesma regra da média de atendimentos por hora, só que contando mensagens trocadas (cliente + suporte). Desconsidera fins de semana; divide pelas horas de expediente (8h/dia) somadas só nos dias úteis com pelo menos 1 mensagem."
            />
            <KpiCard
              label="Pico de atendimentos simultâneos"
              value={data.kpis.pico_simultaneos}
              help="Maior número de atendimentos abertos ao mesmo tempo em um único instante, dentro do período filtrado."
            />
            <KpiCard
              label="Tempo médio de resposta"
              value={data.kpis.tempo_resposta_medio_min_display}
              help="Tempo médio entre a 1ª mensagem do cliente e a 1ª resposta do suporte, por atendimento."
            />
            <KpiCard
              label="% Demanda pouco clara"
              value={data.kpis.pct_pouco_clara_display}
              help="Heurística local (sem IA): mensagem inicial do cliente curta e sem palavra-chave de problema, ou o suporte precisou dizer que não entendeu. Ver docs/demanda-pouco-clara.md."
            />
            <KpiCard
              label="Reclamações de erro"
              value={data.kpis_reclamacao.total_reclamacoes}
              help="Mensagens do cliente classificadas localmente (por palavra-chave, sem IA) como reclamação ou relato de erro - ver pipeline/classify_suporte_local.py."
            />
          </KpiRow>

          <div className="mb-6">
            <InfoNote message={data.aviso_amostra} />
          </div>

          <SectionHeader
            title="Volume de atendimentos"
            right={<GranularidadeToggle value={granularidade} onChange={setGranularidade} />}
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <h3 className="text-base font-semibold text-[#0b0b0b] mb-2">Volume de atendimentos</h3>
              {volumeCombinado.length > 0 ? (
                <BarLineChartCard
                  data={volumeCombinado}
                  xKey="periodo"
                  barKey="conversas"
                  lineKey="mensagens"
                  barColor={CATEGORICAL[0]}
                  lineColor={CATEGORICAL[5]}
                  barLabel="Atendimentos"
                  lineLabel="Mensagens trocadas"
                />
              ) : (
                <InfoNote message="Sem atendimentos no período selecionado." />
              )}
              <p className="text-xs text-[#898781] mt-2">
                Barra: atendimentos iniciados em cada período. Linha: total de mensagens trocadas (cliente +
                suporte) nesses atendimentos, conforme a granularidade escolhida acima.
              </p>
            </div>
            <div>
              <h3 className="text-base font-semibold text-[#0b0b0b] mb-2">Atendimentos simultâneos</h3>
              {data.atendimentos_simultaneos[granularidade].length > 0 ? (
                <BarChartCard
                  data={data.atendimentos_simultaneos[granularidade]}
                  xKey="periodo"
                  yKey="pico_simultaneos"
                  color={CATEGORICAL[3]}
                />
              ) : (
                <InfoNote message="Sem atendimentos no período selecionado." />
              )}
              <p className="text-xs text-[#898781] mt-2">
                Pico de atendimentos abertos ao mesmo tempo dentro de cada período.
              </p>
            </div>
          </div>

          <div className="mb-6">
            <h2 className="text-lg font-semibold text-[#0b0b0b] mb-2">Volume por dia da semana e horário</h2>
            <HeatmapCard
              data={data.volume_por_dia_semana_hora}
              rowKey="dia_semana"
              colKey="faixa_hora"
              valueKey="conversas"
              rows={DIAS_SEMANA_ORDEM}
              cols={FAIXAS_HORA_ORDEM}
              color={CATEGORICAL[0]}
            />
            <p className="text-xs text-[#898781] mt-2">
              % de atendimentos por dia da semana e faixa de horário. 06h–18h agrupado de 2 em 2 horas; fora
              desse intervalo (18h–06h) tudo em uma faixa só.
            </p>
          </div>

          <SectionHeader title="Reclamações de erro" />
          <p className="text-sm text-[#898781] mb-4">
            Mensagens do cliente (fora do suporte) que expressam uma reclamação ou relatam um erro/problema na
            plataforma - mesma taxonomia de categoria/tipo usada em Grupos.
          </p>

          <div className="mb-6">
            <h3 className="text-base font-semibold text-[#0b0b0b] mb-2">Tipo de erro</h3>
            {!tipoErroChartData || tipoErroChartData.length === 0 ? (
              <InfoNote message="Nenhuma reclamação no período selecionado." />
            ) : (
              <HorizontalBarChartCard
                data={tipoErroChartData}
                xKey="mensagens"
                yKey="tipo"
                color={CATEGORICAL[2]}
                showValueLabels
              />
            )}
            <p className="text-xs text-[#898781] mt-2">
              Quantas mensagens de reclamação foram classificadas em cada tipo de problema (classificação local
              por palavra-chave, sem IA).
            </p>
          </div>

          <h3 className="text-base font-semibold text-[#0b0b0b] mb-2">Mensagens com reclamação/erro</h3>
          <div className="mb-6">
            <DataTable
              columns={[
                { key: "timestamp", header: "Data/hora", render: (v) => formatDateTime(v as string) },
                { key: "conversation_id", header: "Conversa" },
                {
                  key: "issue_tipo",
                  header: "Tipo de erro",
                  render: (v) => translateLabel(v as string | null, TIPO_ERRO_LABELS),
                },
                { key: "content", header: "Mensagem" },
              ]}
              rows={data.mensagens_reclamacao}
            />
          </div>

          <h2 className="text-lg font-semibold text-[#0b0b0b] mb-2 mt-4 border-t border-[#e1e0d9] pt-4">
            Atendimentos
          </h2>
          <DataTable
            columns={[
              { key: "started_at", header: "Início", render: (v) => formatDateTime(v as string) },
              { key: "conversation_id", header: "Conversa" },
              { key: "tema", header: "Tema" },
              {
                key: "first_response_seconds",
                header: "Tempo de resposta",
                render: (v) => formatSeconds(v as number | null),
              },
            ]}
            rows={data.atendimentos}
          />
        </>
      )}
    </div>
  );
}
