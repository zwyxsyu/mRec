import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用您子业务空间的阿里云百炼API Key将下行替换为：api_key="sk-xxx",
    api_key="sk-4aedf49d1684488aabe5bb0bda0e9ec1",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
completion = client.chat.completions.create(
    model="qwen-plus",  # 此处以qwen-plus为例，可按需更换模型名称（须完成模型授权，且是标准模型）。支持模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    messages=[
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': '你是谁？'}],
)

print(completion.model_dump_json())
