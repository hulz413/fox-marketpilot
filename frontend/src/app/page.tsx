import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  ProductShell,
  ProductSummaryAside,
  TaskStateCards,
} from "@/features/product-skeleton/components";
import { ResearchTaskList } from "@/features/research/research-task-list";

export default function HomePage() {
  return (
    <ProductShell
      active="tasks"
      title="研究任务"
      description="从这里进入新建研究、查看运行状态，并继续浏览商机推荐与最终报告。"
      action={
        <Button asChild>
          <Link href="/research/new">
            新建研究
            <ArrowRight data-icon="inline-end" />
          </Link>
        </Button>
      }
      aside={<ProductSummaryAside />}
    >
      <div className="grid gap-5">
        <TaskStateCards />
        <ResearchTaskList />
      </div>
    </ProductShell>
  );
}
