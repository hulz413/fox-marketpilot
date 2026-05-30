import Link from "next/link";

import { Button } from "@/components/ui/button";
import { ProductShell } from "@/features/product-skeleton/components";
import { ResearchHistoryList } from "@/features/research/research-history-list";

export default function HistoryPage() {
  return (
    <ProductShell
      active="history"
      title="研究历史"
      description="回看真实研究任务，并从历史记录继续查看报告、进度或重新运行。"
      action={
        <Button asChild>
          <Link href="/research/new">新建研究</Link>
        </Button>
      }
    >
      <ResearchHistoryList />
    </ProductShell>
  );
}
