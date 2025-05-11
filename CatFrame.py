import subprocess
import shutil
import os
from pathlib import Path

# 核心配置参数
input_dir = Path(r"C:\Users……测试")  # 视频源目录
output_dir = Path(r"C:\Users……测试-分帧")  # 输出目录
interval = 0.1  # 分帧间隔（秒）
max_width = 720  # 图片最大宽度（像素）
quality = 3  # 图片质量（1-31，值越小质量越高）
video_exts = ['.mp4', '.avi', '.mov', '.mkv']  # 支持的视频格式
ffmpeg_path = Path(r"C:\ffmpeg\ffmpeg.exe")  # ffmpeg路径

def get_ffmpeg():
    """获取ffmpeg路径"""
    if ffmpeg_path.exists():
        return str(ffmpeg_path)
    
    auto_path = shutil.which("ffmpeg")
    if auto_path:
        return auto_path
    
    raise FileNotFoundError("未找到ffmpeg！请安装ffmpeg或正确设置ffmpeg_path")

def process_video(video_path, out_folder, ffmpeg):
    """处理视频分帧"""
    scale_filter = f"scale='min(iw,{max_width})':-2"
    cmd = [
        ffmpeg,
        '-i', str(video_path),
        '-vf', f'fps={1/interval},{scale_filter}',
        '-qscale:v', str(quality),
        '-sws_flags', 'lanczos',
        str(out_folder / 'frame_%05d.jpg')
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"处理完成：{video_path}")
    except subprocess.CalledProcessError:
        print(f"处理失败：{video_path}")

def main():
    try:
        ffmpeg = get_ffmpeg()
    except FileNotFoundError as e:
        print(e)
        return
    
    # 遍历处理视频
    for root, _, files in os.walk(str(input_dir)):
        root_path = Path(root)
        for file in files:
            if Path(file).suffix.lower() in video_exts:
                video_path = root_path / file
                rel_path = Path(os.path.relpath(root, str(input_dir)))
                out_folder = output_dir / rel_path / Path(file).stem
                out_folder.mkdir(parents=True, exist_ok=True)
                
                process_video(video_path, out_folder, ffmpeg)

if __name__ == "__main__":
    main()