import os
import json
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np

def find_event_file(event_folder: str, target_tag: str) -> str:
    """在事件文件夹中查找指定tag的JSON文件"""
    for filename in os.listdir(event_folder):
        if filename.endswith('.json') and target_tag in filename:
            return os.path.join(event_folder, filename)
    return None

def load_event_data(event_file: str) -> dict:
    """加载事件JSON数据"""
    try:
        with open(event_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error processing {event_file}: {e}")
        return None

def find_state_tags(state_folder: str, state_str: str) -> str:
    """在state文件夹中查找状态对应的tag"""
    for filename in os.listdir(state_folder):
        if filename.endswith('.json'):
            filepath = os.path.join(state_folder, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('state_str') == state_str:
                        return data.get('tag')
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error processing {filename}: {e}")
    return None

def find_state_image(pic_dir: str, tag: str) -> str:
    """在图片文件夹中查找状态截图"""
    image_path = os.path.join(pic_dir, f"screen_{tag}.png")
    return image_path if os.path.exists(image_path) else None

def find_view_image(view_dir: str, view_str: str) -> str:
    """在view文件夹中查找视图截图"""
    image_path = os.path.join(view_dir, f"view_{view_str}.png")
    return image_path if os.path.exists(image_path) else None

def display_comparison(start_img_path: str, stop_img_path: str, view_img_path: str, start_tag: str, stop_tag: str):
    """显示状态转换对比图和视图截图"""
    try:
        # 创建画布
        fig = plt.figure(figsize=(12, 10))
        
        # 打开所有图片
        start_img = Image.open(start_img_path)
        stop_img = Image.open(stop_img_path)
        
        # 调整状态图片大小，使高度一致
        min_height = min(start_img.height, stop_img.height)
        start_img = start_img.resize((int(start_img.width * min_height / start_img.height), min_height))
        stop_img = stop_img.resize((int(stop_img.width * min_height / stop_img.height), min_height))
        
        # 创建状态对比图
        state_comparison = Image.new('RGB', (start_img.width + stop_img.width, min_height))
        state_comparison.paste(start_img, (0, 0))
        state_comparison.paste(stop_img, (start_img.width, 0))
        
        # 添加状态对比图到画布
        ax1 = fig.add_subplot(2, 1, 1)
        ax1.imshow(state_comparison)
        ax1.set_title(f"状态转换对比\n开始: {start_tag} → 结束: {stop_tag}")
        ax1.axis('off')
        
        # 如果有视图截图，添加到下方
        if view_img_path:
            view_img = Image.open(view_img_path)
            ax2 = fig.add_subplot(2, 1, 2)
            ax2.imshow(view_img)
            ax2.set_title("触发事件的视图")
            ax2.axis('off')
        
        plt.tight_layout()
        plt.show()
        
    except Exception as e:
        print(f"显示对比图失败: {e}")

def main():
    # 配置路径
    event_folder = input("请输入事件JSON文件夹路径: ").strip()
    state_folder = input("请输入状态JSON文件夹路径: ").strip()
    pic_dir = input("请输入状态图片文件夹路径: ").strip()
    view_dir = input("请输入视图截图文件夹路径: ").strip()
    target_tag = input("请输入要查找的事件tag (如2025-07-18_024224): ").strip()
    
    # 1. 查找事件JSON文件
    print(f"正在查找tag为 '{target_tag}' 的事件文件...")
    event_file = find_event_file(event_folder, target_tag)
    if not event_file:
        print(f"未找到tag为 '{target_tag}' 的事件文件")
        return
    
    # 2. 加载事件数据
    event_data = load_event_data(event_file)
    if not event_data:
        print("无法加载事件数据")
        return
    
    # 3. 获取前后state_str和view_str
    start_state = event_data.get('start_state')
    stop_state = event_data.get('stop_state')
    view_str = event_data.get('event', {}).get('view', {}).get('view_str')
    
    if not start_state or not stop_state:
        print("事件中没有有效的start_state或stop_state")
        return
    
    print(f"状态转换: {start_state} -> {stop_state}")
    print(f"视图标识: {view_str}")
    
    # 4. 在state文件夹中查找对应的tag
    print("正在查找状态对应的tag...")
    start_tag = find_state_tags(state_folder, start_state)
    stop_tag = find_state_tags(state_folder, stop_state)
    
    if not start_tag:
        print(f"未找到start_state {start_state} 对应的tag")
        return
    if not stop_tag:
        print(f"未找到stop_state {stop_state} 对应的tag")
        return
    
    print(f"找到tag: 开始状态 {start_tag}, 结束状态 {stop_tag}")
    
    # 5. 查找状态图片
    print("正在查找状态图片...")
    start_img = find_state_image(pic_dir, start_tag)
    stop_img = find_state_image(pic_dir, stop_tag)
    
    if not start_img:
        print(f"未找到开始状态图片: screen_{start_tag}.png")
        return
    if not stop_img:
        print(f"未找到结束状态图片: screen_{stop_tag}.png")
        return
    
    # 6. 查找视图截图
    view_img = None
    if view_str:
        print("正在查找视图截图...")
        view_img = find_view_image(view_dir, view_str)
        if not view_img:
            print(f"未找到视图截图: view_{view_str}.png")
    
    # 7. 显示对比图
    print("正在显示状态转换对比图...")
    display_comparison(start_img, stop_img, view_img, start_tag, stop_tag)

if __name__ == "__main__":
    main()