# Modify_nrrd_utf-8

- 按需求修改line 8-line 24
  ```
  # Variables: 自定义的拼写修正json
  # Funcs: 修改后的nrrd读取函数
  from Variables import SPELLING_CORRECTIONS, SPELLING_CORRECTIONS_WORDS
  import Funcs
  
  # 定义全局标签文件路径
  GLOBAL_LABELS_FILE = r'.\Global_labels.json'
  
  # 定义输入（包含原nrrd文件）、输出目录
  input_dir = r'.\extracted_files'
  output_dir = r'.\remapped_files'
  
  # 定义基准目录，用来精简输出部分
  base_dir = r'.\extracted_files'
  
  # 定义日志文件路径
  log_file = r'.\remapped_files\process.log'
  ```
- 标签json（Global_labels.json）格式如下：
  color: 标签颜色, name: 标签名字, value: 标签索引
  ```
  [
    {
        "labels": {
            "color": [
                0.2,
                1.0,
                1.0
            ],
            "name": "Laparoscopic Needle Driver-Tool Clasper",
            "value": 1
        }
    },
    {
        "labels": {
            "color": [
                0.0,
                0.2,
                0.8
            ],
            "name": "Laparoscopic Needle Driver-Tool Shaft",
            "value": 2
        }
    }
  ]
  ```
- (OPTION) 标签json（Global_labels.json）如果有其他清洗要求请修改line 35-line 40
  ```
  # 预处理全局标签映射
  # 去除所有的数字、空格、换行符和'-'，全部变成小写字母
  global_name_mapping = {
      re.sub(r'[\d\s\r\n-]+', '', label["labels"]["name"]).lower().replace("-", "").replace(" ", ""): label["labels"]
      for label in GLOBAL_LABELS
  }
  ```
- 根据具体数据修改line 113-line 129进行清洗
  ```
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
  ```
