import time
import requests

from bot.bot import Bot
from bot.session_manager import SessionManager
from bridge.context import Context, ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from config import conf, load_config

from .example_session import ExampleSession


# default value of custom keys in config
example_arg1 = ""
example_arg2 = ""

MAX_RETRIES = 2


class ExampleBot(Bot):
    def __init__(self):
        super().__init__()
        self.sessions = SessionManager(ExampleSession, model=conf().get("model") or "example")
        self.api_key = conf().get("example_api_key")
        self.base_url = conf().get("example_base_url")
        self.example_arg1 = conf().get("example_arg1", example_arg1)
        self.example_arg2 = conf().get("example_arg2", example_arg2)
        self.request_body = {
            "example_arg1": self.example_arg1,
            "example_arg2": self.example_arg2
        }

    def reply(self, query, context: Context = None) -> Reply:
        logger.info(f"[Example_AI] query={query}, context={context}")
        if context.type == ContextType.TEXT:
            session_id = context["session_id"]
            reply = None
            # 快捷入口
            if query in ["你好", "你是谁"]:
                self.sessions.clear_session(session_id)
                reply = Reply(ReplyType.INFO, self.default_reply)

            clear_memory_commands = conf().get("clear_memory_commands", ["#清除记忆"])
            if query in clear_memory_commands:
                self.sessions.clear_session(session_id)
                reply = Reply(ReplyType.INFO, "记忆已清除")
            elif query == "#清除所有":
                self.sessions.clear_all_session()
                reply = Reply(ReplyType.INFO, "所有人记忆已清除")
            elif query == "#更新配置":
                load_config()
                reply = Reply(ReplyType.INFO, "配置已更新")
            if reply:
                return reply
            
            session = self.sessions.session_query(query, session_id)
            logger.debug(f"[Example_AI] session query={session.messages}")

            model = context.get("example_model")
            new_request_body = self.request_body.copy()
            if model:
                new_request_body["model"] = model
            # if context.get('stream'):
            #     # reply in stream
            #     return self.reply_text_stream(query, new_query, session_id)

            reply_content = self.reply_text(session, request_body=new_request_body)
            logger.debug(
                "[Example_AI] new_query={}, session_id={}, reply_cont={}, completion_tokens={}".format(
                    session.messages,
                    session_id,
                    reply_content["content"],
                    reply_content["completion_tokens"],
                )
            )
            if reply_content["completion_tokens"] == 0 and len(reply_content["content"]) > 0:
                reply = Reply(ReplyType.ERROR, reply_content["content"])
            elif reply_content["completion_tokens"] > 0:
                self.sessions.session_reply(reply_content["content"], session_id, reply_content["total_tokens"])
                reply = Reply(ReplyType.TEXT, reply_content["content"])
            else:
                reply = Reply(ReplyType.ERROR, reply_content["content"])
                logger.debug(f"[Example_AI] reply {reply_content} used 0 tokens.")
            return reply

        # add branches here if you have more model types to support
        elif context.type == ContextType.IMAGE:
            pass
        else:
            reply = Reply(ReplyType.ERROR, "ExampleBot不支持处理{}类型的消息".format(context.type))
            return reply
        
    def reply_text(self, session: ExampleSession, request_body, retry_count=0) -> dict:
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.api_key
            }
            request_body["messages"] = session.messages
            # logger.debug("[Example_AI] response={}".format(response))
            # logger.info("[Example_AI] reply={}, total_tokens={}".format(response.choices[0]['message']['content'], response["usage"]["total_tokens"]))
            res = requests.post(
                self.base_url,
                headers=headers,
                json=request_body,
                timeout=60
            )
            if res.status_code == 200:
                response = res.json()
                return {
                    "total_tokens": response["usage"]["total_tokens"],
                    "completion_tokens": response["usage"]["completion_tokens"],
                    "content": response["choices"][0]["message"]["content"]
                }
            else:
                response = res.json()
                error = response.get("error")
                logger.error(f"[Example_AI] chat failed, status_code={res.status_code}, "
                             f"msg={error.get('message')}, type={error.get('type')}")

                result = {"completion_tokens": 0, "content": "提问太快啦，请休息一下再问我吧"}
                need_retry = False
                if res.status_code >= 500:
                    # server error, need retry
                    logger.warning(f"[Example_AI] do retry, times={retry_count}")
                    need_retry = retry_count < MAX_RETRIES
                elif res.status_code == 401:
                    result["content"] = "授权失败，请检查API Key是否正确"
                    need_retry = retry_count < MAX_RETRIES
                else:
                    need_retry = False

                if need_retry:
                    time.sleep(3)
                    return self.reply_text(session, request_body, retry_count + 1)
                else:
                    return result
        except Exception as e:
            logger.exception(e)
            need_retry = retry_count < MAX_RETRIES
            result = {"completion_tokens": 0, "content": "我现在有点累了，等会再来吧"}
            if need_retry:
                return self.reply_text(session, request_body, retry_count + 1)
            else:
                return result
