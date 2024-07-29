import requests
import time
import os
from datetime import datetime, timedelta
from ics import Calendar, Event
import pytz  # 引入pytz库

# 设置GMT+8时区
tz = pytz.timezone('Asia/Shanghai')

# 区域ID映射
AREA_MAP = {
    0: "海雾村",
    1: "薰衣草苗圃",
    2: "高脚孤丘",
    3: "白银乡",
    4: "穹顶皓天"
}

# 房屋用途限制类型映射
REGION_TYPE_MAP = {
    1: "仅限部队购买",
    2: "仅限个人购买"
}

# 抽签模式下的状态映射
STATE_MAP = {
    0: "未知/没有抽签信息",
    1: "可供购买",
    2: "结果公示阶段"
}

# 计算周期函数
def check_period(current_timestamp):
    # 周期开始时间戳（2024年7月1日23时）
    cycle_start = 1835713200
    
    # 周期的长度（申请期5天，公示期4天）
    application_period_seconds = 5 * 24 * 60 * 60
    publicity_period_seconds = 4 * 24 * 60 * 60
    
    # 计算当前时间距离周期开始时间的秒数
    elapsed_seconds = current_timestamp - cycle_start
    
    if elapsed_seconds < 0:
        return cycle_start + application_period_seconds
    
    # 计算当前时间属于周期的第几个周期
    cycle_number = elapsed_seconds // (application_period_seconds + publicity_period_seconds)
    
    # 计算当前周期内的起始时间戳
    cycle_start_time = cycle_start + cycle_number * (application_period_seconds + publicity_period_seconds)
    
    # 计算当前时间在当前周期内的偏移
    current_cycle_elapsed = current_timestamp - cycle_start_time
    
    # 判断当前时间是申请期还是公示期，并返回结束时间戳
    if current_cycle_elapsed < application_period_seconds:
        application_EndTime = cycle_start_time + application_period_seconds
        return application_EndTime
    else:
        publicity_EndTime = cycle_start_time + application_period_seconds + publicity_period_seconds
        return publicity_EndTime

# 处理日期函数
def process_date(EndTime, LastSeen):
    if EndTime == 0:
        # 如果end_time为0，则使用last_seen进行处理
        EndTime = check_period(LastSeen)
    # 对处理后的数据进行其他操作，这里简单返回end_time作为示例
    return EndTime

# 转换时间戳为本地时间格式
def convert_to_human_readable(timestamp):
    dt = datetime.utcfromtimestamp(timestamp) + timedelta(hours=8)  # 转换为GMT+8时间
    return dt.strftime('%Y-%m-%d %H:%M:%S')

# 读取现有ICS文件
def read_existing_ics(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            cal = Calendar(f.read())
        return cal
    else:
        return Calendar()

try:
    # 设置服务器ID
    server_id = '1173'

    # 设置请求URL
    url = f'https://house.ffxiv.cyou/api/sales?server={server_id}'

    # 设置请求头
    headers = {
        'User-Agent': 'iCal 1.0.0 / Testone <ravens_slalom.0v@icloud.com>'
    }

    # 发送GET请求获取数据
    response = requests.get(url, headers=headers)

    # 检查是否成功获取数据
    if response.status_code == 200:
        # 获取JSON格式的响应数据
        data_from_server = response.json()

        # 处理数据
        processed_data = []

        for item_data in data_from_server:
            Area = item_data['Area']
            ID = item_data['ID']
            EndTime = item_data['EndTime']
            LastSeen = item_data['LastSeen']
            Size = item_data.get('Size')  # 获取Size值
            Slot = item_data.get('Slot')  # 获取Slot值
            RegionType = item_data.get('RegionType')  # 获取RegionType值
            State = item_data.get('State')  # 获取State值

            # 仅在Size值为2时处理数据
            if Size == 2:
                # 调用处理日期函数处理时间戳
                processed_EndTime = process_date(EndTime, LastSeen)

                # 创建一个新的字典存储处理后的数据
                processed_item = {
                    'Area': AREA_MAP.get(Area, "未知"),
                    'ID': ID + 1,  # 房号从1开始计算
                    'EndTime_processed': convert_to_human_readable(processed_EndTime),
                    'Slot': Slot,
                    'RegionType': REGION_TYPE_MAP.get(RegionType, "未知"),
                    'State': STATE_MAP.get(State, "未知")
                }

                # 将处理后的数据存储到新的列表中
                processed_data.append(processed_item)

        # 读取现有ICS文件
        ics_file_path = 'house_sales.ics'
        cal = read_existing_ics(ics_file_path)

        # 创建ICS日历文件
        for item in processed_data:
            event_exists = False
            for event in cal.events:
                if event.name == f"{item['Area']}, {item['Slot']}区 {item['ID']} {item['RegionType']}":
                    existing_end_time = event.end.astimezone(tz)
                    new_end_time_gmt8 = datetime.strptime(item['EndTime_processed'], '%Y-%m-%d %H:%M:%S')
                    new_end_time_gmt8 = tz.localize(new_end_time_gmt8)

                    if new_end_time_gmt8 > existing_end_time:
                        event.end = new_end_time_gmt8
                        event.description = (
                            f"区域: {item['Area']}\n"
                            f"房号: {item['ID']}\n"
                            f"小区编号: {item['Slot']}\n"
                            f"房屋用途限制类型: {item['RegionType']}\n"
                            f"状态: {item['State']}\n"
                            f"当前阶段结束时间: {item['EndTime_processed']}"
                        )
                    event_exists = True
                    break

            if not event_exists:
                event = Event()
                event.name = f"{item['Area']}, {item['Slot']}区 {item['ID']} {item['RegionType']}"
                end_time_gmt8 = datetime.strptime(item['EndTime_processed'], '%Y-%m-%d %H:%M:%S')
                event.end = tz.localize(end_time_gmt8)
                event.description = (
                    f"区域: {item['Area']}\n"
                    f"房号: {item['ID']}\n"
                    f"小区编号: {item['Slot']}\n"
                    f"房屋用途限制类型: {item['RegionType']}\n"
                    f"状态: {item['State']}\n"
                    f"当前阶段结束时间: {item['EndTime_processed']}"
                )
                cal.events.add(event)

        # 写入ICS文件
        with open(ics_file_path, 'w', encoding='utf-8') as f:
            f.writelines(cal)

    else:
        print(f"Failed to retrieve data: {response.status_code}")

except requests.exceptions.RequestException as e:
    print(f"Error fetching data: {e}")
