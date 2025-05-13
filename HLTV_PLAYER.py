import pandas as pd


class HLTVPlayerManager:
    def __init__(self, file_path=None):
        self.file_path = file_path
        self._player_names = None
        self._df = None

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
        sorted_names = sorted(self._player_names) if self._player_names else []
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