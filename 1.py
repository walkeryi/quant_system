# -*- coding: utf-8 -*-
import os
import sys

def print_directory_tree(path, prefix='', max_depth=None, current_depth=0, ignore_dirs=None, file=None):
    """
    递归打印目录树，可忽略某些目录，并可选写入文件
    :param path: 要遍历的根目录路径
    :param prefix: 打印前缀（用于缩进和连接线）
    :param max_depth: 最大递归深度，None表示无限制
    :param current_depth: 当前深度
    :param ignore_dirs: 要忽略的目录名列表（例如 ['.venv', '__pycache__']）
    :param file: 可选的文件对象，用于同时写入内容
    """
    if max_depth is not None and current_depth > max_depth:
        return

    if ignore_dirs is None:
        ignore_dirs = []

    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        line = f"{prefix}└── [权限不足]"
        print(line)
        if file:
            file.write(line + '\n')
        return

    # 过滤掉要忽略的目录
    entries = [e for e in entries if e not in ignore_dirs]

    entries_count = len(entries)
    for index, entry in enumerate(entries):
        full_path = os.path.join(path, entry)
        is_last = (index == entries_count - 1)

        connector = '└── ' if is_last else '├── '
        line = f"{prefix}{connector}{entry}"
        print(line)
        if file:
            file.write(line + '\n')

        if os.path.isdir(full_path):
            extension = '    ' if is_last else '│   '
            print_directory_tree(full_path, prefix + extension, max_depth, current_depth + 1, ignore_dirs, file)

if __name__ == '__main__':
    target_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    IGNORE = ['.venv', '__pycache__', '.git', '.idea', 'venv', 'env', 'build', 'dist']

    # 打开文件（覆盖模式）
    output_file = os.path.join(target_dir, 'directory_tree.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        # 写入标题
        f.write(f"目录树: {os.path.abspath(target_dir)} (忽略: {IGNORE})\n")
        print(f"目录树: {os.path.abspath(target_dir)} (忽略: {IGNORE})")

        # 递归打印目录树，同时写入文件
        print_directory_tree(target_dir, ignore_dirs=IGNORE, file=f)

    print(f"\n目录树已保存到: {output_file}")