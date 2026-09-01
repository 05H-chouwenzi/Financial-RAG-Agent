import { applyBasePath } from "@/lib/utils";

/** 知识库管理模块 - 类型与数据定义 */

export type FolderId = "standard" | "atlas";
export type FileKind = "pdf" | "doc" | "docx" | "txt";

export interface FolderNode {
  id: FolderId;
  name: string;
}

export interface KnowledgeFile {
  id: string;
  /** 展示名称(不含扩展名) */
  name: string;
  kind: FileKind;
  folder: FolderId;
  sizeKB: number;
  /** 展示用修改日期(固定字符串,避免 SSR/CSR 水合不一致) */
  modifiedLabel: string;
  /** 排序用时间戳 */
  modifiedTs: number;
  /**
   * public 目录下真实文件名;存在则支持浏览器原生 PDF 预览与原文件下载。
   * 虚拟(在线新建/模拟入库)文档不设置该字段。
   */
  fileName?: string;
  /** 是否来自后端语料(backend/data/raw);为 true 时删除会同步调用后端 API */
  backend?: boolean;
  /** 文档内容,用于"内容"关键词搜索、虚拟文档预览与导出 */
  content: string;
}

export const FOLDERS: FolderNode[] = [
  { id: "standard", name: "研报" },
  { id: "atlas", name: "图表" },
];

export const FOLDER_LABELS: Record<FolderId, string> = {
  standard: "研报",
  atlas: "图表",
};

export const KIND_LABELS: Record<FileKind, string> = {
  pdf: "PDF",
  doc: "DOC",
  docx: "DOCX",
  txt: "TXT",
};

/** 文件类型图标配色(图标背景 / 图标前景) */
export const KIND_COLORS: Record<FileKind, string> = {
  pdf: "bg-red-100 text-red-600 dark:bg-red-950/60 dark:text-red-400",
  doc: "bg-red-100 text-red-600 dark:bg-red-950/60 dark:text-red-400",
  docx: "bg-red-100 text-red-600 dark:bg-red-950/60 dark:text-red-400",
  txt: "bg-muted text-muted-foreground",
};

/** 初始数据:public/pdf 目录下的真实研报文档(全部归入「研报」知识库) */
export const INITIAL_FILES: KnowledgeFile[] = [
  // ===== 真实年报/半年报（Financial-RAG-Agent 语料，巨潮下载）=====
  { id: "rep-pa-2023", name: "平安银行-2023年年度报告", kind: "pdf", folder: "standard", sizeKB: 5529.6, modifiedLabel: "2024/3/15", modifiedTs: 1710432000000, fileName: "reports/平安银行-2023年年度报告.pdf", content: "平安银行2023年年度报告：实现营业收入1,646.99亿元，同比下降8.4%；归属于本行股东的净利润464.55亿元，同比增长2.1%；加权平均净资产收益率11.38%；不良贷款率1.06%；拨备覆盖率277.63%。利润分配预案为每10股派发现金股利7.19元（含税）。" },
  { id: "rep-pa-2022", name: "平安银行-2022年年度报告", kind: "pdf", folder: "standard", sizeKB: 5580.8, modifiedLabel: "2023/3/9", modifiedTs: 1678291200000, fileName: "reports/平安银行-2022年年度报告.pdf", content: "平安银行2022年年度报告：实现营业收入1,798.95亿元，同比增长6.2%；归属于本行股东的净利润455.16亿元，同比增长25.3%；不良贷款率1.05%；拨备覆盖率290.28%。" },
  { id: "rep-pa-2024h1", name: "平安银行-2024年半年度报告", kind: "pdf", folder: "standard", sizeKB: 4669.4, modifiedLabel: "2024/8/16", modifiedTs: 1723737600000, fileName: "reports/平安银行-2024年半年度报告.pdf", content: "平安银行2024年半年度报告：披露报告期主要会计数据与财务指标，不良贷款率1.07%，拨备覆盖率264.26%，资产质量保持平稳。" },
  { id: "rep-pa-2023h1", name: "平安银行-2023年半年度报告", kind: "pdf", folder: "standard", sizeKB: 1443.8, modifiedLabel: "2023/8/24", modifiedTs: 1692806400000, fileName: "reports/平安银行-2023年半年度报告.pdf", content: "平安银行2023年半年度报告：披露2023年上半年主要财务数据、财务指标变动情况及现金流量情况。" },
  { id: "rep-mt-2023", name: "贵州茅台-2023年年度报告", kind: "pdf", folder: "standard", sizeKB: 3481.6, modifiedLabel: "2024/4/3", modifiedTs: 1712073600000, fileName: "reports/贵州茅台-2023年年度报告.pdf", content: "贵州茅台2023年年度报告：实现营业收入1,476.94亿元，同比增长19.01%；归属于上市公司股东的净利润747.34亿元，同比增长19.16%；经营活动产生的现金流量净额665.93亿元，同比增长81.46%。茅台酒毛利率94.12%。利润分配为每10股派发现金红利308.76元（含税）。" },
  { id: "rep-mt-2022", name: "贵州茅台-2022年年度报告", kind: "pdf", folder: "standard", sizeKB: 3246.1, modifiedLabel: "2023/3/31", modifiedTs: 1680192000000, fileName: "reports/贵州茅台-2022年年度报告.pdf", content: "贵州茅台2022年年度报告：实现营业收入1,241.00亿元，同比增长16.87%；归属于上市公司股东的净利润627.16亿元，同比增长19.55%。" },
  { id: "rep-mt-2024h1", name: "贵州茅台-2024年半年度报告", kind: "pdf", folder: "standard", sizeKB: 2990.1, modifiedLabel: "2024/8/9", modifiedTs: 1723132800000, fileName: "reports/贵州茅台-2024年半年度报告.pdf", content: "贵州茅台2024年半年度报告：披露2024年上半年经营情况、主要会计数据与财务指标。" },
  { id: "rep-mt-2023h1", name: "贵州茅台-2023年半年度报告", kind: "pdf", folder: "standard", sizeKB: 2693.1, modifiedLabel: "2023/8/3", modifiedTs: 1690992000000, fileName: "reports/贵州茅台-2023年半年度报告.pdf", content: "贵州茅台2023年半年度报告：实现营业收入695.76亿元，同比增长20.76%；归属于上市公司股东的净利润359.80亿元，同比增长20.76%。" },
  // ===== 图表知识库（演示 mock）=====
  { id: "fin-chart-1", name: "资产负债率趋势图表集(2020-2025)", kind: "pdf", folder: "atlas", sizeKB: 512.1, modifiedLabel: "2026/8/31", modifiedTs: 1788249600000, content: "公司资产负债率由2020年约68%降至2025年约55%，行业均值稳定在58%-62%区间，2023年起低于行业均值。" },
  { id: "fin-chart-2", name: "营收与经营性现金流对比图", kind: "pdf", folder: "atlas", sizeKB: 428.6, modifiedLabel: "2026/8/31", modifiedTs: 1788249600000, content: "2025年营业收入86亿元，经营性现金流净额同步增长，现金流/净利润比值约1.2，利润含金量较高。" },
  { id: "fin-chart-3", name: "行业PE与PB估值分位图", kind: "pdf", folder: "atlas", sizeKB: 356.9, modifiedLabel: "2026/8/31", modifiedTs: 1788249600000, content: "沪深300整体PE(TTM)约12.5倍，处于近十年35%分位；PB约1.4倍，处于28%分位，估值具备安全边际。" },
];

/** KB / MB 格式化 */
export function formatSize(sizeKB: number): string {
  if (sizeKB < 1024) return `${sizeKB.toFixed(1)} KB`;
  return `${(sizeKB / 1024).toFixed(1)} MB`;
}

/** 将文本按命中关键词切分,用于高亮渲染 */
export function splitHighlight(
  text: string,
  query: string
): Array<{ text: string; hit: boolean }> {
  const q = query.trim();
  if (!q) return [{ text, hit: false }];
  const lowerText = text.toLowerCase();
  const lowerQ = q.toLowerCase();
  const parts: Array<{ text: string; hit: boolean }> = [];
  let from = 0;
  while (true) {
    const idx = lowerText.indexOf(lowerQ, from);
    if (idx === -1) {
      if (from < text.length) parts.push({ text: text.slice(from), hit: false });
      break;
    }
    if (idx > from) parts.push({ text: text.slice(from, idx), hit: false });
    parts.push({ text: text.slice(idx, idx + q.length), hit: true });
    from = idx + q.length;
  }
  return parts;
}

/** 取内容中首次命中的上下文片段,用于"内容"搜索结果的摘要展示 */
export function contentSnippet(content: string, query: string): string | null {
  const q = query.trim();
  if (!q) return null;
  const idx = content.toLowerCase().indexOf(q.toLowerCase());
  if (idx === -1) return null;
  const start = Math.max(0, idx - 24);
  const end = Math.min(content.length, idx + q.length + 36);
  return `${start > 0 ? "…" : ""}${content.slice(start, end)}${end < content.length ? "…" : ""}`;
}

/**
 * 生成一个仅含 ASCII 占位文字的最小合法 PDF(字节偏移按 1 字节/字符计算,全 ASCII 安全)。
 * 用于虚拟(在线新建/模拟入库)PDF 文档的下载,保证下载得到可正常打开的 .pdf 文件。
 */
export function buildVirtualPdfBlob(): Blob {
  const stream = "BT /F1 18 Tf 72 770 Td (FinFlow Virtual PDF Document) Tj ET";
  const objects = [
    "<</Type/Catalog/Pages 2 0 R>>",
    "<</Type/Pages/Kids[3 0 R]/Count 1>>",
    "<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
    `<</Length ${stream.length}>>\nstream\n${stream}\nendstream`,
    "<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
  ];
  let pdf = "%PDF-1.4\n";
  const offsets: number[] = [];
  objects.forEach((body, i) => {
    offsets.push(pdf.length);
    pdf += `${i + 1} 0 obj\n${body}\nendobj\n`;
  });
  const xrefStart = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  offsets.forEach((off) => {
    pdf += `${off.toString().padStart(10, "0")} 00000 n \n`;
  });
  pdf += `trailer\n<</Size ${objects.length + 1}/Root 1 0 R>>\nstartxref\n${xrefStart}\n%%EOF`;
  return new Blob([pdf], { type: "application/pdf" });
}

/** 虚拟文档下载:PDF 生成合法占位 PDF,其余类型回退纯文本(当前数据均为 PDF) */
export function downloadVirtualFile(file: KnowledgeFile): void {
  const isPdf = file.kind === "pdf";
  const blob = isPdf
    ? buildVirtualPdfBlob()
    : new Blob([file.content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${file.name}.${isPdf ? "pdf" : "txt"}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** 真实 PDF 在站点中的访问地址(按路径段编码,自动补 GitHub Pages basePath) */
export function realFileUrl(fileName: string): string {
  const encoded = fileName
    .split("/")
    .map((seg) => encodeURIComponent(seg))
    .join("/");
  return applyBasePath(`/${encoded}`);
}

/** 客户端事件中使用的日期格式化(仅挂载后的交互调用,无水合风险) */
export function todayLabel(): string {
  const d = new Date();
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`;
}

