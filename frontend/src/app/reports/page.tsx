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
      active="tasks"
      title="选择研究结果"
      description="报告需要绑定一条真实研究。请先从我的研究里选择已完成任务。"
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
              <LocalizedText source="返回我的研究" />
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/">
              <LocalizedText source="新建研究" />
              <Sparkles data-icon="inline-end" />
            </Link>
          </Button>
        </CardContent>
      </Card>
    </ProductShell>
  );
}
