import requests
import json
import os
from datetime import datetime, timedelta, timezone
from ics import Calendar, Event
import pytz

# 设置时区
tz = pytz.timezone('Asia/Shanghai')

# 服务器ID与名称映射
SERVER_MAPPING = {
    1167: "红玉海",
    1081: "神意之地",
    1042: "拉诺西亚",
    1044: "幻影群岛",
    1060: "萌芽池",
    1174: "沃仙曦染",
    1175: "晨曦王座",
}

# 数据映射
AREA_MAPPING = {
    0: "海雾村",
    1: "薰衣草苗圃",
    2: "高脚孤丘",
    3: "白银乡",
    4: "穹顶皓天"
}

REGIONTYPE_MAPPING = {
    1: "仅限部队购买",
    2: "仅限个人购买",
    0: "其他"
}

# 计算周期结束时间
def calculate_purchase_endtime(current_timestamp):
    cycle_start = 1719846000
    cycle_length_seconds = 9 * 24 * 60 * 60
    cycle_number = (current_timestamp - cycle_start) // cycle_length_seconds
    cycle_start_time = cycle_start + cycle_number * cycle_length_seconds
    cycle_end_time = cycle_start_time + cycle_length_seconds
    return cycle_end_time + 5 * 24 * 60 * 60

# 从API请求数据
def fetch_data(server_id):
    url = f'https://house.ffxiv.cyou/api/sales?server={server_id}'
    headers = {'User-Agent': 'iCal 1.0.0 / Testone <ravens_slalom.0v@icloud.com>'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# 保存数据到文件
def save_json(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 处理数据
def process_data(data):
    size_1_events = {}
    size_2_events = {}
    
    for item in data:
        size = item.get('Size')
        purchase_endtime = item.get('Purchase_endtime')
        server = item.get('Server')
        area = item.get('Area')
        slot = item.get('Slot')
        id = item.get('ID')
        regiontype = item.get('RegionType')
        
        # 格式化详细信息
        server_name = SERVER_MAPPING.get(server, "未知服务器")
        area_name = AREA_MAPPING.get(area, "未知区域")
        regiontype_name = REGIONTYPE_MAPPING.get(regiontype, "未知类型")
        slot_description = f"{slot+1}区"
        id_description = f"{id}号"
        
        details = f"{server_name} - {area_name} - {slot_description} - {id_description} - {regiontype_name} - 数据来源 https://house.ffxiv.cyou"
        
        if size == 1:
            size_1_events.setdefault(purchase_endtime, []).append(details)
        elif size == 2:
            size_2_events.setdefault(purchase_endtime, []).append(details)
    
    return size_1_events, size_2_events

# 转换时间戳为UTC+8时间
def convert_to_utc_plus_8(timestamp):
    dt_utc = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
    return dt_utc.astimezone(tz)

# 生成日历文件
def generate_calendar(size_1_events, size_2_events, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for size, events in [('M房', size_1_events), ('L房', size_2_events)]:
        cal = Calendar()
        for endtime, details_list in events.items():
            event = Event()
            event.begin = convert_to_utc_plus_8(endtime)
            event.name = f"{size}抽选截至"
            event.description = "\n".join(details_list)
            cal.events.add(event)
        
        output_file = os.path.join(output_dir, f'{size.lower()}_抽选截至.ics')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(str(cal))

# 主函数
def main():
    server_ids = [1167, 1081, 1042, 1044, 1060, 1174, 1175]
    for server_id in server_ids:
        print(f"Processing server {server_id}...")
        try:
            data = fetch_data(server_id)
            filtered_data = [item for item in data if item.get('Size') in [1, 2]]
            for item in filtered_data:
                firstseen_timestamp = item.get('FirstSeen')
                if firstseen_timestamp:
                    current_timestamp = int(firstseen_timestamp)
                    item['Purchase_endtime'] = calculate_purchase_endtime(current_timestamp)
            
            size_1_events, size_2_events = process_data(filtered_data)
            generate_calendar(size_1_events, size_2_events, f'generated_files/server_{server_id}')
            print(f"Files for server {server_id} generated successfully.")
        except Exception as e:
            print(f"Error processing server {server_id}: {e}")

if __name__ == "__main__":
    main()
