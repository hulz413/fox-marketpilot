"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  Compass,
  FileText,
  Languages,
  RefreshCcw,
  SearchCheck,
  TimerReset,
  UserRound,
} from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DemoResearchSamples } from "@/features/research/demo-research-samples";
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
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useLanguage } from "@/features/i18n/language-provider";
import { cn } from "@/lib/utils";

import { productNavItems, type NavKey } from "./data";

type ProductShellProps = {
  active: NavKey;
  title: string;
  eyebrow?: string;
  description?: string;
  action?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
};

export function ProductShell({
  active,
  title,
  eyebrow,
  description,
  action,
  aside,
  children,
}: ProductShellProps) {
  const { t } = useLanguage();
  const agentTitle = "小成本商机顾问";
  const agentDescription =
    "从需求、供给、竞品和风险里，筛出值得快速验证的小生意机会。";

  return (
    <main className="min-h-screen bg-background text-foreground lg:h-screen lg:overflow-hidden">
      <div className="min-h-screen lg:grid lg:h-screen lg:grid-cols-[300px_minmax(0,1fr)]">
        <header className="border-b bg-card/95 px-4 py-4 lg:hidden">
          <div className="flex items-start justify-between gap-4">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Compass className="size-5" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <p className="text-base font-semibold leading-none">MarketPilot</p>
                <p className="mt-1 truncate text-xs text-muted-foreground">
                  {t("商机顾问 Agent")}
                </p>
              </div>
            </div>
            <UserMenu />
          </div>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            {t(agentDescription)}
          </p>
          <ProductNavLinks active={active} layout="mobile" />
        </header>

        <aside className="hidden flex-col border-r bg-card/85 lg:flex lg:h-screen lg:overflow-y-auto">
          <div className="flex items-center gap-4 px-6 py-6">
            <div className="flex size-12 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Compass className="size-6" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <p className="text-lg font-semibold leading-none">MarketPilot</p>
              <p className="mt-2 truncate text-sm text-muted-foreground">
                {t("商机顾问 Agent")}
              </p>
            </div>
          </div>

          <div className="px-5">
            <div
              className="flex items-start gap-4 rounded-lg border bg-background p-4"
              title={`${t(agentTitle)}\n${t(agentDescription)}`}
              aria-label={`${t(agentTitle)}，${t(agentDescription)}`}
            >
              <div className="min-w-0">
                <p className="text-base font-semibold">{t(agentTitle)}</p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  {t(agentDescription)}
                </p>
              </div>
            </div>
          </div>

          <ProductNavLinks active={active} layout="desktop" />

          <div className="mx-5 mb-6 border-t pt-5">
            <div className="flex items-start gap-3 text-sm leading-6 text-muted-foreground">
              <CircleHelp className="mt-1 size-4 shrink-0" aria-hidden="true" />
              <p>{t("来源、供给、竞品、风险和验证计划会在后续切片中逐步展开。")}</p>
            </div>
          </div>
        </aside>

        <section className="min-w-0 lg:flex lg:h-screen lg:flex-col lg:overflow-hidden">
          <header className="flex min-h-20 flex-col gap-4 border-b bg-card px-5 py-4 lg:shrink-0 lg:flex-row lg:items-center lg:justify-between">
            <div className="min-w-0">
              {eyebrow ? (
                <p className="text-sm text-muted-foreground">{eyebrow}</p>
              ) : null}
              <h1
                className={cn(
                  "text-2xl font-semibold tracking-normal sm:text-3xl",
                  eyebrow ? "mt-1" : ""
                )}
              >
                {t(title)}
              </h1>
              {description ? (
                <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
                  {t(description)}
                </p>
              ) : null}
            </div>
            <div className="flex flex-wrap items-center gap-3">
              {action}
              <div className="hidden lg:block">
                <UserMenu />
              </div>
            </div>
          </header>

          <div className="grid gap-4 p-5 lg:min-h-0 lg:flex-1 lg:grid-rows-[auto_minmax(0,1fr)] lg:gap-0 lg:overflow-hidden">
            <div className="relative z-20 lg:-mx-5 lg:-mt-5 lg:border-b lg:border-border/80 lg:bg-background lg:px-5 lg:pb-3 lg:pt-5 lg:shadow-[0_10px_18px_-16px_rgba(31,39,34,0.28)]">
              <ProductBreadcrumb active={active} title={title} />
            </div>
            <div
              className={cn(
                "grid gap-5 lg:min-h-0 lg:overflow-y-auto lg:pr-1 lg:pt-4",
                aside ? "xl:grid-cols-[minmax(0,1fr)_320px]" : ""
              )}
            >
              <div className="min-w-0">{children}</div>
              {aside ? <aside className="min-w-0">{aside}</aside> : null}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function ProductBreadcrumb({
  active,
  title,
}: {
  active: NavKey;
  title: string;
}) {
  const { t } = useLanguage();
  const activeItem = productNavItems.find((item) => item.key === active);
  const activeLabel = activeItem ? t(activeItem.label) : null;
  const titleLabel = t(title);
  const shouldShowTitle = !activeLabel || activeLabel !== titleLabel;

  return (
    <nav
      aria-label={t("面包屑导航")}
      className="flex min-h-6 items-center text-sm text-muted-foreground"
    >
      <ol className="flex min-w-0 flex-wrap items-center gap-1">
        <li>
          <Link
            href="/research/tasks"
            className="font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            {t("MarketPilot")}
          </Link>
        </li>
        {activeItem ? (
          <>
            <BreadcrumbSeparator />
            <li>
              {shouldShowTitle ? (
                <Link
                  href={activeItem.href}
                  className="font-medium text-muted-foreground transition-colors hover:text-foreground"
                >
                  {activeLabel}
                </Link>
              ) : (
                <span className="font-semibold text-foreground" aria-current="page">
                  {activeLabel}
                </span>
              )}
            </li>
          </>
        ) : null}
        {shouldShowTitle ? (
          <>
            <BreadcrumbSeparator />
            <li>
              <span className="font-semibold text-foreground" aria-current="page">
                {titleLabel}
              </span>
            </li>
          </>
        ) : null}
      </ol>
    </nav>
  );
}

function BreadcrumbSeparator() {
  return (
    <li className="flex items-center" aria-hidden="true">
      <ChevronRight className="size-4" />
    </li>
  );
}

function ProductNavLinks({
  active,
  layout,
}: {
  active: NavKey;
  layout: "desktop" | "mobile";
}) {
  const { t } = useLanguage();

  return (
    <nav
      className={cn(
        layout === "desktop"
          ? "flex flex-1 flex-col gap-1 px-5 py-6"
          : "mt-4 flex gap-2 overflow-x-auto pb-1",
      )}
      aria-label={t("主导航")}
    >
      {productNavItems.map((item) => {
        const Icon = item.icon;
        const isActive = active === item.key;

        return (
          <Link
            key={item.key}
            href={item.href}
            className={cn(
              "flex items-center gap-3 rounded-md font-medium transition-colors",
              layout === "desktop"
                ? "min-h-12 px-4 text-base"
                : "min-h-10 shrink-0 px-3 text-sm",
              isActive
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-primary/10 hover:text-primary",
            )}
          >
            <Icon className="size-5" aria-hidden="true" />
            <span className="whitespace-nowrap">{t(item.label)}</span>
          </Link>
        );
      })}
    </nav>
  );
}

function UserMenu() {
  const { language, setLanguage, t } = useLanguage();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon-lg"
          className="size-10 cursor-pointer rounded-full bg-transparent p-0 hover:bg-transparent focus-visible:border-transparent focus-visible:ring-0 focus-visible:ring-offset-0 data-[state=open]:bg-transparent"
          aria-label={t("用户菜单")}
        >
          <Avatar size="lg">
            <AvatarFallback className="bg-primary text-primary-foreground">
              <UserRound aria-hidden="true" />
            </AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>{t("演示用户")}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuSub>
            <DropdownMenuSubTrigger>
              <Languages aria-hidden="true" />
              <span>{t("切换语言")}</span>
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent className="w-36">
              <DropdownMenuGroup>
                <DropdownMenuItem
                  disabled={language === "zh"}
                  onSelect={() => setLanguage("zh")}
                >
                  {language === "zh" ? (
                    <Check aria-hidden="true" />
                  ) : (
                    <span className="size-4" />
                  )}
                  中文
                </DropdownMenuItem>
                <DropdownMenuItem
                  disabled={language === "en"}
                  onSelect={() => setLanguage("en")}
                >
                  {language === "en" ? (
                    <Check aria-hidden="true" />
                  ) : (
                    <span className="size-4" />
                  )}
                  English
                </DropdownMenuItem>
              </DropdownMenuGroup>
            </DropdownMenuSubContent>
          </DropdownMenuSub>
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export type TaskContextNavKey = "progress" | "opportunities" | "report" | "sources";

export function TaskContextNavigation({
  taskUuid,
  active,
  resultsReady = true,
  sourcesCount,
  sourcesHref,
}: {
  taskUuid: string;
  active: TaskContextNavKey;
  resultsReady?: boolean;
  sourcesCount?: number | null;
  sourcesHref?: string;
}) {
  const { t } = useLanguage();
  const items = [
    {
      key: "progress" as const,
      label: t("进度"),
      href: `/research/tasks/${taskUuid}`,
      icon: TimerReset,
      enabled: true,
    },
    {
      key: "opportunities" as const,
      label: t("商机"),
      href: `/opportunities?task=${taskUuid}`,
      icon: BarChart3,
      enabled: resultsReady,
    },
    {
      key: "report" as const,
      label: t("报告"),
      href: `/reports/${taskUuid}`,
      icon: FileText,
      enabled: resultsReady,
    },
    {
      key: "sources" as const,
      label:
        typeof sourcesCount === "number"
          ? t("来源 {count}", { count: sourcesCount })
          : t("来源线索"),
      href: sourcesHref ?? `/reports/${taskUuid}#sources`,
      icon: SearchCheck,
      enabled: resultsReady,
    },
  ];

  return (
    <nav
      aria-label={t("任务上下文导航")}
      className="flex flex-wrap items-center gap-2 rounded-lg border bg-card p-2"
    >
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = active === item.key;

        if (!item.enabled) {
          return (
            <Button key={item.key} type="button" variant="ghost" size="sm" disabled>
              <Icon data-icon="inline-start" />
              {item.label}
            </Button>
          );
        }

        return (
          <Button
            key={item.key}
            asChild
            variant={isActive ? "secondary" : "ghost"}
            size="sm"
          >
            <Link href={item.href}>
              <Icon data-icon="inline-start" />
              {item.label}
            </Link>
          </Button>
        );
      })}
    </nav>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const { t } = useLanguage();
  const tone =
    status === "失败"
      ? "border-destructive/30 bg-destructive/10 text-destructive"
      : status === "运行中"
        ? "border-primary/20 bg-primary/10 text-primary"
        : "border-transparent bg-secondary text-secondary-foreground";

  return (
    <Badge variant="outline" className={cn("rounded-full px-3 py-1", tone)}>
      {t(status)}
    </Badge>
  );
}

export function EmptyResearchState() {
  const { t } = useLanguage();

  return (
    <Card className="rounded-lg border-dashed">
      <CardHeader>
        <CardTitle>{t("还没有真实研究任务")}</CardTitle>
        <CardDescription>
          {t("首次演示可以直接启动下面的中文示例；创建后会进入真实任务进度页。")}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <Button asChild className="w-fit">
          <Link href="/research/new">
            {t("新建研究")}
            <ArrowRight data-icon="inline-end" />
          </Link>
        </Button>
        <DemoResearchSamples />
      </CardContent>
    </Card>
  );
}

export function TaskStateCards() {
  const { t } = useLanguage();
  const states = [
    {
      title: "运行中",
      icon: RefreshCcw,
      body: "正在生成基础商机推荐，后续会展示实时阶段和进度。",
    },
    {
      title: "失败",
      icon: AlertTriangle,
      body: "生成失败时展示原因，并提供重新运行入口。",
    },
    {
      title: "完成",
      icon: CheckCircle2,
      body: "完成后进入商机推荐、商机详情和最终报告。",
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-3">
      {states.map((state) => {
        const Icon = state.icon;

        return (
          <Card key={state.title} className="rounded-lg">
            <CardHeader>
              <div className="mb-2 flex size-9 items-center justify-center rounded-md bg-primary/10 text-primary">
                <Icon className="size-4" aria-hidden="true" />
              </div>
              <CardTitle>{t(state.title)}</CardTitle>
              <CardDescription>{t(state.body)}</CardDescription>
            </CardHeader>
          </Card>
        );
      })}
    </div>
  );
}
