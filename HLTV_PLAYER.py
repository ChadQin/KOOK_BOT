import pandas as pd


class HLTVPlayerManager:
    def __init__(self, file_path=None):
        self.file_path = file_path
        self._player_names = None
        self._df = None
        self.nation_dict = {
            "欧洲": ['德国', '法国', '丹麦', '爱沙尼亚', '北马其顿', '波黑', '波兰', '芬兰', '捷克',
                     '拉脱维亚', '立陶宛', '罗马尼亚', '挪威', '斯洛伐克', '斯洛文尼亚', '土耳其',
                     '西班牙', '匈牙利', '英国','瑞典'],
            "独联体": ['乌克兰', '俄罗斯', '哈萨克斯坦', '白俄罗斯'],
            "亚大": ['中国', '马来西亚', '澳大利亚', '蒙古', '以色列'],
            "北美": ['加拿大', '美国'],
            "南美": ['阿根廷', '巴西', '乌拉圭', '智利'],
            "非洲": ['南非']
        }
        # 生成反向映射：国家→区域（假设一个国家只属于一个区域）
        self.country_to_region = {country: region for region, countries in self.nation_dict.items() for country in
                                  countries}

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

        # 修改排序逻辑，使用lower()忽略大小写
        sorted_names = sorted(self._player_names, key=lambda x: x.lower()) if self._player_names else []
        player_count = len(sorted_names)
        return sorted_names, player_count

    def get_player_info(self, player_name, file_path=None, refresh=False):
        if self._df is None or refresh:
            self.get_sorted_player_names(file_path=file_path, refresh=refresh)
        if self._df is not None:
            player_info = self._df[self._df['NAME'] == player_name]
            if not player_info.empty:
                # 定义固定列头
                fixed_headers = ["NAME", "TEAM", "NATION", "AGE", "ROLE", "MAJ_NUM"]
                # 构建选手数据行，直接从DataFrame中按列名获取数据
                data_values = []
                for header in fixed_headers:
                    if header in self._df.columns:
                        value = player_info[header].iloc[0]
                        data_values.append(str(value))
                    else:
                        # 如果没有匹配的列，使用占位符
                        data_values.append("N/A")
                # 使用制表符连接列头和数据
                headers_line = "\t".join(fixed_headers)
                data_line = "\t".join(data_values)
                return f"{headers_line}\n{data_line}"
            else:
                return f"未找到选手 '{player_name}' 的信息。"
        else:
            return "数据加载失败，请检查文件路径和文件内容。"

    def get_country_region(self, country):
        """通过反向映射快速获取国家所属的区域（单个区域，假设一对一映射）"""
        return self.country_to_region.get(country, None)