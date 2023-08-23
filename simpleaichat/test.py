from simpleaichat import * 
from chatgpt import *

ss = ModelSessionFactory.buildChatGPTSession()

for i in ss('hi'):
    print(i)