import re
import os
import sys
import json
import argparse
import spacy
from wordfreq import zipf_frequency
from tqdm import tqdm
#
# COCA_10K_THRESHOLD = 3.4
COCA_10K_THRESHOLD = 0

def extract_highlight_word_with_spacy(file):
    # 1. 读取文件
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 2. 预检：如果连高亮符号都没有，直接跳过加载模型，节省时间
    if "==" not in content:
        return False

    # 2. 加载模型
    try:
        # 增大 max_length 防止大文件溢出
        nlp = spacy.load("en_core_web_md", disable=["ner"])
        nlp.max_length = 3000000 
    except OSError:
        print("Error: Model not found. Run: python -m spacy download en_core_web_md", file=sys.stderr)
        return False


     # 3. 获取所有高亮区域的坐标范围 (Indices)
    # 只要在 ==...== 之间的字符区域，都被视为“有效区”
    pattern = re.compile(r'==(.+?)==', re.DOTALL)
    valid_ranges = []
    
    # 为了 Spacy 能更好理解句意，我们把 == 替换为空格（保持坐标不变）
    content_list = list(content)

    # 调试：打印一下是否匹配到了东西
    match_count = 0
    for match in pattern.finditer(content):
        match_count += 1
        # match.span(1) 是 == 内部内容的起始和结束位置
        valid_ranges.append(match.span(1))

        # 替换前后 == 为空格
        start, end = match.span(0)
        # ==word==
        # start, start+1 是前 ==
        # end-2, end-1 是后 ==
        # 注意: 只有在 match 是 ==...== 的时候才替换
        # 但 regex 已经保证了这点
        content_list[start] = ' '
        content_list[start+1] = ' '
        content_list[end-2] = ' '
        content_list[end-1] = ' '
    
    cleaned_content = "".join(content_list)
    
    print(f"File: {os.path.basename(file)} | Found {match_count} highlighted segments.")


    # 4. 全文 NLP 处理
    if "CI" not in os.environ:
        print(f"Analyzing context...")
    
    doc = nlp(cleaned_content)
    
    extracted_lemmas = set()

    # 5. 核心逻辑：区间判定 (Interval Check)
    # 将 valid_ranges 排序以优化查找 (可选，但在数据量不大时不做也可以)
    # 为了性能，我们将 ranges 转换为更易查找的结构，或者直接遍历
    # 考虑到 md 文档一般高亮不会几百万个，直接遍历 valid_ranges 是够快的
    
    def is_token_in_highlight(token_start, token_end, ranges):
        """判断 Token 的坐标是否完全落在某一个高亮区间内"""
        for r_start, r_end in ranges:
            # 逻辑：Token 的起始位置 >= 区间起始 AND Token 的结束位置 <= 区间结束
            # 这样可以处理 ==*word*== 的情况：
            # 区间是 *word* (index 10-16)
            # Token 是 word (index 11-15) -> 包含在内 -> 提取
            if token_start >= r_start and token_end <= r_end:
                return True
        return False

    # 遍历所有 Token
    # 如果是 CI 环境，禁用 tqdm
    disable_tqdm = "CI" in os.environ
    for token in tqdm(doc, desc="Extracting", disable=disable_tqdm):
        if token.is_alpha: # 只提取字母，自动过滤掉 * 和空格
            # 检查这个单词是否在我们的高亮名单里
            # token.idx 是 token 在原文中的起始字符位置
            # token.idx + len(token) 是结束位置
            if is_token_in_highlight(token.idx, token.idx + len(token), valid_ranges):
                extracted_lemmas.add(token.lemma_.lower())

    # 6. 频率过滤与输出
    valid_words = [w for w in extracted_lemmas if zipf_frequency(w, 'en') > COCA_10K_THRESHOLD]
    unique_results = sorted(valid_words, key=lambda w: zipf_frequency(w, 'en'))
    
    print(f"Extracted {len(unique_results)} unique words.")
    return _write_to_file(file, unique_results)


def _write_to_file(source_file, words_list):
    output_path = os.path.splitext(source_file)[0] + "_words.txt"

    new_content = "\n".join(words_list)
    # 减少冗长的列表输出，只在非 CI 环境或少量单词时打印
    # if "CI" not in os.environ or len(words_list) < 20:
    #     print(words_list)
    
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            if f.read() == new_content:
                print(f"No changes: {output_path}")
                return False

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Updated: {output_path}")
    return True


if __name__ == "__main__":
    processed_files = []
    
    # 1. 尝试从参数获取变动文件
    try:
        if len(sys.argv) > 1:
            files_to_process = json.loads(sys.argv[1])
            for f in files_to_process:
                if f.endswith('.md') and extract_highlight_word_with_spacy(f):
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
                if extract_highlight_word_with_spacy(md_path):
                    processed_files.append(md_path)

    # 给 Action 提供输出名
    if processed_files and "GITHUB_OUTPUT" in os.environ:
        names = ", ".join([os.path.basename(x) for x in processed_files[:10]])
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"file_names={names}\n")
