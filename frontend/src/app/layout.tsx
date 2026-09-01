import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'FinFlow - 金融研报RAG智能检索助手',
    template: '%s | FinFlow',
  },
  description:
    '基于 RAG 架构的金融图文研报检索智能体，融合 Agentic RAG 与多模态 RAG 双引擎，实现研报要点问答与图表详图双向检索',
  keywords: [
    'FinFlow',
    'RAG',
    'Agentic RAG',
    '多模态RAG',
    '金融研报',
    '图表检索',
    '智能体调度',
    '金融检索',
    '研报问答',
    '金融知识',
  ],
  openGraph: {
    title: 'FinFlow - 金融研报RAG智能检索助手',
    description: '基于 RAG 架构的金融图文研报检索智能体',
    locale: 'zh_CN',
    type: 'website',
  },
  icons: {
    icon: '/rag-icon.png',
    apple: '/rag-icon.png',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // suppressHydrationWarning：Trae 预览运行时会在服务端向 <html>/<body> 注入
    // data-trae-ref 等属性及浏览器检查高亮节点，客户端水合时不复现，
    // 导致 React Hydration Error #185。根元素的属性注入无法通过组件门控规避，
    // 在此显式抑制水合告警（与 next-themes 等运行时注入的常规处理一致）。
    <html lang="zh-CN" suppressHydrationWarning>
      <body className="antialiased bg-background text-foreground font-sans" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
