from pydantic import BaseModel, SecretStr, HttpUrl, Field
from typing import List, Dict, Union, Set, Any
import os
from uuid import uuid4, UUID
import openai
from tools import * 
from models import CommonMessage, CommonChatSession, Function
from utils import remove_a_key
import json
from typing import List, Dict, Union, Optional, Set, Any
import tiktoken

class PromptFactory:
    @staticmethod
    def function_use(gpt_name: str = '', function_name: str = '') -> str:
        return f"\n{gpt_name} is using {function_name} with args: \n"

    @staticmethod
    def function_res(function_name: str = '', args: str = '', res: str = '') -> str:
        return f"\n{function_name} ( {args} ) ==> {res}\n"
    
    @staticmethod
    def japanese_system(name='assistant') -> str:
        return f"You are a helpful {name} who is proficient in both English and Japanese. Please ensure that all your replies are in Japanese, except for computer commands."

    @staticmethod
    def QnAeval(q,a):
        return f'''
You are an expert who conducts strict evaluations. For the given Question and Answer, determine whether the response is adequate. 
If it's sufficient, simply only 'OK'.
If it's not, please provide appropriate advice.

Question:
{q}

Answer:
{a}
'''




class ChatGPTSession(CommonChatSession):    
    ################ openai config
    temperature : Optional[float] = 0.7
    n: Optional[float] = 1
    max_tokens: Optional[int] = 1024
    top_p: Optional[int] = 1
    presence_penalty : Optional[float] = 0.0
    frequency_penalty : Optional[float] = 0.0
    gpt_role: Optional[str] = 'assistant'
    gpt_name: Optional[str] = 'GPT'
    
    ################CommonChatSession
    # id: Union[str, UUID] = Field(default_factory=uuid4)
    # created_at: datetime.datetime = Field(default_factory=now_tz)
    auth: Dict[str, SecretStr] = {"api_key": SecretStr('NULL')}
    api_url: HttpUrl = "https://api.openai.com/v1/chat/completions"
    model: str = 'gpt-3.5-turbo-16k'     
    system_message: CommonMessage = None
    messages: List[CommonMessage] = []
    # recent_messages: Optional[int] = None
    # total_prompt_length: int = 0
    # total_completion_length: int = 0
    # total_length: int = 0
    title: Optional[str] = None

    ############################# internal ##############################    
    _params: Dict[str, Any] = dict(temperature =temperature ,top_p=top_p,n=n,max_tokens=max_tokens,presence_penalty=presence_penalty,frequency_penalty=frequency_penalty)
    _last_prompt:str = None
    _last_receive:str = None

    def __init__(self, *args,**kwargs):
        super(self.__class__, self).__init__(*args,**kwargs)

        if self.system_message is None:
            self.system_message = CommonMessage(role="system", content=f'You are a helpful {self.gpt_role}.').calc_tokens(self.get_token_encoder())

    def __call__(self,prompt: Union[str, Any], user_name:Optional[str]=None
                 , tools:Optional[List[Any]]=None, stream:bool=False) -> str:
        self.add_msg({'user':prompt},user_name)
        if tools is None:
            for r in self._gen() if not stream else self._stream_gen():yield r  
        else:
            for r in self._gen_with_tools(tools) if not stream else self._stream_gen_with_tools(tools):yield r
    
    def get_token_encoder(self):
        try:
            return tiktoken.encoding_for_model(self.model.replace('-16k',''))
        except Exception as e:
            return None
        
    def get_messages_dict(self,fields: Set[str] = {"role", "content", "name"}):
        model_dump = lambda x:x.model_dump(include=fields, exclude_none=True)
        msg = [model_dump(self.system_message)]
        msg += [model_dump(m) for m in self.messages[-self.recent_messages:] ]
        return msg
    
    def _process_response(self,r):
        try:
            funcname = ''
            arguments = ''
            content = ''
            msg = r["choices"][0]["message"]
            if 'function_call' in msg.keys():
                msg = msg['function_call']
                if 'name' in msg.keys():
                    funcname = msg['name']
                    yield PromptFactory.function_use(self.gpt_name,msg['name'])
                if 'arguments' in msg.keys():
                    arguments += msg['arguments']
                    yield msg['arguments']
                # yield PromptFactory.function_use(self.gpt_name,msg['function_call']['name'])
                # func = tools_prompt.get(msg['function_call']['name'],(None,None))[0]
                # args = json.loads(msg['function_call']['arguments'])
                # if func is not None:
                #     res = func(**args)
                #     yield PromptFactory.function_res(msg['function_call']['name'],args,res)
                #     self.add_msg({'function':str(res)},msg['function_call']['name'])
                #     for r in self._gen() :yield r
            else:
                content = msg['content']
                if "name" in msg.keys():
                    self.gpt_name = msg['name']
                # self.add_msg({msg['role']:content},self.gpt_name)                
                self.total_prompt_length += r["usage"]["prompt_tokens"]
                self.total_completion_length += r["usage"]["completion_tokens"]
                self.total_length += r["usage"]["total_tokens"]

            if len(content)>0:
                self.add_msg({self.gpt_role:content},self.gpt_name)
                yield  content
            else:
                yield funcname,arguments

        except KeyError:
            raise KeyError(f"No AI generation: {r}")
        return content

    def _process_stream_response(self,r):
        try:
            funcname = ''
            arguments = ''
            content = []
            for chunk in r:
                msg = chunk["choices"][0]["delta"]
                if 'function_call' in msg.keys():
                    msg = msg['function_call']
                    if 'name' in msg.keys():
                        funcname = msg['name']
                        for r in PromptFactory.function_use(self.gpt_name,msg['name']).split(' '):yield r+' '
                    if 'arguments' in msg.keys():
                        arguments += msg['arguments']
                        yield msg['arguments']
                else:
                    delta = msg.get("content")
                    if delta:
                        content.append(delta)
                        yield content[-1]#{"delta": delta, "response": "".join(content)}
            if len(content)>0:
                self.add_msg({self.gpt_role:"".join(content)},self.gpt_name)
                # yield  "".join(content)
            else:
                yield funcname,arguments
        except KeyError:
            raise KeyError(f"No AI generation: {r}")
        
    def openai_chat_completion_create(self,stream=False,tools_description=None,timeout=None):
        openai.api_key = self.auth['api_key'].get_secret_value()
        if tools_description is None:
            return openai.ChatCompletion.create(model=self.model,
                                                **self._params,stream=stream,
                                                messages=self.get_messages_dict(),
                                                timeout=timeout)
        else:
            return openai.ChatCompletion.create(model=self.model,
                                                **self._params,stream=stream,
                                                messages=self.get_messages_dict(),
                                                functions=tools_description,
                                                function_call="auto",
                                                timeout=timeout)


    def _gen(self,timeout=None):        
        response = self.openai_chat_completion_create(stream=False,timeout=timeout)
        self._last_receive = response    
        for r in  self._process_response(response):yield r
    
    
    def _gen_with_tools(self,tools: List[Any],):
        tools_prompt = {t.get_class_name():(t,t.get_openai_description()) for t in tools}
        self._last_receive = response = self.openai_chat_completion_create(stream=False,
                                                      tools_description=[t[1] for t in tools_prompt.values()])
        for r in  self._process_response(response):
            if type(r) is tuple and len(r)==2:
                funcname,arguments = r
                func = tools_prompt.get(funcname,(None,None))[0]
                args = json.loads(arguments)
                if func is not None:
                    res = func(**args)
                    yield PromptFactory.function_res(funcname,args,res)
                    self.add_msg({'function':str(res)},funcname)
                    for r in self._gen() :yield r
            else:
                yield r

    def _stream_gen(self,timeout=None):
        response = self.openai_chat_completion_create(stream=True,timeout=timeout)
        for r in self._process_stream_response(response):
            self._last_receive = r
            if type(r) is tuple and len(r)==2:continue
            yield r

    def _stream_gen_with_tools(self,tools: List[Any],):
        tools_prompt = {t.get_class_name():(t,t.get_openai_description()) for t in tools}
        response = self.openai_chat_completion_create(stream=True,
                                                      tools_description=[t[1] for t in tools_prompt.values()])
        for r in self._process_stream_response(response):            
            self._last_receive = r
            if type(r) is tuple and len(r)==2:
                funcname,arguments = r
                func = tools_prompt.get(funcname,(None,None))[0]
                args = json.loads(arguments)
                if func is not None:
                    res = func(**args)
                    for r in PromptFactory.function_res(funcname,args,res).split(' '):yield r+' '
                    self.add_msg({'function':str(res)},funcname)
                    for r in self._stream_gen() :yield r
            else:
                yield r
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            