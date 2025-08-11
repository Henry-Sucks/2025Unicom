import os
from pathlib import Path
import json
import re
import subprocess

def extract_doc_task(text):
    # 匹配 "**Your ultimate task is: ...**" 这一段
    task_pattern = r"\n\n\*\*Your ultimate task is: .*?\*\*\n\n"
    
    # 查找匹配的任务语句
    task_match = re.search(task_pattern, text, re.DOTALL)
    
    if task_match:
        task_text = task_match.group()  # 获取匹配的任务文本
        text = re.sub(task_pattern, '', text, count=1)  # 移除原位置的任务文本
        task = task_text.strip()
        # text = text.strip() + "\n\n" + task_text.strip()  # 将任务文本追加到最后
     
        return text, task
    
    return None, None


def extract_time_info(text):
    # 正则表达式说明：
    # ^[^:]+:     匹配行首到第一个冒号的内容（忽略）
    # \s*         匹配冒号后面的空格
    # ([a-zA-Z\s]+time)   捕获以 "time" 结尾的键，如 "sampling time", "load time" 等
    # \s*=\s*     匹配等号两边可能的空格
    # ([\d.]+\s*ms)  捕获时间值，形如 "18.50 ms"
    pattern = r'^[^:]+:\s*([a-zA-Z\s]+time)\s*=\s*([\d.]+)\s*ms'
    
    # 使用 re.M 多行模式匹配所有符合条件的行
    matches = re.findall(pattern, text, re.MULTILINE)
    
    result = {key.strip(): float(value.strip()) for key, value in matches}
    return result

def run_command(cmd):

    # 使用 subprocess.Popen 启动进程
    result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    stdout_output = []
    stderr_output = []
    
    # 循环读取 stdout 和 stderr
    for line in result.stdout:
        print(line, end='')  # 打印到控制台
        stdout_output.append(line)
    
    for line in result.stderr:
        print(line, end='')  # 打印到控制台
        stderr_output.append(line)
    
    # 等待进程结束
    result.wait()

    # 返回 stdout 和 stderr 的内容
    return ''.join(stdout_output), ''.join(stderr_output)

app_name = 'App Launcher' # set app name
llama_cli_path = "build/bin/llama-cli" # set llama-cli path
prompt_path = "all_prompts.json" # set test prompt
model_path = "AutoDroid-V2-Q8_0.gguf" # set model path

all_prompts = json.loads(Path(prompt_path).read_text())

prompt_prefix, _ = extract_doc_task(all_prompts[app_name][0])


# generate cache first

result = run_command([
    f'{llama_cli_path}',
    "-m", f"{model_path}",
    "-p", prompt_prefix,
    "--prompt-cache", f"{app_name}_cache.bin",
    "-n", "1"
])

time_list = []
for idx, prompt in enumerate(all_prompts[app_name]):
    prompt_prefix, task = extract_doc_task(prompt)
    
    assert prompt_prefix is not None
    assert task is not None

    final_prompt = prompt_prefix + task
    stdout, stderr = run_command([
    f'{llama_cli_path}',
    "-m", f"{model_path}",
    "-p", prompt_prefix,
    "--prompt-cache", f"{app_name}_cache.bin",
    "--prompt-cache-ro",
    "-n", "3"
    ])
    time_dict = extract_time_info(stderr)
    time_list.append(time_dict)

# calc total time average
total_time = sum([time_dict['total time'] for time_dict in time_list]) / len(time_list)
print(f"Total time average: {total_time}")
