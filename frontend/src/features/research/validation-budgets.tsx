"use client";

import { useMemo, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowRight, Calculator, RefreshCcw } from "lucide-react";

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
  fetchOpportunityValidationBudgets,
  fetchTaskValidationBudgets,
  type Opportunity,
  type OpportunityValidationBudget,
  type ValidationBudgetEstimateStatus,
} from "@/features/research/api";

const estimateStatusLabels: Record<ValidationBudgetEstimateStatus, string> = {
  derived: "基于现有信息粗算",
  fallback: "本地回退生成",
  insufficient_data: "线索不足粗算",
};

export function OpportunityValidationBudgetPanel({
  opportunityUuid,
}: {
  opportunityUuid: string;
}) {
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ["opportunity-validation-budgets", opportunityUuid],
    queryFn: () => fetchOpportunityValidationBudgets(opportunityUuid),
  });

  if (isLoading) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>验证预算</CardTitle>
          <CardDescription>正在读取首批验证预算和关键假设。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-32 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <ValidationBudgetEmptyState
        action={
          <Button type="button" variant="outline" onClick={() => void refetch()}>
            <RefreshCcw data-icon="inline-start" />
            重新加载
          </Button>
        }
        description="验证预算暂不可用，基础商机详情、货源候选和竞品参考仍可继续阅读。"
        title="验证预算读取失败"
      />
    );
  }

  if (!data?.length) {
    return (
      <ValidationBudgetEmptyState
        description="当前商机还没有验证预算估算。可先用价格带、货源候选和竞品参考做人工粗算，采购价、售价和首批数量都需要继续确认。"
        title="暂无验证预算"
      />
    );
  }

  return (
    <Card id="validation-budgets" className="rounded-lg">
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">验证预算</Badge>
          <Badge variant="outline">粗略估算</Badge>
          <Badge variant="outline">待验证假设</Badge>
        </div>
        <CardTitle>首批大概要准备多少钱</CardTitle>
        <CardDescription>
          以下内容是首批验证预算粗算，不代表采购价、售价、毛利或回本结果已经确认。
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {data.map((budget) => (
          <ValidationBudgetCard key={budget.uuid} budget={budget} />
        ))}
      </CardContent>
    </Card>
  );
}

export function TaskValidationBudgetSummary({
  opportunities,
  taskUuid,
}: {
  opportunities: Opportunity[];
  taskUuid: string;
}) {
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ["task-validation-budgets", taskUuid],
    queryFn: () => fetchTaskValidationBudgets(taskUuid),
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

  if (isLoading) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>验证预算摘要</CardTitle>
          <CardDescription>正在读取每个商机的首批验证预算。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-28 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <ValidationBudgetEmptyState
        action={
          <Button type="button" variant="outline" onClick={() => void refetch()}>
            <RefreshCcw data-icon="inline-start" />
            重新加载
          </Button>
        }
        description="验证预算暂不可用，报告主体仍保留基础推荐、需求洞察、货源候选和竞品参考。"
        title="验证预算读取失败"
      />
    );
  }

  if (!data?.length) {
    return (
      <ValidationBudgetEmptyState
        description="当前任务还没有验证预算摘要。基础报告仍可阅读，后续可补充首批预算、售价和关键假设。"
        title="暂无验证预算摘要"
      />
    );
  }

  return (
    <Card className="rounded-lg">
      <CardHeader>
        <Badge variant="secondary" className="w-fit">
          验证预算
        </Badge>
        <CardTitle>验证预算摘要</CardTitle>
        <CardDescription>
          为每个商机整理首批验证预算、粗略毛利空间和最需要确认的假设。
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {data.map((budget) => {
          const opportunity = opportunityNameByUuid.get(budget.opportunity_uuid);

          return (
            <section
              key={budget.uuid}
              className="rounded-lg border bg-background p-4"
            >
              <div className="flex flex-wrap items-center gap-2">
                {opportunity ? (
                  <Badge variant="outline">
                    {String(opportunity.rank).padStart(2, "0")}
                  </Badge>
                ) : null}
                <Badge variant="secondary">
                  {estimateStatusLabels[budget.estimate_status]}
                </Badge>
                <Badge variant="outline">待验证</Badge>
              </div>
              <h2 className="mt-3 font-semibold">
                {opportunity?.name ?? "商机验证预算"}
              </h2>
              <div className="mt-3 grid gap-2">
                <p className="rounded-md bg-muted/40 px-3 py-2 text-sm leading-6 text-muted-foreground">
                  首批预算：{budget.first_batch_budget}
                </p>
                <p className="rounded-md bg-muted/40 px-3 py-2 text-sm leading-6 text-muted-foreground">
                  关键假设：{budget.key_assumptions[0]}
                </p>
              </div>
              <Button asChild variant="ghost" size="sm" className="mt-3 px-0">
                <Link href={`/opportunities/${budget.opportunity_uuid}`}>
                  查看完整预算
                  <ArrowRight data-icon="inline-end" />
                </Link>
              </Button>
            </section>
          );
        })}
      </CardContent>
    </Card>
  );
}

function ValidationBudgetCard({
  budget,
}: {
  budget: OpportunityValidationBudget;
}) {
  return (
    <article className="rounded-lg border bg-background p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">
              {estimateStatusLabels[budget.estimate_status]}
            </Badge>
            <Badge variant="outline">粗略估算</Badge>
            <Badge variant="outline">待验证</Badge>
          </div>
          <h2 className="mt-3 font-semibold">验证预算粗算</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {budget.calculation_note}
          </p>
        </div>
        <Calculator className="size-5 shrink-0 text-primary" aria-hidden="true" />
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <InfoBlock label="预估拿货成本" value={budget.estimated_unit_cost} />
        <InfoBlock label="预估售价" value={budget.estimated_selling_price} />
        <InfoBlock label="粗略毛利空间" value={budget.rough_gross_margin} />
        <InfoBlock label="首批验证数量" value={budget.first_batch_quantity} />
        <InfoBlock label="首批验证预算" value={budget.first_batch_budget} />
        <InfoBlock
          label="估算状态"
          value={estimateStatusLabels[budget.estimate_status]}
        />
      </div>

      <section className="mt-4 rounded-lg border bg-muted/20 p-3">
        <h3 className="text-sm font-semibold">关键验证假设</h3>
        <ul className="mt-3 grid gap-2 text-sm leading-6 text-muted-foreground">
          {budget.key_assumptions.map((assumption) => (
            <li key={assumption} className="rounded-md bg-background px-3 py-2">
              {assumption}
            </li>
          ))}
        </ul>
      </section>
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

function ValidationBudgetEmptyState({
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
