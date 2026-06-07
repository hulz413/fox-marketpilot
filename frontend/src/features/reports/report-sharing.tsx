"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  Copy,
  ExternalLink,
  Link2Off,
  RefreshCcw,
  Share2,
} from "lucide-react";

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
  createReportShare,
  fetchTaskReportShares,
  revokeReportShare,
  type ReportShare,
} from "@/features/research/api";
import { formatDateTime } from "@/lib/datetime";

export function ReportSharePanel({ taskUuid }: { taskUuid: string }) {
  const queryClient = useQueryClient();
  const [copiedToken, setCopiedToken] = useState<string | null>(null);
  const [copyError, setCopyError] = useState<string | null>(null);
  const {
    data: shares,
    error,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["report-shares", taskUuid],
    queryFn: () => fetchTaskReportShares(taskUuid),
  });
  const createMutation = useMutation({
    mutationFn: () => createReportShare(taskUuid),
    onSuccess: async (share) => {
      await queryClient.invalidateQueries({ queryKey: ["report-shares", taskUuid] });
      await copyShareLink(share);
    },
  });
  const revokeMutation = useMutation({
    mutationFn: (shareUuids: string[]) =>
      Promise.all(shareUuids.map((shareUuid) => revokeReportShare(shareUuid))),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["report-shares", taskUuid] });
    },
  });
  const activeShares = shares?.filter((share) => share.status === "active") ?? [];
  const activeShare = activeShares[0] ?? null;
  const latestShare = activeShare ?? shares?.[0] ?? null;
  const shareUrl = activeShare ? buildShareUrl(activeShare.share_token) : null;
  const actionError = createMutation.error ?? revokeMutation.error ?? error;

  async function copyShareLink(share: ReportShare) {
    const url = buildShareUrl(share.share_token);
    setCopyError(null);

    if (!navigator.clipboard) {
      setCopyError("当前浏览器不支持自动复制，请手动打开分享页后复制地址。");
      return;
    }

    try {
      await navigator.clipboard.writeText(url);
      setCopiedToken(share.share_token);
    } catch {
      setCopyError("复制失败，请手动打开分享页后复制地址。");
    }
  }

  return (
    <Card className="rounded-lg">
      <CardHeader className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <Badge variant="secondary" className="mb-2">
            在线分享
          </Badge>
          <CardTitle>分享最终报告</CardTitle>
          <CardDescription>
            生成只读链接后，收件人可直接在线浏览当前报告快照。
          </CardDescription>
        </div>
        <Button
          type="button"
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending}
        >
          <Share2 data-icon="inline-start" />
          {createMutation.isPending ? "生成中" : "生成分享链接"}
        </Button>
      </CardHeader>
      <CardContent className="grid gap-4">
        {isLoading ? (
          <div className="h-16 rounded-md border bg-muted/40" />
        ) : latestShare ? (
          <div className="grid gap-3 rounded-md border bg-background p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={latestShare.status === "active" ? "default" : "outline"}>
                {latestShare.status === "active" ? "可访问" : "已撤销"}
              </Badge>
              <span className="text-sm text-muted-foreground">
                {formatDateTime(latestShare.created_at)}
              </span>
            </div>
            {shareUrl ? (
              <p className="max-w-full truncate rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground">
                {shareUrl}
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">
                最近的分享链接已撤销，可重新生成新的只读链接。
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              {activeShare ? (
                <>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => void copyShareLink(activeShare)}
                  >
                    <Copy data-icon="inline-start" />
                    {copiedToken === activeShare.share_token ? "已复制" : "复制链接"}
                  </Button>
                  <Button asChild variant="outline">
                    <Link href={`/share/reports/${activeShare.share_token}`} target="_blank">
                      <ExternalLink data-icon="inline-start" />
                      打开分享页
                    </Link>
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() =>
                      revokeMutation.mutate(
                        activeShares.map((share) => share.uuid),
                      )
                    }
                    disabled={revokeMutation.isPending || !activeShares.length}
                  >
                    <Link2Off data-icon="inline-start" />
                    {revokeMutation.isPending ? "撤销中" : "撤销分享"}
                  </Button>
                </>
              ) : null}
            </div>
          </div>
        ) : (
          <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            还没有分享链接。生成后会固定当前报告内容，后续重新运行不会覆盖旧链接。
          </p>
        )}

        {copyError ? (
          <p className="text-sm text-destructive">{copyError}</p>
        ) : null}

        {actionError ? (
          <div className="flex flex-wrap items-center gap-3 rounded-md border border-destructive/30 p-3 text-sm text-destructive">
            <span>
              分享功能暂不可用，不影响继续阅读报告：
              {actionError instanceof Error ? actionError.message : "请求失败"}
            </span>
            {error ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => void refetch()}
              >
                <RefreshCcw data-icon="inline-start" />
                重试
              </Button>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function buildShareUrl(token: string) {
  if (typeof window === "undefined") {
    return `/share/reports/${token}`;
  }

  return `${window.location.origin}/share/reports/${token}`;
}
