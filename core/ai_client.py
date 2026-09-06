# -*- coding: utf-8 -*-
"""
AI客户端封装
支持多种AI后端
"""
import ast
import json
import re
from typing import Optional
from openai import OpenAI
from settings_module import get_settings


class AIClient:
    """AI客户端封装"""

    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[OpenAI] = None
        self._connect()

    def _connect(self):
        """连接到AI服务"""
        config = self.settings.get_ai_config()
        provider = config.get("provider", "openai")
        api_key = config.get("api_key", "")
        base_url = config.get("base_url", "")

        if not api_key:
            raise ValueError("请先配置API Key")

        try:
            # 直接传 float 总超时（秒），避免显式依赖 httpx（不同环境可能是 httpx2）
            timeout = 30.0

            if provider == "openai":
                self.client = OpenAI(
                    api_key=api_key,
                    base_url=base_url or "https://api.openai.com/v1",
                    timeout=timeout,
                )
            elif provider == "azure":
                from openai import AzureOpenAI
                self.client = AzureOpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    api_version="2024-02-01",
                    timeout=timeout,
                )
            else:
                # 自定义/OpenAI兼容
                self.client = OpenAI(
                    api_key=api_key,
                    base_url=base_url or "https://api.openai.com/v1",
                    timeout=timeout,
                )
        except Exception as e:
            raise ConnectionError(f"连接AI服务失败: {e}")

    def chat(
        self,
        messages: list,
        model: Optional[str] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[dict] = None,
    ) -> str:
        """发送聊天请求"""
        if not self.client:
            self._connect()

        config = self.settings.get_ai_config()
        model = model or config.get("model", "gpt-4o")
        temperature = temperature if temperature is not None else config.get("temperature", 0.7)
        max_tokens = max_tokens or config.get("max_tokens", 4096)

        try:
            if stream:
                return self._stream_chat(messages, model, temperature, max_tokens)
            else:
                return self._chat(messages, model, temperature, max_tokens, response_format)
        except Exception as e:
            raise RuntimeError(f"AI调用失败: {e}")

    def _chat(self, messages, model, temperature, max_tokens, response_format=None) -> str:
        """非流式聊天"""
        kwargs = dict(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if response_format:
            kwargs["response_format"] = response_format
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def _stream_chat(
        self, messages, model, temperature, max_tokens
    ):
        """流式聊天"""
        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def generate_json(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """生成JSON格式输出（JSON mode 优先，坏JSON自动修复兜底）"""
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个专业的演示文稿策划助手。"
                    "请输出严格合法的JSON（键值对之间用英文逗号分隔，字符串用双引号包裹，"
                    "数组元素之间用逗号分隔，不要输出JSON以外的任何说明文字）。"
                ),
            },
            {"role": "user", "content": prompt},
        ]

        # 优先尝试 JSON mode（治本：约束模型只输出合法 JSON）；模型不支持时回退普通模式
        last_error = None
        for use_json_mode in (True, False):
            try:
                kwargs = {"model": model}
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens
                if use_json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                response = self.chat(messages, **kwargs)
                return self._extract_json(response)
            except Exception as e:
                last_error = e
                # 若 JSON mode 报错则回退普通模式再试；若普通模式也失败则抛出
        raise RuntimeError(f"JSON生成失败: {last_error}")

    def _extract_json(self, text: str) -> dict:
        """从响应中提取JSON（多层容错，兼容LLM生成的坏JSON）"""
        if not text or not text.strip():
            raise ValueError("AI返回内容为空")

        original = text

        # 1. 提取代码块中的JSON
        code_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if code_match:
            text = code_match.group(1)

        # 2. 截取第一个 { 或 [ 到最后一个 } 或 ]（去掉前后多余说明文字）
        start_obj = text.find("{")
        start_arr = text.find("[")
        starts = [x for x in (start_obj, start_arr) if x != -1]
        ends = [x for x in (text.rfind("}"), text.rfind("]")) if x != -1]
        if starts and ends:
            start = min(starts)
            end = max(ends)
            if end > start:
                text = text[start : end + 1]

        # 3. 逐层尝试解析
        candidates = [text, self._repair_json(text)]

        for cand in candidates:
            if not cand:
                continue
            # 直接解析
            try:
                result = json.loads(cand)
                if isinstance(result, dict):
                    return result
            except (json.JSONDecodeError, ValueError):
                pass
            # ast.literal_eval 兜底（兼容单引号、Python 风格字典）
            try:
                result = ast.literal_eval(cand)
                if isinstance(result, dict):
                    return result
            except (ValueError, SyntaxError, TypeError):
                pass

        raise ValueError(f"无法解析AI返回的JSON: {original[:300]}...")

    def _repair_json(self, text: str) -> str:
        """修复LLM生成坏JSON的常见问题：注释、尾逗号、缺失逗号"""
        text = self._strip_comments(text)
        # 尾逗号：{"a":1,} 或 [1,2,]
        text = re.sub(r",\s*([}\]])", r"\1", text)
        # 缺失逗号（状态机，正确区分字符串内外与键值）
        text = self._fix_missing_commas(text)
        return text

    def _strip_comments(self, text: str) -> str:
        """移除 JSON 中的注释（//、#、块注释），不误伤字符串内容"""
        out = []
        in_string = False
        escape = False
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if in_string:
                out.append(ch)
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                i += 1
                continue
            if ch == '"':
                out.append(ch)
                in_string = True
                i += 1
                continue
            # 字符串外
            if ch == "/" and i + 1 < n and text[i + 1] == "/":
                while i < n and text[i] != "\n":
                    i += 1
                continue
            if ch == "/" and i + 1 < n and text[i + 1] == "*":
                i += 2
                while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                    i += 1
                i += 2
                continue
            if ch == "#":
                while i < n and text[i] != "\n":
                    i += 1
                continue
            out.append(ch)
            i += 1
        return "".join(out)

    def _fix_missing_commas(self, text: str) -> str:
        """修复JSON中缺失的逗号（值结束后紧跟下一个元素却无逗号）"""
        out = []
        in_string = False
        escape = False
        i = 0
        n = len(text)

        def _next_non_space(idx):
            while idx < n and text[idx] in " \t\n\r":
                idx += 1
            return idx

        while i < n:
            ch = text[i]

            if in_string:
                out.append(ch)
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                    # 字符串结束：若它是"值"（后面不是冒号），且后紧跟新值则补逗号
                    j = _next_non_space(i + 1)
                    if j < n and (text[j] in "\"{[tfn-" or text[j].isdigit()):
                        out.append(",")
                i += 1
                continue

            if ch == '"':
                out.append(ch)
                in_string = True
                i += 1
                continue

            # 字符串外
            if ch in "}]":
                out.append(ch)
                j = _next_non_space(i + 1)
                if j < n and (text[j] in "\"{[tfn-" or text[j].isdigit()):
                    out.append(",")
                i += 1
                continue

            # true/false/null 结束
            if ch in "tfn":
                word = None
                if text[i : i + 4] == "true":
                    word = "true"
                elif text[i : i + 5] == "false":
                    word = "false"
                elif text[i : i + 4] == "null":
                    word = "null"
                if word:
                    out.append(word)
                    i += len(word)
                    j = _next_non_space(i)
                    if j < n and (text[j] in "\"{[tfn-" or text[j].isdigit()):
                        out.append(",")
                    continue

            # 数字结束
            if ch.isdigit():
                out.append(ch)
                i += 1
                while i < n and (text[i].isdigit() or text[i] in ".eE+-"):
                    out.append(text[i])
                    i += 1
                j = _next_non_space(i)
                if j < n and (text[j] in "\"{[tfn-" or text[j].isdigit()):
                    out.append(",")
                continue

            out.append(ch)
            i += 1

        return "".join(out)
