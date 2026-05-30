import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  ClipboardList,
  FileText,
  History,
  Sparkles,
} from "lucide-react";

export type NavKey = "new" | "tasks" | "opportunities" | "report" | "history";

export type ProductNavItem = {
  key: NavKey;
  label: string;
  href: string;
  icon: LucideIcon;
};

export const productNavItems: ProductNavItem[] = [
  { key: "new", label: "新建研究", href: "/research/new", icon: Sparkles },
  { key: "tasks", label: "研究任务", href: "/research/tasks", icon: ClipboardList },
  { key: "opportunities", label: "商机推荐", href: "/opportunities", icon: BarChart3 },
  { key: "report", label: "最终报告", href: "/reports", icon: FileText },
  { key: "history", label: "研究历史", href: "/history", icon: History },
];

export const samplePrompts = [
  "预算 5000 元以内，从 1688 找适合小红书种草的产品，不做食品和电子产品。",
  "找适合社群团购的宠物清洁用品，首批验证预算控制在 3000 元内。",
  "面向租房办公人群，寻找低库存、可内容种草的桌面小物。",
];
