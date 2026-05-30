"use client";

import { useMemo, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowRight, ExternalLink, PackageSearch, RefreshCcw } from "lucide-react";

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
  fetchOpportunitySupplyCandidates,
  fetchTaskSupplyCandidates,
  type Opportunity,
  type OpportunitySupplyCandidate,
  type SupplyCandidateSourceStatus,
} from "@/features/research/api";

const sourceStatusLabels: Record<SupplyCandidateSourceStatus, string> = {
  linked: "已关联公开线索",
  no_sources: "暂无直接来源",
  fallback: "本地回退生成",
};

export function OpportunitySupplyCandidatePanel({
  opportunityUuid,
}: {
  opportunityUuid: string;
}) {
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ["opportunity-supply-candidates", opportunityUuid],
    queryFn: () => fetchOpportunitySupplyCandidates(opportunityUuid),
  });

  if (isLoading) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>货源候选</CardTitle>
          <CardDescription>正在读取候选货源和询盘问题。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-32 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <SupplyEmptyState
        action={
          <Button type="button" variant="outline" onClick={() => void refetch()}>
            <RefreshCcw data-icon="inline-start" />
            重新加载
          </Button>
        }
        description="货源候选暂不可用，基础商机详情和需求洞察仍可继续阅读。"
        title="货源候选读取失败"
      />
    );
  }

  if (!data?.length) {
    return (
      <SupplyEmptyState
        description="当前商机还没有货源候选。可先使用商机方向继续搜索公开供给市场，价格、库存和履约能力都需要待确认。"
        title="暂无货源候选"
      />
    );
  }

  return (
    <Card id="supply-candidates" className="rounded-lg">
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">货源候选</Badge>
          <Badge variant="outline">初步参考</Badge>
          <Badge variant="outline">待确认</Badge>
        </div>
        <CardTitle>可以从哪里继续找货</CardTitle>
        <CardDescription>
          以下内容是候选方向和询盘清单，不代表供应商、库存、报价或履约能力已经确认。
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {data.map((candidate) => (
          <SupplyCandidateCard key={candidate.uuid} candidate={candidate} />
        ))}
      </CardContent>
    </Card>
  );
}

export function TaskSupplyCandidateSummary({
  opportunities,
  taskUuid,
}: {
  opportunities: Opportunity[];
  taskUuid: string;
}) {
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ["task-supply-candidates", taskUuid],
    queryFn: () => fetchTaskSupplyCandidates(taskUuid),
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
  const candidatesByOpportunity = useMemo(() => {
    const grouped = new Map<string, OpportunitySupplyCandidate[]>();

    for (const candidate of data ?? []) {
      const current = grouped.get(candidate.opportunity_uuid) ?? [];
      current.push(candidate);
      grouped.set(candidate.opportunity_uuid, current);
    }

    return grouped;
  }, [data]);

  if (isLoading) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>货源候选摘要</CardTitle>
          <CardDescription>正在读取每个商机的候选货源。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-28 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <SupplyEmptyState
        action={
          <Button type="button" variant="outline" onClick={() => void refetch()}>
            <RefreshCcw data-icon="inline-start" />
            重新加载
          </Button>
        }
        description="货源候选暂不可用，报告主体仍保留基础推荐、需求洞察和公开来源。"
        title="货源候选读取失败"
      />
    );
  }

  if (!data?.length) {
    return (
      <SupplyEmptyState
        description="当前任务还没有货源候选摘要。基础报告仍是待验证推荐，后续可补充公开供给线索和询盘结果。"
        title="暂无货源候选摘要"
      />
    );
  }

  return (
    <Card className="rounded-lg">
      <CardHeader>
        <Badge variant="secondary" className="w-fit">
          货源候选
        </Badge>
        <CardTitle>货源候选摘要</CardTitle>
        <CardDescription>
          为每个商机整理可继续搜索的候选方向、供给市场和待确认问题。
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {Array.from(candidatesByOpportunity.entries()).map(
          ([opportunityUuid, candidates]) => {
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
                  <Badge variant="secondary">{candidates.length} 个候选</Badge>
                  <Badge variant="outline">待验证</Badge>
                </div>
                <h2 className="mt-3 font-semibold">
                  {opportunity?.name ?? "商机货源候选"}
                </h2>
                <div className="mt-3 grid gap-2">
                  {candidates.slice(0, 2).map((candidate) => (
                    <p
                      key={candidate.uuid}
                      className="rounded-md bg-muted/40 px-3 py-2 text-sm leading-6 text-muted-foreground"
                    >
                      {candidate.candidate_name}：{candidate.supply_market}
                    </p>
                  ))}
                </div>
                <Button asChild variant="ghost" size="sm" className="mt-3 px-0">
                  <Link href={`/opportunities/${opportunityUuid}`}>
                    查看完整候选
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

function SupplyCandidateCard({
  candidate,
}: {
  candidate: OpportunitySupplyCandidate;
}) {
  return (
    <article className="rounded-lg border bg-background p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{String(candidate.rank).padStart(2, "0")}</Badge>
            <Badge variant="secondary">
              {sourceStatusLabels[candidate.source_status]}
            </Badge>
            <Badge variant="outline">待确认</Badge>
          </div>
          <h2 className="mt-3 font-semibold">{candidate.candidate_name}</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {candidate.recommendation_note}
          </p>
        </div>
        <PackageSearch className="size-5 shrink-0 text-primary" aria-hidden="true" />
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <InfoBlock label="供给市场" value={candidate.supply_market} />
        <InfoBlock label="价格区间" value={candidate.price_range} />
        <InfoBlock label="起订量" value={candidate.minimum_order_quantity} />
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <SupplyList title="搜索关键词" items={candidate.search_keywords} />
        <SupplyList title="规格参考" items={candidate.specification_notes} />
        <SupplyList title="供应商确认问题" items={candidate.supplier_questions} />
        <SupplySources candidate={candidate} />
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

function SupplyList({ items, title }: { items: string[]; title: string }) {
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

function SupplySources({
  candidate,
}: {
  candidate: OpportunitySupplyCandidate;
}) {
  if (!candidate.sources.length) {
    return (
      <section className="rounded-lg border border-dashed bg-muted/20 p-3">
        <h3 className="text-sm font-semibold">关联来源</h3>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          暂无直接关联来源。该候选仍是初步参考，需要继续搜索和向供应商确认。
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border bg-muted/20 p-3">
      <h3 className="text-sm font-semibold">关联来源</h3>
      <div className="mt-3 grid gap-2">
        {candidate.sources.map((source) => (
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

function SupplyEmptyState({
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
