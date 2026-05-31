import Link from "next/link";
import { ClipboardList, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { LocalizedText } from "@/features/i18n/language-provider";
import { ProductShell } from "@/features/product-skeleton/components";

export default function ReportsIndexPage() {
  return (
    <ProductShell
      active="report"
      title="最终报告"
      description="选择一条已完成研究任务后，查看对应的基础报告和待验证商机摘要。"
      action={
        <Button asChild>
          <Link href="/research/tasks">
            <LocalizedText source="研究任务" />
            <ClipboardList data-icon="inline-end" />
          </Link>
        </Button>
      }
    >
      <Card className="rounded-lg border-dashed">
        <CardHeader>
          <CardTitle>
            <LocalizedText source="请选择一条已完成任务" />
          </CardTitle>
          <CardDescription>
            <LocalizedText source="报告需要绑定真实研究任务，避免把静态演示内容误当成本次研究结果。" />
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button asChild>
            <Link href="/research/tasks">
              <ClipboardList data-icon="inline-start" />
              <LocalizedText source="返回研究任务" />
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/research/new">
              <LocalizedText source="新建研究" />
              <Sparkles data-icon="inline-end" />
            </Link>
          </Button>
        </CardContent>
      </Card>
    </ProductShell>
  );
}
