# Bot 扩展开发说明
## 背景介绍
Bot 是项目中用来统一对接各类大模型的工厂类，当前已经支持GPT-3.5, GPT-4o-mini, GPT-4o, GPT-4, Claude-3.5, Gemini, 文心一言, 讯飞星火, 通义千问，ChatGLM-4，Kimi(月之暗面), MiniMax, GiteeAI, ModelScope(魔搭社区)等各类大模型或 MaaS 平台。如果需要支持新的大模型或者用户自定义部署的大模型，一般有两种方式：

- 1.用户自行把待接入的大模型 API 按照 OpenAI 协议统一封装，然后使用内置的 openai Bot 进行对接；
- 2.用户按照本文档，自定义扩展开发一个新的 Bot。

本文档介绍如何自定义扩展开发一个新的 Bot。

## 扩展开发
### 定义新的 Bot 标识
确定唯一的 Bot 标识，如 `example`，在 `common/const.py` 的 bot_type 段落中新增如下代码：
```
EXAMPLE = "example"
```

### 新建 Bot 工厂类【核心代码】
在 `bot` 目录下新建目录，目录名建议和上一步中唯一的 Bot 标识一致，即`example`。接着新建两个 py 文件，命名建议分别为 `xx_bot.py` 和 `xx_session.py`，在样例里即为 `example_bot.py`、`example_session.py`。

#### 新建 session 类（可选）
在 `example_session.py` 文件中新建 `ExampleSession` 类，`ExampleSession` 类是用来管理用户的对话上下文，避免历史会话信息过长超出大模型 token 限制。

`ExampleSession` 类一般需要包含三个方法，分别是：
- `__init__`：用来进行 Session 初始化。
- `discard_exceeding`：判断历史消息是否超出最大 token 限制，超过的话进入循环，从最早一条历史对话开始丢弃，直到总长度满足要求。
- `calc_tokens`：待接入的大模型计算 token 的方法。


#### 新建 bot 类（必须）
在 `example_bot.py` 文件中新建 `ExampleBot` 类，`ExampleBot` 类是用于各个渠道和新的大模型进行消息通信的模块。

`ExampleBot` 类至少需要包含三个方法，分别是：
- `__init__`：用来进行 Bot 初始化。
- `reply`：根据不同类型消息进行转发，其中文本消息转发到 `reply_text` 方法进行处理，并且文本消息可以支持一些特殊指令，如“#清除记忆”等。也可以扩展其他不同的消息类型，如 image。
- `reply_text`：文本类型消息回复方法，如果需要和大模型进行交互，在这里通过 requests 包或 SDK 和第三方大模型进行交互。注意要确保项目部署的服务器有权限请求对应的大模型 API。
 
### 注册新 Bot 类
- 在 `bot/bot_factory.py` 的 `create_bot` 函数中新增分支代码
```
    elif bot_type == const.EXAMPLE:
        from bot.example.example_bot import ExampleBot
        return ExampleBot()
```

- 在 `bridge/bridge.py` 的 `__init__` 方法中新增代码分支
```
            if model_type in [const.EXAMPLE]:
                self.btype["chat"] = const.EXAMPLE
```
注意：如果 EXAMPLE 大模型支持多种不同衍生模型，可以在判断条件里把 `[const.EXAMPLE]` 换成衍生模型标识列表。

### 定义 Bot 需要的环境变量
在 `config.py` 中定义新的 Bot 在部署时需要配置的环境变量信息。如：
```
    # Example配置
    "example_api_key": "",
    "example_base_url": "",
    "example_arg1": "",
    "example_arg2": "",
```
