"use client";

import { useMemo, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowRight, ExternalLink, RefreshCcw, SearchCheck } from "lucide-react";

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
  fetchOpportunityCompetitorReferences,
  fetchTaskCompetitorReferences,
  type CompetitorReferenceSourceStatus,
  type HomogenizationLevel,
  type Opportunity,
  type OpportunityCompetitorReference,
} from "@/features/research/api";

const sourceStatusLabels: Record<CompetitorReferenceSourceStatus, string> = {
  linked: "已关联公开线索",
  no_sources: "暂无直接来源",
  fallback: "本地回退生成",
};

const homogenizationLabels: Record<HomogenizationLevel, string> = {
  low: "低同质化",
  medium: "中同质化",
  high: "高同质化",
};

export function OpportunityCompetitorReferencePanel({
  opportunityUuid,
}: {
  opportunityUuid: string;
}) {
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ["opportunity-competitor-references", opportunityUuid],
    queryFn: () => fetchOpportunityCompetitorReferences(opportunityUuid),
  });

  if (isLoading) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>竞品参考</CardTitle>
          <CardDescription>正在读取类似产品和差异化切入点。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-32 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <CompetitorEmptyState
        action={
          <Button type="button" variant="outline" onClick={() => void refetch()}>
            <RefreshCcw data-icon="inline-start" />
            重新加载
          </Button>
        }
        description="竞品参考暂不可用，基础商机详情、需求洞察和货源候选仍可继续阅读。"
        title="竞品参考读取失败"
      />
    );
  }

  if (!data?.length) {
    return (
      <CompetitorEmptyState
        description="当前商机还没有竞品参考。可先使用商机方向继续搜索公开内容和类似产品，售价、卖点和同质化程度都需要待验证。"
        title="暂无竞品参考"
      />
    );
  }

  return (
    <Card id="competitor-references" className="rounded-lg">
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">竞品参考</Badge>
          <Badge variant="outline">公开线索</Badge>
          <Badge variant="outline">待确认</Badge>
          <Badge variant="outline">待验证</Badge>
        </div>
        <CardTitle>市场上有哪些类似产品</CardTitle>
        <CardDescription>
          以下内容是类似产品参考和差异化切入点，不代表竞品、销量、售价或市场规模已经被全面核验。
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {data.map((reference) => (
          <CompetitorReferenceCard key={reference.uuid} reference={reference} />
        ))}
      </CardContent>
    </Card>
  );
}

export function TaskCompetitorReferenceSummary({
  opportunities,
  taskUuid,
}: {
  opportunities: Opportunity[];
  taskUuid: string;
}) {
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ["task-competitor-references", taskUuid],
    queryFn: () => fetchTaskCompetitorReferences(taskUuid),
  });
  const opportunityNameByUuid = useMemo(
    () =>
      new Map(
        opportunities.map((opportunity) => [
          opportunity.uuid,
          {
            name: opportunity.name,
            rank: opportunity.rank,
          },
        ]),
      ),
    [opportunities],
  );
  const referencesByOpportunity = useMemo(() => {
    const grouped = new Map<string, OpportunityCompetitorReference[]>();

    for (const reference of data ?? []) {
      const current = grouped.get(reference.opportunity_uuid) ?? [];
      current.push(reference);
      grouped.set(reference.opportunity_uuid, current);
    }

    return grouped;
  }, [data]);

  if (isLoading) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>竞品参考摘要</CardTitle>
          <CardDescription>正在读取每个商机的类似产品参考。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-28 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <CompetitorEmptyState
        action={
          <Button type="button" variant="outline" onClick={() => void refetch()}>
            <RefreshCcw data-icon="inline-start" />
            重新加载
          </Button>
        }
        description="竞品参考暂不可用，报告主体仍保留基础推荐、需求洞察、货源候选和公开来源。"
        title="竞品参考读取失败"
      />
    );
  }

  if (!data?.length) {
    return (
      <CompetitorEmptyState
        description="当前任务还没有竞品参考摘要。基础报告仍是待验证推荐，后续可补充公开竞品线索和小批量反馈。"
        title="暂无竞品参考摘要"
      />
    );
  }

  return (
    <Card className="rounded-lg">
      <CardHeader>
        <Badge variant="secondary" className="w-fit">
          竞品参考
        </Badge>
        <CardTitle>竞品参考摘要</CardTitle>
        <CardDescription>
          为每个商机整理类似产品、常见售价、常见卖点和差异化切入点。
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {Array.from(referencesByOpportunity.entries()).map(
          ([opportunityUuid, references]) => {
            const opportunity = opportunityNameByUuid.get(opportunityUuid);

            return (
              <section
                key={opportunityUuid}
                className="rounded-lg border bg-background p-4"
              >
                <div className="flex flex-wrap items-center gap-2">
                  {opportunity ? (
                    <Badge variant="outline">
                      {String(opportunity.rank).padStart(2, "0")}
                    </Badge>
                  ) : null}
                  <Badge variant="secondary">{references.length} 个参考</Badge>
                  <Badge variant="outline">待验证</Badge>
                </div>
                <h2 className="mt-3 font-semibold">
                  {opportunity?.name ?? "商机竞品参考"}
                </h2>
                <div className="mt-3 grid gap-2">
                  {references.slice(0, 2).map((reference) => (
                    <p
                      key={reference.uuid}
                      className="rounded-md bg-muted/40 px-3 py-2 text-sm leading-6 text-muted-foreground"
                    >
                      {reference.reference_name}：{reference.price_range}
                    </p>
                  ))}
                </div>
                <Button asChild variant="ghost" size="sm" className="mt-3 px-0">
                  <Link href={`/opportunities/${opportunityUuid}`}>
                    查看完整参考
                    <ArrowRight data-icon="inline-end" />
                  </Link>
                </Button>
              </section>
            );
          },
        )}
      </CardContent>
    </Card>
  );
}

function CompetitorReferenceCard({
  reference,
}: {
  reference: OpportunityCompetitorReference;
}) {
  return (
    <article className="rounded-lg border bg-background p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{String(reference.rank).padStart(2, "0")}</Badge>
            <Badge variant="secondary">
              {sourceStatusLabels[reference.source_status]}
            </Badge>
            <Badge variant="outline">
              {homogenizationLabels[reference.homogenization_level]}
            </Badge>
          </div>
          <h2 className="mt-3 font-semibold">{reference.reference_name}</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {reference.reference_note}
          </p>
        </div>
        <SearchCheck className="size-5 shrink-0 text-primary" aria-hidden="true" />
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <InfoBlock label="参考市场" value={reference.reference_market} />
        <InfoBlock label="售价区间" value={reference.price_range} />
        <InfoBlock
          label="同质化程度"
          value={homogenizationLabels[reference.homogenization_level]}
        />
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <CompetitorList title="常见卖点" items={reference.common_selling_points} />
        <CompetitorList title="差异化切入点" items={reference.differentiation_angles} />
        <CompetitorSources reference={reference} />
      </div>
    </article>
  );
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <section className="rounded-lg border bg-muted/20 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-2 break-words text-sm font-semibold leading-6">{value}</p>
    </section>
  );
}

function CompetitorList({ items, title }: { items: string[]; title: string }) {
  return (
    <section className="rounded-lg border bg-muted/20 p-3">
      <h3 className="text-sm font-semibold">{title}</h3>
      <ul className="mt-3 grid gap-2 text-sm leading-6 text-muted-foreground">
        {items.map((item) => (
          <li key={item} className="rounded-md bg-background px-3 py-2">
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}

function CompetitorSources({
  reference,
}: {
  reference: OpportunityCompetitorReference;
}) {
  if (!reference.sources.length) {
    return (
      <section className="rounded-lg border border-dashed bg-muted/20 p-3">
        <h3 className="text-sm font-semibold">关联来源</h3>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          暂无直接关联来源。该竞品参考仍是初步参考，需要继续搜索公开资料和验证。
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border bg-muted/20 p-3">
      <h3 className="text-sm font-semibold">关联来源</h3>
      <div className="mt-3 grid gap-2">
        {reference.sources.map((source) => (
          <a
            key={source.uuid}
            href={source.url}
            target="_blank"
            rel="noreferrer"
            className="rounded-md border bg-background p-3 text-sm transition-colors hover:border-primary/40 hover:bg-primary/5"
          >
            <span className="flex items-start justify-between gap-3 font-medium">
              <span className="break-words">{source.title}</span>
              <ExternalLink className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            </span>
            <span className="mt-2 block leading-6 text-muted-foreground">
              {source.relevance_note}
            </span>
          </a>
        ))}
      </div>
    </section>
  );
}

function CompetitorEmptyState({
  action,
  description,
  title,
}: {
  action?: ReactNode;
  description: string;
  title: string;
}) {
  return (
    <Card className="rounded-lg border-dashed">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      {action ? <CardContent>{action}</CardContent> : null}
    </Card>
  );
}
