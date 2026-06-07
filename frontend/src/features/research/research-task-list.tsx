"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import {
  BarChart3,
  ChevronsLeft,
  ChevronsRight,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Eye,
  MoreHorizontal,
  RefreshCcw,
} from "lucide-react";

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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useLanguage } from "@/features/i18n/language-provider";
import { formatDate, formatDateTime } from "@/lib/datetime";
import {
  EmptyResearchState,
  StatusBadge,
} from "@/features/product-skeleton/components";
import { cn } from "@/lib/utils";

import {
  fetchResearchTasks,
  startResearchRun,
  type ResearchTask,
} from "./api";

const statusLabels: Record<ResearchTask["status"], string> = {
  created: "已创建",
  queued: "运行中",
  running: "运行中",
  completed: "已完成",
  failed: "失败",
};

const stageLabels: Record<ResearchTask["current_stage"], string> = {
  intake: "需求已提交",
  queued: "等待后台执行",
  normalize_intake: "整理研究需求",
  generate_opportunities: "生成基础推荐",
  validate_results: "校验推荐结果",
  persist_results: "保存研究结果",
  collect_research_sources: "收集公开来源线索",
  index_rag_evidence: "整理公开来源证据",
  generate_demand_insights: "生成需求洞察",
  generate_supply_candidates: "生成货源候选",
  generate_competitor_references: "生成竞品参考",
  estimate_validation_budgets: "估算验证预算",
  review_opportunity_risks: "复核商机风险",
  create_action_plans: "生成行动计划",
  completed: "基础推荐已生成",
  failed: "生成失败",
};

type TaskStatusFilter = "all" | "active" | "completed" | "failed";

const taskStatusFilters: Array<{
  key: TaskStatusFilter;
  label: string;
  href: string;
}> = [
  { key: "all", label: "全部", href: "/research/tasks" },
  { key: "active", label: "进行中", href: "/research/tasks?status=active" },
  { key: "completed", label: "已完成", href: "/research/tasks?status=completed" },
  { key: "failed", label: "失败", href: "/research/tasks?status=failed" },
];

const researchTaskPageSizeOptions = [10, 20, 50, 100] as const;
const defaultResearchTaskPageSize = 10;
type ResearchTaskPageSize = (typeof researchTaskPageSizeOptions)[number];

const taskTableTaskMinWidth = 440;
const taskTableColumns: Array<{ key: string; width?: number }> = [
  { key: "task" },
  { key: "status", width: 120 },
  { key: "stage", width: 180 },
  { key: "createdAt", width: 160 },
  { key: "actions", width: 200 },
];
const taskTableMinWidth = `${
  taskTableTaskMinWidth +
  taskTableColumns.reduce((total, column) => total + (column.width ?? 0), 0)
}px`;

function TaskTableColumnGroup() {
  return (
    <colgroup>
      {taskTableColumns.map((column) => (
        <col
          key={column.key}
          style={{ width: column.width ? `${column.width}px` : undefined }}
        />
      ))}
    </colgroup>
  );
}

type PaginationItem = number | "start-ellipsis" | "end-ellipsis";

function getPaginationItems(
  currentPage: number,
  totalPages: number,
): PaginationItem[] {
  if (totalPages <= 5) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  if (currentPage <= 3) {
    return [1, 2, 3, "end-ellipsis", totalPages];
  }

  if (currentPage >= totalPages - 2) {
    return [1, "start-ellipsis", totalPages - 2, totalPages - 1, totalPages];
  }

  return [
    1,
    "start-ellipsis",
    currentPage - 1,
    currentPage,
    currentPage + 1,
    "end-ellipsis",
    totalPages,
  ];
}

function parseTaskStatusFilter(value?: string): TaskStatusFilter {
  return value === "active" || value === "completed" || value === "failed"
    ? value
    : "all";
}

function matchesTaskStatusFilter(task: ResearchTask, filter: TaskStatusFilter) {
  if (filter === "active") {
    return task.status === "created" || task.status === "queued" || task.status === "running";
  }

  if (filter === "completed" || filter === "failed") {
    return task.status === filter;
  }

  return true;
}

function TaskCreatedAt({ value }: { value: string }) {
  const { t } = useLanguage();
  const day = formatDate(value);
  const fullDate = formatDateTime(value);

  return (
    <time
      dateTime={value}
      title={fullDate}
      aria-label={t("完整创建时间：{date}", { date: fullDate })}
    >
      {day}
    </time>
  );
}

function LoadingLine({ className }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn("block animate-pulse rounded bg-muted", className)}
    />
  );
}

function ResearchTaskListLoading() {
  const { t } = useLanguage();

  return (
    <Card
      aria-busy="true"
      className="overflow-hidden rounded-lg py-0 shadow-none"
    >
      <CardHeader className="grid grid-cols-[minmax(0,1fr)_auto] grid-rows-[auto] items-center gap-4 border-b px-5 pt-4 pb-3 [.border-b]:pb-3">
        <div className="grid gap-2">
          <CardTitle>{t("研究记录")}</CardTitle>
          <CardDescription>{t("正在加载真实研究任务。")}</CardDescription>
        </div>
        <div className="flex flex-wrap items-center gap-2 lg:justify-end">
          <div className="inline-flex flex-wrap rounded-lg bg-muted/40 p-1">
            {taskStatusFilters.map((filter) => (
              <Button
                key={filter.key}
                disabled
                variant={filter.key === "completed" ? "secondary" : "ghost"}
                size="sm"
                className="rounded-md"
              >
                {t(filter.label)}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="grid gap-3 p-4 md:hidden">
          {[0, 1, 2].map((item) => (
            <div key={item} className="rounded-lg border bg-card p-4">
              <div className="mb-4 flex gap-2">
                <LoadingLine className="h-7 w-16" />
                <LoadingLine className="h-7 w-24" />
              </div>
              <LoadingLine className="mb-3 h-5 w-4/5" />
              <LoadingLine className="mb-5 h-4 w-2/3" />
              <LoadingLine className="h-9 w-32" />
            </div>
          ))}
        </div>
        <div className="hidden md:block">
          <Table className="table-fixed" style={{ minWidth: taskTableMinWidth }}>
            <TaskTableColumnGroup />
            <TableHeader>
              <TableRow className="bg-muted/50 hover:bg-muted/50">
                <TableHead className="h-14 px-5">{t("任务")}</TableHead>
                <TableHead>{t("状态")}</TableHead>
                <TableHead>{t("阶段摘要")}</TableHead>
                <TableHead>{t("创建时间")}</TableHead>
                <TableHead className="px-5">{t("操作")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[0, 1, 2].map((item) => (
                <TableRow key={item} className="h-[72px]">
                  <TableCell className="px-5">
                    <LoadingLine className="mb-2 h-4 w-72" />
                    <LoadingLine className="h-3 w-52" />
                  </TableCell>
                  <TableCell>
                    <LoadingLine className="h-7 w-16" />
                  </TableCell>
                  <TableCell>
                    <LoadingLine className="h-4 w-28" />
                  </TableCell>
                  <TableCell>
                    <LoadingLine className="h-4 w-32" />
                  </TableCell>
                  <TableCell className="px-5">
                    <div className="flex justify-start">
                      <LoadingLine className="h-9 w-32" />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

export function ResearchTaskList({ statusFilter }: { statusFilter?: string }) {
  const activeFilter = parseTaskStatusFilter(statusFilter);
  const [pagination, setPagination] = useState<{
    filter: TaskStatusFilter;
    page: number;
    pageSize: ResearchTaskPageSize;
  }>({
    filter: activeFilter,
    page: 1,
    pageSize: defaultResearchTaskPageSize,
  });
  const currentPage = pagination.filter === activeFilter ? pagination.page : 1;
  const currentPageSize = pagination.pageSize;
  const { t } = useLanguage();
  const queryClient = useQueryClient();
  const {
    data: tasks,
    error,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["research-tasks"],
    queryFn: fetchResearchTasks,
    refetchInterval: 5000,
  });
  const startRunMutation = useMutation({
    mutationFn: startResearchRun,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["research-tasks"] });
    },
  });

  if (isLoading) {
    return <ResearchTaskListLoading />;
  }

  if (error) {
    return (
      <Card className="rounded-lg border-destructive/30">
        <CardHeader>
          <CardTitle>{t("任务加载失败")}</CardTitle>
          <CardDescription>
            {error instanceof Error ? error.message : t("无法读取研究任务。")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button type="button" variant="outline" onClick={() => void refetch()}>
            <RefreshCcw data-icon="inline-start" />
            {t("重新加载")}
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!tasks?.length) {
    return <EmptyResearchState />;
  }

  const filteredTasks = tasks.filter((task) =>
    matchesTaskStatusFilter(task, activeFilter),
  );
  const totalPages = Math.max(
    1,
    Math.ceil(filteredTasks.length / currentPageSize),
  );
  const safePage = Math.min(currentPage, totalPages);
  const pageStart = (safePage - 1) * currentPageSize;
  const paginatedTasks = filteredTasks.slice(
    pageStart,
    pageStart + currentPageSize,
  );

  return (
    <Card className="overflow-hidden rounded-lg py-0 shadow-none">
      <CardHeader className="grid grid-cols-[minmax(0,1fr)_auto] grid-rows-[auto] items-center gap-4 border-b px-5 pt-4 pb-3 [.border-b]:pb-3">
        <div className="grid gap-2">
          <CardTitle>{t("研究记录")}</CardTitle>
          <CardDescription>{t("统一查看进行中、已完成和失败的真实研究。")}</CardDescription>
        </div>
        <div className="flex flex-wrap items-center gap-2 lg:justify-end">
          <div className="inline-flex flex-wrap rounded-lg bg-muted/40 p-1">
            {taskStatusFilters.map((filter) => (
              <Button
                key={filter.key}
                asChild
                variant={activeFilter === filter.key ? "secondary" : "ghost"}
                size="sm"
                className="rounded-md"
              >
                <Link href={filter.href}>{t(filter.label)}</Link>
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {filteredTasks.length ? (
          <>
            <div className="grid gap-3 p-4 md:hidden">
              {paginatedTasks.map((task) => (
                <TaskCard
                  key={task.uuid}
                  task={task}
                  isStarting={startRunMutation.isPending}
                  onStart={() => startRunMutation.mutate(task.uuid)}
                />
              ))}
            </div>
            <div className="hidden md:block">
              <Table className="table-fixed" style={{ minWidth: taskTableMinWidth }}>
                <TaskTableColumnGroup />
                <TableHeader>
                  <TableRow className="bg-muted/50 hover:bg-muted/50">
                    <TableHead className="h-14 px-5">{t("任务")}</TableHead>
                    <TableHead>{t("状态")}</TableHead>
                    <TableHead>{t("阶段摘要")}</TableHead>
                    <TableHead>{t("创建时间")}</TableHead>
                    <TableHead className="px-5">{t("操作")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedTasks.map((task) => (
                    <TableRow key={task.uuid} className="h-[72px]">
                      <TableCell className="px-5">
                        <TaskTitle task={task} compact />
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={statusLabels[task.status]} />
                      </TableCell>
                      <TableCell className="max-w-[240px] text-sm">
                        <TaskStageSummary task={task} />
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        <TaskCreatedAt value={task.created_at} />
                      </TableCell>
                      <TableCell className="px-5">
                        <TaskActions
                          task={task}
                          isStarting={startRunMutation.isPending}
                          onStart={() => startRunMutation.mutate(task.uuid)}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <ResearchTaskPagination
              currentPage={safePage}
              pageSize={currentPageSize}
              totalPages={totalPages}
              onPageChange={(page) => {
                setPagination({
                  filter: activeFilter,
                  page,
                  pageSize: currentPageSize,
                });
              }}
              onPageSizeChange={(pageSize) => {
                setPagination({ filter: activeFilter, page: 1, pageSize });
              }}
            />
          </>
        ) : (
          <EmptyFilteredState filter={activeFilter} />
        )}
      </CardContent>
    </Card>
  );
}

function ResearchTaskPagination({
  currentPage,
  pageSize,
  totalPages,
  onPageChange,
  onPageSizeChange,
}: {
  currentPage: number;
  pageSize: ResearchTaskPageSize;
  totalPages: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: ResearchTaskPageSize) => void;
}) {
  const { t } = useLanguage();
  const paginationItems = getPaginationItems(currentPage, totalPages);

  return (
    <div className="flex flex-wrap items-center justify-end gap-3 border-t px-5 py-3">
      <div className="whitespace-nowrap text-sm font-medium text-muted-foreground">
        {currentPage}/{totalPages}
      </div>
      <nav aria-label={t("研究记录分页")} className="flex items-center gap-1">
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label={t("第一页")}
          disabled={currentPage === 1}
          onClick={() => onPageChange(1)}
        >
          <ChevronsLeft aria-hidden="true" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label={t("上一页")}
          disabled={currentPage === 1}
          onClick={() => onPageChange(Math.max(1, currentPage - 1))}
        >
          <ChevronLeft aria-hidden="true" />
        </Button>
        {paginationItems.map((item) =>
          typeof item === "number" ? (
            <Button
              key={item}
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label={t("第 {page} 页", { page: item })}
              aria-current={item === currentPage ? "page" : undefined}
              className={cn(
                "rounded-md",
                item === currentPage
                  ? "bg-muted shadow-none hover:bg-muted focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
                  : "",
              )}
              onClick={() => onPageChange(item)}
            >
              {item}
            </Button>
          ) : (
            <span
              key={item}
              aria-hidden="true"
              className="flex size-8 items-center justify-center text-sm font-medium"
            >
              ...
            </span>
          ),
        )}
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label={t("下一页")}
          disabled={currentPage === totalPages}
          onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
        >
          <ChevronRight aria-hidden="true" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label={t("最后一页")}
          disabled={currentPage === totalPages}
          onClick={() => onPageChange(totalPages)}
        >
          <ChevronsRight aria-hidden="true" />
        </Button>
      </nav>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            variant="outline"
            size="sm"
            aria-label={t("每页条数")}
            className="min-w-24 justify-center"
          >
            {t("{count} 条/页", { count: pageSize })}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-32">
          <DropdownMenuRadioGroup
            value={String(pageSize)}
            onValueChange={(value) => {
              const nextPageSize = Number(value) as ResearchTaskPageSize;

              if (researchTaskPageSizeOptions.includes(nextPageSize)) {
                onPageSizeChange(nextPageSize);
              }
            }}
          >
            {researchTaskPageSizeOptions.map((option) => (
              <DropdownMenuRadioItem key={option} value={String(option)}>
                {t("{count} 条/页", { count: option })}
              </DropdownMenuRadioItem>
            ))}
          </DropdownMenuRadioGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

function TaskCard({
  task,
  isStarting,
  onStart,
}: {
  task: ResearchTask;
  isStarting: boolean;
  onStart: () => void;
}) {
  const { t } = useLanguage();

  return (
    <article className="rounded-lg border bg-background p-4">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={statusLabels[task.status]} />
        <Badge variant="outline">{t(stageLabels[task.current_stage])}</Badge>
      </div>
      <div className="mt-3">
        <TaskTitle task={task} />
      </div>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        <TaskCreatedAt value={task.created_at} />
      </p>
      {task.failure_reason ? (
        <p className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {task.failure_reason}
        </p>
      ) : null}
      <div className="mt-4 flex flex-wrap justify-end gap-2">
        <TaskActions task={task} isStarting={isStarting} onStart={onStart} />
      </div>
    </article>
  );
}

function TaskTitle({
  task,
  compact = false,
}: {
  task: ResearchTask;
  compact?: boolean;
}) {
  const title = task.title.trim();
  const brief = task.brief.trim();
  const showBrief = brief && brief !== title;
  const titleText = title || brief;
  const meta = [
    task.budget,
    task.target_channels.join("、"),
    task.target_audience,
  ].filter(Boolean);
  const compactSubtitle = [
    showBrief ? brief : null,
    ...meta,
  ]
    .filter(Boolean)
    .join(" · ");

  if (compact) {
    return (
      <div className="grid min-w-0 gap-1">
        <p className="truncate font-medium leading-5" title={titleText}>
          {titleText}
        </p>
        {compactSubtitle ? (
          <p
            className="truncate text-xs leading-4 text-muted-foreground"
            title={compactSubtitle}
          >
            {compactSubtitle}
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <div className="min-w-0">
      <p className="truncate font-medium">{titleText}</p>
      {showBrief ? (
        <p className="mt-1 truncate text-xs text-muted-foreground">
          {brief}
        </p>
      ) : null}
      {meta.length ? (
        <p className="mt-1 truncate text-xs text-muted-foreground">
          {meta.join(" · ")}
        </p>
      ) : null}
    </div>
  );
}

function TaskStageSummary({ task }: { task: ResearchTask }) {
  const { t } = useLanguage();
  const stage = t(stageLabels[task.current_stage]);
  const failureReason = task.failure_reason?.trim();

  return (
    <div className="grid min-w-0 gap-1">
      <span className="truncate text-muted-foreground" title={stage}>
        {stage}
      </span>
      {failureReason ? (
        <span className="truncate text-destructive" title={failureReason}>
          {failureReason}
        </span>
      ) : null}
    </div>
  );
}

function TaskActions({
  task,
  isStarting,
  onStart,
}: {
  task: ResearchTask;
  isStarting: boolean;
  onStart: () => void;
}) {
  const { t } = useLanguage();

  if (task.status === "completed") {
    return (
      <TaskActionGroup>
        <Button asChild size="sm" className="w-28 rounded-r-none">
          <Link href={`/reports/${task.uuid}`}>
            {t("查看研究结果")}
          </Link>
        </Button>
        <TaskSecondaryActions
          task={task}
          isStarting={isStarting}
          onStart={onStart}
        />
      </TaskActionGroup>
    );
  }

  if (task.status === "queued" || task.status === "running") {
    return (
      <TaskActionGroup>
        <Button asChild size="sm" className="w-28 rounded-r-none">
          <Link href={`/research/tasks/${task.uuid}`}>
            {t("查看进度")}
          </Link>
        </Button>
        <TaskSecondaryActions
          task={task}
          isStarting={isStarting}
          onStart={onStart}
        />
      </TaskActionGroup>
    );
  }

  const actionVariant = task.status === "failed" ? "outline" : "default";

  return (
    <TaskActionGroup>
      <Button
        type="button"
        variant={actionVariant}
        size="sm"
        className="w-28 rounded-r-none"
        disabled={isStarting}
        onClick={onStart}
      >
        {task.status === "failed" ? t("重新运行") : t("开始研究")}
      </Button>
      <TaskSecondaryActions
        task={task}
        isStarting={isStarting}
        onStart={onStart}
        triggerVariant={actionVariant}
      />
    </TaskActionGroup>
  );
}

function TaskActionGroup({ children }: { children: ReactNode }) {
  return (
    <div className="flex justify-start">
      <div className="inline-flex overflow-hidden rounded-md shadow-xs">
        {children}
      </div>
    </div>
  );
}

function TaskSecondaryActions({
  task,
  isStarting,
  onStart,
  triggerVariant = "default",
}: {
  task: ResearchTask;
  isStarting: boolean;
  onStart: () => void;
  triggerVariant?: "default" | "outline";
}) {
  const { t } = useLanguage();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant={triggerVariant}
          size="icon-sm"
          className={cn(
            "w-9 rounded-l-none",
            triggerVariant === "default"
              ? "border-l border-primary-foreground/30"
              : "border-l-0",
          )}
          aria-label={t("更多操作")}
        >
          <MoreHorizontal aria-hidden="true" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        <DropdownMenuLabel>{t("次要入口")}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem asChild>
            <Link href={`/research/tasks/${task.uuid}`}>
              <Eye aria-hidden="true" />
              {t("进度")}
            </Link>
          </DropdownMenuItem>
          {task.status === "completed" ? (
            <>
              <DropdownMenuItem asChild>
                <Link href={`/opportunities?task=${task.uuid}`}>
                  <BarChart3 aria-hidden="true" />
                  {t("商机推荐")}
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem
                disabled={isStarting}
                onSelect={() => {
                  onStart();
                }}
              >
                <RefreshCcw aria-hidden="true" />
                {t("重新运行")}
              </DropdownMenuItem>
            </>
          ) : null}
          {task.trace_url ? (
            <DropdownMenuItem asChild>
              <a href={task.trace_url} target="_blank" rel="noreferrer">
                <ExternalLink aria-hidden="true" />
                LangSmith
              </a>
            </DropdownMenuItem>
          ) : null}
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function EmptyFilteredState({ filter }: { filter: TaskStatusFilter }) {
  const { t } = useLanguage();
  const label = taskStatusFilters.find((item) => item.key === filter)?.label ?? "全部";

  return (
    <div className="m-5 rounded-lg border border-dashed p-5">
      <h2 className="font-semibold">{t("当前筛选没有研究记录")}</h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        {t("当前没有{filter}状态的研究，可以切换筛选或新建研究。", {
          filter: t(label),
        })}
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        <Button asChild>
          <Link href="/research/tasks">{t("查看全部")}</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/research/new">{t("新建研究")}</Link>
        </Button>
      </div>
    </div>
  );
}
