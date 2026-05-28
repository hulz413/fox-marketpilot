import { Activity, BarChart3, FileText } from "lucide-react";

const scaffoldItems = [
  {
    label: "研究任务",
    description: "后续承接创建任务、运行进度和 SSE 状态流。",
    icon: Activity,
  },
  {
    label: "商机推荐",
    description: "后续承接排行榜、商机详情和关键判断展示。",
    icon: BarChart3,
  },
  {
    label: "最终报告",
    description: "后续承接可阅读的商机研究报告。",
    icon: FileText,
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <section className="mx-auto flex min-h-screen w-full max-w-5xl flex-col justify-center px-6 py-16">
        <div className="max-w-2xl">
          <p className="text-sm font-medium text-muted-foreground">
            MarketPilot MVP
          </p>
          <h1 className="mt-3 text-4xl font-semibold tracking-normal sm:text-5xl">
            项目骨架已就绪
          </h1>
          <p className="mt-5 text-base leading-7 text-muted-foreground sm:text-lg">
            前端入口已预留研究任务、商机推荐和最终报告三个 MVP 方向，后续
            OpenSpec change 会逐步填充真实产品流程。
          </p>
        </div>

        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {scaffoldItems.map((item) => {
            const Icon = item.icon;

            return (
              <article
                key={item.label}
                className="rounded-lg border bg-card p-5 text-card-foreground"
              >
                <Icon className="size-5 text-primary" aria-hidden="true" />
                <h2 className="mt-4 text-lg font-medium">{item.label}</h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  {item.description}
                </p>
              </article>
            );
          })}
        </div>
      </section>
    </main>
  );
}
