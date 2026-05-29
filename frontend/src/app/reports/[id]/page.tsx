import Link from "next/link";
import { ArrowRight, BarChart3 } from "lucide-react";

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
import { opportunities, reportSections } from "@/features/product-skeleton/data";

export function generateStaticParams() {
  return [{ id: "demo-report" }];
}

export default function ReportPage() {
  return (
    <ProductShell
      active="report"
      title="最终报告"
      description="汇总推荐排序、商机摘要、风险摘要和下一步行动。"
      action={
        <Button asChild>
          <Link href="/opportunities">
            商机推荐
            <BarChart3 data-icon="inline-end" />
          </Link>
        </Button>
      }
      aside={<ProductSummaryAside />}
    >
      <div className="grid gap-5">
        <Card className="rounded-lg">
          <CardHeader>
            <Badge variant="secondary" className="w-fit">演示报告</Badge>
            <CardTitle className="text-2xl">5000 元内中文内容平台商机研究</CardTitle>
            <CardDescription>
              汇总推荐排序、商机摘要、风险摘要和下一步行动摘要。
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            {reportSections.map((section) => (
              <section key={section.title} className="rounded-lg border bg-background p-4">
                <h2 className="font-semibold">{section.title}</h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  {section.content}
                </p>
              </section>
            ))}
          </CardContent>
        </Card>

        <Card className="overflow-hidden rounded-lg py-0 shadow-none">
          <CardHeader className="border-b px-5 py-4">
            <CardTitle>推荐排序</CardTitle>
            <CardDescription>报告中可回看全部候选商机。</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50 hover:bg-muted/50">
                  <TableHead className="px-5">排序</TableHead>
                  <TableHead>商机</TableHead>
                  <TableHead>预算</TableHead>
                  <TableHead>风险</TableHead>
                  <TableHead className="pr-5 text-right">详情</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {opportunities.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="px-5">
                      <Badge variant="outline">{item.rank}</Badge>
                    </TableCell>
                    <TableCell className="font-medium">{item.name}</TableCell>
                    <TableCell>{item.budget}</TableCell>
                    <TableCell>{item.risk}</TableCell>
                    <TableCell className="pr-5 text-right">
                      <Button asChild variant="ghost" size="sm">
                        <Link href={`/opportunities/${item.id}`}>
                          打开
                          <ArrowRight data-icon="inline-end" />
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </ProductShell>
  );
}
