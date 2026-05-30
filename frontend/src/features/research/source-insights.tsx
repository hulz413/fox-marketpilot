"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { ExternalLink, RefreshCcw, SearchCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import {
  fetchOpportunitySources,
  fetchTaskSources,
  type ResearchSource,
  type ResearchSourceType,
  type SourceSupportLevel,
} from "./api";

const sourceTypeLabels: Record<ResearchSourceType, string> = {
  demand: "需求线索",
  supply: "货源线索",
  competitor: "竞品线索",
  risk: "风险线索",
  general: "背景线索",
};

const supportLabels: Record<SourceSupportLevel, string> = {
  weak: "弱相关",
  medium: "中相关",
  strong: "较相关",
};

export function TaskSourceInsights({ taskUuid }: { taskUuid: string }) {
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ["task-sources", taskUuid],
    queryFn: () => fetchTaskSources(taskUuid),
  });

  return (
    <SourceInsights
      description="这些内容是公开来源线索和初步参考，用于帮助判断方向，仍需要小批量验证。"
      error={error}
      isLoading={isLoading}
      onRetry={() => void refetch()}
      sources={data}
      title="来源线索"
    />
  );
}

export function OpportunitySourceInsights({
  opportunityUuid,
}: {
  opportunityUuid: string;
}) {
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ["opportunity-sources", opportunityUuid],
    queryFn: () => fetchOpportunitySources(opportunityUuid),
  });

  return (
    <SourceInsights
      description="与这个商机关联的公开线索，只表示可能支持相关判断，不代表商机已经被证明成立。"
      error={error}
      isLoading={isLoading}
      onRetry={() => void refetch()}
      sources={data}
      title="关联来源"
    />
  );
}

function SourceInsights({
  title,
  description,
  sources,
  isLoading,
  error,
  onRetry,
}: {
  title: string;
  description: string;
  sources?: ResearchSource[];
  isLoading: boolean;
  error: unknown;
  onRetry: () => void;
}) {
  const groupedSources = useMemo(() => groupSources(sources ?? []), [sources]);
  const sourceCount = sources?.length ?? 0;

  return (
    <Card id="sources" className="rounded-lg">
      <CardHeader className="gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <SearchCheck className="size-5 text-primary" aria-hidden="true" />
              <CardTitle>{title}</CardTitle>
            </div>
            <CardDescription className="mt-2 leading-6">{description}</CardDescription>
          </div>
          <Badge variant="secondary">{sourceCount} 条公开线索</Badge>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4">
        {isLoading ? (
          <div className="h-24 rounded-md border bg-muted/40" />
        ) : error ? (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-dashed p-4">
            <p className="text-sm leading-6 text-muted-foreground">
              来源暂不可用，基础商机结果仍可作为待验证草案阅读。
            </p>
            <Button type="button" variant="outline" size="sm" onClick={onRetry}>
              <RefreshCcw data-icon="inline-start" />
              重新加载
            </Button>
          </div>
        ) : sourceCount === 0 ? (
          <div className="rounded-lg border border-dashed p-4 text-sm leading-6 text-muted-foreground">
            暂无可展示来源线索。当前结果仍是待验证基础推荐，建议后续结合公开资料和小批量试单继续确认。
          </div>
        ) : (
          groupedSources.map(([sourceType, items]) => (
            <section key={sourceType} className="grid gap-3">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold">
                  {sourceTypeLabels[sourceType]}
                </h2>
                <Badge variant="outline">{items.length} 条</Badge>
              </div>
              <div className="grid gap-3">
                {items.map((source) => (
                  <SourceItem key={source.uuid} source={source} />
                ))}
              </div>
            </section>
          ))
        )}
      </CardContent>
    </Card>
  );
}

function SourceItem({ source }: { source: ResearchSource }) {
  return (
    <article className="rounded-lg border bg-background p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <a
            href={source.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 font-medium text-primary hover:underline"
          >
            <span className="break-words">{source.title}</span>
            <ExternalLink className="size-4 shrink-0" aria-hidden="true" />
          </a>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {source.summary || source.snippet}
          </p>
        </div>
        <Badge variant="outline">{supportLabels[source.support_level]}</Badge>
      </div>
      <p className="mt-3 text-xs leading-5 text-muted-foreground">
        关联判断：{source.linked_claim || "可作为初步参考的公开线索。"}
      </p>
    </article>
  );
}

function groupSources(sources: ResearchSource[]) {
  const grouped = new Map<ResearchSourceType, ResearchSource[]>();

  for (const source of sources) {
    const current = grouped.get(source.source_type) ?? [];
    current.push(source);
    grouped.set(source.source_type, current);
  }

  return Array.from(grouped.entries());
}
