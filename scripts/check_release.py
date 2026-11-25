#!/usr/bin/env python3
"""阻止 API Key、真实配置和本地生成物进入 SkillHub 公开包。"""

import re
from pathlib import Path


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


SKILL_ROOT = Path(__file__).resolve().parent.parent
SKIP_PARTS = {".git"}
BANNED_DIRS = {"outputs", "eval"}
WORKSPACE_DIR = SKILL_ROOT / "official-docs"
ALLOWED_WORKSPACE_FILES = {".gitkeep"}
SKIP_FILES = set()
BANNED_FILES = {"config.ini", "_meta.json", "config.ini.example", "CHANGE_log.md"}
BANNED_ARTIFACT_NAMES = {".DS_Store"}
BANNED_ARTIFACT_SUFFIXES = {".pyc", ".pyo"}
BANNED_TERMS: tuple = ()  # 内部客户名单不随公开包分发
ALLOWED_API_KEY_VALUES = {"", "your_api_key_here", "你的深知可信搜索 API Key", "你的深知搜索 API Key"}
API_KEY_PATTERN = re.compile(r"(?im)^\s*api_key[^\S\r\n]*=[^\S\r\n]*([^\s#;]+)[^\S\r\n]*$")
SECRET_TOKEN_PATTERN = re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")
# 注册发码通行码（对齐深知公文写作 3.9.9 / 可信搜索 1.8.2；对外口径「注册通行码」，非用户凭证）：
# 渠道分配、只用于申请注册验证码、可吊销，允许随包分发但必须"登记在册"。
# 未登记的值与未登记的高熵长串一律拦下。
REGISTRATION_KEY_VALUE_PATTERN = re.compile(r'(?:REGISTRATION_PASSCODE|REGISTRATION_KEY)\s*=\s*"([A-Za-z0-9_-]{32,})"')
REGISTRATION_KEY_ALLOWED = {
    "So3EdPDJMf7z0MmH1zfvm6VDEQpR2EIRRsqqtnl866MrpVPl-Sj--g",  # skillhub 渠道（2026-11-18 分配；法律助手与可信搜索、公文写作共用同一注册渠道码）
}
OPAQUE_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{40,}")


def _is_opaque_secret_token(token: str) -> bool:
    """长串里同时含字母与数字才当作凭据候选（函数/变量名虽长但通常没有数字）。"""
    return any(c.isdigit() for c in token) and any(c.isalpha() for c in token)
OUTSIDE_PATH_PATTERN = re.compile(r"(?:01-问题清单|02-数据问题报告|03-测试与对比|04-产品文档|05-证据数据|06-标签目录|07-税务通交接|99-临时)/")
# 手机号红线（2026-10-29 审核新增）：对外话术/文档不得出现完整 11 位手机号，
# 也不得出现脱敏形式的具体号码（模板一律用 <脱敏手机号> 占位、运行时由脚本 user_message 填充）
FULL_PHONE_PATTERN = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
MASKED_PHONE_PATTERN = re.compile(r"1[3-9]\d\*{4}\d{4}")


def main():
    findings = []
    for path in SKILL_ROOT.rglob("*"):
        if path.resolve() == Path(__file__).resolve():
            continue
        if path.name in BANNED_ARTIFACT_NAMES or path.suffix in BANNED_ARTIFACT_SUFFIXES:
            findings.append(f"{path.relative_to(SKILL_ROOT)}: 公开包不得包含本地产物或平台不允许的文件")
            continue
        if any(part in BANNED_DIRS for part in path.relative_to(SKILL_ROOT).parts):
            findings.append(f"{path.relative_to(SKILL_ROOT)}: 公开包不得包含本地生成输出目录")
            continue
        if any(part == "__pycache__" for part in path.parts):
            findings.append(f"{path.relative_to(SKILL_ROOT)}: 公开包不得包含 __pycache__")
            continue
        if path.is_file() and path.name in BANNED_FILES:
            findings.append(f"{path.relative_to(SKILL_ROOT)}: 公开包不得包含真实配置文件或开发记录")
            continue
        if path.is_file() and _is_within(path, WORKSPACE_DIR) and path.name not in ALLOWED_WORKSPACE_FILES:
            findings.append(f"{path.relative_to(SKILL_ROOT)}: official-docs/ 工作区内只允许 .gitkeep 占位，公开包不得包含工作区产物")
            continue
        if not path.is_file() or path.name in SKIP_FILES or any(part in SKIP_PARTS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            for term in BANNED_TERMS:
                if term in line:
                    findings.append(f"{path.relative_to(SKILL_ROOT)}:{line_number}: {term}")
            if OUTSIDE_PATH_PATTERN.search(line):
                findings.append(f"{path.relative_to(SKILL_ROOT)}:{line_number}: 引用了公开包之外的内部工作区路径")
        if path.suffix != ".py":
            for match in API_KEY_PATTERN.finditer(text):
                if match.group(1) not in ALLOWED_API_KEY_VALUES:
                    findings.append(f"{path.relative_to(SKILL_ROOT)}: 发现非占位符 api_key")
        if SECRET_TOKEN_PATTERN.search(text):
            findings.append(f"{path.relative_to(SKILL_ROOT)}: 发现疑似 API Key")
        for match in REGISTRATION_KEY_VALUE_PATTERN.finditer(text):
            if match.group(1) not in REGISTRATION_KEY_ALLOWED:
                findings.append(
                    f"{path.relative_to(SKILL_ROOT)}: 未登记的注册发码通行码"
                    "（新增值需先在 check_release.py 登记渠道与分配日期）")
        for line_number, line in enumerate(text.splitlines(), 1):
            for match in OPAQUE_TOKEN_PATTERN.finditer(line):
                token = match.group(0)
                if token in REGISTRATION_KEY_ALLOWED or not _is_opaque_secret_token(token):
                    continue
                findings.append(
                    f"{path.relative_to(SKILL_ROOT)}:{line_number}: 发现未登记的长随机串"
                    "（如为新增通行码，需先在 check_release.py 登记渠道与分配日期）")
        for line_number, line in enumerate(text.splitlines(), 1):
            if FULL_PHONE_PATTERN.search(line):
                findings.append(f"{path.relative_to(SKILL_ROOT)}:{line_number}: 发现完整手机号（不得写入对外包）")
            if MASKED_PHONE_PATTERN.search(line):
                findings.append(f"{path.relative_to(SKILL_ROOT)}:{line_number}: 发现脱敏手机号具体示例（请改用 <脱敏手机号> 占位）")

    if findings:
        print("发布检查失败：发现不应进入 SkillHub 公开包的内容")
        print("\n".join(findings))
        raise SystemExit(1)
    print("发布检查通过：未发现真实配置、API Key 或本地生成物")


if __name__ == "__main__":
    main()
