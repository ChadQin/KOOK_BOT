import os
import asyncio
import sys
import time
from dotenv import load_dotenv
import aiohttp
import logging
import subprocess
from khl import Bot, Message, PublicVoiceChannel
from khl.card import Card, CardMessage, Module, Element, Types
from khl.card.color import Color
from typing import Dict, Optional, Union

"""Update Time: 2025/05/07"""

class StableMusicBot:
    def __init__(self, token: str):
        self._setup_logging()
        self._init_event_loop()  # 初始化事件循环
        self.bot_token = token  # 存储令牌作为类属性

        self.bot = Bot(token=token)
        self._http = None  # type: Optional[aiohttp.ClientSession]
        self._api_endpoints = [
            "https://music.163.com/api/search/get",
            "https://music.163.com/api/song/enhance/player/url"
        ]
        self._cookie = "cookie"
        self._register_handlers()
        self.current_stream_params = {}  # 存储推流参数 (audio_ssrc, audio_pt, ip, port, rtcp_port)
        self.is_playing = False  # 新增：用于跟踪歌曲播放状态，防止重复播放
        self.bot_name = "Chad Bot"
        self.bot_version = "1.0"
        self.author = "Chad Qin"

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('musicbot.log', mode='w', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _init_event_loop(self):
        if sys.platform == 'win32':
            if sys.version_info >= (3, 8):
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            else:
                asyncio.set_event_loop(asyncio.ProactorEventLoop())
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

    async def _ensure_http(self):
        if self._http is None or self._http.closed:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://music.163.com/",
                "Cookie": self._cookie,
                "Accept": "application/json",
                "Authorization": f"Bot {self.bot_token}"
            }
            self._http = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15),
                connector=aiohttp.TCPConnector(ssl=False, limit=10),
                headers=headers
            )

    async def _fetch_music_data(self, query: str) -> Dict[str, Union[str, int]]:
        await self._ensure_http()
        for retry in range(3):
            search_url = self._api_endpoints[0]
            search_params = {
                "s": query,
                "type": 1,
                "limit": 1
            }
            self.logger.info(f"[搜索歌曲] 请求 URL: {search_url}, 参数: {search_params}")
            try:
                async with self._http.get(search_url, params=search_params) as resp:
                    self.logger.info(f"[搜索歌曲] 响应状态码: {resp.status}")
                    if resp.status != 200:
                        self.logger.error(f"[搜索歌曲] 失败，状态码: {resp.status}, 响应内容: {await resp.text()}")
                        continue
                    data = await resp.json(content_type=None)
                    self.logger.info(f"[搜索歌曲] 响应内容: {data}")
                    if data['code'] == 200 and data['result']['songCount'] > 0:
                        song = data['result']['songs'][0]
                        song_id = song['id']
                        url_url = self._api_endpoints[1]
                        url_params = {
                            "ids": f"[{song_id}]",
                            "br": 320000,
                            "csrf_token": ""
                        }
                        self.logger.info(f"[获取播放链接] 请求 URL: {url_url}, 参数: {url_params}")
                        try:
                            async with self._http.post(url_url, data=url_params) as url_resp:
                                self.logger.info(f"[获取播放链接] 响应状态码: {url_resp.status}")
                                if url_resp.status != 200:
                                    self.logger.error(
                                        f"[获取播放链接] 失败，状态码: {url_resp.status}, 响应内容: {await url_resp.text()}")
                                    continue
                                url_data = await url_resp.json(content_type=None)
                                self.logger.info(f"[获取播放链接] 响应内容: {url_data}")
                                if url_data['code'] == 200 and url_data['data']:
                                    return {
                                        'url': url_data['data'][0]['url'],
                                        'title': song['name'],
                                        'artist': song['artists'][0]['name']
                                    }
                        except Exception as e:
                            self.logger.error(f"[获取播放链接] 异常: {str(e)}")
            except Exception as e:
                self.logger.error(f"[搜索歌曲] 异常: {str(e)}")
        raise ValueError("未找到匹配的歌曲")

    async def _join_user_voice_channel(self, msg: Message):
        author = msg.author
        guild_id = msg.ctx.guild.id
        await self._ensure_http()
        channel_list_url = f"https://www.kaiheila.cn/api/v3/channel/list?guild_id={guild_id}"
        self.logger.info(f"[获取频道列表] 请求 URL: {channel_list_url}")
        try:
            async with self._http.get(channel_list_url) as resp:
                if resp.status != 200:
                    self.logger.error(f"[获取频道列表] 失败，状态码: {resp.status}")
                    await msg.reply("获取频道列表失败，请稍后重试。")
                    return None
                channel_list_data = await resp.json()
                channels = channel_list_data.get('data', {}).get('items', [])
        except Exception as e:
            self.logger.error(f"[获取频道列表] 异常: {str(e)}")
            await msg.reply("获取频道列表时发生异常，请稍后重试。")
            return None

        voice_channel = None
        for channel in channels:
            if isinstance(channel, dict) and channel.get('type') == 2:
                try:
                    user_list_url = f"https://www.kaiheila.cn/api/v3/channel/user-list?channel_id={channel['id']}"
                    async with self._http.get(user_list_url) as resp:
                        if resp.status != 200:
                            continue
                        user_list_data = await resp.json()
                        if any(user['id'] == author.id for user in user_list_data.get('data', [])):
                            voice_channel = channel
                            break
                except Exception as e:
                    self.logger.error(f"[获取用户列表] 异常: {str(e)}")

        if not voice_channel:
            await msg.reply("你没有在语音频道中，请先加入一个语音频道。")
            return None

        join_url = "https://www.kaiheila.cn/api/v3/voice/join"
        data = {"channel_id": voice_channel['id']}
        self.logger.info(f"[加入语音频道] 请求 URL: {join_url}, 参数: {data}")
        try:
            async with self._http.post(join_url, json=data) as resp:
                if resp.status != 200:
                    self.logger.error(f"[加入语音频道] 失败，状态码: {resp.status}")
                    await msg.reply(f"加入语音频道失败: 状态码{resp.status}")
                    return None
                join_result = await resp.json()
                self.current_stream_params = {
                    "audio_ssrc": join_result['data']['audio_ssrc'],
                    "audio_pt": join_result['data']['audio_pt'],
                    "ip": join_result['data']['ip'],
                    "port": join_result['data']['port'],
                    "rtcp_port": join_result['data']['rtcp_port']
                }
                self.logger.info(f"已加入 {voice_channel['name']} 语音频道")
                return voice_channel
        except Exception as e:
            self.logger.error(f"[加入语音频道] 异常: {str(e)}")
            await msg.reply(f"加入语音频道失败: {str(e)}")
            return None

    async def _safe_play(self, msg: Message, query: str):
        self.logger.info(f"[播放歌曲] 进入函数，当前推流参数: {self.current_stream_params}")
        if self.is_playing:
            await msg.reply("当前正在播放其他歌曲，请稍候。")
            return

        try:
            self.is_playing = True
            if not self.current_stream_params:
                await self._join_user_voice_channel(msg)
                if not self.current_stream_params:
                    self.is_playing = False
                    return

            music_data = await self._fetch_music_data(query)
            await msg.reply(f"🎵 正在播放: {music_data['title']} - {music_data['artist']}")

            # 构建 ffmpeg 命令（音质优化核心参数）
            stream_url = music_data['url']
            ffmpeg_cmd = [
                'ffmpeg', '-re', '-i', stream_url, '-bufsize', '1024k', '-map', '0:a:0',
                '-acodec', 'libopus',  # 使用高效的 Opus 编码（优于 MP3）
                '-vbr', 'on',  # 启用可变码率（VBR），复杂段落分配更多码率
                '-ab', '48k',  # 码率提升至 256kbps（原 48k 过低，提升8倍音质）
                '-ac', '2',  # 保持立体声（2 通道）
                '-ar', '48000',  # 保持高采样率（48kHz 专业级音频标准）
                '-filter:a', 'volume=0.5',  # 音量控制（如需默认音量可移除此参数）
                '-f', 'tee',
                f'[select=a:f=rtp:ssrc={self.current_stream_params["audio_ssrc"]}:payload_type={self.current_stream_params["audio_pt"]}]'
                f'rtp://{self.current_stream_params["ip"]}:{self.current_stream_params["port"]}?rtcpport={self.current_stream_params["rtcp_port"]}'
            ]
            self.logger.info(f"[播放歌曲] ffmpeg 命令: {' '.join(ffmpeg_cmd)}")

            loop = asyncio.get_running_loop()
            process = await loop.run_in_executor(
                None,
                lambda: subprocess.Popen(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            )

            stdout, stderr = await loop.run_in_executor(
                None,
                process.communicate
            )
            self.logger.info(f"[播放歌曲] ffmpeg 标准输出: {stdout if stdout else '无'}")
            self.logger.info(f"[播放歌曲] ffmpeg 标准错误: {stderr if stderr else '无'}")
            if process.returncode != 0:
                self.logger.error(f"[播放歌曲] ffmpeg 执行失败，返回码: {process.returncode}")
                await msg.reply("歌曲播放失败，请检查日志")
            else:
                self.logger.info("[播放歌曲] ffmpeg 执行成功")
            self.is_playing = False
        except ValueError as e:
            await msg.reply(f"❌ 播放失败: {str(e)}")
            self.logger.error(f"[播放歌曲] 业务错误: {str(e)}")
        except Exception as e:
            await msg.reply("⚠️ 系统异常，请稍后重试")
            self.logger.critical(f"[播放歌曲] 系统异常: {str(e)}", exc_info=True)
        finally:
            # 无论播放成功与否，都将播放状态设为False
            self.is_playing = False

    async def _leave_voice_channel(self, msg: Message):
        await self._ensure_http()
        leave_url = "https://www.kaiheila.cn/api/v3/voice/leave"
        try:
            bot_id = self.bot.me.id
            guild_id = msg.ctx.guild.id
            channel_list_url = f"https://www.kaiheila.cn/api/v3/channel/list?guild_id={guild_id}"
            async with self._http.get(channel_list_url) as resp:
                channels = (await resp.json()).get('data', {}).get('items', [])

            voice_channel = None
            for channel in channels:
                if isinstance(channel, dict) and channel.get('type') == 2:
                    try:
                        user_list_url = f"https://www.kaiheila.cn/api/v3/channel/user-list?channel_id={channel['id']}"
                        async with self._http.get(user_list_url) as resp:
                            users = (await resp.json()).get('data', [])
                            if any(user['id'] == bot_id for user in users):
                                voice_channel = channel
                                break
                    except Exception as e:
                        self.logger.error(f"[检查用户列表] 异常: {str(e)}")

            if voice_channel:
                data = {"channel_id": voice_channel['id']}
                async with self._http.post(leave_url, json=data) as resp:
                    if resp.status == 200:
                        self.current_stream_params = {}  # 清空推流参数
                        await msg.reply("已离开语音频道")
                    else:
                        await msg.reply(f"离开失败，状态码: {resp.status}")
            else:
                await msg.reply("机器人不在语音频道中，无需离开。")
        except Exception as e:
            self.logger.error(f"[离开语音频道] 异常: {str(e)}")
            await msg.reply(f"离开语音频道失败: {str(e)}")

    def _register_handlers(self):
        @self.bot.command(name='play')
        async def play_cmd(msg: Message, query: str):
            self.logger.info(f"接收到 /play 指令，参数: {query}")
            time.sleep(0.5)
            await self._safe_play(msg, query)

        @self.bot.command(name='come')
        async def come_cmd(msg: Message):
            self.logger.info(f"接收到 /come 指令")
            # 保留原come指令以备未来可能的独立使用
            await self._join_user_voice_channel(msg)

        @self.bot.command(name='leave')
        async def leave_cmd(msg: Message):
            await self._leave_voice_channel(msg)

        @self.bot.command(name='help')
        async def help_cmd(msg: Message):
            await msg.reply(
                "/help:\t指令帮助\n/idn:\t版本信息\n/play(此处有空格)+歌曲名:\t点歌\n/wiki:\t查询wiki\n/price:\t查询价格\n/sim:\t生产模拟\n/Precrafts:\t配方查询\n/act_cafe:\t咖啡ACT下载链接\n/act_diemoe:\t呆萌ACT下载链接"
            )

        @self.bot.command(name='wiki')
        async def wiki_cmd(msg: Message):
            await msg.reply('https://ff14.huijiwiki.com/wiki/首页?veaction=edit')

        @self.bot.command(name='price')
        async def price_cmd(msg: Message):
            await msg.reply('https://www.ff14pvp.top/#/')

        @self.bot.command(name='sim')
        async def sim_cmd(msg: Message):
            await msg.reply('https://tnze.yyyy.games/#/welcome')

        @self.bot.command(name='precrafts')
        async def precrafts_cmd(msg: Message):
            await msg.reply('https://hqhelper.nbb.fan/#/')

        @self.bot.command(name='act_cafe')
        async def act_cafe_cmd(msg: Message):
            await msg.reply('https://www.ffcafe.cn/act/')

        @self.bot.command(name='act_diemoe')
        async def act_diemoe_cmd(msg: Message):
            await msg.reply('https://act.diemoe.net/')

        @self.bot.command(name='idn')
        async def idn_cmd(msg: Message):
            # 创建卡片，设置颜色和主题
            card = Card(theme=Types.Theme.PRIMARY, size=Types.Size.LG, color=Color(hex_color='#007BFF'))
            # 添加标题
            card.append(Module.Header(Element.Text(content="机器人信息", type=Types.Text.PLAIN)))
            # 添加分隔线
            card.append(Module.Divider())
            # 添加机器人名称信息
            card.append(Module.Section(Element.Text(content=f"**机器人名称：** {self.bot_name}", type=Types.Text.KMD)))
            # 添加分隔线
            card.append(Module.Divider())
            # 添加机器人版本信息
            card.append(Module.Section(Element.Text(content=f"**机器人版本：** {self.bot_version}", type=Types.Text.KMD)))
            # 添加分隔线
            card.append(Module.Divider())
            # 添加作者信息
            card.append(Module.Section(Element.Text(content=f"**作者：** {self.author}", type=Types.Text.KMD)))

            card_msg = CardMessage(card)
            await msg.reply(card_msg)

    async def cleanup(self):
        if self._http and not self._http.closed:
            await self._http.close()
        if hasattr(self.bot, 'client') and hasattr(self.bot.client, 'close'):
            await self.bot.client.close()


async def main():
    load_dotenv()
    kook_token = os.getenv("KOOK_TOKEN")
    print(kook_token)
    print(f"Loaded KOOK_TOKEN: {kook_token}")  # 添加调试信息
    if not kook_token:
        raise ValueError("KOOK_TOKEN not found in .env file")
    bot = StableMusicBot(kook_token)
    try:
        await bot.bot.start()
    except asyncio.CancelledError:
        pass
    finally:
        await bot.cleanup()


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main(), debug=True)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.critical(f"致命错误: {str(e)}", exc_info=True)