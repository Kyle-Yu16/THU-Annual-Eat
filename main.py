from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64
import json
import matplotlib.pyplot as plt
import requests
import platform
import argparse

def decrypt_aes_ecb(encrypted_data: str) -> str:
    
    key = encrypted_data[:16].encode('utf-8')
    encrypted_data = encrypted_data[16:]
    encrypted_data_bytes = base64.b64decode(encrypted_data)
    
    cipher = AES.new(key, AES.MODE_ECB)
    
    decrypted_data = unpad(cipher.decrypt(encrypted_data_bytes), AES.block_size)

    return decrypted_data.decode('utf-8')



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type = str)
    parser.add_argument("--starttime", type = str)
    parser.add_argument("--endtime", type = str)
    parser.add_argument("--max_n", type = int)
    parser.add_argument("--show", action = "store_true")

    args = parser.parse_args()
    if args.starttime is not None or args.endtime is not None:
        assert args.year is None, "指定起始日期和截止日期时不能同时指定年份"
        year = None
        starttime = args.starttime
        endtime = args.endtime
        assert starttime is not None and endtime is not None, "必须同时指定起始日期和截止日期"
    else:
        year = args.year if args.year else "2025"
        starttime = f"{year}-01-01"
        endtime = f"{year}-12-31"
        
    # 读入账户信息
    try:
        with open("config.json", "r", encoding='utf-8') as f:
            account = json.load(f)
            idserial = account["idserial"]
            servicehall = account["servicehall"]
    except Exception as e:
        print("账户信息读取失败，请重新输入")
        idserial = input("请输入学号: ")
        servicehall = input("请输入服务代码: ")
        with open("config.json", "w", encoding='utf-8') as f:
            json.dump({"idserial": idserial, "servicehall": servicehall}, f, indent=4)
    
    # 发送请求，得到加密后的字符串
    base_url = "https://card.tsinghua.edu.cn/business/querySelfTradeList"
    params = {
        "pageNumber": 0,
        "pageSize": 5000,
        "starttime": starttime,
        "endtime": endtime,
        "idserial": idserial,
        "tradetype": -1
    }
    cookie = {
        "servicehall": servicehall,
    }
    response = requests.post(base_url, params=params, cookies=cookie)

    # 解密字符串
    encrypted_string = json.loads(response.text)["data"]
    decrypted_string = decrypt_aes_ecb(encrypted_string)

    # 整理数据
    all_data = dict()
    data = json.loads(decrypted_string)
    for item in data["resultData"]["rows"]:
        try:
            if item["mername"] in all_data:
                all_data[item["mername"]] += item["txamt"]
            else:
                all_data[item["mername"]] = item["txamt"]
        except Exception as e:
            pass
    all_data = {k: round(v / 100, 2) for k, v in all_data.items()} # 将分转换为元，并保留两位小数
    consumption = sum(all_data.values())
    all_data = dict(sorted(all_data.items(), key=lambda x: x[1], reverse=False))
    if args.max_n and len(all_data) > args.max_n:
        all_data = dict(list(all_data.items())[len(all_data)-args.max_n:])

    # 输出结果
    # TODO 统计平均每天/周/月的消费金额
    if platform.system() == "Darwin":
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
    elif platform.system() == "Linux":
        plt.rcParams['font.family'] = ['Droid Sans Fallback', 'DejaVu Sans']
    else:
        plt.rcParams['font.sans-serif'] = ['SimHei']
    
    fig_height = max(8, len(all_data) * 0.4)
    plt.figure(figsize=(12, fig_height))
    plt.barh(list(all_data.keys()), list(all_data.values()))
    for index, value in enumerate(list(all_data.values())):
        plt.text(value + 0.01 * max(all_data.values()),
                index,
                str(value),
                va='center')
        
    # plt.tight_layout()
    plt.xlim(0, 1.2 * max(all_data.values()))
    plt.title(f"华清大学食堂消费情况（共计{consumption}元）")
    plt.xlabel("消费金额（元）")

    save_path = f"results/result_{year}.png" if year else f"results/result_{starttime}_{endtime}.png"
    plt.savefig(save_path)
    if args.show :
        plt.show()

if __name__ == "__main__":
    main()
    