"use client";

import { useState, useRef, useEffect, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Header from "@/components/header";
import { useMounted } from "@/hooks/use-mounted";
import { Textarea } from "@/components/ui/textarea";
import {
  Upload,
  Send,
  FileText,
  X,
  BookOpen,
  Loader2,
  AlertCircle,
  CheckCircle,
  ImageIcon,
  Library,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { applyBasePath } from "@/lib/utils";
import { INITIAL_FILES } from "@/lib/knowledge-data";

type Mode = "upload" | "standard" | "atlas";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  attachedFileName?: string;
  streaming?: boolean;
}

interface KnowledgeBaseItem {
  id: string;
  title: string;
  fileId?: string;
  category: "standard" | "atlas";
  /**
   * public 目录下真实 PDF 文件名(用于在线预览与下载)。
   * 仅对入库到本地 public 目录的初始研报/图表文档设置;
   * 用户通过 Dify 上传入库的条目不带该字段,因此不显示预览/下载按钮。
   */
  fileName?: string;
}

interface UploadStatus {
  status: "idle" | "uploading" | "success" | "error";
  message: string;
}

const SAVED_CHATS_KEY = "knowflow-saved-chats";

type SavedChatMessage = Omit<Message, "timestamp"> & { timestamp: string };

/** 已保存的历史对话(localStorage 持久化,最多保留 20 条) */
interface SavedChat {
  id: string;
  mode: Mode;
  title: string;
  savedAt: string;
  messages: SavedChatMessage[];
}

/**
 * 将 Dify 返回的图片/文件 URL 转换为通过 Next.js 代理的路径
 */
function transformDifyImageUrl(src: string): string {
  if (!src) return src;
  if (src.startsWith("/dify/")) return src;
  if (src.startsWith("https://")) return src;
  if (src.startsWith("data:")) return src;
  if (src.startsWith("http://127.0.0.1") || src.startsWith("http://localhost")) {
    try {
      const url = new URL(src);
      return `/dify${url.pathname}${url.search}${url.hash}`;
    } catch {
      return src;
    }
  }
  if (src.startsWith("/files/") || src.startsWith("/api/files/")) {
    return `/dify${src}`;
  }
  return src;
}

const MODE_LABELS: Record<Mode, string> = {
  upload: "上传知识库",
  standard: "研报检索",
  atlas: "图表检索",
};

// Mock 研报检索回答：当用户在“研报检索”模式输入“上市公司财务风险分析”时，
// 不调用 API，思考 2s 后直接流式输出以下内容（来源：public/mock-研报检索.doc）。
const MOCK_STANDARD_ANSWER = `# 上市公司财务风险分析要点与研报整合解析

## 1. 财务风险分析的基本原则与框架

### 1.1 分析框架总体原则

依据《上市公司信息披露管理办法》及监管层对定期报告的要求，财务风险分析应以**真实性、完整性与可比性**为原则，围绕资产负债表、利润表与现金流量表展开。分析需结合公司所处行业特征与商业模式，避免单一指标误判。

### 1.2 四大能力维度

财务风险识别通常从四个维度展开：

- **偿债能力**：流动比率、速动比率、资产负债率、利息保障倍数。
- **营运能力**：应收账款周转率、存货周转率、总资产周转率。
- **盈利能力**：毛利率、净利率、ROE、ROIC。
- **现金流质量**：经营性现金流/净利润比值、自由现金流。

## 2. 关键风险点与识别方法

### 2.1 偿债风险

资产负债率持续攀升、短期债务占比过高、利息保障倍数低于行业均值，均构成偿债风险信号。监管要求上市公司在年报中披露有息负债结构及偿债安排，分析时应结合授信额度与再融资能力综合判断。

### 2.2 现金流风险

经营性现金流长期低于净利润，往往预示利润质量不佳，可能存在应收账款虚增或存货积压。**经营活动现金流净额连续两期为负**是重要预警指标，需进一步核查应收账款的账龄结构与客户集中度。

### 2.3 合规与审计风险

关注审计意见类型、关键审计事项、关联交易占比、商誉减值等异常信号。被出具**保留意见或无法表示意见**的审计报告，属于重大风险提示。

## 3. 行业对比与结论

### 3.1 同业对比口径

财务风险判断不能脱离行业基准。应选取同行业、同规模、同发展阶段的可比公司，采用中位数或四分位口径进行横向对比。

### 3.2 结论与跟踪

综合评级：**低 / 中 / 高**三档风险。高风险标的需结合公告、新闻与监管问询函持续跟踪，并在投资决策中予以折价或回避。

---

本内容为研报检索整合结果，仅作参考，不构成投资建议。具体决策请核对公司定期报告与监管公告原文。`;

// Mock 图表检索回答：当用户在“图表检索”模式输入“资产负债率趋势图”时，
// 不调用 API，思考 2s 后直接流式输出以下内容（含图片）。
// 文本来源：public/mock-图表检索.doc；图片：public/mock-atlas/image1.jpeg、image2.jpeg。
const MOCK_ATLAS_ANSWER = `**📈 图表 1：资产负债率趋势对比**

![公司资产负债率 vs 行业均值(2020-2025)](/mock-atlas/image1.png)

**📋 解读**

- **图表名称：** 公司资产负债率与行业均值对比（2020—2025）
- **趋势：** 公司资产负债率由 2020 年约 68% 逐步降至 2025 年约 55%，杠杆水平持续改善。
- **对比：** 行业均值稳定在 58%—62% 区间，公司自 2023 年起低于行业均值，偿债压力边际缓解。
- **要点：** 需结合有息负债结构进一步确认，若降杠杆主要来自应付账款扩张而非有息负债偿还，则质量存疑。

---

**📈 图表 2：营收与经营性现金流**

![营业收入与经营活动现金流(2023-2025)](/mock-atlas/image2.png)

**📋 解读**

- **图表名称：** 营业收入与经营活动现金流净额（2023—2025）
- **趋势：** 营业收入保持 15% 以上增速，2025 年达 86 亿元。
- **质量：** 经营性现金流净额同步增长，2025 年现金流/净利润比值约 1.2，利润含金量较高。
- **要点：** 若营收增长而现金流持续背离，应警惕应收账款与存货风险，本图呈现健康匹配形态。`;

function SearchContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [activeMode, setActiveMode] = useState<Mode>("standard");
  // 根因修复：Trae 预览运行时在服务端向 DOM 注入 `data-trae-ref` 等属性，
  // 客户端水合时不复现，触发 React Hydration Error #185。
  // 服务端/首帧统一返回 null，挂载后再渲染真实 UI，从根因上消除不一致。
  const mounted = useMounted();
  useEffect(() => {
    const fromUrl =
      (searchParams.get("category") as Mode | null) || "standard";
    if (["upload", "standard", "atlas"].includes(fromUrl)) {
      setActiveMode(fromUrl);
    }
  }, [searchParams]);
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({
    status: "idle",
    message: "",
  });

  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- 历史对话保存(localStorage 持久化) ---
  const [savedChats, setSavedChats] = useState<SavedChat[]>([]);
  const savedChatsLoadedRef = useRef(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(SAVED_CHATS_KEY);
      if (raw) setSavedChats(JSON.parse(raw) as SavedChat[]);
    } catch {
      // localStorage 不可用或数据损坏时静默降级为无历史
    }
    savedChatsLoadedRef.current = true;
  }, []);

  useEffect(() => {
    if (!savedChatsLoadedRef.current) return;
    try {
      window.localStorage.setItem(SAVED_CHATS_KEY, JSON.stringify(savedChats));
    } catch {
      // 存储空间不足时静默失败
    }
  }, [savedChats]);

  const handleSaveConversation = () => {
    if (messages.length === 0) return;
    const firstUser = messages.find((m) => m.role === "user");
    const chat: SavedChat = {
      id: `sc-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
      mode: activeMode,
      title: firstUser
        ? firstUser.content.slice(0, 30)
        : `${MODE_LABELS[activeMode]}对话`,
      savedAt: new Date().toISOString(),
      messages: messages.map((m) => ({
        ...m,
        timestamp: m.timestamp.toISOString(),
        streaming: false,
      })),
    };
    setSavedChats((prev) => [chat, ...prev].slice(0, 20));
    setUploadStatus({ status: "success", message: "对话已保存到本地" });
  };

  const handleRestoreConversation = (chat: SavedChat) => {
    setActiveMode(chat.mode);
    setMessages(
      chat.messages.map((m) => ({ ...m, timestamp: new Date(m.timestamp) }))
    );
    setUploadStatus({ status: "idle", message: "" });
  };

  const handleDeleteSavedChat = (id: string) => {
    setSavedChats((prev) => prev.filter((c) => c.id !== id));
  };

  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBaseItem[]>([
    {
      id: "kb-init-1",
      title: "2025年半导体行业深度研报-摘要",
      category: "standard",
    },
    {
      id: "kb-init-2",
      title: "沪深300估值分位图",
      category: "atlas",
    },
  ]);

  const [conversationId, setConversationId] = useState<Record<Mode, string>>({
    upload: "",
    standard: "",
    atlas: "",
  });

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const msgIdRef = useRef(0);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // --- File handling ---
  const validateFile = (file: File): string | null => {
    if (file.size > 50 * 1024 * 1024) return "文件大小不能超过 50MB";
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf"))
      return "仅支持 PDF 文件格式";
    return null;
  };

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const error = validateFile(file);
      if (error) {
        setUploadStatus({ status: "error", message: error });
        return;
      }
      setAttachedFile(file);
      setUploadStatus({ status: "idle", message: "" });
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      const error = validateFile(file);
      if (error) {
        setUploadStatus({ status: "error", message: error });
        return;
      }
      setAttachedFile(file);
      setUploadStatus({ status: "idle", message: "" });
      // Switch to upload mode automatically
      setActiveMode("upload");
    }
  };

  const removeAttachedFile = () => {
    setAttachedFile(null);
    setUploadStatus({ status: "idle", message: "" });
  };

  // --- Mode switching ---
  const handleModeSwitch = (mode: Mode) => {
    setActiveMode(mode);
    setAttachedFile(null);
    setUploadStatus({ status: "idle", message: "" });
  };

  // --- Knowledge import ---
  const handleKnowledgeImport = useCallback(
    async (importCommand: "研报入库" | "图表入库", rawQuestion?: string) => {
      if (!attachedFile) {
        setUploadStatus({
          status: "error",
          message: "请先上传 PDF 文件",
        });
        return;
      }

      // 精确文件名 + 命令文本 匹配：命中则本地模拟入库，不调用 API
      const EXACT_PAIRS: Array<{
        fileName: string;
        command: "研报入库" | "图表入库";
        kb: KnowledgeBaseItem;
      }> = [
        {
          fileName: "2025年半导体行业深度研报.pdf",
          command: "研报入库",
          kb: {
            id: "kb-predefined-report2025",
            title: "2025年半导体行业深度研报-摘要",
            category: "standard",
          },
        },
        {
          fileName: "沪深300估值分位图.pdf",
          command: "图表入库",
          kb: {
            id: "kb-predefined-chart006",
            title: "沪深300估值分位图",
            category: "atlas",
          },
        },
      ];

      const matched = EXACT_PAIRS.find(
        (p) =>
          attachedFile.name === p.fileName && importCommand === p.command
      );

      // 命令文本存在时必须严格等于 importCommand；否则报错
      if (typeof rawQuestion === "string") {
        if (rawQuestion !== importCommand) {
          setUploadStatus({
            status: "error",
            message: `请在输入框中准确输入 "${importCommand}" 来执行该入库操作（当前输入不匹配）。`,
          });
          return;
        }
      }

      if (matched) {
        // 本地模拟入库：展示指定 KB tag（不调用 /api/dify/upload）
        setUploadStatus({
          status: "uploading",
          message: `正在上传文件并${importCommand}...`,
        });
        setIsLoading(true);
        await new Promise((r) => setTimeout(r, 800));

        setKnowledgeBases((prev) => {
          if (prev.some((k) => k.id === matched.kb.id)) return prev;
          return [...prev, { ...matched.kb }];
        });
        setUploadStatus({
          status: "success",
          message: `"${matched.kb.title}" 已成功${importCommand}`,
        });
        msgIdRef.current += 1;
        const systemMsg: Message = {
          id: `msg-${msgIdRef.current}`,
          role: "assistant",
          content: `文件 "${matched.kb.title}" 已成功${importCommand}。您可以在对应的检索模式中输入问题进行查询。`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, systemMsg]);
        setAttachedFile(null);
        setIsLoading(false);
        setTimeout(() => {
          setUploadStatus((prev) =>
            prev.status === "success" || prev.status === "error"
              ? { status: "idle", message: "" }
              : prev
          );
        }, 5000);
        return;
      }

      // 未命中：区分错误原因，给出精准错误提示
      const matchedName = EXACT_PAIRS.find(
        (p) => attachedFile.name === p.fileName
      );
      if (matchedName) {
        setUploadStatus({
          status: "error",
          message: `文件 "${attachedFile.name}" 只能用于 "${matchedName.command}"，当前选择的 "${importCommand}" 不匹配，请切换为 "${matchedName.command}" 后重试。`,
        });
        return;
      }
      const matchedCmd = EXACT_PAIRS.find((p) => importCommand === p.command);
      if (matchedCmd) {
        setUploadStatus({
          status: "error",
          message: `执行 "${importCommand}" 需要选择文件名完全为 "${matchedCmd.fileName}" 的 PDF，当前文件 "${attachedFile.name}" 不匹配。`,
        });
        return;
      }
      setUploadStatus({
        status: "error",
        message: `上传文件或入库指令不在预置列表中（支持 "${EXACT_PAIRS.map(
          (p) => p.fileName + " + " + p.command
        ).join("、")}"）。`,
      });
      return;
    },
    [attachedFile]
  );

  // --- Send message (search) ---
  const handleSend = useCallback(
    async (textOverride?: string) => {
      const question = textOverride || inputValue.trim();
      if (!question || isLoading) return;

      // Upload mode: check for import commands
      if (activeMode === "upload" && attachedFile) {
        if (question === "研报入库") {
          await handleKnowledgeImport("研报入库", question);
          setInputValue("");
          return;
        }
        if (question === "图表入库") {
          await handleKnowledgeImport("图表入库", question);
          setInputValue("");
          return;
        }
        // If in upload mode with file but no import command
        setUploadStatus({
          status: "error",
          message:
            '请在输入框中准确输入 "研报入库" 或 "图表入库" 来分类上传文件（注意：文本必须严格匹配，不含多余字符）。',
        });
        return;
      }

      // Search mode (standard / atlas)
      msgIdRef.current += 1;
      const userMsg: Message = {
        id: `msg-${msgIdRef.current}`,
        role: "user",
        content: question,
        timestamp: new Date(),
        attachedFileName: attachedFile?.name,
      };
      setMessages((prev) => [...prev, userMsg]);
      setInputValue("");
      setIsLoading(true);

      msgIdRef.current += 1;
      const assistantId = `msg-${msgIdRef.current}-ai`;
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        streaming: true,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // 优先调用真实后端（Financial-RAG-Agent /api/chat），失败时回退内置 mock 演示
      try {
        const response = await fetch("/api/finance/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question, top_k: 5 }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(
            errorData.error || "后端调用失败 (" + response.status + ")"
          );
        }

        const data = await response.json();
        const answer = (data.answer || "").trim();
        if (!answer) throw new Error("后端返回空回答");

        // 流式输出后端回答
        const chunkSize = 12;
        for (let i = 0; i < answer.length; i += chunkSize) {
          const partial = answer.slice(0, i + chunkSize);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: partial } : m
            )
          );
          await new Promise((r) => setTimeout(r, 12));
        }
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, streaming: false } : m
          )
        );
        setIsLoading(false);
        return;
      } catch (err) {
        // 后端不可用时回退到内置 mock 演示
        const isStandardMock =
          activeMode === "standard" && question.includes("上市公司财务风险分析");
        const isAtlasMock =
          activeMode === "atlas" && question.includes("资产负债率趋势图");
        if (isStandardMock || isAtlasMock) {
          const mockContent = isAtlasMock ? MOCK_ATLAS_ANSWER : MOCK_STANDARD_ANSWER;
          await new Promise((resolve) => setTimeout(resolve, 2000));
          if (isAtlasMock) {
            // 图表按段落流式，保证图片标签整体出现不被截断
            const segments = mockContent.split("\n\n");
            for (let s = 1; s <= segments.length; s++) {
              const partial = segments.slice(0, s).join("\n\n");
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId ? { ...m, content: partial } : m
                )
              );
              await new Promise((r) => setTimeout(r, 200));
            }
          } else {
            // 研报按字符流式
            const mockChunkSize = 10;
            for (let i = 0; i < mockContent.length; i += mockChunkSize) {
              const partial = mockContent.slice(0, i + mockChunkSize);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId ? { ...m, content: partial } : m
                )
              );
              await new Promise((r) => setTimeout(r, 15));
            }
          }
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, streaming: false } : m
            )
          );
          setIsLoading(false);
          return;
        }
        const errorMsg =
          err instanceof Error ? err.message : "检索服务暂时不可用";
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: "❌ " + errorMsg } : m
          )
        );
        setIsLoading(false);
      }
    },
    [inputValue, isLoading, attachedFile, activeMode, conversationId, handleKnowledgeImport]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleBack = () => router.push("/");

  const handleModeButtonClick = (mode: Mode) => {
    if (mode !== activeMode) {
      handleModeSwitch(mode);
      return;
    }
    if (activeMode !== "upload" && inputValue.trim()) {
      handleSend();
    } else {
      textareaRef.current?.focus();
    }
  };

  // 角标数字与「知识库」页真实数据保持一致(研报 20 / 图表 10)
  const standardCount = INITIAL_FILES.filter(
    (f) => f.folder === "standard"
  ).length;
  const atlasCount = INITIAL_FILES.filter((f) => f.folder === "atlas").length;

  const hasMessages = messages.length > 0;
  const modeLabel = MODE_LABELS[activeMode];

  const getPlaceholder = () => {
    if (activeMode === "upload") {
      if (attachedFile)
        return '输入"研报入库"或"图表入库"来分类上传文件...';
      return "点击上传按钮或拖入 PDF 文件，然后输入分类指令...";
    }
    if (activeMode === "standard") {
      return "研报检索——输入问题开始检索，例如上市公司财务风险分析";
    }
    if (activeMode === "atlas") {
      return "图表检索——输入问题开始检索，例如资产负债率趋势图";
    }
    return `${modeLabel} — 输入问题开始检索...`;
  };

  if (!mounted) return null;

  return (
    <div className="flex h-screen flex-col bg-background">
      <Header />

      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <aside className="w-64 shrink-0 border-r border-border bg-muted/20 overflow-y-auto">
          <div className="p-4">
            <button
              onClick={handleBack}
              className="mb-4 flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="h-4 w-4"
              >
                <path d="m12 19-7-7 7-7" />
                <path d="M19 12H5" />
              </svg>
              返回首页
            </button>

            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              历史对话
            </h3>
            <div className="space-y-1">
              {messages
                .filter((m) => m.role === "user")
                .slice(-5)
                .reverse()
                .map((msg) => (
                  <button
                    key={msg.id}
                    className="flex w-full items-start gap-2 rounded-lg px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted/50"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
                    >
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                    </svg>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-foreground">
                        {msg.content}
                      </div>
                    </div>
                  </button>
                ))}
            </div>

            {hasMessages ? (
              <button
                onClick={handleSaveConversation}
                className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium text-foreground transition-colors hover:bg-muted/60"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-3.5 w-3.5"
                >
                  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
                  <polyline points="17 21 17 13 7 13 7 21" />
                  <polyline points="7 3 7 8 15 8" />
                </svg>
                保存当前对话
              </button>
            ) : null}

            {savedChats.length > 0 ? (
              <div className="mt-5">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  已保存对话({savedChats.length})
                </h3>
                <div className="space-y-1">
                  {savedChats.map((chat) => (
                    <div key={chat.id} className="group flex items-center gap-1">
                      <button
                        onClick={() => handleRestoreConversation(chat)}
                        title="点击恢复该对话"
                        className="flex min-w-0 flex-1 items-start gap-2 rounded-lg px-3 py-2 text-left transition-colors hover:bg-muted/50"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
                        >
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                          <polyline points="14 2 14 8 20 8" />
                        </svg>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm text-foreground">
                            {chat.title}
                          </span>
                          <span className="block truncate text-xs text-muted-foreground">
                            {MODE_LABELS[chat.mode]} ·{" "}
                            {new Date(chat.savedAt).toLocaleDateString()}
                          </span>
                        </span>
                      </button>
                      <button
                        onClick={() => handleDeleteSavedChat(chat.id)}
                        title={`删除「${chat.title}」`}
                        aria-label={`删除 ${chat.title}`}
                        className="mr-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-muted-foreground opacity-0 transition-all hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex flex-1 flex-col overflow-hidden">
          {!hasMessages ? (
            <div className="flex flex-1 flex-col items-center px-6 pt-16" suppressHydrationWarning>
              <div className="mx-auto w-full max-w-5xl">
                <div className="flex gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10" suppressHydrationWarning>
                    {activeMode === "atlas" ? (
                      <ImageIcon className="h-5 w-5 text-primary" />
                    ) : activeMode === "upload" ? (
                      <Library className="h-5 w-5 text-primary" />
                    ) : (
                      <BookOpen className="h-5 w-5 text-primary" />
                    )}
                  </div>
                  <div className="flex-1 rounded-2xl border border-border bg-card px-5 py-4" suppressHydrationWarning>
                    <div className="text-sm leading-relaxed text-foreground" suppressHydrationWarning>
                      您好，我是 FinFlow Agent，您的智能检索助手。当前模式：
                      <span className="font-semibold text-primary" suppressHydrationWarning>
                        {modeLabel}
                      </span>
                    </div>
                    <ul className="mt-2 space-y-1 text-sm text-muted-foreground" suppressHydrationWarning>
                      {activeMode === "upload" ? (
                        <>
                          <li>
                            • 点击上传按钮或将 PDF 文件拖入输入框区域
                          </li>
                          <li>
                            • 输入&quot;研报入库&quot;或&quot;图表入库&quot;分类入库
                          </li>
                          <li>• 入库后可在对应的检索模式中查询</li>
                        </>
                      ) : (
                        <>
                          <li>• 输入问题，点击&quot;{modeLabel}&quot;按钮检索</li>
                          <li>• 支持流式输出和 Markdown 格式渲染</li>
                          <li>• 图表检索模式支持图片展示</li>
                        </>
                      )}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div
              className="flex-1 overflow-y-auto px-6 py-8"
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <div className="mx-auto max-w-5xl space-y-6">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-2xl px-5 py-3.5 ${
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "border border-border bg-card text-foreground"
                      }`}
                    >
                      {msg.attachedFileName && (
                        <div className="mb-2 flex items-center gap-1.5 text-xs opacity-80">
                          <FileText className="h-3 w-3" />
                          <span>{msg.attachedFileName}</span>
                        </div>
                      )}
                      <div className="text-sm leading-relaxed">
                        {msg.role === "assistant" ? (
                          msg.streaming ? (
                          <span className="whitespace-pre-wrap break-words">
                            {msg.content}
                            {isLoading && msg.content === "" && (
                              <span className="inline-flex gap-1">
                                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:0ms]" />
                                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:150ms]" />
                                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:300ms]" />
                              </span>
                            )}
                          </span>
                        ) : (
                          <div className="prose prose-sm max-w-none dark:prose-invert prose-img:rounded-lg prose-img:border prose-img:border-border prose-headings:font-bold prose-headings:leading-tight prose-h1:text-2xl prose-h1:mt-6 prose-h1:mb-3 prose-h2:text-xl prose-h2:mt-5 prose-h2:mb-2 prose-h3:text-lg prose-h3:mt-4 prose-h3:mb-2 prose-h4:text-base prose-h4:mt-3 prose-h4:mb-1 prose-p:my-3 prose-li:my-1 prose-strong:font-semibold">
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              rehypePlugins={[rehypeRaw]}
                              components={{
                                h1: ({ children, ...props }) => (
                                  <h1 className="text-xl font-bold mt-6 mb-3 leading-tight tracking-tight" {...props}>
                                    {children}
                                  </h1>
                                ),
                                h2: ({ children, ...props }) => (
                                  <h2 className="text-xl font-bold mt-5 mb-2 leading-tight tracking-tight" {...props}>
                                    {children}
                                  </h2>
                                ),
                                h3: ({ children, ...props }) => (
                                  <h3 className="text-lg font-bold mt-4 mb-2 leading-tight" {...props}>
                                    {children}
                                  </h3>
                                ),
                                h4: ({ children, ...props }) => (
                                  <h4 className="text-base font-bold mt-3 mb-1 leading-tight" {...props}>
                                    {children}
                                  </h4>
                                ),
                                img: ({ src, alt, ...props }) => {
                                  const imgSrc =
                                    typeof src === "string" ? src : "";
                                  // 注意：isMockAtlas 基于原始 src（加 basePath 前）判断，
                                  // 因为 /FinFlow/mock-atlas/... 仍然会命中 includes，后续同样成立。
                                  const isMockAtlas =
                                    imgSrc.includes("/mock-atlas/");
                                  const transformed = applyBasePath(
                                    transformDifyImageUrl(imgSrc)
                                  );
                                  return (
                                    <span
                                      key={transformed}
                                      className={`my-3 block overflow-hidden rounded-lg border border-border bg-muted/20 ${
                                        isMockAtlas ? "min-h-0" : "min-h-[120px]"
                                      }`}
                                    >
                                      {/* eslint-disable-next-line @next/next/no-img-element */}
                                      <img
                                        src={transformed}
                                        alt={alt || ""}
                                        className={`block object-contain ${
                                          isMockAtlas
                                            ? "mx-auto w-1/2"
                                            : "max-w-full"
                                        }`}
                                        loading="eager"
                                        decoding="async"
                                        onLoad={(e) => {
                                          const target = e.currentTarget;
                                          target.parentElement!.style.minHeight =
                                            "";
                                          target.parentElement!.style.background =
                                            "";
                                          target.style.opacity = "1";
                                        }}
                                        style={{ opacity: "0", transition: "opacity 0.2s" }}
                                        onError={(e) => {
                                          const target = e.currentTarget;
                                          if (target.dataset.fallbackApplied)
                                            return;
                                          target.dataset.fallbackApplied = "true";
                                          target.parentElement!.style.minHeight =
                                            "";
                                          target.parentElement!.style.background =
                                            "";
                                          target.style.display = "none";
                                          const placeholder =
                                            document.createElement("div");
                                          placeholder.className =
                                            "flex items-center gap-2 px-4 py-3 text-sm text-muted-foreground";
                                          placeholder.innerHTML = `<span>图片加载失败: ${alt || imgSrc}</span>`;
                                          target.parentElement!.appendChild(
                                            placeholder
                                          );
                                        }}
                                        {...props}
                                      />
                                    </span>
                                  );
                                },
                                a: ({ href, children, ...props }) => {
                                  const transformed =
                                    typeof href === "string"
                                      ? applyBasePath(transformDifyImageUrl(href))
                                      : href;
                                  return (
                                    <a
                                      href={transformed}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      {...props}
                                    >
                                      {children}
                                    </a>
                                  );
                                },
                              }}
                            >
                              {msg.content}
                            </ReactMarkdown>
                          </div>
                          )
                        ) : (
                          <span className="whitespace-pre-wrap">
                            {msg.content}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            </div>
          )}

          {/* Upload Status Toast */}
          {uploadStatus.status !== "idle" && (
            <div className="mx-auto max-w-5xl px-6" suppressHydrationWarning>
              <div
                suppressHydrationWarning
                className={`flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm ${
                  uploadStatus.status === "uploading"
                    ? "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                    : uploadStatus.status === "success"
                      ? "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300"
                      : "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300"
                }`}
              >
                {uploadStatus.status === "uploading" && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                {uploadStatus.status === "success" && (
                  <CheckCircle className="h-4 w-4" />
                )}
                {uploadStatus.status === "error" && (
                  <AlertCircle className="h-4 w-4" />
                )}
                <span suppressHydrationWarning>{uploadStatus.message}</span>
              </div>
            </div>
          )}

          {/* Bottom Chat Input Area */}
          <div className="mt-auto border-t border-border bg-background px-6 pb-5 pt-3">
            <div className="mx-auto max-w-5xl">
              {/* Attached File Display */}
              {attachedFile && (
                <div className="mb-2 flex items-center gap-2 rounded-lg bg-muted/50 px-3 py-2 text-sm">
                  <FileText className="h-4 w-4 text-primary" />
                  <span className="truncate text-foreground">
                    {attachedFile.name}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    ({(attachedFile.size / 1024 / 1024).toFixed(2)} MB)
                  </span>
                  <button
                    type="button"
                    onClick={removeAttachedFile}
                    className="ml-auto text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                onChange={handleFileChange}
              />

              {/* Input Box with drag-drop support */}
              <div
                className={`relative rounded-2xl border bg-card shadow-sm transition-all focus-within:shadow-md ${
                  isDragOver
                    ? "border-primary border-2 border-dashed"
                    : "border-border focus-within:border-primary/30"
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                {isDragOver && (
                  <div className="absolute inset-0 z-10 flex items-center justify-center rounded-2xl bg-primary/5">
                    <div className="flex flex-col items-center gap-2 text-primary">
                      <Upload className="h-8 w-8" />
                      <span className="text-sm font-medium">
                        释放鼠标上传 PDF 文件
                      </span>
                    </div>
                  </div>
                )}
                <Textarea
                  ref={textareaRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={getPlaceholder()}
                  rows={2}
                  suppressHydrationWarning
                  className="min-h-[80px] resize-none border-0 bg-transparent p-4 pr-24 text-base shadow-none focus-visible:ring-0"
                />
                <div className="absolute bottom-3 right-3 flex items-center gap-1.5" suppressHydrationWarning>
                  {activeMode === "upload" && (
                    <button
                      type="button"
                      onClick={handleFileClick}
                      className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                      title="上传 PDF 文件"
                    >
                      <Upload className="h-4 w-4" />
                    </button>
                  )}
                  <button
                    onClick={() => handleSend()}
                    disabled={
                      isLoading || (!inputValue.trim() && !attachedFile)
                    }
                    className="flex h-9 w-9 items-center justify-center rounded-lg bg-destructive text-white transition-all hover:bg-destructive/90 disabled:opacity-40"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Action Buttons(上传知识库入口已取消,知识库管理迁至 /knowledge 页) */}
              <div className="mt-3 grid grid-cols-2 gap-2" suppressHydrationWarning>
                {/* Standard Search */}
                <button
                  onClick={() => handleModeButtonClick("standard")}
                  disabled={isLoading}
                  suppressHydrationWarning
                  className={`group flex items-center justify-between rounded-xl border px-4 py-3 text-sm font-semibold transition-all ${
                    activeMode === "standard"
                      ? "border-destructive bg-destructive text-white shadow-sm"
                      : "border-border bg-card text-foreground hover:border-destructive/30 hover:bg-destructive/5"
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <BookOpen className="h-4 w-4" />
                    研报检索
                  </span>
                  <span
                    suppressHydrationWarning
                    className={`flex h-5 min-w-[20px] items-center justify-center rounded-full px-1.5 text-xs font-medium ${
                      activeMode === "standard"
                        ? "bg-white/20 text-white"
                        : "bg-muted text-muted-foreground group-hover:bg-destructive/10 group-hover:text-destructive"
                    }`}
                  >
                    {standardCount}
                  </span>
                </button>
                {/* Atlas Search */}
                <button
                  onClick={() => handleModeButtonClick("atlas")}
                  disabled={isLoading}
                  suppressHydrationWarning
                  className={`group flex items-center justify-between rounded-xl border px-4 py-3 text-sm font-semibold transition-all ${
                    activeMode === "atlas"
                      ? "border-destructive bg-destructive text-white shadow-sm"
                      : "border-border bg-card text-foreground hover:border-destructive/30 hover:bg-destructive/5"
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <ImageIcon className="h-4 w-4" />
                    图表检索
                  </span>
                  <span
                    suppressHydrationWarning
                    className={`flex h-5 min-w-[20px] items-center justify-center rounded-full px-1.5 text-xs font-medium ${
                      activeMode === "atlas"
                        ? "bg-white/20 text-white"
                        : "bg-muted text-muted-foreground group-hover:bg-destructive/10 group-hover:text-destructive"
                    }`}
                  >
                    {atlasCount}
                  </span>
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center bg-background">
          <div className="text-sm text-muted-foreground">加载中...</div>
        </div>
      }
    >
      <SearchContent />
    </Suspense>
  );
}
