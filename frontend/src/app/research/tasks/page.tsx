import { ProductShell } from "@/features/product-skeleton/components";
import { ResearchTaskList } from "@/features/research/research-task-list";

type ResearchTasksPageProps = {
  searchParams?: Promise<{
    status?: string | string[];
  }>;
};

export default async function ResearchTasksPage({
  searchParams,
}: ResearchTasksPageProps) {
  const resolvedSearchParams = await searchParams;
  const statusParam = resolvedSearchParams?.status;
  const statusFilter = Array.isArray(statusParam) ? statusParam[0] : statusParam;

  return (
    <ProductShell
      active="tasks"
      title="我的研究"
      description="统一查看进行中、已完成和失败的研究，并从同一入口继续进度或阅读结果。"
    >
      <div className="grid gap-5">
        <ResearchTaskList statusFilter={statusFilter} />
      </div>
    </ProductShell>
  );
}
