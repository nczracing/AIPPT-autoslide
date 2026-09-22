import sys; sys.path.insert(0, '.')
from core.prompt_builder import PromptBuilder
pb = PromptBuilder()
ctx_block = pb._build_context_block('测试材料：营收增长35%')
assert "EXTRACT, don't copy" in ctx_block, '缺结构化引导'
assert 'Three material types' in ctx_block, '缺三类材料'
print('OK ctx block')
ref_block = pb._build_references_block('Smith (2024). Journal')
assert 'Do NOT fabricate' in ref_block, '缺忠实度'
assert 'appended automatically' in ref_block, '缺引用说明'
print('OK ref block')
prompt = pb.build_outline_prompt('主题', 5, 'zh', 'Business', references='Smith (2024)', context='营收增长35%')
assert 'MUST be grounded' in prompt
assert "EXTRACT, don" in prompt
assert 'FAITHFUL' in prompt
print(f'OK full prompt ({len(prompt)} chars)')
