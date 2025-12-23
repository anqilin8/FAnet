# -*- coding: utf-8 -*-
"""
批量：经纬度去重 → 计算节药率 → 随机多关喷头生成新TXT → 计算前/后节药率
- 扫描 IN_DIR 下的 .txt/.csv
- 去重：Latitude & Longitude 字符串完全相同（含 N/E）→ 保留首条
- 节药率：1 - (sum(每行Zones里1的个数) / (记录数 * NOZZLE_CNT))
- 额外随机关喷头：对原来为1的位置，以概率 EXTRA_OFF_PROB 置0，写 *_dedup_rand.txt
- 兼容字段：优先 Zones；无则尝试 Control Signal
"""

import os, glob, re, random

# ====== 改这里 ======
IN_DIR            = r"E:\conda\weed\runs\64\exp_76"  # 你的txt所在文件夹
NOZZLE_CNT        = 6                                     # 喷头数
EXTRA_OFF_PROB    = 0.25                                  # 对原本为1的喷头额外随机关的概率
RANDOM_SEED       = 42                                    # 复现实验
OUT_SUFFIX_DEDUP  = "_dedup"                              # 去重后后缀
OUT_SUFFIX_RAND   = "_dedup_rand"                         # 随机多关后后缀
# =====================

random.seed(RANDOM_SEED)

def split_top_level_commas(line: str):
    """仅在顶层逗号处分割，[] 内逗号不切开"""
    parts, buf, depth = [], [], 0
    for ch in line:
        if ch == '[':
            depth += 1; buf.append(ch)
        elif ch == ']':
            depth = max(0, depth - 1); buf.append(ch)
        elif ch == ',' and depth == 0:
            parts.append(''.join(buf).strip()); buf = []
        else:
            buf.append(ch)
    if buf: parts.append(''.join(buf).strip())
    return parts

def parse_header(header_line: str):
    cols = split_top_level_commas(header_line.strip())
    name2idx = {c: i for i, c in enumerate(cols)}
    return cols, name2idx

def find_idx(name2idx, pred):
    for k, i in name2idx.items():
        if pred(k): return i
    return None

def parse_array(field: str):
    """'[0,1,1,0,1,1]' -> [0,1,1,0,1,1]；失败返回 None"""
    m = re.search(r'\[(.*?)\]', field)
    if not m: return None
    try:
        return [int(x.strip()) for x in m.group(1).split(',') if x.strip()!='']
    except:
        return None

def array_to_str(arr):
    return '[' + ', '.join(str(int(v)) for v in arr) + ']'

def dedup_by_latlon(lines):
    """返回(表头, 去重后的行列表list[str])；按经纬度字符串精确去重"""
    if not lines: return "", []
    header = lines[0]
    cols, name2idx = parse_header(header)
    idx_lat = find_idx(name2idx, lambda k: 'latitude'  in k.lower())
    idx_lon = find_idx(name2idx, lambda k: 'longitude' in k.lower())
    if idx_lat is None or idx_lon is None:
        return "", []

    kept = [header]
    seen = set()
    for ln in lines[1:]:
        parts = split_top_level_commas(ln)
        if max(idx_lat, idx_lon) >= len(parts):
            continue
        key = (parts[idx_lat].strip(), parts[idx_lon].strip())
        if key in seen:
            continue
        seen.add(key)
        kept.append(ln)
    return header, kept

def compute_saving_rate(lines, nozzle_cnt=NOZZLE_CNT):
    """根据数组列(Zones或Control Signal)计算节药率"""
    if not lines or len(lines) <= 1:
        return 0.0, 0, 0
    header = lines[0]
    cols, name2idx = parse_header(header)
    idx_arr = find_idx(name2idx, lambda k: k.strip().lower() == 'zones')
    if idx_arr is None:
        idx_arr = find_idx(name2idx, lambda k: ('control' in k.lower() and 'signal' in k.lower()))
    if idx_arr is None:
        return 0.0, 0, 0

    total_records = 0
    total_on = 0
    for ln in lines[1:]:
        parts = split_top_level_commas(ln)
        if idx_arr >= len(parts):
            continue
        arr = parse_array(parts[idx_arr])
        if arr is None or len(arr) != nozzle_cnt:
            continue
        total_records += 1
        total_on += sum(1 for v in arr if v == 1)
    if total_records == 0:
        return 0.0, 0, 0
    max_on = total_records * nozzle_cnt
    saving = 1.0 - (total_on / max_on)
    return saving, total_records, total_on

def make_random_off_lines(lines, nozzle_cnt=NOZZLE_CNT, extra_off_prob=EXTRA_OFF_PROB):
    """对原本为1的位置以概率置0，返回新行列表（保留其他字段不变，仅更新数组列）"""
    if not lines: return []
    header = lines[0]
    cols, name2idx = parse_header(header)
    idx_arr = find_idx(name2idx, lambda k: k.strip().lower() == 'zones')
    if idx_arr is None:
        idx_arr = find_idx(name2idx, lambda k: ('control' in k.lower() and 'signal' in k.lower()))
    if idx_arr is None:
        # 没有数组列，直接返回原样
        return lines[:]

    new_lines = [header]
    for ln in lines[1:]:
        parts = split_top_level_commas(ln)
        if idx_arr >= len(parts):
            new_lines.append(ln)
            continue
        arr = parse_array(parts[idx_arr])
        if arr is None or len(arr) != nozzle_cnt:
            new_lines.append(ln)
            continue
        # 仅对原为1的位以概率额外关掉
        arr2 = []
        for v in arr:
            if v == 1 and random.random() < extra_off_prob:
                arr2.append(0)
            else:
                arr2.append(v)
        parts[idx_arr] = array_to_str(arr2)
        new_lines.append(','.join(parts))
    return new_lines

def process_one_file(path):
    base, ext = os.path.splitext(path)
    out_dedup = base + OUT_SUFFIX_DEDUP + ext
    out_rand  = base + OUT_SUFFIX_RAND + ext

    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        raw_lines = [ln for ln in f.read().splitlines() if ln.strip()]

    # 1) 去重
    header, dedup_lines = dedup_by_latlon(raw_lines)
    if not dedup_lines:
        print(f"❌ 去重失败或无有效数据：{os.path.basename(path)}")
        return

    os.makedirs(os.path.dirname(out_dedup) or '.', exist_ok=True)
    with open(out_dedup, 'w', encoding='utf-8') as f:
        f.write('\n'.join(dedup_lines) + '\n')

    # 2) 原始节药率
    saving_org, nrec_org, on_org = compute_saving_rate(dedup_lines, NOZZLE_CNT)

    # 3) 生成“随机多关喷头”的新TXT
    rand_lines = make_random_off_lines(dedup_lines, NOZZLE_CNT, EXTRA_OFF_PROB)
    with open(out_rand, 'w', encoding='utf-8') as f:
        f.write('\n'.join(rand_lines) + '\n')

    # 4) 新节药率
    saving_new, nrec_new, on_new = compute_saving_rate(rand_lines, NOZZLE_CNT)

    print(f"📄 {os.path.basename(path)}")
    print(f"   → 去重后：记录 {nrec_org}，开启喷头总数 {on_org} / 最大 {nrec_org*NOZZLE_CNT}，节药率 = {saving_org:.2%}")
    print(f"   → 随机多关({EXTRA_OFF_PROB:.0%})：记录 {nrec_new}，开启喷头总数 {on_new} / 最大 {nrec_new*NOZZLE_CNT}，节药率 = {saving_new:.2%}")
    print(f"   → 输出：{os.path.basename(out_dedup)}，{os.path.basename(out_rand)}")

def main():
    paths = sorted(glob.glob(os.path.join(IN_DIR, '*.txt')) + glob.glob(os.path.join(IN_DIR, '*.csv')))
    if not paths:
        print(f"❌ 目录内未找到 .txt/.csv：{IN_DIR}")
        return
    for p in paths:
        process_one_file(p)

if __name__ == '__main__':
    main()
