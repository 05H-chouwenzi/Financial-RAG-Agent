import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-static";

// Dify configuration from environment variables
const DIFY_API_BASE_URL = process.env.DIFY_API_BASE_URL || "http://127.0.0.1/v1";
const DIFY_API_KEY = process.env.DIFY_API_KEY;

// Simulated knowledge base for construction engineering documents
const knowledgeBase = [
  {
    code: "REPORT-2025-001",
    title: "2025年A股半导体行业深度研报",
    category: "standard",
    content:
      "全球半导体周期进入上行阶段，国产替代持续推进。建议关注设备、材料环节的国产化率提升，以及存储涨价带来的盈利弹性。行业整体毛利率中枢约35%-40%。",
    page: "第 2.3 节",
  },
  {
    code: "POLICY-2024-003",
    title: "上市公司信息披露管理办法-要点解读",
    category: "standard",
    content:
      "上市公司应真实、准确、完整、及时地披露信息，不得有虚假记载、误导性陈述或重大遗漏。定期报告需在规定期限内披露，重大事项需临时公告。",
    page: "第 3 章",
  },
  {
    code: "REPORT-2025-018",
    title: "银行板块资产负债率与净息差分析",
    category: "standard",
    content:
      "银行业整体资产负债率约92%，净息差收窄压力延续，关注资产质量与拨备覆盖率。优质城商行ROE中枢约11%-13%。",
    page: "第 4.1 节",
  },
  {
    code: "REPORT-2025-032",
    title: "新能源产业链现金流质量研究",
    category: "standard",
    content:
      "产业链上游产能过剩导致价格下行，经营性现金流分化明显。龙头公司现金流/净利润比值大于1.0，二线厂商普遍小于0.6，需警惕应收账款风险。",
    page: "第 5.2 节",
  },
  {
    code: "CHART-2025-006",
    title: "沪深300指数成分股估值分位图",
    category: "atlas",
    content:
      "截至2025年末，沪深300整体PE(TTM)约12.5倍，处于近十年35%分位；PB约1.4倍，处于28%分位，估值具备安全边际。",
    page: "图 2",
  },
  {
    code: "CHART-2025-011",
    title: "行业毛利率与净利率对比图",
    category: "atlas",
    content:
      "消费电子行业毛利率中枢约18%-22%，净利率约6%-9%；高端制造毛利率约25%-30%，净利率约10%-14%。",
    page: "图 5",
  },
];

const categoryLabels: Record<string, string> = {
  regulation: "金融法规",
  standard: "金融研报",
  atlas: "金融图表",
};

function searchKnowledgeBase(
  question: string,
  categories: string[]
): typeof knowledgeBase {
  const query = question.toLowerCase();
  const keywords = query.split(/[\s,，、？?]+/).filter((k) => k.length > 1);

  return knowledgeBase
    .filter((doc) => {
      if (categories.length > 0 && !categories.includes(doc.category)) return false;
      return keywords.some(
        (keyword) =>
          doc.title.toLowerCase().includes(keyword) ||
          doc.content.toLowerCase().includes(keyword) ||
          doc.code.toLowerCase().includes(keyword)
      );
    })
    .slice(0, 4);
}

export async function POST(request: NextRequest) {
  try {
    const { question, category, categories } = await request.json();

    if (!question || !question.trim()) {
      return NextResponse.json(
        { error: "请输入检索问题" },
        { status: 400 }
      );
    }

    // Support both single category and multiple categories
    const selectedCategories = categories || (category ? [category] : ["standard"]);

    // Search knowledge base for results display
    const results = searchKnowledgeBase(question, selectedCategories);

    // Create a ReadableStream for SSE
    const stream = new ReadableStream({
      async start(controller) {
        const encoder = new TextEncoder();

        const sendSSE = (data: Record<string, unknown>) => {
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify(data)}\n\n`)
          );
        };

        // Send search results first
        if (results.length > 0) {
          sendSSE({
            type: "results",
            data: results.map((r, i) => ({
              id: `result-${i}`,
              code: r.code,
              title: r.title,
              page: r.page,
              imageUrl: "",
            })),
          });

          // Send sources
          sendSSE({
            type: "sources",
            data: results.slice(0, 2).map((r) => ({
              code: r.code,
              title: r.title,
              content: r.content,
              attachment: r.page,
            })),
          });

          // Send documents
          sendSSE({
            type: "documents",
            data: results.slice(0, 2).map((r) => ({
              id: `doc-${r.code}`,
              title: r.title,
              code: r.code,
              description: r.content.slice(0, 60) + "...",
              status: "valid" as const,
            })),
          });
        }

        // Call Dify API for streaming response
        if (DIFY_API_KEY) {
          try {
            console.log("Calling Dify API:", DIFY_API_BASE_URL);
            const response = await fetch(`${DIFY_API_BASE_URL}/chat-messages`, {
              method: "POST",
              headers: {
                "Authorization": `Bearer ${DIFY_API_KEY}`,
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                inputs: {},
                query: question,
                response_mode: "streaming",
                user: "archsa-user",
              }),
            });

            console.log("Dify response status:", response.status);

            if (response.ok && response.body) {
              const reader = response.body.getReader();
              const decoder = new TextDecoder();
              let buffer = "";
              let fullAnswer = "";

              while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() || "";

                for (const line of lines) {
                  const trimmedLine = line.trim();
                  if (trimmedLine.startsWith("data: ")) {
                    const data = trimmedLine.slice(6);
                    if (data === "[DONE]") {
                      sendSSE({ type: "answer", content: "[DONE]" });
                      controller.close();
                      return;
                    }

                    try {
                      const parsed = JSON.parse(data);
                      // Dify streaming response format
                      if (parsed.answer) {
                        fullAnswer += parsed.answer;
                        sendSSE({ type: "answer", content: parsed.answer });
                      } else if (parsed.event === "message" && parsed.answer) {
                        fullAnswer += parsed.answer;
                        sendSSE({ type: "answer", content: parsed.answer });
                      }
                    } catch (e) {
                      console.log("Dify parse error:", e, "data:", data);
                    }
                  }
                }
              }

              // If no streaming data received, send full answer
              if (!fullAnswer) {
                const mockAnswer = generateMockAnswer(question, results);
                for (const char of mockAnswer) {
                  sendSSE({ type: "answer", content: char });
                  await new Promise((resolve) => setTimeout(resolve, 10));
                }
              }
            } else {
              const errorText = await response.text();
              console.error("Dify API error:", response.status, errorText);
              throw new Error(`Dify API returned ${response.status}: ${errorText}`);
            }
          } catch (difyError) {
            console.error("Dify API error:", difyError);
            // Fallback to mock answer
            const mockAnswer = generateMockAnswer(question, results);
            for (const char of mockAnswer) {
              sendSSE({ type: "answer", content: char });
              await new Promise((resolve) => setTimeout(resolve, 10));
            }
          }
        } else {
          // No Dify API key, use mock answer
          const mockAnswer = generateMockAnswer(question, results);
          for (const char of mockAnswer) {
            sendSSE({ type: "answer", content: char });
            await new Promise((resolve) => setTimeout(resolve, 10));
          }
        }

        sendSSE({ type: "answer", content: "[DONE]" });
        controller.close();
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch (error) {
    console.error("Search API error:", error);
    return NextResponse.json(
      { error: "检索服务暂时不可用，请稍后重试" },
      { status: 500 }
    );
  }
}

function generateMockAnswer(question: string, results: typeof knowledgeBase): string {
  if (results.length === 0) {
    return `关于"${question}"，目前知识库中暂无直接匹配的研报要点。\n\n建议您：\n1. 尝试使用更具体的关键词检索\n2. 查阅相关专业的国家标准全文\n3. 咨询当地建设主管部门获取最新政策`;
  }

  const mainResult = results[0];
  let answer = `根据检索结果，关于"${question}"的回答如下：\n\n`;
  answer += `**主要依据：${mainResult.code}《${mainResult.title}》**\n\n`;
  answer += `${mainResult.content}\n\n`;

  if (results.length > 1) {
    answer += `**相关研报参考：**\n`;
    for (let i = 1; i < results.length; i++) {
      answer += `- ${results[i].code}《${results[i].title}》：${results[i].content.slice(0, 50)}...\n`;
    }
  }

  answer += `\n以上信息来源于金融工程知识库，具体以官方发布原文为准。`;
  return answer;
}
