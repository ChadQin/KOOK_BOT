import requests
import json
from datetime import datetime


class FF14PriceQuery:
    BASE_URL = "https://universalis.app/api/v2"
    cities_translate = {
        "Limsa Lominsa": "利姆萨·罗敏萨",
        "Gridania": "格里达尼亚",
        "Ul'dah": "乌尔达哈",
        "Ishgard": "伊修加德",
        "Kugane": "黄金港",
        "Crystarium": "水晶都",
        "Old Sharlayan": "旧萨雷安",
        "Tuliyollal": "图莱尤拉"
    }

    server_id_dict = {
        21: "Ravana",
        22: "Bismarck",
        23: "Asura",
        24: "Belias",
        28: "Pandaemonium",
        29: "Shinryu",
        30: "Unicorn",
        31: "Yojimbo",
        32: "Zeromus",
        33: "Twintania",
        34: "Brynhildr",
        35: "Famfrit",
        36: "Lich",
        37: "Mateus",
        39: "Omega",
        40: "Jenova",
        41: "Zalera",
        42: "Zodiark",
        43: "Alexander",
        44: "Anima",
        45: "Carbuncle",
        46: "Fenrir",
        47: "Hades",
        48: "Ixion",
        49: "Kujata",
        50: "Typhon",
        51: "Ultima",
        52: "Valefor",
        53: "Exodus",
        54: "Faerie",
        55: "Lamia",
        56: "Phoenix",
        57: "Siren",
        58: "Garuda",
        59: "Ifrit",
        60: "Ramuh",
        61: "Titan",
        62: "Diabolos",
        63: "Gilgamesh",
        64: "Leviathan",
        65: "Midgardsormr",
        66: "Odin",
        67: "Shiva",
        68: "Atomos",
        69: "Bahamut",
        70: "Chocobo",
        71: "Moogle",
        72: "Tonberry",
        73: "Adamantoise",
        74: "Coeurl",
        75: "Malboro",
        76: "Tiamat",
        77: "Ultros",
        78: "Behemoth",
        79: "Cactuar",
        80: "Cerberus",
        81: "Goblin",
        82: "Mandragora",
        83: "Louisoix",
        85: "Spriggan",
        86: "Sephirot",
        87: "Sophia",
        88: "Zurvan",
        90: "Aegis",
        91: "Balmung",
        92: "Durandal",
        93: "Excalibur",
        94: "Gungnir",
        95: "Hyperion",
        96: "Masamune",
        97: "Ragnarok",
        98: "Ridill",
        99: "Sargatanas",
        400: "Sagittarius",
        401: "Phantom",
        402: "Alpha",
        403: "Raiden",
        404: "Marilith",
        405: "Seraph",
        406: "Halicarnassus",
        407: "Maduin",
        408: "Cuchulainn",
        409: "Kraken",
        410: "Rafflesia",
        411: "Golem",
        3000: "Cloudtest01",
        3001: "Cloudtest02",
        1167: "红玉海",
        1081: "神意之地",
        1042: "拉诺西亚",
        1044: "幻影群岛",
        1060: "萌芽池",
        1173: "宇宙和音",
        1174: "沃仙曦染",
        1175: "晨曦王座",
        1172: "白银乡",
        1076: "白金幻象",
        1171: "神拳痕",
        1170: "潮风亭",
        1113: "旅人栈桥",
        1121: "拂晓之间",
        1166: "龙巢神殿",
        1176: "梦羽宝境",
        1043: "紫水栈桥",
        1169: "延夏",
        1106: "静语庄园",
        1045: "摩杜纳",
        1177: "海猫茶屋",
        1178: "柔风海湾",
        1179: "琥珀原",
        1192: "水晶塔",
        1183: "银泪湖",
        1180: "太阳海岸",
        1186: "伊修加德",
        1201: "红茶川",
        1068: "黄金谷",
        1064: "月牙湾",
        1187: "雪松原",
        2075: "카벙클",
        2076: "초코보",
        2077: "모그리",
        2078: "톤베리",
        2080: "펜리르"
    }

    def get_market_data(self, dc_name, item_id, listing_count=10):
        """查询指定大区和物品的市场板数据"""
        url = f"{self.BASE_URL}/{dc_name}/{item_id}?listings={listing_count}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"请求出错: {e}")
            return None

    def extract_listing_info(self, data):
        """提取上架信息（含时间转换）"""
        """
        调用方法：
            listings = ff14.extract_listing_info(market_data)
            for listing in listings:
                print(listing)
        """
        listings = []
        if not data or 'listings' not in data:
            return listings

        for listing in data['listings']:
            timestamp = listing.get('lastReviewTime', 0)
            upload_time = "未知"
            if timestamp > 0:
                timestamp = timestamp / 1000 if timestamp > 10000000000 else timestamp
                try:
                    upload_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                except:
                    upload_time = "时间格式错误"

            info = {
                '服务器名': listing['worldName'],
                '单价': listing['pricePerUnit'],
                '上架数量': listing['quantity'],
                '上架雇员名': listing['retainerName'],
                '总价': listing['total'],
                '是否为HQ': listing['hq'],
                '上架时间': upload_time
            }
            listings.append(info)
        return listings

    def get_market_tax_rates(self, server_name):
        """通过服务器名称查询税率并转换为中文"""
        """
        调用方法:
            for city, rate in tax_rates.items():
                print(f"{city}：{rate}%")
        """

        server_id = next((k for k, v in self.server_id_dict.items() if v == server_name), None)
        if not server_id:
            print(f"错误：未找到服务器 '{server_name}' 的ID")
            return None

        try:
            url = f"{self.BASE_URL}/tax-rates?world={server_id}"
            response = requests.get(url)
            response.raise_for_status()
            tax_data = response.json()
            return {self.cities_translate.get(city, city): rate for city, rate in tax_data.items()}
        except Exception as e:
            print(f"税率查询出错: {e}")
            return None

    def get_exact_match_item_id(self, target_name):
        """精确匹配物品ID"""
        base_url = "https://cafemaker.wakingsands.com/Search"
        params = {"indexes": "item", "string": target_name}
        try:
            response = requests.get(base_url, params=params, proxies={'http': None, 'https': None})
            response.raise_for_status()
            data = response.json()
            for item in data.get("Results", []):
                if item.get("Name") == target_name:
                    return item.get("ID")
            print(f"警告：未找到物品 '{target_name}'")
            return None
        except Exception as e:
            print(f"物品ID查询出错: {e}")
            return None

    def get_item_price_dc(self, server_name, item_id):
        """获取数据中心价格数据"""
        url = f"{self.BASE_URL}/aggregated/{server_name}/{item_id}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"价格数据查询出错: {e}")
            return None

    def visualize_dc_data(self, price_data):
        """可视化数据中心价格数据"""
        output = []
        if not price_data or not price_data.get('results'):
            print("错误：未获取到有效价格数据")
            return ""

        for item in price_data['results']:
            item_output = [f"物品ID: {item['itemId']}"]
            world_time_map = {
                upload['worldId']: datetime.fromtimestamp(upload['timestamp'] / 1000)
                for upload in item.get('worldUploadTimes', [])
            }

            # 处理NQ数据
            nq_data = item.get('nq', {})
            nq_items = self._process_quality_data(nq_data, world_time_map, "NQ")
            if nq_items:
                item_output.append("\nNQ:")
                item_output.extend(nq_items)

            # 处理HQ数据
            hq_data = item.get('hq', {})
            hq_items = self._process_quality_data(hq_data, world_time_map, "HQ", require_complete=True)
            if hq_items:
                item_output.append("\nHQ:")
                item_output.extend(hq_items)

            output.append("\n".join(item_output))
        return "\n\n".join(output) if output else "无有效数据"

    def _process_quality_data(self, quality_data, world_time_map, quality_type, require_complete=False):
        """处理NQ/HQ数据的内部方法"""
        items = []
        required_fields = ['minListing', 'recentPurchase', 'averageSalePrice', 'dailySaleVelocity']

        if require_complete:
            if not all(f in quality_data and 'dc' in quality_data[f] for f in required_fields):
                return []

        # 最低售价
        min_listing = quality_data.get('minListing', {}).get('dc', {})
        if min_listing and 'price' in min_listing:
            items.append(self._format_price_item(
                "1. 最低售价", min_listing, world_time_map, "数据上传时间"
            ))

        # 最近售出价
        recent_purchase = quality_data.get('recentPurchase', {}).get('dc', {})
        if recent_purchase and 'price' in recent_purchase and 'timestamp' in recent_purchase:
            items.append(self._format_price_item(
                "2. 最近售出价", recent_purchase, world_time_map, "售出时间", is_purchase=True
            ))

        # 平均售价
        avg_price = quality_data.get('averageSalePrice', {}).get('dc', {})
        if avg_price and 'price' in avg_price:
            items.append(f"3. 平均售价：{avg_price['price']}")

        # 日销量
        daily_sale = quality_data.get('dailySaleVelocity', {}).get('dc', {})
        if daily_sale and 'quantity' in daily_sale:
            items.append(f"4. 日销量：{daily_sale['quantity']:.2f}")

        return items

    def _format_price_item(self, title, data, world_time_map, time_type, is_purchase=False):
        """格式化价格条目的内部方法"""
        world_id = data.get('worldId', '未知')
        server_name = self.server_id_dict.get(world_id, f"未知服务器({world_id})")
        price = data.get('price', '未知')
        time_stamp = data.get('timestamp', data.get('worldId'))  # 兼容两种时间字段
        upload_time = world_time_map.get(world_id, "未知")

        if isinstance(upload_time, datetime):
            upload_time = upload_time.strftime("%Y-%m-%d %H:%M:%S")
        elif time_stamp and isinstance(time_stamp, (int, float)):
            upload_time = datetime.fromtimestamp(time_stamp / 1000).strftime("%Y-%m-%d %H:%M:%S")

        time_info = f"({server_name}, {time_type}：{upload_time})" if upload_time != "未知" else f"({server_name})"
        return f"{title}：{price}{time_info}"