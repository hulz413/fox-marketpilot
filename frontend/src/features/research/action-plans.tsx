"use client";

import { useMemo, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowRight, ClipboardCheck, RefreshCcw } from "lucide-react";

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
  fetchOpportunityActionPlans,
  fetchTaskActionPlans,
  type ActionPlanStatus,
  type Opportunity,
  type OpportunityActionPlan,
} from "@/features/research/api";

const planStatusLabels: Record<ActionPlanStatus, string> = {
  derived: "基于现有信息生成",
  fallback: "本地回退生成",
  insufficient_data: "线索不足建议",
};

export function OpportunityActionPlanPanel({
  opportunityUuid,
}: {
  opportunityUuid: string;
}) {
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ["opportunity-action-plans", opportunityUuid],
    queryFn: () => fetchOpportunityActionPlans(opportunityUuid),
  });

  if (isLoading) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>行动计划</CardTitle>
          <CardDescription>正在读取验证计划和询盘话术。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-32 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <ActionPlanEmptyState
        action={
          <Button type="button" variant="outline" onClick={() => void refetch()}>
            <RefreshCcw data-icon="inline-start" />
            重新加载
          </Button>
        }
        description="行动计划暂不可用，基础商机详情、验证预算和风险复核仍可继续阅读。"
        title="行动计划读取失败"
      />
    );
  }

  if (!data?.length) {
    return (
      <ActionPlanEmptyState
        description="当前商机还没有行动计划。可先人工整理样品确认、内容测试、询盘话术和上架前检查事项。"
        title="暂无行动计划"
      />
    );
  }

  return (
    <Card id="action-plans" className="rounded-lg">
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">行动计划</Badge>
          <Badge variant="outline">人工执行</Badge>
          <Badge variant="outline">待确认</Badge>
        </div>
        <CardTitle>下一步怎么开始验证</CardTitle>
        <CardDescription>
          以下内容是首批验证建议和询盘话术，需要人工调整后使用，不代表系统已经自动触达外部平台或完成真实验证。
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {data.map((plan) => (
          <ActionPlanCard key={plan.uuid} plan={plan} />
        ))}
      </CardContent>
    </Card>
  );
}

export function TaskActionPlanSummary({
  opportunities,
  taskUuid,
}: {
  opportunities: Opportunity[];
  taskUuid: string;
}) {
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ["task-action-plans", taskUuid],
    queryFn: () => fetchTaskActionPlans(taskUuid),
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
          <CardTitle>行动计划摘要</CardTitle>
          <CardDescription>正在读取每个商机的验证计划。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-28 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <ActionPlanEmptyState
        action={
          <Button type="button" variant="outline" onClick={() => void refetch()}>
            <RefreshCcw data-icon="inline-start" />
            重新加载
          </Button>
        }
        description="行动计划暂不可用，报告主体仍保留基础推荐、验证预算和风险复核。"
        title="行动计划读取失败"
      />
    );
  }

  if (!data?.length) {
    return (
      <ActionPlanEmptyState
        description="当前任务还没有行动计划摘要。基础报告仍可阅读，后续可补充首批验证计划、内容角度和上架前检查清单。"
        title="暂无行动计划摘要"
      />
    );
  }

  return (
    <Card className="rounded-lg">
      <CardHeader>
        <Badge variant="secondary" className="w-fit">
          行动计划
        </Badge>
        <CardTitle>行动计划摘要</CardTitle>
        <CardDescription>
          为每个商机整理首批验证计划、内容测试角度和上架前检查事项。
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {data.map((plan) => {
          const opportunity = opportunityNameByUuid.get(plan.opportunity_uuid);

          return (
            <section
              key={plan.uuid}
              className="rounded-lg border bg-background p-4"
            >
              <div className="flex flex-wrap items-center gap-2">
                {opportunity ? (
                  <Badge variant="outline">
                    {String(opportunity.rank).padStart(2, "0")}
                  </Badge>
                ) : null}
                <Badge variant="secondary">
                  {planStatusLabels[plan.plan_status]}
                </Badge>
                <Badge variant="outline">人工执行</Badge>
              </div>
              <h2 className="mt-3 font-semibold">
                {opportunity?.name ?? "商机行动计划"}
              </h2>
              <div className="mt-3 grid gap-2">
                <p className="rounded-md bg-muted/40 px-3 py-2 text-sm leading-6 text-muted-foreground">
                  首批计划：{plan.first_batch_plan}
                </p>
                <p className="rounded-md bg-muted/40 px-3 py-2 text-sm leading-6 text-muted-foreground">
                  内容角度：{plan.content_angles[0]}
                </p>
                <p className="rounded-md bg-muted/40 px-3 py-2 text-sm leading-6 text-muted-foreground">
                  上架检查：{plan.prelaunch_checklist[0]}
                </p>
              </div>
              <Button asChild variant="ghost" size="sm" className="mt-3 px-0">
                <Link href={`/opportunities/${plan.opportunity_uuid}`}>
                  查看完整计划
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

function ActionPlanCard({ plan }: { plan: OpportunityActionPlan }) {
  return (
    <article className="rounded-lg border bg-background p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">
              {planStatusLabels[plan.plan_status]}
            </Badge>
            <Badge variant="outline">人工执行</Badge>
            <Badge variant="outline">待确认</Badge>
          </div>
          <h2 className="mt-3 font-semibold">首批验证计划</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {plan.validation_goal}
          </p>
        </div>
        <ClipboardCheck className="size-5 shrink-0 text-primary" aria-hidden="true" />
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <InfoBlock label="首批计划" value={plan.first_batch_plan} />
        <InfoBlock label="选品验证方式" value={plan.product_validation_method} />
        <InfoBlock label="计划状态" value={planStatusLabels[plan.plan_status]} />
      </div>

      <ListBlock title="内容种草角度" items={plan.content_angles} />
      <ListBlock title="商品标题建议" items={plan.title_suggestions} />
      <ListBlock title="卖点建议" items={plan.selling_point_suggestions} />

      <section className="mt-4 rounded-lg border bg-muted/20 p-3">
        <h3 className="text-sm font-semibold">供应商询盘话术</h3>
        <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">
          {plan.supplier_inquiry_script}
        </p>
      </section>

      <ListBlock title="上架前检查清单" items={plan.prelaunch_checklist} />
    </article>
  );
}

function ListBlock({ items, title }: { items: string[]; title: string }) {
  return (
    <section className="mt-4 rounded-lg border bg-muted/20 p-3">
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

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <section className="rounded-lg border bg-muted/20 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-2 break-words text-sm font-semibold leading-6">{value}</p>
    </section>
  );
}

function ActionPlanEmptyState({
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
