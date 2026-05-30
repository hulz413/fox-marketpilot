import Link from "next/link";
import type { ReactNode } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Building2,
  CheckCircle2,
  CircleHelp,
  Compass,
  Languages,
  RefreshCcw,
  UserRound,
} from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
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
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

import { productNavItems, samplePrompts, type NavKey } from "./data";

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
  const agentTitle = "小成本商机顾问";
  const agentDescription = "从需求、供给、竞品和风险中发现可快速验证的小生意机会。";

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="grid min-h-screen lg:grid-cols-[300px_minmax(0,1fr)]">
        <aside className="flex flex-col border-r bg-card/85">
          <div className="flex items-center gap-4 px-6 py-6">
            <div className="flex size-12 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Compass className="size-6" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <p className="text-lg font-semibold leading-none">MarketPilot</p>
              <p className="mt-2 truncate text-sm text-muted-foreground">
                商机顾问 Agent
              </p>
            </div>
          </div>

          <div className="px-5">
            <div
              className="flex items-start gap-4 rounded-lg border bg-background p-4"
              title={`${agentTitle}\n${agentDescription}`}
              aria-label={`${agentTitle}，${agentDescription}`}
            >
              <div className="mt-1 flex size-8 items-center justify-center rounded-md bg-primary/10 text-primary">
                <Building2 className="size-4" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <p className="text-base font-semibold">{agentTitle}</p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  {agentDescription}
                </p>
              </div>
            </div>
          </div>

          <nav className="flex flex-1 flex-col gap-1 px-5 py-6" aria-label="主导航">
            {productNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = active === item.key;

              return (
                <Link
                  key={item.key}
                  href={item.href}
                  className={cn(
                    "flex min-h-12 items-center gap-4 rounded-md px-4 text-base font-medium transition-colors",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-primary/10 hover:text-primary"
                  )}
                >
                  <Icon className="size-5" aria-hidden="true" />
                  <span className="truncate">{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="mx-5 mb-6 border-t pt-5">
            <div className="flex items-start gap-3 text-sm leading-6 text-muted-foreground">
              <CircleHelp className="mt-1 size-4 shrink-0" aria-hidden="true" />
              <p>来源、供给、竞品、风险和验证计划会在后续切片中逐步展开。</p>
            </div>
          </div>
        </aside>

        <section className="min-w-0">
          <header className="flex min-h-20 flex-col gap-4 border-b bg-card px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
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
                {title}
              </h1>
              {description ? (
                <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
                  {description}
                </p>
              ) : null}
            </div>
            <div className="flex flex-wrap items-center gap-3">
              {action}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon-lg"
                    className="size-10 cursor-pointer rounded-full bg-transparent p-0 hover:bg-transparent focus-visible:border-transparent focus-visible:ring-0 focus-visible:ring-offset-0 data-[state=open]:bg-transparent"
                    aria-label="用户菜单"
                  >
                    <Avatar size="lg">
                      <AvatarFallback className="bg-primary text-primary-foreground">
                        <UserRound aria-hidden="true" />
                      </AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel>演示用户</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuGroup>
                    <DropdownMenuSub>
                      <DropdownMenuSubTrigger>
                        <Languages aria-hidden="true" />
                        <span>切换语言</span>
                      </DropdownMenuSubTrigger>
                      <DropdownMenuSubContent className="w-32">
                        <DropdownMenuGroup>
                          <DropdownMenuItem disabled className="text-muted-foreground">
                            中文
                          </DropdownMenuItem>
                          <DropdownMenuItem>English</DropdownMenuItem>
                        </DropdownMenuGroup>
                      </DropdownMenuSubContent>
                    </DropdownMenuSub>
                  </DropdownMenuGroup>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </header>

          <div
            className={cn(
              "grid gap-5 p-5",
              aside ? "xl:grid-cols-[minmax(0,1fr)_320px]" : ""
            )}
          >
            <div className="min-w-0">{children}</div>
            {aside ? <aside className="min-w-0">{aside}</aside> : null}
          </div>
        </section>
      </div>
    </main>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const tone =
    status === "失败"
      ? "border-destructive/30 bg-destructive/10 text-destructive"
      : status === "运行中"
        ? "border-primary/20 bg-primary/10 text-primary"
        : "border-transparent bg-secondary text-secondary-foreground";

  return (
    <Badge variant="outline" className={cn("rounded-full px-3 py-1", tone)}>
      {status}
    </Badge>
  );
}

export function EmptyResearchState() {
  return (
    <Card className="rounded-lg border-dashed">
      <CardHeader>
        <CardTitle>还没有真实研究任务</CardTitle>
        <CardDescription>
          首次演示可以从下面的中文示例开始；真实任务接入后会显示你的研究记录。
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <Button asChild className="w-fit">
          <Link href="/research/new">
            新建研究
            <ArrowRight data-icon="inline-end" />
          </Link>
        </Button>
        <div className="grid gap-3">
          {samplePrompts.map((prompt) => (
            <div key={prompt} className="rounded-md border bg-background p-3 text-sm">
              {prompt}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function TaskStateCards() {
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
              <CardTitle>{state.title}</CardTitle>
              <CardDescription>{state.body}</CardDescription>
            </CardHeader>
          </Card>
        );
      })}
    </div>
  );
}
