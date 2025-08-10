import os
import re
import hashlib
import ast
from openai import OpenAI
from openai import OpenAI, APITimeoutError, APIError
import time
ACTION_MISSED = None

def query_deepseek(prompt, max_retries=3, timeout=60):
    client = OpenAI(
        # api_key=os.environ['DEEPSEEK_API_KEY'],  # 替换为你的 DeepSeek API Key 环境变量名
        api_key = "sk-c28d942a29394ba5ba8bab30dc4db683",
        base_url="https://api.deepseek.com",      # DeepSeek API 的基础 URL
    )
    
    for attempt in range(1, max_retries + 1):
        try:
            completion = client.chat.completions.create(
                messages=[
                    {"role": "user", "content": prompt}
                ],
                model="deepseek-chat",
                timeout=timeout
            )

            res = completion.choices[0].message.content.strip()
            # 如果 DeepSeek 返回了 JSON 包裹，去掉包裹符
            res = res.strip("```json").strip("```").strip()
            return res

        except APITimeoutError:
            print(f"[DeepSeek] 第 {attempt} 次请求超时（timeout={timeout}s）")
        except APIError as e:
            print(f"[DeepSeek] API 错误: {e}")
        except Exception as e:
            print(f"[DeepSeek] 未知错误: {e}")

        if attempt < max_retries:
            wait_time = 2 ** attempt  # 指数退避
            print(f"[DeepSeek] {wait_time} 秒后重试...")
            time.sleep(wait_time)
        else:
            print("[DeepSeek] 达到最大重试次数，放弃请求。")

    return ACTION_MISSED