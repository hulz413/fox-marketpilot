import Link from "next/link";
import { ArrowRight, FileText } from "lucide-react";

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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  EmptyResearchState,
  ProductShell,
  ProductSummaryAside,
  StatusBadge,
  TaskStateCards,
} from "@/features/product-skeleton/components";
import { researchTasks } from "@/features/product-skeleton/data";

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
        <EmptyResearchState />
        <TaskStateCards />
        <Card className="overflow-hidden rounded-lg py-0 shadow-none">
          <CardHeader className="flex flex-row items-center justify-between gap-4 border-b px-5 py-4">
            <div>
              <CardTitle>研究任务列表</CardTitle>
              <CardDescription>演示任务用于展示运行中、失败和完成状态。</CardDescription>
            </div>
            <Badge variant="secondary">演示任务</Badge>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table className="min-w-[760px]">
                <TableHeader>
                  <TableRow className="bg-muted/50 hover:bg-muted/50">
                    <TableHead className="h-14 px-5">任务标题</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>当前阶段</TableHead>
                    <TableHead>创建时间</TableHead>
                    <TableHead className="pr-5 text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {researchTasks.map((task) => (
                    <TableRow key={task.id} className="h-16">
                      <TableCell className="px-5">
                        <p className="font-medium">{task.title}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{task.summary}</p>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={task.status} />
                      </TableCell>
                      <TableCell>{task.stage}</TableCell>
                      <TableCell>{task.createdAt}</TableCell>
                      <TableCell className="pr-5">
                        <div className="flex justify-end gap-2">
                          <Button asChild variant="outline" size="sm">
                            <Link href={task.primaryHref}>查看推荐</Link>
                          </Button>
                          <Button asChild variant="ghost" size="sm">
                            <Link href={task.reportHref}>
                              <FileText data-icon="inline-start" />
                              报告
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
      </div>
    </ProductShell>
  );
}
