import os
import json
import requests
from datetime import datetime, timedelta, timezone
from ics import Calendar, Event
import pytz

# 设置GMT+8时区
tz = pytz.timezone('Asia/Shanghai')

# 映射转换
AREA_MAPPING = {
    0: "海雾村",
    1: "薰衣草苗圃",
    2: "高脚孤丘",
    3: "白银乡",
    4: "穹顶皓天"
}

REGIONTYPE_MAPPING = {
    1: "部队",
    2: "个人",
    0: "其他"  # RegionType 为 0 的情况改为 "其他"
}

SERVER_MAPPING = {
    1173: "宇宙和音",
    1167: "红玉海",
    1081: "神意之地",
    1042: "拉诺西亚",
    1044: "幻影群岛",
    1060: "萌芽池",
    1174: "沃仙曦染",
    1175: "晨曦王座"
}

# 设置服务器ID
SERVER_IDS = ['1173', '1167', '1081', '1042', '1044', '1060', '1174', '1175']

# 计算周期函数
def check_period(current_timestamp):
    cycle_start = 1719846000  # 周期开始时间戳（2024年7月1日23时）
    cycle_length_seconds = 9 * 24 * 60 * 60  # 周期的长度（9天）
    cycle_number = (current_timestamp - cycle_start) // cycle_length_seconds
    cycle_start_time = cycle_start + cycle_number * cycle_length_seconds
    cycle_end_time = cycle_start_time + cycle_length_seconds
    purchase_end_time = cycle_end_time + 5 * 24 * 60 * 60
    return purchase_end_time

# 从API请求数据
def fetch_data(server_id):
    url = f'https://house.ffxiv.cyou/api/sales?server={server_id}'
    headers = {
        'User-Agent': 'iCal 1.0.0 / Testone <ravens_slalom.0v@icloud.com>'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to retrieve data: {response.status_code}")

# 筛选出Size为1和2的数据
def filter_data(data):
    return [item for item in data if item.get('Size') in [1, 2]]

# 保存数据为JSON文件
def save_to_json(data, folder_path, file_name):
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, file_name)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 读取JSON文件并处理数据
def process_data(input_file, output_folder):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    processed_data = []
    for item in data:
        area = item.get('Area')
        id = item.get('ID')
        slot = item.get('Slot')
        regiontype = item.get('RegionType')
        size = item.get('Size')
        server = item.get('Server')
        
        firstseen_timestamp = item.get('FirstSeen')
        if firstseen_timestamp:
            try:
                current_timestamp = int(firstseen_timestamp)
                purchased_endtime_timestamp = check_period(current_timestamp)
                
                processed_item = {
                    'Area': area,
                    'ID': id,
                    'Slot': slot,
                    'RegionType': regiontype,
                    'Size': size,
                    'Server': server,
                    'Purchase_endtime': purchased_endtime_timestamp
                }
                processed_data.append(processed_item)
            except ValueError:
                pass

    os.makedirs(output_folder, exist_ok=True)
    output_file = os.path.join(output_folder, 'processed_data.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=4)

# 将时间戳转换为 UTC+8 时间
def convert_to_utc_plus_8(timestamp):
    timestamp = int(timestamp)
    dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    dt_utc_plus_8 = dt_utc.astimezone(tz)
    return dt_utc_plus_8

# 生成日历文件
def generate_calendar(input_file, output_folder):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
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
        
        server_name = SERVER_MAPPING.get(server, server)
        area_name = AREA_MAPPING.get(area, "未知区域")
        regiontype_name = REGIONTYPE_MAPPING.get(regiontype, "未知类型")
        
        slot_description = f"{slot+1}区"
        id_description = f"{id}号"
        
        details = (f"{server_name} - {area_name} - {slot_description} - {id_description} - {regiontype_name}")
        
        if size == 1:
            if purchase_endtime not in size_1_events:
                size_1_events[purchase_endtime] = []
            size_1_events[purchase_endtime].append(details)
        elif size == 2:
            if purchase_endtime not in size_2_events:
                size_2_events[purchase_endtime] = []
            size_2_events[purchase_endtime].append(details)
    
    cal = Calendar()
    
    for endtime, details_list in size_1_events.items():
        event = Event()
        event.begin = convert_to_utc_plus_8(endtime)
        event.name = "M房抽选截止"
        event.description = "\n".join(details_list) + "\n数据来源https://house.ffxiv.cyou"
        cal.events.add(event)
    
    for endtime, details_list in size_2_events.items():
        event = Event()
        event.begin = convert_to_utc_plus_8(endtime)
        event.name = "L房抽选截止"
        event.description = "\n".join(details_list) + "\n数据来源https://house.ffxiv.cyou"
        cal.events.add(event)
    
    os.makedirs(output_folder, exist_ok=True)
    output_file = os.path.join(output_folder, 'calendar.ics')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(str(cal))

def main():
    for server_id in SERVER_IDS:
        try:
            # 请求数据
            data = fetch_data(server_id)

            # 筛选数据
            filtered_data = filter_data(data)

            # 保存为JSON文件
            folder_path = 'data/'  # 确保是相对路径
            server_folder = os.path.join(folder_path, server_id)
            save_to_json(filtered_data, server_folder, 'filtered_data.json')

            # 处理数据
            process_data(os.path.join(server_folder, 'filtered_data.json'), server_folder)

            # 生成日历
            generate_calendar(os.path.join(server_folder, 'processed_data.json'), server_folder)

            print(f"服务器 {server_id} 的文件已成功生成并保存到 {server_folder}")

        except Exception as e:
            print(f"服务器 {server_id} 发生错误: {e}")

if __name__ == "__main__":
    main()
