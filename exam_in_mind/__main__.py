"""支持 python -m exam_in_mind 调用方式。"""
import sys

# Windows 终端默认 GBK 编码,强制切换为 UTF-8 避免中文乱码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from exam_in_mind.main import main

if __name__ == "__main__":
    main()
