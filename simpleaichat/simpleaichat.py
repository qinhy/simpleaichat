import os
import datetime
from uuid import uuid4, UUID
from contextlib import contextmanager, asynccontextmanager
import csv

from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Union, Optional, Any, Callable
from pydantic import BaseModel, SecretStr, HttpUrl, Field
from typing import List, Dict, Union, Optional, Set, Any

from utils import wikipedia_search_lookup
from models import CommonMessage, CommonChatSession
from chatgpt import ChatGPTSession

class ModelSessionFactory:        

    @staticmethod
    def buildChatGPTSession(
        ################CommonChatSession common
        auth: Dict[str, SecretStr] = {"api_key": SecretStr(os.getenv("OPENAI_API_KEY",''))},
        api_url: HttpUrl = "https://api.openai.com/v1/chat/completions",
        model: str = 'gpt-3.5-turbo-16k',
        system: str = "You are a helpful assistant.",
        messages: List[CommonMessage] = [],
        title: Optional[str] = None,
        
        ################openai ChatGPT
        gpt_role: Optional[str] = 'assistant',
        gpt_name: Optional[str] = 'GPT',
        temperature : Optional[float] = 0.7,
        n: Optional[float] = 1,
        max_tokens: Optional[int] = 1024,
        top_p: Optional[int] = 1,
        presence_penalty : Optional[float] = 0.0,
        frequency_penalty : Optional[float] = 0.0,
    ):  
        res = locals()
        res['system_message'] = CommonMessage(role="system", content=res.pop('system'))
        res['_params'] = dict(temperature=temperature,top_p=top_p,n=n,max_tokens=max_tokens,presence_penalty=presence_penalty,frequency_penalty=frequency_penalty)        
        return ChatGPTSession(**res)

# class AIChat(BaseModel):
#     client: Any
#     default_session: Optional[CommonChatSession]
#     sessions: Dict[Union[str, UUID], CommonChatSession] = {}

#     def __init__(
#         self,
#         # character: str = None,
#         # character_command: str = None,
#         # system: str = None,
#         # id: Union[str, UUID] = uuid4(),
#         # prime: bool = True,
#         default_session: bool = True,
#         # console: bool = True,
#         model_session_config_func: Callable = lambda:dict(),
#     ):

#         client = Client(proxies=os.getenv("https_proxy"))
#         # system_format = self.build_system(character, character_command, system)

#         sessions = {}
#         new_default_session = None
#         if default_session:
#             new_session = self.new_session(
#                 return_session=True, model_session_config_func=model_session_config_func
#             )

#             new_default_session = new_session
#             sessions = {new_session.id: new_session}

#         super().__init__(
#             client=client, default_session=new_default_session, sessions=sessions
#         )

#         # if console:
#         #     character = "ChatGPT" if not character else character
#         #     new_default_session.title = character
#         #     self.interactive_console(character=character, prime=prime)

#     def new_session(
#         self,
#         return_session: bool = False,
#         model_session_config_func: Callable = lambda:dict(),
#     ) -> Optional[ChatGPTSession]:
#         kwargs = model_session_config_func()
#         print(kwargs)
#         # TODO: Add support for more models (PaLM, Claude)
#         if "gpt-" in kwargs["model"]:
#             gpt_api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
#             assert gpt_api_key, f"An API key for {kwargs['model'] } was not defined."
#             sess = ChatGPTSession(**kwargs,)
#         if return_session:
#             return sess
#         else:
#             self.sessions[sess.id] = sess

#     def get_first_session(self) -> CommonChatSession:
#         return self.get_session(list(self.sessions.keys()).pop())

#     def get_session_by_uuid(self, id: str) -> CommonChatSession:
#         return self.get_session(UUID(id))

#     def get_session(self, id: Union[str, UUID] = None) -> CommonChatSession:
#         try:
#             sess = self.sessions[id] if id else self.default_session
#         except KeyError:
#             raise KeyError("No session by that key exists.")
#         if not sess:
#             raise ValueError("No default session exists.")
#         return sess

#     def reset_session(self, id: Union[str, UUID] = None) -> None:
#         sess = self.get_session(id)
#         sess.messages = []

#     def delete_session(self, id: Union[str, UUID] = None) -> None:
#         sess = self.get_session(id)
#         if self.default_session:
#             if sess.id == self.default_session.id:
#                 self.default_session = None
#         del self.sessions[sess.id]
#         del sess

#     # @contextmanager
#     # def session(self, **kwargs):
#     #     sess = self.new_session(return_session=True, **kwargs)
#     #     self.sessions[sess.id] = sess
#     #     try:
#     #         yield sess
#     #     finally:
#     #         self.delete_session(sess.id)

#     def __call__(
#         self,
#         prompt: Union[str, Any],
#         id: Union[str, UUID] = None,
#         system: str = None,
#         save_messages: bool = None,
#         params: Dict[str, Any] = None,
#         tools: List[Any] = None,
#         input_schema: Any = None,
#         output_schema: Any = None,
#     ) -> str:
#         sess = self.get_session(id)
#         if tools:
#             for tool in tools:
#                 assert tool.__doc__, f"Tool {tool} does not have a docstring."
#             assert len(tools) <= 9, "You can only have a maximum of 9 tools."
#             return sess.gen_with_tools(
#                 prompt,
#                 tools,
#                 client=self.client,
#                 system=system,
#                 save_messages=save_messages,
#                 params=params,
#             )
#         else:
#             return sess.gen(
#                 prompt,
#                 client=self.client,
#                 system=system,
#                 save_messages=save_messages,
#                 params=params,
#                 input_schema=input_schema,
#                 output_schema=output_schema,
#             )

#     def stream_chat(
#         self,
#         prompt: str,
#         id: Union[str, UUID] = None,
#         system: str = None,
#         save_messages: bool = None,
#         params: Dict[str, Any] = None,
#         input_schema: Any = None,
#     ) -> str:
#         sess = self.get_session(id)
#         return sess.stream_chat(
#             prompt,
#             client=self.client,
#             system=system,
#             save_messages=save_messages,
#             params=params,
#             input_schema=input_schema,
#         )

#     def interactive_console(self, character: str = None, prime: bool = True) -> None:
#         console = Console(highlight=False, force_jupyter=False)
#         sess = self.default_session
#         ai_text_color = "bright_magenta"

#         # prime with a unique starting response to the user
#         if prime:
#             console.print(f"[b]{character}[/b]: ", end="", style=ai_text_color)
#             for chunk in sess.stream("Hello!", self.client):
#                 console.print(chunk["delta"], end="", style=ai_text_color)

#         while True:
#             console.print()
#             try:
#                 user_input = console.input("[b]You:[/b] ").strip()
#                 if not user_input:
#                     break

#                 console.print(f"[b]{character}[/b]: ", end="", style=ai_text_color)
#                 for chunk in sess.stream(user_input, self.client):
#                     console.print(chunk["delta"], end="", style=ai_text_color)
#             except KeyboardInterrupt:
#                 break

#     def __str__(self) -> str:
#         if self.default_session:
#             return self.default_session.model_dump_json(
#                 exclude={"api_key", "api_url"},
#                 exclude_none=True,
#                 option=orjson.OPT_INDENT_2,
#             )

#     def __repr__(self) -> str:
#         return ""

#     # Save/Load Chats given a session id
#     def save_session(
#         self,
#         output_path: str = None,
#         id: Union[str, UUID] = None,
#         format: str = "csv",
#         minify: bool = False,
#     ):
#         sess = self.get_session(id)
#         sess.save_session(output_path=output_path,
#                           format=format,
#                           minify=minify,)

#     def load_session(self, input_path: str, id: Union[str, UUID] = uuid4(), **kwargs):

#         assert input_path.endswith(".csv") or input_path.endswith(
#             ".json"
#         ), "Only CSV and JSON imports are accepted."

#         if input_path.endswith(".csv"):
#             with open(input_path, "r", encoding="utf-8") as f:
#                 r = csv.DictReader(f)
#                 messages = []
#                 for row in r:
#                     # need to convert the datetime back to UTC
#                     local_datetime = datetime.datetime.strptime(
#                         row["last_update"], "%Y-%m-%d %H:%M:%S"
#                     ).replace(tzinfo=dateutil.tz.tzlocal())
#                     row["last_update"] = local_datetime.astimezone(
#                         datetime.timezone.utc
#                     )
#                     # https://stackoverflow.com/a/68305271
#                     row = {k: (None if v == "" else v) for k, v in row.items()}
#                     messages.append(CommonMessage(**row))

#             self.new_session(id=id, **kwargs)
#             self.sessions[id].messages = messages

#         if input_path.endswith(".json"):
#             with open(input_path, "rb") as f:
#                 sess_dict = orjson.loads(f.read())
#             # update session with info not loaded, e.g. auth/api_url
#             for arg in kwargs:
#                 sess_dict[arg] = kwargs[arg]
#             self.new_session(**sess_dict)

#     # Tabulators for returning total token counts
#     def message_totals(self, attr: str, id: Union[str, UUID] = None) -> int:
#         sess = self.get_session(id)
#         return getattr(sess, attr)

#     @property
#     def total_prompt_length(self, id: Union[str, UUID] = None) -> int:
#         return self.message_totals("total_prompt_length", id)

#     @property
#     def total_completion_length(self, id: Union[str, UUID] = None) -> int:
#         return self.message_totals("total_completion_length", id)

#     @property
#     def total_length(self, id: Union[str, UUID] = None) -> int:
#         return self.message_totals("total_length", id)

#     # alias total_tokens to total_length for common use
#     @property
#     def total_tokens(self, id: Union[str, UUID] = None) -> int:
#         return self.total_length(id)


# class AsyncAIChat(AIChat):
#     async def __call__(
#         self,
#         prompt: str,
#         id: Union[str, UUID] = None,
#         system: str = None,
#         save_messages: bool = None,
#         params: Dict[str, Any] = None,
#         tools: List[Any] = None,
#         input_schema: Any = None,
#         output_schema: Any = None,
#     ) -> str:
#         # TODO: move to a __post_init__ in Pydantic 2.0
#         if isinstance(self.client, Client):
#             self.client = AsyncClient(proxies=os.getenv("https_proxy"))
#         sess = self.get_session(id)
#         if tools:
#             for tool in tools:
#                 assert tool.__doc__, f"Tool {tool} does not have a docstring."
#             assert len(tools) <= 9, "You can only have a maximum of 9 tools."
#             return await sess.gen_with_tools_async(
#                 prompt,
#                 tools,
#                 client=self.client,
#                 system=system,
#                 save_messages=save_messages,
#                 params=params,
#             )
#         else:
#             return await sess.gen_async(
#                 prompt,
#                 client=self.client,
#                 system=system,
#                 save_messages=save_messages,
#                 params=params,
#                 input_schema=input_schema,
#                 output_schema=output_schema,
#             )

#     async def stream(
#         self,
#         prompt: str,
#         id: Union[str, UUID] = None,
#         system: str = None,
#         save_messages: bool = None,
#         params: Dict[str, Any] = None,
#         input_schema: Any = None,
#     ) -> str:
#         # TODO: move to a __post_init__ in Pydantic 2.0
#         if isinstance(self.client, Client):
#             self.client = AsyncClient(proxies=os.getenv("https_proxy"))
#         sess = self.get_session(id)
#         return sess.stream_async(
#             prompt,
#             client=self.client,
#             system=system,
#             save_messages=save_messages,
#             params=params,
#             input_schema=input_schema,
#         )

#     @asynccontextmanager
#     async def session(self, **kwargs):
#         sess = self.new_session(return_session=True, **kwargs)
#         self.sessions[sess.id] = sess
#         try:
#             yield sess
#         finally:
#             self.delete_session(sess.id)
