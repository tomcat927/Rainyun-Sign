

# 雨云签到脚本

目前为准

m401a版本

其他文件夹都是可以删除


# 青龙脚本依赖安装

cv2

pip install opencv-python
 pip install --timeout 300 --retries 10 -i https://mirrors.aliyun.com/pypi/simple/     selenium numpy pillow lxml
 

[]20250927雨云 | Notion
https://www.notion.so/1289/20250927-27b04cb8350380fe8e0cfd082778238d


# 判断脚本是否在执行

ps aux | grep rainyun.py
方法 1：按进程名杀掉
<BASH>
pkill -f rainyun.py