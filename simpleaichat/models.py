import datetime
from uuid import uuid4, UUID

from pydantic import BaseModel, SecretStr, HttpUrl, Field
from typing import List, Dict, Union, Optional, Set, Any
import csv
import inspect
import tiktoken
import json


def now_tz():
    # Need datetime w/ timezone for cleanliness
    # https://stackoverflow.com/a/24666683
    return datetime.datetime.now(datetime.timezone.utc)

class Function(BaseModel):
    class Parameter(BaseModel):
        type: str
        description: str
    name: str = None
    description: str = None
    _properties: Dict[str, Parameter] = {}
    parameters: Dict[str, Any] = {"type": "object",'properties':_properties}
    required: List[str] = []
    _parameters_description: Dict[str, str] = {}

    def _extract_signature(self):
        self.name=self.__class__.__name__
        sig = inspect.signature(self.__call__)
        # Map Python types to more generic strings
        type_map = {
            int: "integer",float: "number",
            str: "string",bool: "boolean",
            list: "array",dict: "object"
            # ... add more mappings if needed
        }
        for name, param in sig.parameters.items():
            param_type = type_map.get(param.annotation, "unknown")
            self._properties[name] = Function.Parameter(type=param_type, description=self._parameters_description.get(name,''))
            if param.default is inspect._empty:
                self.required.append(name)
        self.parameters['properties']=self._properties
    def get_class_name(self):
        return self.__class__.__name__
    
    def get_openai_description(self):
        return self.model_dump()

    def json(self):
        return self.model_dump_json()

class CommonMessage(BaseModel):    
    role: str
    content: str
    embedding: Optional[List[float]] = None
    name: Optional[str] = None
    function_call: Optional[str] = None
    last_update: datetime.datetime = Field(default_factory=now_tz)
    finish_reason: Optional[str] = None
    prompt_length: Optional[int] = None
    completion_length: Optional[int] = None
    total_length: Optional[int] = None
    content_tokens: Optional[int] = 0

    @staticmethod
    def custom_construct_list(d=[{'system':'FREE'},{'user':'hello!'}]):
        return [CommonMessage.custom_construct_one(ii) for ii in d]
    
    @staticmethod
    def custom_construct_one(d={'user':'Hello!'}):
        i = d.popitem()
        return CommonMessage(role=i[0],content=i[1])
    
    def calc_tokens(self,token_encoder=None):
        if token_encoder is not None:
            self.content_tokens = len(token_encoder.encode(self.content))
        else:
            self.content_tokens = 0
        return self
    
    def __str__(self) -> str:
        return str(self.model_dump(exclude_none=True))


class CommonChatSession(BaseModel):
    id: Union[str, UUID] = Field(default_factory=uuid4)
    created_at: datetime.datetime = Field(default_factory=now_tz)
    auth: Dict[str, SecretStr]
    api_url: HttpUrl
    model: str
    # system: str

    system_message: CommonMessage = None
    messages: List[CommonMessage] = []
    last_update: datetime.datetime = Field(default_factory=now_tz)

    recent_messages: int = 0
    total_prompt_length: int = 0
    total_completion_length: int = 0
    total_length: int = 0
    title: Optional[str] = None
        
    ###########################################################
    
    _token_encoder = None    
    _last_prompt:str = ''

    def __str__(self) -> str:
        sess_start_str = self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        last_message_str = self.messages[-1].last_update.strftime("%Y-%m-%d %H:%M:%S")
        return f"""Chat session started at {sess_start_str}:
        - {len(self.messages):,} Messages
        - Last message sent at {last_message_str}"""

    def add_msg(self,m = {'user':'Hello!'}, name=None):
        try:
            if type(m) is not CommonMessage:
                m = CommonMessage.custom_construct_one(m).calc_tokens(self.get_token_encoder())
        except Exception as e:
            print(e)
            return False
        if name is not None:
            m.name = name
        self.messages.append(m)
        return True

    def to_dict(self):
        return self.model_dump()
    
    def load_from_dict(self,d):
        d = dict(**d)
        d['system_message'] = CommonMessage(**d['system_message']) if 'system_message' in d.keys() else None
        d['messages'] = [CommonMessage(**i) for i in d['messages']]
        return self.model_copy(update=d)

    # def save_session(
    #     self,
    #     output_path: str = None,
    #     format: str = "csv",
    #     minify: bool = False,
    # ):
    #     sess = self
    #     sess_dict = sess.model_dump(
    #         exclude={"api_url", "input_fields"},
    #         exclude_none=True,
    #     )
    #     output_path = output_path or f"chat_session.{format}"
    #     if format == "csv":
    #         with open(output_path, "w", encoding="utf-8") as f:
    #             fields = [
    #                 "role",
    #                 "content",
    #                 "last_update",
    #                 "content_tokens",
    #             ]
    #             w = csv.DictWriter(f, fieldnames=fields)
    #             w.writeheader()
    #             for message in sess_dict["messages"]:                    
    #                 # datetime must be in common format to be loaded into spreadsheet
    #                 # for human-readability, the timezone is set to local machine
    #                 local_datetime = message["last_update"].astimezone()
    #                 message["last_update"] = local_datetime.strftime("%Y-%m-%d %H:%M:%S")
    #                 tmp = {f:message.get(f,None) for f in fields}
    #                 w.writerow(tmp)
    #     elif format == "json":
    #         with open(output_path, "wb") as f:
    #             f.write(
    #                 orjson.dumps(
    #                     sess_dict, option=orjson.OPT_INDENT_2 if not minify else None
    #                 )
    #             )
