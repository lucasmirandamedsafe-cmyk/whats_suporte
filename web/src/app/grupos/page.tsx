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
import { AREA_LABELS, CATEGORIA_ERRO_LABELS, TIPO_ERRO_LABELS, translateLabel } from "@/lib/labels";
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

  const volumePorAreaChartData = data?.volume_por_area.map((r) => ({
    area: translateLabel(r.area, AREA_LABELS),
    problemas: r.problemas,
  }));
  const distribuicaoCategoriaChartData = data?.distribuicao_categoria.map((r) => ({
    categoria: translateLabel(r.categoria, CATEGORIA_ERRO_LABELS),
    incidentes: r.incidentes,
  }));
  const tipoErroChartData = data?.distribuicao_tipo_erro.map((r) => ({
    tipo: translateLabel(r.tipo, TIPO_ERRO_LABELS),
    incidentes: r.incidentes,
  }));

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
          labels={AREA_LABELS}
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
            <KpiCard
              label="Mensagens analisadas"
              value={data.kpis.total_mensagens}
              help="Total de mensagens de grupo (sem contar mídia) no filtro de área/período selecionado."
            />
            <KpiCard
              label="Reclamações/erros identificados"
              value={data.kpis.total_problemas}
              help="Incidentes únicos: mensagens da mesma conversa, mesmo tipo de erro e mesmo dia são agrupadas em 1, para não contar cada resposta da thread como um problema novo."
            />
            <KpiCard
              label="% do total"
              value={data.kpis.pct_problemas_display}
              help="Incidentes únicos dividido pelo total de mensagens analisadas."
            />
            <KpiCard
              label="% erro de app"
              value={data.kpis.pct_erro_app_display}
              help="Proporção de incidentes classificados como erro técnico do aplicativo (em vez de processo administrativo)."
            />
          </KpiRow>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <h2 className="text-lg font-semibold text-[#0b0b0b] mb-2">Problemas por área</h2>
              <BarChartCard data={volumePorAreaChartData ?? []} xKey="area" yKey="problemas" color={CATEGORICAL[0]} />
              <p className="text-xs text-[#898781] mt-2">
                Quantos incidentes únicos foram identificados em cada área.
              </p>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[#0b0b0b] mb-2">Distribuição por categoria</h2>
              <BarChartCard
                data={distribuicaoCategoriaChartData ?? []}
                xKey="categoria"
                yKey="incidentes"
                color={CATEGORICAL[1]}
                showValueLabels
              />
              <p className="text-xs text-[#898781] mt-2">
                Incidentes por categoria: erro no aplicativo vs. processo administrativo.
              </p>
            </div>
          </div>

          <h2 className="text-lg font-semibold text-[#0b0b0b] mb-2">Tipo de erro</h2>
          <div className="mb-6">
            {!tipoErroChartData || tipoErroChartData.length === 0 ? (
              <InfoNote message="Tipo de erro ainda nao classificado. Rode `python pipeline/classify_tipo_erro.py`." />
            ) : (
              <HorizontalBarChartCard
                data={tipoErroChartData}
                xKey="incidentes"
                yKey="tipo"
                color={CATEGORICAL[2]}
                showValueLabels
              />
            )}
            <p className="text-xs text-[#898781] mt-2">Incidentes classificados por tipo específico de problema.</p>
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
            <p className="text-xs text-[#898781] mt-2">
              Quantidade de incidentes por período, conforme a granularidade escolhida acima.
            </p>
          </div>

          <h2 className="text-lg font-semibold text-[#0b0b0b] mb-2">Mensagens</h2>
          <DataTable
            columns={[
              { key: "timestamp", header: "Data/hora", render: (v) => formatDateTime(v as string) },
              { key: "area", header: "Área", render: (v) => translateLabel(v as string | null, AREA_LABELS) },
              { key: "conversation_id", header: "Conversa" },
              { key: "sender", header: "Remetente" },
              {
                key: "issue_categoria",
                header: "Categoria de erro",
                render: (v) => translateLabel(v as string | null, CATEGORIA_ERRO_LABELS),
              },
              {
                key: "issue_tipo",
                header: "Tipo de erro",
                render: (v) => translateLabel(v as string | null, TIPO_ERRO_LABELS),
              },
              { key: "issue_tema", header: "Tema" },
              { key: "content", header: "Mensagem" },
            ]}
            rows={mensagensExibidas}
          />
        </>
      )}
    </div>
  );
}
