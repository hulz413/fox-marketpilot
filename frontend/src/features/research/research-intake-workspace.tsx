"use client";

import { FilePenLine, MessageCircle } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useLanguage } from "@/features/i18n/language-provider";
import { ProductShell } from "@/features/product-skeleton/components";

import type { ResearchIntakeDraft } from "./api";
import { NewResearchForm } from "./new-research-form";
import { ResearchIntakeChat } from "./research-intake-chat";

type ResearchIntakeMode = "chat" | "form";

export function ResearchIntakeWorkspace() {
  const { t } = useLanguage();
  const [mode, setMode] = useState<ResearchIntakeMode>("chat");
  const [formDraft, setFormDraft] = useState<{
    draft: ResearchIntakeDraft;
    version: number;
  } | null>(null);
  const isChatMode = mode === "chat";

  function editDraftInForm(draft: ResearchIntakeDraft) {
    setFormDraft((current) => ({
      draft,
      version: (current?.version ?? 0) + 1,
    }));
    setMode("form");
  }

  return (
    <ProductShell
      active="new"
      title="新建研究"
      description="通过聊天或表单把商机想法整理成可启动的研究任务。"
      breadcrumbAction={
        <Button
          type="button"
          variant="outline"
          onClick={() => setMode(isChatMode ? "form" : "chat")}
        >
          {isChatMode ? t("表单模式") : t("聊天模式")}
          {isChatMode ? (
            <FilePenLine data-icon="inline-end" />
          ) : (
            <MessageCircle data-icon="inline-end" />
          )}
        </Button>
      }
      contentScroll={false}
    >
      <div className="h-full min-h-0" hidden={!isChatMode}>
        <ResearchIntakeChat onEditDraft={editDraftInForm} />
      </div>
      <div className="h-full min-h-0 overflow-y-auto" hidden={isChatMode}>
        <NewResearchForm
          initialDraft={formDraft?.draft}
          initialDraftVersion={formDraft?.version}
        />
      </div>
    </ProductShell>
  );
}
