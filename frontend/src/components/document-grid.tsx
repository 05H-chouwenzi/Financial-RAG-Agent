'use client';

interface DocumentItem {
  id: string;
  code: string;
  title: string;
  category: '研报' | '图表';
}

const documents: DocumentItem[] = [
  // 研报
  { id: 'g1', code: 'REPORT-2025-001', title: '2025年半导体行业深度研报', category: '研报' },
  { id: 'g2', code: 'POLICY-2024-003', title: '上市公司信息披露管理办法解读', category: '研报' },
  { id: 'g3', code: 'REPORT-2025-018', title: '银行板块净息差与资产质量分析', category: '研报' },
  { id: 'g4', code: 'REPORT-2025-032', title: '新能源产业链现金流质量研究', category: '研报' },
  { id: 'g5', code: 'REPORT-2025-040', title: '白酒行业盈利与估值复盘', category: '研报' },
  // 图表
  { id: 't1', code: 'CHART-2025-006', title: '沪深300估值分位图', category: '图表' },
  { id: 't2', code: 'CHART-2025-011', title: '行业毛利率与净利率对比图', category: '图表' },
  { id: 't3', code: 'CHART-2025-018', title: '资产负债率趋势图', category: '图表' },
  { id: 't4', code: 'CHART-2025-022', title: '营收与经营性现金流对比图', category: '图表' },
  { id: 't5', code: 'CHART-2025-030', title: '行业PE与PB估值分位图', category: '图表' },
];

interface DocumentGridProps {
  activeCategory?: '研报' | '图表';
  selectedId?: string;
  onSelect?: (id: string) => void;
  customDocs?: DocumentItem[];
}

export default function DocumentGrid({ activeCategory = '研报', selectedId, onSelect, customDocs = [] }: DocumentGridProps) {
  const filteredDocs = [...documents.filter((doc) => doc.category === activeCategory), ...customDocs];

  return (
    <section className="py-4">
      {/* Document List - 3 columns */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filteredDocs.map((doc) => (
          <div
            key={doc.id}
            onClick={() => onSelect?.(doc.id)}
            className={`group flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3.5 transition-all hover:-translate-y-0.5 hover:shadow-md ${
              selectedId === doc.id
                ? 'border-destructive/30 bg-destructive/10'
                : 'border-border bg-card'
            }`}
          >
            <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-sm font-bold ${
              selectedId === doc.id
                ? 'bg-destructive/20 text-destructive'
                : 'bg-destructive/10 text-destructive'
            }`}>
              {doc.category === '研报' ? '研' : '图'}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-foreground">{doc.title}</p>
              {doc.code && (
                <p className="mt-0.5 font-mono text-xs text-muted-foreground">{doc.code}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
