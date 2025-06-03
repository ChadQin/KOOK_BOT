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

    def get_sale_history(self, dc_name, item_name, entries=100):
        """
        查询指定大区和物品的销售历史记录

        参数:
            dc_name (str): 大区名称（如"猫小胖"）
            item_name (str): 物品中文名（如"黑星石"）
            entries (int): 返回记录条数（默认100，最大限制请参考API文档）

        返回:
            str: 格式化后的销售历史字符串，或错误信息
        """
        # 1. 通过物品名获取ID
        item_id = self.get_item_match_id(item_name)
        if not item_id:
            return "错误：未找到对应的物品ID"

        # 2. 构建API请求
        url = f"{self.BASE_URL}/history/{dc_name}/{item_id}?entriesToReturn={entries}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            sale_data = response.json()
        except requests.exceptions.RequestException as e:
            return f"销售历史查询失败: {str(e)}"

        # 3. 解析并格式化数据
        return self._format_sale_history(sale_data, item_name)

    def _format_sale_history(self, data, item_name):
        """内部方法：格式化销售历史数据"""
        if not data or 'entries' not in data or not data['entries']:
            return "无有效销售记录"

        formatted = [f"\n==== {item_name} 销售历史（共{len(data['entries'])}条） ===="]

        # 按时间倒序排列（最新的在前）
        entries = sorted(data['entries'], key=lambda x: x.get('timestamp', 0), reverse=True)

        for idx, entry in enumerate(entries, 1):
            # 处理时间戳（毫秒级转秒级）
            timestamp = entry.get('timestamp', 0)
            if timestamp:
                # 修复时间戳转换问题（除以1000转换为秒）
                try:
                    sale_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, OSError):
                    sale_time = "时间格式错误"
            else:
                sale_time = "未知"

            # 解析服务器名称
            world_id = entry.get('worldID')
            server_name = self.server_id_dict.get(world_id, f"未知服务器({world_id})") if world_id else "未知服务器"

            # 获取销售信息
            price_per_unit = entry.get('pricePerUnit', 0)
            quantity = entry.get('quantity', 0)

            # 计算总价（原数据没有总价，需通过单价*数量计算）
            total_price = price_per_unit * quantity

            # 获取HQ状态
            hq_status = "★HQ" if entry.get('hq', False) else "NQ"

            # 获取买家名称
            buyer_name = entry.get('buyerName', '匿名')

            # 构建记录（优化格式，添加千位分隔符）
            formatted.append(f"\n第{idx}条:")
            formatted.append(f"服务器: {server_name}")
            formatted.append(f"品质: {hq_status}")
            formatted.append(f"单价: {price_per_unit:,} gil")
            formatted.append(f"数量: {quantity}")
            formatted.append(f"总价: {total_price:,} gil")  # 使用计算的总价
            formatted.append(f"售出时间: {sale_time}")
            formatted.append(f"买家名称: {buyer_name}")

        return "\n".join(formatted)


    def get_market_data(self, dc_name, item_id, listing_count=500):
        """查询指定大区和物品的市场板数据"""
        url = f"{self.BASE_URL}/{dc_name}/{item_id}?listings={listing_count}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"请求出错: {e}")
            return None

    def extract_listing_info(self, data, sort_by='price', ascending=True):
        """提取并排序上架信息"""
        listings = []
        if not data or 'listings' not in data:
            return listings

        default_server = data.get('worldName', '未知服务器')

        for listing in data['listings']:
            server_name = listing.get('worldName', default_server)
            timestamp = listing.get('lastReviewTime', 0)
            upload_time = self._format_timestamp(timestamp)

            info = {
                '服务器名': server_name,
                '单价': listing.get('pricePerUnit', 0),
                '上架数量': listing.get('quantity', 0),
                '上架雇员名': listing.get('retainerName', '匿名'),
                '总价': listing.get('total', 0),
                'hq': listing.get('hq', False),  # 确保使用'hq'作为键名
                '上架时间': upload_time,
            }
            listings.append(info)

        # 按价格或时间排序
        if sort_by == 'price':
            listings.sort(key=lambda x: x['单价'], reverse=not ascending)
        elif sort_by == 'time':
            listings.sort(key=lambda x: x['上架时间'], reverse=not ascending)

        return listings

    def format_listings(self, listings, nq_count=25, hq_count=25):
        """按NQ/HQ分组显示，支持分别指定显示条数"""
        if not listings:
            return "无有效上架信息"

        # 调试输出：检查字段名
        if listings and 'hq' not in listings[0]:
            print(f"警告：列表元素缺少'hq'字段，可用字段：{listings[0].keys()}")

        nq_listings = [item for item in listings if not item.get('hq', False)]  # 使用get()避免KeyError
        hq_listings = [item for item in listings if item.get('hq', False)]

        formatted = []

        # 处理NQ部分
        if nq_listings:
            formatted.append(f"\n【普通品质 (NQ)】前{nq_count}条:")
            for idx, item in enumerate(nq_listings[:nq_count], 1):
                formatted.append(f"\n第{idx}条")
                formatted.append(f"服务器: {item['服务器名']}")
                formatted.append(f"单价: {item['单价']} gil")
                formatted.append(f"数量: {item['上架数量']} ×")
                formatted.append(f"雇员: {item['上架雇员名']}")
                formatted.append(f"总价: {item['总价']} gil")
                formatted.append(f"上架时间: {item['上架时间']}")

        # 处理HQ部分
        if hq_listings:
            formatted.append(f"\n\n【高品质 (HQ)】前{hq_count}条:")
            for idx, item in enumerate(hq_listings[:hq_count], 1):
                formatted.append(f"\n第{idx}条 ★")
                formatted.append(f"服务器: {item['服务器名']}")
                formatted.append(f"单价: {item['单价']} gil")
                formatted.append(f"数量: {item['上架数量']} ×")
                formatted.append(f"雇员: {item['上架雇员名']}")
                formatted.append(f"总价: {item['总价']} gil")
                formatted.append(f"上架时间: {item['上架时间']}")

        return "\n".join(formatted) if formatted else "无有效上架信息"

    def get_formatted_market_listings(self, dc_name, item, nq_count=10, hq_count=10, sort_by='price', ascending=True):
        """支持分别指定NQ/HQ显示条数的一站式查询"""
        print('查询商品名称：' + item)
        item_id = item if isinstance(item, int) else self.get_item_match_id(item)
        if not item_id:
            return "错误：未找到物品ID"

        market_data = self.get_market_data(dc_name, item_id)
        if not market_data:
            return "错误：未获取到市场数据"

        listings = self.extract_listing_info(market_data, sort_by, ascending)
        return self.format_listings(listings, nq_count, hq_count)

    def get_item_match_id(self, target_name):
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

    def get_market_tax_rates(self, server_name):
        """通过服务器名称查询税率并转换为中文"""
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

    def item_query(self, server_name, item):
        """合并获取数据与可视化的核心方法"""
        # 处理物品ID（支持名称或ID传入）
        item_id = item if isinstance(item, int) else self.get_item_match_id(item)
        if not item_id:
            return "错误：未找到对应的物品ID"

        # 获取价格数据
        price_data = self._fetch_price_data(server_name, item_id)
        if not price_data:
            return "错误：未获取到价格数据"

        # 可视化数据
        return self._visualize_price_data(price_data)

    def _fetch_price_data(self, server_name, item_id):
        """内部方法：获取价格数据"""
        url = f"{self.BASE_URL}/aggregated/{server_name}/{item_id}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"数据获取失败：{str(e)}")
            return None

    def _visualize_price_data(self, price_data):
        """内部方法：可视化价格数据"""
        output = []
        if not price_data or not price_data.get('results'):
            return "无有效价格数据"

        for item in price_data['results']:
            item_output = []  # 移除物品ID行
            world_time_map = self._build_world_time_map(item)

            # 处理NQ数据
            nq_items = self._process_quality_data(
                item.get('nq', {}),
                world_time_map,
                "NQ",
                require_complete=False
            )
            if nq_items:
                item_output.append("\nNQ:")
                item_output.extend(nq_items)

            # 处理HQ数据
            hq_items = self._process_quality_data(
                item.get('hq', {}),
                world_time_map,
                "HQ",
                require_complete=True
            )
            if hq_items:
                item_output.append("\nHQ:")
                item_output.extend(hq_items)

            # 过滤空的item_output（避免输出空行）
            if item_output:
                output.append("\n".join(item_output))

        return "\n\n".join(output) if output else "无有效数据"

    def _build_world_time_map(self, item):
        """构建服务器ID到时间的映射"""
        return {
            upload['worldId']: datetime.fromtimestamp(upload['timestamp'] / 1000)
            for upload in item.get('worldUploadTimes', [])
        }

    def _process_quality_data(self, quality_data, world_time_map, quality_type, require_complete=False):
        """处理NQ/HQ数据的内部方法"""
        items = []
        required_fields = ['minListing', 'recentPurchase', 'averageSalePrice', 'dailySaleVelocity']

        if require_complete and not all(f in quality_data for f in required_fields):
            return []

        # 最低售价
        min_listing = quality_data.get('minListing', {}).get('dc', {})
        items.extend(self._format_price_field(
            min_listing, world_time_map, "1. 最低售价", "数据上传时间"
        ))

        # 最近售出价
        recent_purchase = quality_data.get('recentPurchase', {}).get('dc', {})
        items.extend(self._format_price_field(
            recent_purchase, world_time_map, "2. 最近售出价", "售出时间", is_purchase=True
        ))

        # 平均售价
        avg_price = quality_data.get('averageSalePrice', {}).get('dc', {})
        if avg_price.get('price') is not None:
            items.append(f"3. 平均售价：{avg_price['price']:.2f}")

        # 日销量
        daily_sale = quality_data.get('dailySaleVelocity', {}).get('dc', {})
        if daily_sale.get('quantity') is not None:
            items.append(f"4. 日销量：{daily_sale['quantity']:.2f}")

        return [item for item in items if item]  # 过滤空条目

    def _format_price_field(self, data, world_time_map, title, time_type, is_purchase=False):
        """格式化价格字段"""
        if not data:
            return []

        world_id = data.get('worldId', '未知')
        server_name = self.server_id_dict.get(world_id, f"未知服务器({world_id})")
        price = data.get('price', '未知')

        # 处理时间
        if is_purchase:
            timestamp = data.get('timestamp', 0)
            time = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S") if timestamp else "未知"
        else:
            upload_time = world_time_map.get(world_id, None)
            time = upload_time.strftime("%Y-%m-%d %H:%M:%S") if upload_time else "未知"

        return [f"{title}：{price}(服务器：{server_name}, {time_type}：{time})"]

    def _format_timestamp(self, timestamp):
        """内部方法：格式化时间戳"""
        if timestamp <= 0:
            return "未知"
        try:
            # 自动处理毫秒级时间戳
            ts = timestamp / 1000 if timestamp > 10000000000 else timestamp
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except:
            return "时间格式错误"


# ===== 使用指南 =====
# 1. 导入类
#    from FF14_Price_Query import FF14PriceQuery
#
# 2. 初始化实例
#    price_query = FF14PriceQuery()
#
# 3. 调用方法示例：
#    # 查询物品ID
#    item_id = price_query.get_item_match_id('黑星石')
#
#    # 查询税率
#    tax_rates = price_query.get_market_tax_rates('海猫茶屋')
#
#    # 查询价格信息
#    price_info = price_query.item_query('海猫茶屋', '黑星石')
#
#    # 获取市场板信息
#    market_listings = price_query.get_formatted_market_listings('猫小胖', '棕豆蔻')
#
#    # 获取销售历史
#    sale_history = price_query.get_sale_history('猫小胖', '黑星石', 10)

    # 更多示例可以继续添加...
