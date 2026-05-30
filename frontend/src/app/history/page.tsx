import Link from "next/link";
import { ArrowRight, RefreshCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ProductShell,
  StatusBadge,
} from "@/features/product-skeleton/components";
import { historyRows } from "@/features/product-skeleton/data";

export default function HistoryPage() {
  return (
    <ProductShell
      active="history"
      title="研究历史"
      description="回看之前完成、运行中或失败的商机研究任务。"
      action={
        <Button asChild>
          <Link href="/research/new">新建研究</Link>
        </Button>
      }
    >
        <Card className="overflow-hidden rounded-lg py-0 shadow-none">
          <CardHeader className="border-b px-5 py-4">
            <CardTitle>历史研究列表</CardTitle>
          <CardDescription>保留已完成、运行中和失败任务的继续入口。</CardDescription>
          </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table className="min-w-[760px]">
              <TableHeader>
                <TableRow className="bg-muted/50 hover:bg-muted/50">
                  <TableHead className="h-14 px-5">任务标题</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead className="pr-5 text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {historyRows.map((row) => (
                  <TableRow key={row.id} className="h-16">
                    <TableCell className="px-5 font-medium">{row.title}</TableCell>
                    <TableCell>{row.createdAt}</TableCell>
                    <TableCell>
                      <StatusBadge status={row.status} />
                    </TableCell>
                    <TableCell className="pr-5">
                      <div className="flex justify-end gap-2">
                        <Button asChild variant="outline" size="sm">
                          <Link href={row.reportHref}>
                            报告
                            <ArrowRight data-icon="inline-end" />
                          </Link>
                        </Button>
                        <Button asChild variant="ghost" size="sm">
                          <Link href="/research/new">
                            <RefreshCcw data-icon="inline-start" />
                            重新运行
                          </Link>
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </ProductShell>
  );
}
