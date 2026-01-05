import re
import os
import sys
import json
from nltk.stem import WordNetLemmatizer as wnl

def process_file(file_path):
    if not os.path.exists(file_path):
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r'==(.*?)=='
    matches = re.findall(pattern, content, re.DOTALL)

    unique_results = sorted(list(set(WordLemmatization(m.strip()) for m in matches if m.strip())))

    output_path = os.path.splitext(file_path)[0] + "_words.txt"

    if not unique_results:
        if os.path.exists(output_path):
            os.remove(output_path)
            print(f"Removed: {output_path}")
        return False

    # 检查是否真的需要写入（防止文件时间戳改变导致无意义提交）
    new_content = "\n".join(unique_results)
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            if f.read() == new_content:
                return False

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Updated: {output_path}")
    return True

def WordLemmatization(word: str):
    return wnl().lemmatize(word)

if __name__ == "__main__":
    processed_files = []
    
    # 1. 尝试从参数获取变动文件
    try:
        if len(sys.argv) > 1:
            files_to_process = json.loads(sys.argv[1])
            for f in files_to_process:
                if f.endswith('.md') and process_file(f):
                    processed_files.append(f)
    except:
        pass

    # 2. 【核心修复】全量扫描缺失的文件
    # 如果 md 存在但 _words.txt 不存在，强制跑一遍
    for root, dirs, files in os.walk('.'):
        if '.git' in root or '.github' in root: continue
        for file in files:
            if file.endswith('.md'):
                md_path = os.path.join(root, file)
                txt_path = os.path.splitext(md_path)[0] + "_words.txt"
                if not os.path.exists(txt_path):
                    if process_file(md_path):
                        processed_files.append(md_path)

    # 给 Action 提供输出名
    if processed_files and "GITHUB_OUTPUT" in os.environ:
        names = ", ".join([os.path.basename(x) for x in processed_files[:10]])
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"file_names={names}\n")
