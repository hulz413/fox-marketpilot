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
  ProductShell,
  ProductSummaryAside,
} from "@/features/product-skeleton/components";
import { opportunities } from "@/features/product-skeleton/data";

export default function OpportunitiesPage() {
  return (
    <ProductShell
      active="opportunities"
      title="商机推荐"
      description="每次研究任务完成后，这里展示 3-5 个可用小预算验证的商机。"
      action={
        <Button asChild>
          <Link href="/reports/demo-report">
            最终报告
            <FileText data-icon="inline-end" />
          </Link>
        </Button>
      }
      aside={<ProductSummaryAside />}
    >
      <Card className="overflow-hidden rounded-lg py-0 shadow-none">
        <CardHeader className="flex flex-row items-center justify-between gap-4 border-b px-5 py-4">
          <div>
            <CardTitle>商机推荐列表</CardTitle>
            <CardDescription>展示名称、人群、预算、风险和优先级。</CardDescription>
          </div>
          <Badge variant="secondary">{opportunities.length} 个推荐</Badge>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table className="min-w-[820px]">
              <TableHeader>
                <TableRow className="bg-muted/50 hover:bg-muted/50">
                  <TableHead className="h-14 px-5">排序</TableHead>
                  <TableHead>商机名称</TableHead>
                  <TableHead>目标人群</TableHead>
                  <TableHead>验证预算</TableHead>
                  <TableHead>风险等级</TableHead>
                  <TableHead>推荐优先级</TableHead>
                  <TableHead className="pr-5 text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {opportunities.map((item) => (
                  <TableRow key={item.id} className="h-16">
                    <TableCell className="px-5">
                      <Badge variant="outline">{item.rank}</Badge>
                    </TableCell>
                    <TableCell>
                      <p className="font-medium">{item.name}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{item.direction}</p>
                    </TableCell>
                    <TableCell>{item.audience}</TableCell>
                    <TableCell>{item.budget}</TableCell>
                    <TableCell>{item.risk}</TableCell>
                    <TableCell>
                      <Badge className="rounded-full bg-primary/10 text-primary">
                        {item.priority}
                      </Badge>
                    </TableCell>
                    <TableCell className="pr-5 text-right">
                      <Button asChild variant="outline" size="sm">
                        <Link href={`/opportunities/${item.id}`}>
                          详情
                          <ArrowRight data-icon="inline-end" />
                        </Link>
                      </Button>
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
