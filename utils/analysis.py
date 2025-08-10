import json
import os
from typing import Dict, Tuple, List, DefaultDict
from collections import defaultdict

def load_state_mapping(state_folder: str) -> Dict[str, str]:
    """加载状态文件夹中的所有state_str到state_str_content_free的映射"""
    state_mapping = {}
    for filename in os.listdir(state_folder):
        if filename.endswith('.json'):
            filepath = os.path.join(state_folder, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    state_str = data.get('state_str')
                    content_free = data.get('state_str_content_free')
                    if state_str and content_free:
                        state_mapping[state_str] = content_free
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error processing {filename}: {e}")
    return state_mapping

def process_event_files(event_folder: str, state_mapping: Dict[str, str]) -> Tuple[Dict[Tuple[str, str], int], DefaultDict[Tuple[str, str], List[Tuple[str, str, str]]]]:
    """处理事件文件夹中的文件，统计状态转换次数和原始state对"""
    transition_counts = defaultdict(int)
    original_state_pairs = defaultdict(list)
    
    for filename in sorted(os.listdir(event_folder)):  # 按文件名排序，通常文件名包含时间信息
        if filename.endswith('.json'):
            filepath = os.path.join(event_folder, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    start_state = data.get('start_state')
                    stop_state = data.get('stop_state')
                    tag = data.get('tag', '')  # 获取tag信息
                    
                    if start_state and stop_state:
                        start_content_free = state_mapping.get(start_state, "Not found")
                        stop_content_free = state_mapping.get(stop_state, "Not found")
                        transition_key = (start_content_free, stop_content_free)
                        transition_counts[transition_key] += 1
                        original_state_pairs[transition_key].append((start_state, stop_state, tag))
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error processing {filename}: {e}")
    
    return transition_counts, original_state_pairs

def save_results(transition_counts: Dict[Tuple[str, str], int], 
                original_state_pairs: DefaultDict[Tuple[str, str], List[Tuple[str, str, str]]],
                output_file: str):
    """将统计结果保存到文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        # 写入表头
        f.write("=== 状态转换统计 ===\n\n")
        f.write("start_state_content_free\tstop_state_content_free\tcount\t原始state_str对及时间戳\n")
        
        # 按出现次数降序排序
        sorted_transitions = sorted(transition_counts.items(), key=lambda x: x[1], reverse=True)
        
        for (start_cf, stop_cf), count in sorted_transitions:
            # 写入转换统计
            f.write(f"{start_cf}\t{stop_cf}\t{count}\n")
            
            # 获取并按tag排序原始state_str对
            state_pairs = sorted(original_state_pairs[(start_cf, stop_cf)], key=lambda x: x[2])
            
            # 写入对应的原始state_str对和时间戳
            for start_state, stop_state, tag in state_pairs:
                f.write(f"\t{start_state} -> {stop_state}\t({tag})\n")
            
            f.write("\n")  # 添加空行分隔不同转换组


def count_unique_states(state_folder: str) -> Dict[str, Dict[str, int]]:
    """统计状态文件夹中所有唯一的state_str和state_str_content_free"""
    state_stats = {
        'state_str': defaultdict(int),
        'state_str_content_free': defaultdict(int),
        'state_pairs': defaultdict(int)
    }
    
    for filename in os.listdir(state_folder):
        if filename.endswith('.json'):
            filepath = os.path.join(state_folder, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    state_str = data.get('state_str')
                    content_free = data.get('state_str_content_free')
                    
                    if state_str:
                        state_stats['state_str'][state_str] += 1
                    if content_free:
                        state_stats['state_str_content_free'][content_free] += 1
                    if state_str and content_free:
                        state_stats['state_pairs'][(state_str, content_free)] += 1
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error processing {filename}: {e}")
    
    return state_stats

def save_state_stats(state_stats: Dict[str, Dict[str, int]], output_file: str):
    """将统计结果保存到文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=== 状态统计结果 ===\n\n")
        
        # 统计state_str
        f.write(f"1. 唯一state_str数量: {len(state_stats['state_str'])}\n")
        f.write(f"   出现次数最多的state_str:\n")
        top_state_str = sorted(state_stats['state_str'].items(), key=lambda x: x[1], reverse=True)[:5]
        for state, count in top_state_str:
            f.write(f"   - {state}: {count} 次\n")
        
        # 统计state_str_content_free
        f.write(f"\n2. 唯一state_str_content_free数量: {len(state_stats['state_str_content_free'])}\n")
        f.write(f"   出现次数最多的state_str_content_free:\n")
        top_content_free = sorted(state_stats['state_str_content_free'].items(), key=lambda x: x[1], reverse=True)[:5]
        for content_free, count in top_content_free:
            f.write(f"   - {content_free}: {count} 次\n")
        
        # 统计state_str和content_free的组合
        f.write(f"\n3. 唯一(state_str, state_str_content_free)组合数量: {len(state_stats['state_pairs'])}\n")
        f.write(f"   出现次数最多的组合:\n")
        top_pairs = sorted(state_stats['state_pairs'].items(), key=lambda x: x[1], reverse=True)[:5]
        for (state, content_free), count in top_pairs:
            f.write(f"   - ({state}, {content_free}): {count} 次\n")

def main():
    # 配置文件夹路径
    # event_folder = r"C:\Projects\2025Unicom\output\Unicom_dfs_1\events"
    # state_folder = r"C:\Projects\2025Unicom\output\Unicom_dfs_1\states"
    # output_file = r"C:\Projects\2025Unicom\output\Unicom_dfs_1\transition_counts.txt"
    # output_file1 = r"C:\Projects\2025Unicom\output\Unicom_dfs_1\state_counts.txt"
    event_folder = r"C:\Projects\2025Unicom\output\Telegram_dfs_1\events"
    state_folder = r"C:\Projects\2025Unicom\output\Telegram_dfs_1\states"
    output_file = r"C:\Projects\2025Unicom\output\Telegram_dfs_1\transition_counts.txt"
    output_file1 = r"C:\Projects\2025Unicom\output\Telegram_dfs_1\state_counts.txt"


    # 统计状态
    print("正在统计状态信息...")
    state_stats = count_unique_states(state_folder)
    
    # 保存结果
    save_state_stats(state_stats, output_file1)
    print(f"统计结果已保存到 {output_file1}")
    # 打印摘要信息
    print("\n统计摘要:")
    print(f"唯一state_str数量: {len(state_stats['state_str'])}")
    print(f"唯一state_str_content_free数量: {len(state_stats['state_str_content_free'])}")
    print(f"唯一(state_str, state_str_content_free)组合数量: {len(state_stats['state_pairs'])}")
    
    # 加载状态映射
    print("正在加载状态映射...")
    state_mapping = load_state_mapping(state_folder)
    print(f"已加载 {len(state_mapping)} 个状态映射")
    
    # 处理事件文件并统计转换次数
    print("正在处理事件文件并统计转换次数...")
    transition_counts, original_state_pairs = process_event_files(event_folder, state_mapping)
    
    # 保存结果
    save_results(transition_counts, original_state_pairs, output_file)
    print(f"统计结果已保存到 {output_file}")

    # 打印一些统计信息
    total_transitions = sum(transition_counts.values())
    unique_transitions = len(transition_counts)
    print(f"\n统计摘要:")
    print(f"总转换次数: {total_transitions}")
    print(f"唯一转换组合数: {unique_transitions}")
    
    # 打印最常见的5个转换
    print("\n最常见的5个状态转换:")
    sorted_transitions = sorted(transition_counts.items(), key=lambda x: x[1], reverse=True)
    for (start, stop), count in sorted_transitions[:5]:
        print(f"{start} -> {stop}: {count} 次")

if __name__ == "__main__":
    main()