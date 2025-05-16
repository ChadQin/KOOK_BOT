import os
import asyncio
import sys
import time
from dotenv import load_dotenv
import aiohttp
import logging
import subprocess
import random
import datetime
from khl import Bot, Message
from khl.card import Card, CardMessage, Module, Element, Types
from khl.card.color import Color
from typing import Dict, Optional, Union
from HLTV_PLAYER import HLTVPlayerManager

"""Update Time: 2025/05/16"""


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
        self.bot_version = "V1.2.4"
        self.author = "Chad Qin"
        self.roll_info = {}  # 初始化 roll_info 属性
        self.player_manager = HLTVPlayerManager(r"F:\Python_project\kook_bot_project\data\HLTV_Player.xlsx")
        # 新增猜测功能状态
        self.correct_player = None  # 正确选手名
        self.guess_attempts = 0  # 剩余猜测次数
        self.current_process = None  # 新增：保存FFmpeg进程对象

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
                'ffmpeg', '-re', '-i', stream_url, '-bufsize', '8192k', '-map', '0:a:0',
                '-acodec', 'libopus',  # 使用高效的 Opus 编码（优于 MP3）
                '-vbr', 'on',  # 启用可变码率（VBR），复杂段落分配更多码率
                '-ab', '50k',  # 码率提升至 256kbps（原 48k 过低，提升8倍音质）
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
                        # ---------------------- 新增核心逻辑 ----------------------
                        # 1. 终止FFmpeg播放进程
                        if self.current_process and self.current_process.poll() is None:
                            try:
                                self.logger.info("[离开频道] 尝试终止FFmpeg播放进程")
                                self.current_process.terminate()  # 优雅终止进程
                                await asyncio.sleep(0.5)  # 等待进程响应
                                if self.current_process.poll() is None:
                                    self.current_process.kill()  # 强制终止（超时未响应时）
                                self.logger.info("[离开频道] FFmpeg进程已终止")
                            except Exception as e:
                                self.logger.error(f"[离开频道] 终止进程失败: {str(e)}")
                        # 2. 重置播放状态
                        self.is_playing = False
                        self.current_stream_params = {}  # 清空推流参数
                        # ---------------------------------------------------------
                        await msg.reply("已离开语音频道")
                    else:
                        await msg.reply(f"离开失败，状态码: {resp.status}")
            else:
                await msg.reply("机器人不在语音频道中，无需离开。")
        except Exception as e:
            self.logger.error(f"[离开语音频道] 异常: {str(e)}")
            await msg.reply(f"离开语音频道失败: {str(e)}")

    def _register_handlers(self):
        @self.bot.on_message()
        async def handle_all_messages(msg: Message):
            content = msg.content.strip()
            if not content.startswith('/'):
                # 处理猜测逻辑（非指令消息）
                await self.handle_guess(msg)
                return

            # 处理指令消息
            parts = content[1:].split(' ', 1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ''

            if command == 'play':
                await self.play_cmd(msg, args)
            elif command == 'come':
                await self.come_cmd(msg)
            elif command == 'leave':
                await self.leave_cmd(msg)
            elif command == 'help':
                await self.help_cmd(msg)
            elif command == 'wiki':
                await self.wiki_cmd(msg)
            elif command == 'price':
                await self.price_cmd(msg)
            elif command == 'sim':
                await self.sim_cmd(msg)
            elif command == 'hq_helper':
                await self.precrafts_cmd(msg)
            elif command == 'act_cafe':
                await self.act_cafe_cmd(msg)
            elif command == 'act_diemoe':
                await self.act_diemoe_cmd(msg)
            elif command == 'idn':
                await self.idn_cmd(msg)
            elif command == 'roll':
                await self.roll_cmd(msg)
            elif command == 'id':
                await self.id_cmd(msg)
            elif command == 'guess':
                await self.guess_cmd(msg)
            elif command == 'result':
                await self.result_cmd(msg)

    # 以下所有指令处理函数现在是类的方法，与 _register_handlers 同级
    async def play_cmd(self, msg: Message, query: str):
        self.logger.info(f"接收到 /play 指令，参数: {query}")
        time.sleep(0.5)
        await self._safe_play(msg, query)

    async def come_cmd(self, msg: Message):
        self.logger.info(f"接收到 /come 指令")
        await self._join_user_voice_channel(msg)

    async def leave_cmd(self, msg: Message):
        await self._leave_voice_channel(msg)

    async def help_cmd(self, msg: Message):
        await msg.reply(
            "/help:\t指令帮助\n/idn:\t版本信息\n/play(此处有空格)+歌曲名:\t点歌\n/wiki:\t查询wiki\n/price:\t查询价格\n/sim:\t生产模拟\n/hq_helper:\t配方查询\n/act_cafe:\t咖啡ACT下载链接\n/act_diemoe:\t呆萌ACT下载链接\n/roll:\t掷骰子（1 - 999）\n/ID:\t查看选手名单\n/GUESS:\t开始猜测选手\n/RESULT:\t显示结果（猜测正确时自动触发）"
        )

    wiki_image_src = 'https://av.huijiwiki.com/site_avatar_ff14_l.png?1745349668'
    price_image_src = 'https://huiji-public.huijistatic.com/ff14/uploads/4/4a/065002.png'
    sim_image_src = 'https://huiji-public.huijistatic.com/ff14/uploads/b/b9/061543.png'
    hq_helper_img_src = 'https://raw.githubusercontent.com/InfSein/hqhelper-dawntrail/master/public/icons/logo_v2_shadowed.png'
    act_cafe_img_src = 'https://www.ffcafe.cn/images/logos/334.png'
    act_diemoe_imsg_src = 'https://act.diemoe.net/assets/img/logo.png'

    async def wiki_cmd(self, msg: Message):
        url = 'https://ff14.huijiwiki.com/wiki/首页?veaction=edit'
        card = Card(
            Module.Section(
                text=Element.Text(content=url, type=Types.Text.KMD)
            ),
            Module.Divider(),
            Module.Section(
                text=Element.Text(content="点击跳转------------------>", type=Types.Text.KMD),
                accessory=Element.Button(
                    text="跳转",
                    value=url,
                    click=Types.Click.LINK,
                    theme=Types.Theme.PRIMARY
                ),
                mode=Types.SectionMode.RIGHT
            ),
            Module.Section(
                accessory=Element.Image(src=self.wiki_image_src, size=Types.Size.SM),
                mode=Types.SectionMode.RIGHT
            )
        )
        card_msg = CardMessage(card)
        await msg.reply(card_msg)

    async def price_cmd(self, msg: Message):
        url = 'https://www.ff14pvp.top/#/'
        card = Card(
            Module.Section(
                text=Element.Text(content=url, type=Types.Text.KMD)
            ),
            Module.Divider(),
            Module.Section(
                text=Element.Text(content="点击跳转------------------>", type=Types.Text.KMD),
                accessory=Element.Button(
                    text="跳转",
                    value=url,
                    click=Types.Click.LINK,
                    theme=Types.Theme.PRIMARY
                ),
                mode=Types.SectionMode.RIGHT
            ),
            Module.Section(
                accessory=Element.Image(src=self.price_image_src, size=Types.Size.SM),
                mode=Types.SectionMode.RIGHT
            )
        )
        card_msg = CardMessage(card)
        await msg.reply(card_msg)

    async def sim_cmd(self, msg: Message):
        url = 'https://tnze.yyyy.games/#/welcome'
        card = Card(
            Module.Section(
                text=Element.Text(content=url, type=Types.Text.KMD)
            ),
            Module.Divider(),
            Module.Section(
                text=Element.Text(content="点击跳转------------------>", type=Types.Text.KMD),
                accessory=Element.Button(
                    text="跳转",
                    value=url,
                    click=Types.Click.LINK,
                    theme=Types.Theme.PRIMARY
                ),
                mode=Types.SectionMode.RIGHT
            ),
            Module.Section(
                accessory=Element.Image(src=self.sim_image_src, size=Types.Size.SM),
                mode=Types.SectionMode.RIGHT
            )
        )
        card_msg = CardMessage(card)
        await msg.reply(card_msg)

    async def precrafts_cmd(self, msg: Message):
        url = 'https://hqhelper.nbb.fan/#/'
        card = Card(
            Module.Section(
                text=Element.Text(content=url, type=Types.Text.KMD)
            ),
            Module.Divider(),
            Module.Section(
                text=Element.Text(content="点击跳转------------------>", type=Types.Text.KMD),
                accessory=Element.Button(
                    text="跳转",
                    value=url,
                    click=Types.Click.LINK,
                    theme=Types.Theme.PRIMARY
                ),
                mode=Types.SectionMode.RIGHT
            ),
            Module.Section(
                accessory=Element.Image(src=self.hq_helper_img_src, size=Types.Size.SM),
                mode=Types.SectionMode.RIGHT
            )
        )
        card_msg = CardMessage(card)
        await msg.reply(card_msg)

    async def act_cafe_cmd(self, msg: Message):
        url = 'https://www.ffcafe.cn/act/'
        card = Card(
            Module.Section(
                text=Element.Text(content=url, type=Types.Text.KMD)
            ),
            Module.Divider(),
            Module.Section(
                text=Element.Text(content="点击跳转------------------>", type=Types.Text.KMD),
                accessory=Element.Button(
                    text="跳转",
                    value=url,
                    click=Types.Click.LINK,
                    theme=Types.Theme.PRIMARY
                ),
                mode=Types.SectionMode.RIGHT
            ),
            Module.Section(
                accessory=Element.Image(src=self.act_cafe_img_src, size=Types.Size.SM),
                mode=Types.SectionMode.RIGHT
            )
        )
        card_msg = CardMessage(card)
        await msg.reply(card_msg)

    async def act_diemoe_cmd(self, msg: Message):
        url = 'https://act.diemoe.net/'
        card = Card(
            Module.Section(
                text=Element.Text(content=url, type=Types.Text.KMD)
            ),
            Module.Divider(),
            Module.Section(
                text=Element.Text(content="点击跳转------------------>", type=Types.Text.KMD),
                accessory=Element.Button(
                    text="跳转",
                    value=url,
                    click=Types.Click.LINK,
                    theme=Types.Theme.PRIMARY
                ),
                mode=Types.SectionMode.RIGHT
            ),
            Module.Section(
                accessory=Element.Image(src=self.act_diemoe_imsg_src, size=Types.Size.SM),
                mode=Types.SectionMode.RIGHT
            )
        )
        card_msg = CardMessage(card)
        await msg.reply(card_msg)

    async def idn_cmd(self, msg: Message):
        card = Card(theme=Types.Theme.PRIMARY, size=Types.Size.LG, color=Color(hex_color='#007BFF'))
        card.append(Module.Header(Element.Text(content="机器人信息", type=Types.Text.PLAIN)))
        card.append(Module.Divider())
        card.append(Module.Section(Element.Text(content=f"**机器人名称：** {self.bot_name}", type=Types.Text.KMD)))
        card.append(Module.Divider())
        card.append(Module.Section(Element.Text(content=f"**机器人版本：** {self.bot_version}", type=Types.Text.KMD)))
        card.append(Module.Divider())
        card.append(Module.Section(Element.Text(content=f"**作者：** {self.author}", type=Types.Text.KMD)))
        card.append(Module.Divider())
        github_url = "https://github.com/ChadQin/KOOK_BOT"
        card.append(Module.Section(
            Element.Text(content=f"**GitHub 地址：** (ins){github_url}(ins)", type=Types.Text.KMD),
            Element.Button(
                text="查看仓库",
                click=Types.Click.LINK,
                value=github_url,
                theme=Types.Theme.SUCCESS
            )
        ))
        card_msg = CardMessage(card)
        await msg.reply(card_msg)

    async def roll_cmd(self, msg: Message):
        random_num = random.randint(1, 999)
        channel_id = msg.channel.id
        user_id = msg.author.id
        if channel_id not in self.roll_info:
            self.roll_info[channel_id] = {
                'end_time': datetime.datetime.now() + datetime.timedelta(minutes=5),
                'results': {},
                'total_people': 0
            }
        self.roll_info[channel_id]['results'][user_id] = random_num
        self.roll_info[channel_id]['total_people'] += 1
        card = Card(
            Module.Section(
                text=Element.Text(content=f"你掷出了: **(font){random_num}(font)[pink]**", type=Types.Text.KMD)
            )
        )
        card_msg = CardMessage(card)
        await msg.reply(card_msg)

    async def id_cmd(self, msg: Message):
        sorted_names, player_count = self.player_manager.get_sorted_player_names()
        if player_count > 0:
            player_list = "\n".join(sorted_names)
            reply_msg = f"选手名单（共 {player_count} 人）：\n{player_list}"
        else:
            reply_msg = "未找到选手数据。"
        await msg.reply(reply_msg)

    async def guess_cmd(self, msg: Message):
        sorted_names, player_count = self.player_manager.get_sorted_player_names()
        if player_count == 0:
            await msg.reply("未找到选手数据，无法开始猜测。")
            return

        self.correct_player = random.choice(sorted_names)
        print(self.correct_player)
        self.guess_attempts = 7
        await msg.reply(f"已抽取一名选手，请猜测他的名字！你有 {self.guess_attempts} 次机会。\n直接发送选手名进行猜测！")

    async def handle_guess(self, msg: Message):
        if not self.correct_player or self.guess_attempts <= 0:
            return

        guess = msg.content.strip()
        player_info = self.player_manager.get_player_info(guess)

        if "未找到" in player_info:
            await msg.reply("该选手不存在，请重新输入！")
            return

        # 获取正确选手信息
        correct_info = self.player_manager.get_player_info(self.correct_player)
        if "未找到" in correct_info:
            await msg.reply("内部错误：无法获取正确选手信息")
            self.correct_player = None
            self.guess_attempts = 0
            return

        # 解析正确选手数据
        correct_data = correct_info.split('\n')[1].split('\t')
        correct_dict = {
            "AGE": correct_data[3] if len(correct_data) > 3 else "",
            "MAJ_NUM": correct_data[5] if len(correct_data) > 5 else ""
        }

        if guess == self.correct_player:
            await self.send_correct_result(msg, correct_data)
            self.correct_player = None
            self.guess_attempts = 0
        else:
            self.guess_attempts -= 1
            fixed_headers = ["NAME", "TEAM", "NATION", "AGE", "ROLE", "MAJ_NUM"]
            data = player_info.split('\n')[1]
            data_items = data.split('\t')
            reply_text = ""

            for i, header in enumerate(fixed_headers):
                if i < len(data_items):
                    value = data_items[i]
                    # 处理完全匹配（最高优先级）
                    if i < len(correct_data) and value.strip() == correct_data[i].strip():
                        value += "✅"
                    # 处理国籍区域提示（仅当不完全匹配时）
                    elif header == "NATION" and i < len(correct_data):
                        correct_nation = correct_data[i].strip()
                        guess_nation = value.strip()
                        # 获取两个国家的区域（使用反向映射）
                        correct_region = self.player_manager.get_country_region(correct_nation)
                        guess_region = self.player_manager.get_country_region(guess_nation)
                        # 判断是否属于同一区域（且非完全匹配）
                        if correct_region and guess_region and correct_region == guess_region and guess_nation != correct_nation:
                            value += f" (同属{correct_region})"  # 替换为具体区域名称
                    # 处理数字比较提示 (AGE和MAJ_NUM)
                    elif header in ["AGE", "MAJ_NUM"]:
                        try:
                            user_value = int(value)
                            correct_value = int(correct_dict.get(header, 0))
                            diff = abs(user_value - correct_value)
                            if diff <= 2:
                                value += " 🔺" if user_value > correct_value else " 🔻"
                        except ValueError:
                            pass  # 非数字值不处理
                    # 修正：将这一行移到外层if语句下，确保所有字段都被添加到回复中
                    reply_text += f"- {header} :\t{value}\n"
                else:
                    reply_text += f"- {header} :\t\n"

            if self.guess_attempts > 0:
                await msg.reply(f"猜测错误！你还有 {self.guess_attempts} 次机会。\n你猜测的选手信息：\n{reply_text}")
            else:
                await self.send_fail_result(msg, correct_data)
                self.correct_player = None
                self.guess_attempts = 0

    async def send_correct_result(self, msg: Message, correct_data):
        fixed_headers = ["NAME", "TEAM", "NATION", "AGE", "ROLE", "MAJ_NUM"]
        correct_text = "\n".join([f"- {h} :\t{v}✅" for h, v in zip(fixed_headers, correct_data)])
        self.celebrate_image_path = r'F:\Python_project\kook_bot_project\img\celebrate.png'
        # 上传庆祝图片
        try:
            img_url = await self.bot.client.create_asset(self.celebrate_image_path)
        except Exception as e:
            self.logger.error(f"庆祝图片上传失败: {e}")
            await msg.reply("🎉 猜中啦！不过庆祝图片发送失败，请联系管理员检查路径~")
            await msg.reply(correct_text)
            return

        # 创建卡片
        card = Card(
            Module.Header("恭喜你猜中了！正确答案是"),
            Module.Divider(),
            Module.Container(Element.Image(src=img_url, size=Types.Size.SM))
        )

        # 发送消息
        await msg.reply(CardMessage(card))
        await msg.reply(correct_text)

        self.correct_player = None
        self.guess_attempts = 0

    async def send_fail_result(self, msg: Message, correct_data):
        """猜测次数用尽时发送失败图片和正确答案"""
        fixed_headers = ["NAME", "TEAM", "NATION", "AGE", "ROLE", "MAJ_NUM"]
        correct_text = "\n".join([f"- {h} :\t{v}✅" for h, v in zip(fixed_headers, correct_data)])
        self.fail_image_path = r'F:\Python_project\kook_bot_project\img\sad.png'
        # 上传失败图片（与其他场景逻辑一致）
        try:
            img_url = await self.bot.client.create_asset(self.fail_image_path)
        except Exception as e:
            self.logger.error(f"失败图片上传失败: {e}")
            await msg.reply(f"很遗憾，你的7次机会已用完！\n正确答案是：\n{correct_text}")
            return

        # 创建失败卡片（结构与猜对卡片一致，仅标题和图片不同）
        card = Card(
            Module.Header("很遗憾，你输了！"),  # 失败标题
            Module.Divider(),  # 分隔线
            Module.Container(Element.Image(src=img_url, size=Types.Size.SM))  # 小尺寸图片
        )

        # 发送卡片和文本（与其他场景一致）
        await msg.reply(CardMessage(card))
        await msg.reply(f"正确答案是：\n{correct_text}")

    async def result_cmd(self, msg: Message):
        if not self.correct_player:
            await msg.reply("请先通过 /GUESS 开始猜测！")
            return

        player_info = self.player_manager.get_player_info(self.correct_player)
        if player_info.startswith("未找到") or player_info.startswith("数据加载失败"):
            await msg.reply(player_info)
            self.correct_player = None
            self.guess_attempts = 0
            return

        correct_data = player_info.split('\n')[1].split('\t')
        fixed_headers = ["NAME", "TEAM", "NATION", "AGE", "ROLE", "MAJ_NUM"]
        correct_text = "\n".join([f"- {h} :\t{v}✅" for h, v in zip(fixed_headers, correct_data)])
        self.taunt_image_path = r"F:\Python_project\kook_bot_project\img\taunt.png"
        # 上传图片并获取URL
        try:
            img_url = await self.bot.client.create_asset(self.taunt_image_path)
            if not img_url:
                await msg.reply("❌ 图片上传失败，请检查文件路径")
                return
        except Exception as e:
            self.logger.error(f"图片上传异常: {str(e)}")
            await msg.reply(f"❌ 图片上传异常: {str(e)}")
            return

        # 创建卡片消息：文本和图片在同一卡片中
        card = Card(
            Module.Header("小B崽子，猜不出来叭！"),  # 标题文本
            Module.Divider(),  # 分隔线
            Module.Container(Element.Image(src=img_url, size=Types.Size.LG))  # 图片容器
        )

        # 发送卡片消息
        await msg.reply(CardMessage(card))

        # 单独发送选手信息（保持纯文本）
        await msg.reply(correct_text)

        self.correct_player = None
        self.guess_attempts = 0

    async def cleanup(self):
        if self._http and not self._http.closed:
            await self._http.close()
        if hasattr(self.bot, 'client') and hasattr(self.bot.client, 'close'):
            await self.bot.client.close()
            # 终止可能存在的FFmpeg进程
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
                await asyncio.wait_for(self.current_process.wait(), timeout=5)
            except Exception:
                pass


async def main():
    load_dotenv()
    kook_token = os.getenv("KOOK_TOKEN")
    print(kook_token)
    print(f"Loaded KOOK_TOKEN: {kook_token}")
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