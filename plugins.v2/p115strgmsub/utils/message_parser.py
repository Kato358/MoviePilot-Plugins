"""
频道消息解析器
从 Telegram 频道消息中提取 115 网盘链接和资源标题
适配 gimy115、QukanMovie、yingshiziyuanpindao 三个频道格式
"""
import re
from typing import Dict, List, Optional


class MessageParser:
    """频道消息解析器"""

    # 115 链接正则
    PATTERN_115 = r'https?://(?:www\.)?115\.com/s/\w+'
    _compiled_115 = re.compile(PATTERN_115, re.IGNORECASE)

    # 常见标题前缀/包裹符号
    _TITLE_BRACKETS = re.compile(r'[【\[](.*?)[】\]]')
    _TITLE_PREFIXES = re.compile(r'^(?:名称|片名|标题|资源|电影|剧集)[：:\s]*(.+)', re.IGNORECASE)

    @classmethod
    def extract_115_urls(cls, text: str) -> List[str]:
        """
        从文本中提取所有 115 网盘链接

        :param text: 消息文本
        :return: 115 链接列表
        """
        if not text:
            return []
        return cls._compiled_115.findall(text)

    @classmethod
    def is_115_url(cls, url: str) -> bool:
        """
        判断是否是 115 网盘链接

        :param url: URL 字符串
        :return: 是否是 115 链接
        """
        if not url:
            return False
        return bool(cls._compiled_115.search(url))

    @classmethod
    def parse_message(cls, text: str, channel: str = "") -> List[Dict]:
        """
        从消息文本中提取 115 链接和资源标题

        :param text: 消息文本
        :param channel: 频道名（用于适配不同频道格式）
        :return: [{"url": "...", "title": "..."}]
        """
        if not text:
            return []

        urls = cls.extract_115_urls(text)
        if not urls:
            return []

        results = []
        for url in urls:
            title = cls.extract_title(text, url)
            if title:
                results.append({"url": url, "title": title})

        return results

    @classmethod
    def extract_title(cls, text: str, url: str) -> str:
        """
        从消息文本中提取资源标题

        策略:
        1. 按频道格式适配 (gimy115, QukanMovie, yingshiziyuanpindao)
        2. 提取链接前最近的非空文本行

        :param text: 消息文本
        :param url: 115 链接
        :return: 资源标题，无法提取时返回空字符串
        """
        if not text:
            return ""

        # 尝试按频道格式提取
        title = cls._extract_by_channel_format(text, url)
        if title:
            return cls._clean_title(title)

        # 通用策略: 链接前最近的非空文本行
        title = cls._extract_nearest_text_before_url(text, url)
        return cls._clean_title(title) if title else ""

    @classmethod
    def _extract_by_channel_format(cls, text: str, url: str) -> str:
        """按频道格式适配提取标题"""

        # 1. gimy115 格式: 标题通常用 【】 包裹，或在消息开头
        bracket_matches = cls._TITLE_BRACKETS.findall(text)
        if bracket_matches:
            # 取第一个 【】 中的内容作为标题
            candidate = bracket_matches[0].strip()
            # 过滤掉明显的非标题内容（如 "115网盘"、"夸克网盘" 等）
            if candidate and len(candidate) > 1 and not cls._is_noise(candidate):
                return candidate

        # 2. QukanMovie 格式: "标题 + 链接" 或 "名称：xxx\n链接"
        prefix_match = cls._TITLE_PREFIXES.search(text)
        if prefix_match:
            candidate = prefix_match.group(1).strip()
            if candidate and len(candidate) > 1:
                return candidate

        # 3. yingshiziyuanpindao 格式: 多季打包，标题在链接前多行
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 如果该行包含链接，停止
            if url in line or "115.com" in line:
                break
            # 如果该行包含明显标题特征
            if cls._looks_like_title(line):
                return line

        return ""

    @classmethod
    def _extract_nearest_text_before_url(cls, text: str, url: str) -> str:
        """提取链接前最近的非空文本行作为标题"""
        lines = text.split("\n")
        url_found = False

        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            if url in line:
                url_found = True
                continue
            if url_found:
                # 移除可能的序号前缀（如 "1."、"①" 等）
                cleaned = re.sub(r'^[\d①②③④⑤⑥⑦⑧⑨⑩]+[.、．]\s*', '', line)
                cleaned = cleaned.strip()
                if cleaned and len(cleaned) > 1 and not cls._is_noise(cleaned):
                    return cleaned

        return ""

    @classmethod
    def _looks_like_title(cls, line: str) -> bool:
        """判断一行文本是否看起来像资源标题"""
        # 包含【】包裹
        if cls._TITLE_BRACKETS.search(line):
            return True
        # 包含年份信息
        if re.search(r'[\(（]\d{4}[\)）]', line):
            return True
        # 包含季/集信息
        if re.search(r'[Ss]\d+|第\d+[季集]', line):
            return True
        # 包含中文且长度适中
        if re.search(r'[一-鿿]', line) and 3 <= len(line) <= 80:
            return True
        return False

    @classmethod
    def _is_noise(cls, text: str) -> bool:
        """判断文本是否为噪音内容（不是真正的标题）"""
        noise_patterns = [
            r'^115网盘$', r'^夸克网盘$', r'^阿里云盘$', r'^百度网盘$',
            r'^链接', r'^提取码', r'^密码', r'^http',
            r'^回复', r'^转发', r'^频道',
        ]
        for pattern in noise_patterns:
            if re.match(pattern, text.strip(), re.IGNORECASE):
                return True
        return False

    @classmethod
    def _clean_title(cls, title: str) -> str:
        """清理标题文本"""
        if not title:
            return ""

        # 移除首尾空白
        title = title.strip()

        # 移除常见的无关后缀
        title = re.sub(r'\s*(链接|网盘|资源|下载|分享)\s*$', '', title)

        # 移除多余空格
        title = re.sub(r'\s+', ' ', title)

        return title.strip()
