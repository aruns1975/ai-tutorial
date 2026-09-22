from typing import Dict, List

class Box:
    def __init__(self, length, width):
        self.length = length
        self.width = width
    def __str__(self):
        return f"Box(length={self.length}, width={self.width})"


b1:Box=Box(20,30)
print(b1)

b2:Box=Box(20,30)
print(b2)

class Message:
    def __init__(self, content,role):
        self.role=role
        self.content = content
    def __str__(self):
        return f"{self.__class__.__name__}(role={self.role}, content={self.content})"

class AIMessage(Message):
    def __init__(self, content):
        super().__init__(content,"AI")


class UserMessage(Message):
    def __init__(self, content):
        super().__init__(content,"User")

class SystemMessage(Message):
    def __init__(self, content):
        super().__init__(content,"System")


def print_message(message: Message):
    print(f"The user is {message.role.upper()} and the content is {message.content}")

myMessage = AIMessage(content="what is your name?")
print(myMessage)

class PromptMessages(Dict):
    messages: List[Message]
    def __str__(self):
        messages = ", ".join(str(message)+"\n" for message in self.messages)
        return f"{type(self).__name__}(messages=\n[\n{messages}])"


prompts:PromptMessages = PromptMessages()

prompts.messages=[
    SystemMessage(content="You are a genious metahmaticain"),
    UserMessage(content="What is 3+4"),
    AIMessage(content="7"),

]

response={
    "messages":[
        SystemMessage(content="You are a genious metahmaticain"),
        UserMessage(content="What is 3+4"),
        AIMessage(content="7"),
    ]
}

request={
    "messages":[
        {"role":"system", "content":"You are a genious metahmaticain"},
        {"role":"user", "content":"What is 3+4"},
        {"role":"AI", "content":"7"},
    ]
}

print("")

for message in response["messages"]:
    print(message)
print("")

print(response["messages"][-1].content)

print()

print(f"The messages are {prompts}")

my_dict = {
    "k1":"v1",
    "k2":"v2",
    "k3":"v3"
}

print(my_dict["k1"])
print(my_dict["k2"])
print(my_dict["k3"])
my_array = [
    "v1",
    "v2",
    "v3"
]

my_array_as_dict = {
    "0":"v1",
    "1":"v2",
    "2":"v3"
}
my_array_as_dict["0"]