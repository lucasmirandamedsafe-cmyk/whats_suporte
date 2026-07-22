"use client";
import { useState } from "react";

import { BarChartCard } from "@/components/charts/BarChartCard";
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
import type { Granularidade, SuporteFiltrosState } from "@/lib/types";

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

  return (
    <div>
      <PageHeader title="Suporte WhatsApp" />

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
        />
        <SingleSelect
          label="Categoria de erro"
          value={filters.categoriaErro}
          onChange={(categoriaErro) => setFilters((f) => ({ ...f, categoriaErro }))}
          options={filtrosOut.categorias_erro}
          sentinel="Todas"
        />
        <SingleSelect
          label="Tipo de erro"
          value={filters.tipoErro}
          onChange={(tipoErro) => setFilters((f) => ({ ...f, tipoErro }))}
          options={filtrosOut.tipos_erro}
          sentinel="Todos"
        />
      </div>

      {error ? <InfoNote message={`Erro ao carregar dados: ${error}`} /> : null}
      {loading || !data ? (
        <EmptyState message="Carregando..." />
      ) : (
        <>
          <KpiRow>
            <KpiCard label="Atendimentos" value={data.kpis.total_sessoes} />
            <KpiCard label="Tempo médio de resposta" value={data.kpis.tempo_resposta_medio_min_display} />
            <KpiCard label="Pico simultâneos" value={data.kpis.pico_simultaneos} />
            <KpiCard label="% Demanda pouco clara" value={data.kpis.pct_pouco_clara_display} />
            <KpiCard label="Reclamações de erro" value={data.kpis_reclamacao.total_reclamacoes} />
            <KpiCard label="% msgs com reclamação" value={data.kpis_reclamacao.pct_reclamacoes_display} />
          </KpiRow>
          <p className="text-xs text-[#898781] mb-6">
            Pico simultâneos: maior nº de atendimentos abertos ao mesmo tempo em um único dia. Demanda pouco
            clara: heurística local (sem IA) - mensagem inicial curta/sem detalhe do problema, ou suporte
            precisou dizer que não entendeu. Reclamações de erro: classificação local por palavra-chave (sem
            IA) das mensagens do cliente - ver pipeline/classify_suporte_local.py.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <h2 className="text-lg font-semibold text-[#0b0b0b] mb-2">Volume de atendimentos por dia</h2>
              <BarChartCard data={data.volume_por_dia} xKey="dia" yKey="conversas" color={CATEGORICAL[0]} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[#0b0b0b] mb-2">Volume por hora do dia</h2>
              <BarChartCard data={data.volume_por_hora} xKey="hora" yKey="conversas" color={CATEGORICAL[0]} />
            </div>
          </div>

          <SectionHeader
            title="Atendimentos simultâneos"
            right={<GranularidadeToggle value={granularidade} onChange={setGranularidade} />}
          />
          {data.atendimentos_simultaneos[granularidade].length > 0 ? (
            <div className="mb-6">
              <BarChartCard
                data={data.atendimentos_simultaneos[granularidade]}
                xKey="periodo"
                yKey="pico_simultaneos"
                color={CATEGORICAL[3]}
              />
            </div>
          ) : (
            <div className="mb-6">
              <InfoNote message="Sem atendimentos no período selecionado." />
            </div>
          )}

          <SectionHeader title="Reclamações de erro" />
          <p className="text-sm text-[#898781] mb-4">
            Mensagens do cliente (fora do suporte) que expressam uma reclamação ou relatam um erro/problema na
            plataforma - mesma taxonomia de categoria/tipo usada em Grupos.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <h3 className="text-base font-semibold text-[#0b0b0b] mb-2">Distribuição por categoria</h3>
              {data.distribuicao_categoria_erro.length === 0 ? (
                <InfoNote message="Nenhuma reclamação no período selecionado." />
              ) : (
                <BarChartCard
                  data={data.distribuicao_categoria_erro}
                  xKey="categoria"
                  yKey="mensagens"
                  color={CATEGORICAL[1]}
                  showValueLabels
                />
              )}
            </div>
            <div>
              <h3 className="text-base font-semibold text-[#0b0b0b] mb-2">Tipo de erro</h3>
              {data.distribuicao_tipo_erro.length === 0 ? (
                <InfoNote message="Nenhuma reclamação no período selecionado." />
              ) : (
                <HorizontalBarChartCard
                  data={data.distribuicao_tipo_erro}
                  xKey="mensagens"
                  yKey="tipo"
                  color={CATEGORICAL[2]}
                  showValueLabels
                />
              )}
            </div>
          </div>

          <h3 className="text-base font-semibold text-[#0b0b0b] mb-2">Mensagens com reclamação/erro</h3>
          <div className="mb-6">
            <DataTable
              columns={[
                { key: "timestamp", header: "timestamp", render: (v) => formatDateTime(v as string) },
                { key: "conversation_id", header: "conversation_id" },
                { key: "issue_categoria", header: "issue_categoria" },
                { key: "issue_tipo", header: "issue_tipo" },
                { key: "content", header: "content" },
              ]}
              rows={data.mensagens_reclamacao}
            />
          </div>

          <h2 className="text-lg font-semibold text-[#0b0b0b] mb-2 mt-4 border-t border-[#e1e0d9] pt-4">
            Atendimentos
          </h2>
          <DataTable
            columns={[
              { key: "started_at", header: "started_at", render: (v) => formatDateTime(v as string) },
              { key: "conversation_id", header: "conversation_id" },
              { key: "categoria", header: "categoria" },
              { key: "tema", header: "tema" },
              { key: "resumo", header: "resumo" },
              {
                key: "first_response_seconds",
                header: "first_response_seconds",
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
