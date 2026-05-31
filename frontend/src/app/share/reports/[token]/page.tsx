import type { Metadata } from "next";

import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { SharedReportView } from "@/features/reports/shared-report";
import { fetchPublicReportShare } from "@/features/research/api";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "分享报告 | MarketPilot",
  description: "在线浏览 MarketPilot 商机研究分享报告",
};

export default async function SharedReportPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  let share: Awaited<ReturnType<typeof fetchPublicReportShare>>;

  try {
    share = await fetchPublicReportShare(token);
  } catch {
    return (
      <main className="flex min-h-screen items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md rounded-lg border-dashed">
          <CardHeader>
            <CardTitle>分享报告不可访问</CardTitle>
            <CardDescription>
              链接不存在、已撤销，或后端服务暂时无法读取该报告。
            </CardDescription>
          </CardHeader>
        </Card>
      </main>
    );
  }

  return <SharedReportView share={share} />;
}
