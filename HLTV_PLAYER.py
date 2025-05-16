import os
import pandas as pd


class HLTVPlayerManager:
    def __init__(self, file_path=None):
        self.file_path = file_path
        self._player_names = None
        self._df = None
        self.nation_dict = {
            "欧洲": ['德国', '法国', '丹麦', '爱沙尼亚', '北马其顿', '波黑', '波兰', '芬兰', '捷克',
                     '拉脱维亚', '立陶宛', '罗马尼亚', '挪威', '斯洛伐克', '斯洛文尼亚', '土耳其',
                     '西班牙', '匈牙利', '英国', '瑞典'],
            "独联体": ['乌克兰', '俄罗斯', '哈萨克斯坦', '白俄罗斯'],
            "亚大": ['中国', '马来西亚', '澳大利亚', '蒙古', '以色列'],
            "北美": ['加拿大', '美国'],
            "南美": ['阿根廷', '巴西', '乌拉圭', '智利'],
            "非洲": ['南非']
        }
        self.country_to_region = {country: region for region, countries in self.nation_dict.items() for country in
                                  countries}

    # 原有方法保持不变...
    def set_file_path(self, file_path):
        self.file_path = file_path
        self._player_names = None
        self._df = None

    def get_sorted_player_names(self, file_path=None, refresh=False):
        if refresh or self._player_names is None:
            path = file_path or self.file_path
            if not path:
                raise ValueError("未指定 Excel 文件路径，请使用 set_file_path 方法设置或在调用时提供")
            try:
                self._df = pd.read_excel(path, header=1)
                if 'Unnamed: 0' in self._df.columns:
                    self._df = self._df.drop(columns=['Unnamed: 0'])
                self._df = self._df.reset_index(drop=True)
                if 'NAME' in self._df.columns:
                    self._df['NAME'] = self._df['NAME'].astype(str)
                    self._player_names = self._df['NAME'].tolist()
                else:
                    print(f"错误：文件中未找到 'NAME' 列。列名：{', '.join(self._df.columns)}")
                    self._player_names = []
            except FileNotFoundError:
                print(f"错误：未找到文件 '{path}'。请检查文件路径是否正确。")
                self._player_names = []
            except Exception as e:
                print(f"错误：读取文件时发生未知错误：{e}")
                self._player_names = []

        sorted_names = sorted(self._player_names, key=lambda x: x.lower()) if self._player_names else []
        player_count = len(sorted_names)
        return sorted_names, player_count

    def get_player_info(self, player_name, file_path=None, refresh=False):
        if self._df is None or refresh:
            self.get_sorted_player_names(file_path=file_path, refresh=refresh)
        if self._df is not None:
            player_info = self._df[self._df['NAME'] == player_name]
            if not player_info.empty:
                fixed_headers = ["NAME", "TEAM", "NATION", "AGE", "ROLE", "MAJ_NUM"]
                data_values = []
                for header in fixed_headers:
                    if header in self._df.columns:
                        value = player_info[header].iloc[0]
                        data_values.append(str(value))
                    else:
                        data_values.append("N/A")
                headers_line = "\t".join(fixed_headers)
                data_line = "\t".join(data_values)
                return f"{headers_line}\n{data_line}"
            else:
                return f"未找到选手 '{player_name}' 的信息。"
        else:
            return "数据加载失败，请检查文件路径和文件内容。"

    def get_country_region(self, country):
        return self.country_to_region.get(country, None)

    # 新增方法：验证选手图片
    def validate_player_images(self, img_dir='img', suffix='.png', file_path=None):
        """
        验证选手名单与图片文件是否一一对应

        参数:
            img_dir (str): 图片文件夹路径，默认为同级目录下的'img'文件夹
            suffix (str): 图片文件后缀，默认为'.png'
            file_path (str): 可选，指定Excel文件路径，若不指定则使用已设置的路径

        返回:
            dict: 包含验证结果的字典
        """
        # 使用指定的文件路径或已设置的路径
        if file_path:
            self.set_file_path(file_path)

        # 确保数据已加载
        if self._df is None:
            self.get_sorted_player_names()

        # 检查必要条件
        if 'NAME' not in self._df.columns:
            return {
                'status': 'error',
                'message': "数据中未找到'NAME'列",
                'missing_images': []
            }

        # 获取所有选手名称
        player_names = set(self._df['NAME'].tolist())

        # 检查图片文件夹
        if not os.path.exists(img_dir):
            return {
                'status': 'error',
                'message': f"图片文件夹不存在: {img_dir}",
                'missing_images': list(player_names)
            }

        # 获取所有图片文件名（去除后缀）
        image_files = set()
        for filename in os.listdir(img_dir):
            if filename.endswith(suffix):
                player_name = filename[:-len(suffix)]
                image_files.add(player_name)

        # 计算差异
        missing_images = sorted([name for name in player_names if name not in image_files])
        extra_images = sorted([name for name in image_files if name not in player_names])

        return {
            'status': 'success',
            'missing_images': missing_images,
            'extra_images': extra_images,
            'total_players': len(player_names),
            'total_images': len(image_files),
            'valid': len(missing_images) == 0
        }


# 新增：独立验证函数（不影响类的原有功能）
def validate_player_images_standalone(excel_path="data/HLTV_Player.xlsx", img_dir="img", suffix=".png"):
    """独立验证函数，用于直接从命令行验证图片"""
    if not os.path.exists(excel_path):
        return {
            'status': 'error',
            'message': f"Excel文件不存在: {excel_path}"
        }

    manager = HLTVPlayerManager(excel_path)
    return manager.validate_player_images(img_dir=img_dir, suffix=suffix)


# 主程序入口
# if __name__ == "__main__":
#     # 默认使用 data/HLTV_Player.xlsx 和 img 文件夹，后缀为 .png
#     result = validate_player_images_standalone()
#
#     if result['status'] == 'error':
#         print(f"验证失败: {result['message']}")
#     else:
#         if result['valid']:
#             print(f"验证成功！所有 {result['total_players']} 名选手均有对应的图片。")
#         else:
#             print(f"验证完成：共 {result['total_players']} 名选手，发现 {len(result['missing_images'])} 处缺失：")
#             for name in result['missing_images']:
#                 print(f"- 缺失图片: {name}.png")  # 直接使用 .png 后缀，无需变量
#
#             if result['extra_images']:
#                 print("\n以下图片没有对应的选手数据：")
#                 for name in result['extra_images']:
#                     print(f"- 多余图片: {name}.png")  # 直接使用 .png 后缀