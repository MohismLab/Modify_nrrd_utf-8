import os
import re
import nrrd
import json
import shutil
import numpy as np

# Variables: 自定义的拼写修正json
# Funcs: 修改后的nrrd读取函数
from Variables import SPELLING_CORRECTIONS, SPELLING_CORRECTIONS_WORDS
import Funcs

# 定义全局标签文件路径
GLOBAL_LABELS_FILE = r'D:\301-Task2\Global_labels.json'

# 定义输入（包含原nrrd文件）、输出目录
input_dir = r'D:\301-Task2\extracted_files'
output_dir = r'D:\301-Task2\remapped_files'

# 定义基准目录，用来精简输出部分
base_dir = r'D:\301-Task2\extracted_files'

# 定义日志文件路径
log_file = r'D:\301-Task2\remapped_files\process.log' 

# 从 JSON 文件中加载全局标签（有中文）
def load_global_labels(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data

# 加载全局标签
GLOBAL_LABELS = load_global_labels(GLOBAL_LABELS_FILE)

# 预处理全局标签映射
# 去除所有的数字、空格、换行符和'-'，全部变成小写字母
global_name_mapping = {
    re.sub(r'[\d\s\r\n-]+', '', label["labels"]["name"]).lower().replace("-", "").replace(" ", ""): label["labels"]
    for label in GLOBAL_LABELS
}

global_color_mapping = {tuple(label["labels"]["color"]): label["labels"]["name"] for label in GLOBAL_LABELS}
global_value_mapping = {label["labels"]["name"]: label["labels"]["value"] for label in GLOBAL_LABELS}

   
def process_nrrd_files(root_dir, output_dir, log_file):
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    
    # 创建日志文件
    with open(log_file, "w", encoding="utf-8") as log:
        log.write("处理日志开始\n")
        
        # 遍历所有nrrd文件
        conflict_log = []
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.endswith('.nrrd'):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(root, root_dir)
                    output_subdir = os.path.join(output_dir, relative_path)
                    os.makedirs(output_subdir, exist_ok=True)
                    
                    try:
                        with open(file_path, 'rb') as f:
                            # 读取nrrd文件
                            # 使用修改后的nrrd读取函数
                            header = Funcs.read_header_v2(f)

                            data = nrrd.read_data(header, f)

                        # ---------- 如果直接修改nrrd读取函数行不通，可以选择按行读取nrrd header然后按行写入 ----------
                        # encoding = 'utf-8'
                        # 读取 nrrd 文件
                        # data, header = read_nrrd_with_encoding(file_path)        
                        # with open(file_path, 'rb') as f:
                        #     # 读取原始字节并解码为UTF-8字符串
                        #     raw_header = []
                        #     while True:
                        #         line = f.readline().decode('utf-8').strip()
                        #         if line == '':
                        #             break  # Header结束标志
                        #         raw_header.append(line)                          
                        #     # 手动解析Header键值对
                        #     header = {}
                        #     for line in raw_header:
                        #         if ':' in line:
                        #             key, value = line.split(':', 1)
                        #             key = key.strip()
                        #             value = value.strip()
                        #             if key == 'sizes':
                        #                 value = [int(num) for num in value.split()]
                        #             header[key] = value                         
                        #     f.seek(0)  # 重置文件指针
                        #     data = nrrd.read_data(header, f)
                        # ----------------------------------------------------------------------

                        # 解析标签组
                        if 'org.mitk.multilabel.segmentation.labelgroups' not in header:
                            relative_path3 = os.path.relpath(file_path, base_dir)
                            log.write(f"跳过文件（未找到标签组）: {relative_path3}\n")
                            continue
                            
                        labelgroups = json.loads(header['org.mitk.multilabel.segmentation.labelgroups'])
                        
                        # 建立旧值到新值的映射
                        value_mapping = {}
                        color_conflicts = []
                        
                        for group in labelgroups:
                            for label in group['labels']:
                                # 清洗标签名称
                                original_name = label['name']
                                # 去除所有数字、换行符'\r'和'\n'，并转换为小写
                                clean_name = re.sub(r'[\d]+', '', original_name).lower()
                                clean_name = re.sub(r'[\s]+', '-', clean_name)  # 将一个或多个空格替换为'-'
                                clean_name = clean_name.replace("\\r", '')  # 替换字符串中的 "\r"（字符'\'和'r'而不是换行符） 为空
                                clean_name = clean_name.replace("\\n", '')
                                clean_name = clean_name.replace('\r', '').replace('\n', '').replace('\t', '')

                                # 拼写修正，'\b'只替换独立的单词
                                pattern1 = re.compile(r'\b(' + '|'.join(map(re.escape, SPELLING_CORRECTIONS_WORDS.keys())) + r')\b')
                                clean_name = pattern1.sub(lambda match: SPELLING_CORRECTIONS_WORDS[match.group(0)], clean_name)
                                pattern2 = re.compile('|'.join(map(re.escape, SPELLING_CORRECTIONS.keys())))
                                clean_name = pattern2.sub(lambda match: SPELLING_CORRECTIONS[match.group(0)], clean_name)

                                # 最后删除空白字符、'-'、'.'，避免把'drive'替换成'driver'
                                clean_name = re.sub(r'[\s\-\.]+', '', clean_name)

                                # 查找全局标签
                                global_label = global_name_mapping.get(clean_name)
                                
                                if not global_label:
                                    relative_path1 = os.path.relpath(file_path, base_dir)
                                    # log.write(f"{relative_path1}未找到匹配的全局标签: {original_name})\n")
                                    log.write(f"{relative_path1}未找到匹配的全局标签: {clean_name} (原始: {original_name})\n")
                                    continue
                                    
                                # 更新标签名称
                                label['name'] = global_label['name']
                                
                                # 检查颜色冲突
                                current_color = tuple(round(c, 4) for c in label['color']['value'])
                                global_color = tuple(round(c, 4) for c in global_label['color'])
                                
                                if current_color != global_color:
                                    color_conflicts.append({
                                        'original': original_name,
                                        'current_color': current_color,
                                        'global_color': global_color
                                    })

                                # 按照全局映射修改颜色冲突部分
                                label['color']['value'] = global_color
                                
                                # 建立值映射
                                old_value = label['value']
                                new_value = global_label['value']
                                value_mapping[old_value] = new_value
                                label['value'] = new_value
                        
                        # 记录颜色冲突
                        if color_conflicts:
                            conflict_log.append({
                                'file': file_path,
                                'conflicts': color_conflicts
                            })
                        
                        # 更新header
                        # ensure_ascii: 确保非 ASCII 字符被转义为 Unicode 转义序列
                        header['org.mitk.multilabel.segmentation.labelgroups'] = json.dumps(labelgroups, ensure_ascii=True)
                        
                        # 重新映射像素值
                        remapped_data = np.zeros_like(data)
                        for old_val, new_val in value_mapping.items():
                            remapped_data[data == old_val] = new_val

                        # ---------- 强制转换 Header 内容为 ASCII ----------
                        for key in list(header.keys()):
                            value = header[key]
                            if isinstance(value, str):
                                # 直接忽略非 ASCII 字符
                                # header[key] = value.encode('ascii', 'ignore').decode('ascii')                                
                                # 用问号 '?' 替换非 ASCII 字符
                                header[key] = value.encode('ascii', 'replace').decode('ascii')
                                original_value = header[key]
                                encode_value = original_value.encode('ascii', 'replace').decode('ascii')
                                if original_value != encode_value:
                                    log.write(f"清理非 ASCII 字符: {key} (原始值: {original_value} -> 新值: {encode_value})\n")
                            
                        # -----------------------------------------------------
                        
                        # 保存新文件
                        output_path = os.path.join(output_subdir, file)
                        nrrd.write(output_path, remapped_data, header=header)
                        # log.write(f"已处理: {file_path} -> {output_path}\n")
                        
                    except Exception as e:
                        log.write(f"处理文件 {file_path} 失败: {str(e)}\n")
        
        # 输出颜色冲突报告
        log.write("\n颜色冲突报告:\n")
        for entry in conflict_log:
            relative_path2 = os.path.relpath(entry['file'], base_dir)
            log.write(f"\n文件: {relative_path2}\n")
            for conflict in entry['conflicts']:
                log.write(f"  标签 '{conflict['original']}'\n")
                log.write(f"    当前颜色: {conflict['current_color']}\n")
                log.write(f"    全局颜色: {conflict['global_color']}\n")
        
        log.write("处理日志结束\n")

def processing(input_dir, output_dir, log_file, base_dir = ''):
    # 清空输出目录
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    process_nrrd_files(input_dir, output_dir, log_file)

processing(input_dir, output_dir, log_file, base_dir)