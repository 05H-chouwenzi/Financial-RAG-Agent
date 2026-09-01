// 前端纯函数单测（Node 内置 test runner + TypeScript 类型剥离，无需额外依赖）
import test from "node:test";
import assert from "node:assert/strict";
import { applyBasePath, cn } from "../src/lib/utils.ts";

test("applyBasePath: 绝对外链原样返回", () => {
  assert.equal(applyBasePath("https://example.com/a.png"), "https://example.com/a.png");
  assert.equal(applyBasePath("//cdn.example.com/a.png"), "//cdn.example.com/a.png");
  assert.equal(applyBasePath("data:image/png;base64,xx"), "data:image/png;base64,xx");
});

test("applyBasePath: 相对路径（非 / 开头）原样返回", () => {
  assert.equal(applyBasePath("assets/a.png"), "assets/a.png");
});

test("applyBasePath: 未配置 basePath 时 / 开头路径原样返回", () => {
  const prev = process.env.NEXT_PUBLIC_BASE_PATH;
  delete process.env.NEXT_PUBLIC_BASE_PATH;
  try {
    assert.equal(applyBasePath("/a.png"), "/a.png");
  } finally {
    if (prev !== undefined) process.env.NEXT_PUBLIC_BASE_PATH = prev;
  }
});

test("applyBasePath: 配置 basePath 时补前缀且不重复", () => {
  const prev = process.env.NEXT_PUBLIC_BASE_PATH;
  process.env.NEXT_PUBLIC_BASE_PATH = "/KnowFlow";
  try {
    assert.equal(applyBasePath("/a.png"), "/KnowFlow/a.png");
    assert.equal(applyBasePath("/KnowFlow/a.png"), "/KnowFlow/a.png");
  } finally {
    if (prev !== undefined) process.env.NEXT_PUBLIC_BASE_PATH = prev;
    else delete process.env.NEXT_PUBLIC_BASE_PATH;
  }
});

test("cn: 合并 class 并去重冲突", () => {
  assert.equal(cn("a", "b"), "a b");
  assert.equal(cn("px-2", "px-4"), "px-4");
  assert.equal(cn(false && "x", "y"), "y");
});
