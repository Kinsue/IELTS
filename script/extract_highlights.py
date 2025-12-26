import re
import os
import sys
import json

def process_file(file_path):
    if not os.path.exists(file_path):
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r'==(.*?)=='
    matches = re.findall(pattern, content, re.DOTALL)
    
    unique_results = []
    seen = set()
    for m in matches:
        clean = m.strip()
        if clean and clean not in seen:
            seen.add(clean)
            unique_results.append(clean)

    unique_results = sorted(unique_results)
    

    output_path = os.path.splitext(file_path)[0] + "_words.txt"

    if not unique_results:
        # 如果当前 md 删除了所有高亮，则尝试删除对应的 txt 文件
        if os.path.exists(output_path):
            os.remove(output_path)
            print(f"Removed: {output_path}")
        return False

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(unique_results))
    print(f"Updated: {output_path}")
    return True

if __name__ == "__main__":
    # 从第一个参数读取 JSON 数组
    try:
        files_json = sys.argv[1]
        files_to_process = json.loads(files_json)
        for file_path in files_to_process:
            if file_path.endswith('.md'):
                process_file(file_path)
    except Exception as e:
        print(f"Error: {e}")


