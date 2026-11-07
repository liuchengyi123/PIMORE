# 服装数字人直播最小间 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 做一个能在夜里接着讲的服装直播中控：知识库写下一句，弹幕可答，改价和换款立刻生效。

**Architecture:** 纯函数负责填稿、回答和拦截编造。房间状态机只决定下一句是讲解还是回答。FastAPI 中控台调用千问改写和语音合成；没有密钥时用知识库原句，直播不中断。

**Tech Stack:** Python 3.12、FastAPI、httpx、通义千问兼容接口、qwen3-tts-flash。

---

### Task 1: 话术与知识库

**Files:**
- Create: `liveroom/speech.py`
- Test: `tests/test_liveroom_speech.py`

- [x] 写失败测试：填价格、回答尺码、库外问题不编、禁用词和错误价格被换掉
- [x] 实现 `fill`、`answer_line`、`selling_line`、`guard`
- [x] 跑测试通过

### Task 2: 房间状态

**Files:**
- Create: `liveroom/room.py`
- Create: `liveroom/store.py`
- Create: `liveroom/default_room.json`

- [x] 讲解进度在回答时不往前跳
- [x] 改一行、改价格、换款作用于下一句
- [x] 读写 JSON

### Task 3: 模型和语音

**Files:**
- Create: `liveroom/llm.py`
- Create: `liveroom/tts.py`
- Test: `tests/test_liveroom_api.py`

- [x] 千问只改写一句，请求里带上知识库事实
- [x] 语音接口使用 qwen3-tts-flash，取回音频地址
- [x] 用假的 HTTP 测请求体

### Task 4: 中控台

**Files:**
- Create: `liveroom/api.py`
- Create: `liveroom/static/index.html`

- [x] 三栏页面，人工智能标识不可关闭
- [x] 弹幕、下一句、保存、换款、上传站播
- [x] 没有密钥时仍然返回知识库里的句子
