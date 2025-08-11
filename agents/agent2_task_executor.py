import subprocess
import os
import re
from datetime import datetime

class Agent2TaskExecutor:
    def __init__(self, apk_path, output_dir, task_str, log_path, instruction_path):
        """
        初始化任务执行器
        :param apk_path: APK 文件路径 (绝对路径)
        :param output_dir: 输出目录
        :param task_str: 任务描述
        :param log_file: 日志文件路径
        """
        self.apk_path = apk_path
        self.output_dir = output_dir
        self.task_str = task_str
        self.log_path = log_path
        self.instruction_path = instruction_path

    def _generate_log_filename(self):
        """
        根据时间戳、APK 文件名和任务字符串生成日志文件名，并拼接 log_path。
        """
        # 获取时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 获取 APK 文件名（不带路径和扩展名）
        apk_name = os.path.splitext(os.path.basename(self.apk_path))[0]

        # 将 task_str 转成安全的文件名（只保留字母数字和下划线）
        safe_task = re.sub(r'[^a-zA-Z0-9]+', '_', self.task_str).strip("_")

        # 拼接文件名
        filename = f"{timestamp}_{apk_name}_{safe_task}.log"

        # 返回完整路径
        return os.path.join(self.log_path, filename)
    
    def run(self):
        """运行任务"""
        if not os.path.exists(self.apk_path):
            raise FileNotFoundError(f"APK 文件不存在: {self.apk_path}")

        os.makedirs(self.output_dir, exist_ok=True)

        cmd = [
            "python", "start.py",
            "-a", self.apk_path,
            "-o", self.output_dir,
            "-adaptive_policy",
            "-adaptive_instructions", self.instruction_path,
            "-task", self.task_str,
            "-keep_app",
            "-keep_env",
            "-is_emulator"
        ]

        log_file = self._generate_log_filename()
        
        with open(log_file, "wb") as f:
            process = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
            process.communicate()

        if process.returncode == 0:
            print(f"[Agent2] 任务执行完成，日志已保存到: {log_file}")
        else:
            print(f"[Agent2] 任务执行失败，请查看日志: {log_file}")


if __name__ == "__main__":
    # 示例用法
    executor = Agent2TaskExecutor(
        apk_path=r"C:\Projects\2025Unicom\apks\unicom.apk",
        output_dir="./output/",
        task_str="Book a flight from Beijing to Haikou in August 10th.",
        log_path="test1.log"
    )
    executor.run()
