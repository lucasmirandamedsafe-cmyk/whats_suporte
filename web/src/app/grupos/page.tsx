"use client";
import { useState } from "react";

import { BarChartCard } from "@/components/charts/BarChartCard";
import { HorizontalBarChartCard } from "@/components/charts/HorizontalBarChartCard";
import { CATEGORICAL } from "@/components/charts/chartTheme";
import { Checkbox } from "@/components/filters/Checkbox";
import { DateRangePicker } from "@/components/filters/DateRangePicker";
import { GranularidadeToggle } from "@/components/filters/GranularidadeToggle";
import { MultiSelect } from "@/components/filters/MultiSelect";
import { KpiCard } from "@/components/kpi/KpiCard";
import { KpiRow } from "@/components/kpi/KpiRow";
import { EmptyState } from "@/components/layout/EmptyState";
import { InfoNote } from "@/components/layout/InfoNote";
import { PageHeader } from "@/components/layout/PageHeader";
import { SectionHeader } from "@/components/layout/SectionHeader";
import { DataTable } from "@/components/tables/DataTable";
import { useGruposDashboard } from "@/hooks/useGruposDashboard";
import { useGruposFiltros } from "@/hooks/useGruposFiltros";
import { formatDateTime } from "@/lib/formatters";
import type { Granularidade, GruposFiltrosState } from "@/lib/types";

export default function GruposPage() {
  const { data: filtrosOut, loading: loadingFiltros } = useGruposFiltros();
  const [filters, setFilters] = useState<GruposFiltrosState>({});
  const [granularidade, setGranularidade] = useState<Granularidade>("dia");
  const [apenasProblemas, setApenasProblemas] = useState(true);

  // Antes do usuario mexer no filtro de area, trata como "todas selecionadas"
  // (equivalente a nao filtrar - o backend ja interpreta areas=[] como sem filtro).
  const areasEfetivas = filters.areas ?? filtrosOut?.areas ?? [];
  const { data, loading, error } = useGruposDashboard({ ...filters, areas: areasEfetivas });

  if (loadingFiltros) {
    return <EmptyState message="Carregando..." />;
  }

  if (!filtrosOut?.has_data) {
    return (
      <EmptyState message="Nenhuma mensagem de grupo encontrada. Rode `python pipeline/parse_groups.py` e `python pipeline/classify_issues.py` antes de abrir esta página." />
    );
  }

  const mensagensExibidas = data ? (apenasProblemas ? data.mensagens.filter((m) => m.is_issue === 1) : data.mensagens) : [];

  return (
    <div>
      <PageHeader
        title="Grupos - Reclamações e Erros na Plataforma"
        caption="Piauí Primeira Infância · mensagens de grupos (saúde, educação, assistência) classificadas quanto a reclamação/erro"
      />

      <div className="flex flex-wrap gap-4 mb-6 rounded-lg border border-[#e1e0d9] bg-white p-4">
        <MultiSelect
          label="Área"
          options={filtrosOut.areas}
          values={areasEfetivas}
          onChange={(areas) => setFilters((f) => ({ ...f, areas }))}
        />
        <DateRangePicker
          start={filters.start}
          end={filters.end}
          minDate={filtrosOut.min_date}
          maxDate={filtrosOut.max_date}
          onChange={(start, end) => setFilters((f) => ({ ...f, start, end }))}
        />
        <Checkbox
          label="Mostrar só mensagens com problema na tabela"
          checked={apenasProblemas}
          onChange={setApenasProblemas}
        />
      </div>

      {error ? <InfoNote message={`Erro ao carregar dados: ${error}`} /> : null}
      {loading || !data ? (
        <EmptyState message="Carregando..." />
      ) : data.is_empty ? (
        <InfoNote message="Nenhuma mensagem no filtro selecionado." />
      ) : (
        <>
          <KpiRow>
            <KpiCard label="Mensagens analisadas" value={data.kpis.total_mensagens} />
            <KpiCard label="Reclamações/erros identificados" value={data.kpis.total_problemas} />
            <KpiCard label="% do total" value={data.kpis.pct_problemas_display} />
            <KpiCard label="% erro de app" value={data.kpis.pct_erro_app_display} />
          </KpiRow>
          <p className="text-xs text-[#898781] mb-6">
            Reclamações/erros contam incidentes únicos (mensagens da mesma conversa, mesmo tipo e mesmo dia são
            agrupadas em 1), não cada mensagem individual.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <h2 className="text-lg font-semibold text-[#0b0b0b] mb-2">Problemas por área</h2>
              <BarChartCard data={data.volume_por_area} xKey="area" yKey="problemas" color={CATEGORICAL[0]} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[#0b0b0b] mb-2">Distribuição por categoria</h2>
              <BarChartCard
                data={data.distribuicao_categoria}
                xKey="categoria"
                yKey="incidentes"
                color={CATEGORICAL[1]}
                showValueLabels
              />
            </div>
          </div>

          <h2 className="text-lg font-semibold text-[#0b0b0b] mb-2">Tipo de erro</h2>
          <div className="mb-6">
            {data.distribuicao_tipo_erro.length === 0 ? (
              <InfoNote message="Tipo de erro ainda nao classificado. Rode `python pipeline/classify_tipo_erro.py`." />
            ) : (
              <HorizontalBarChartCard
                data={data.distribuicao_tipo_erro}
                xKey="incidentes"
                yKey="tipo"
                color={CATEGORICAL[2]}
                showValueLabels
              />
            )}
          </div>

          <SectionHeader
            title="Problemas ao longo do tempo"
            right={<GranularidadeToggle value={granularidade} onChange={setGranularidade} />}
          />
          <div className="mb-6">
            {data.problemas_por_periodo[granularidade].length > 0 ? (
              <BarChartCard
                data={data.problemas_por_periodo[granularidade]}
                xKey="periodo"
                yKey="problemas"
                color={CATEGORICAL[5]}
              />
            ) : (
              <InfoNote message="Nenhum problema no período selecionado." />
            )}
          </div>

          <h2 className="text-lg font-semibold text-[#0b0b0b] mb-2">Mensagens</h2>
          <DataTable
            columns={[
              { key: "timestamp", header: "timestamp", render: (v) => formatDateTime(v as string) },
              { key: "area", header: "area" },
              { key: "conversation_id", header: "conversation_id" },
              { key: "sender", header: "sender" },
              { key: "issue_categoria", header: "issue_categoria" },
              { key: "issue_tipo", header: "issue_tipo" },
              { key: "issue_tema", header: "issue_tema" },
              { key: "content", header: "content" },
            ]}
            rows={mensagensExibidas}
          />
        </>
      )}
    </div>
  );
}
