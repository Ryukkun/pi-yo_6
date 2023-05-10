import openai

from config import Config

if Config.ChatGPT.organization:
    openai.organization = Config.ChatGPT.organization
openai.api_key = Config.ChatGPT.api_key


class ChatGPTThread:
    def __init__(self) -> None:
        self.chat_log = []

    def ask(self, message):
        _ = [
            "絶対に回答の語尾を「なのだ」にして下さい",
            "長い話は避けて"
            ]
        send_message = [
            {"role": "system", "content": '\n'.join(_)},
            ]
        
        if 4 < len(self.chat_log):
            log = self.chat_log[-4:]
        else:
            log = self.chat_log

        send_message.extend(log)
        send_message.append({"role":"user", "content":message })


        # 応答設定
        completion = openai.ChatCompletion.create(
                    model    = "gpt-3.5-turbo",     # モデルを選択
                    messages = send_message,
        
                    max_tokens  = 1024,             # 生成する文章の最大単語数
                    n           = 1,                # いくつの返答を生成するか
                    stop        = None,             # 指定した単語が出現した場合、文章生成を打ち切る
                    temperature = 0.5,              # 出力する単語のランダム性（0から2の範囲） 0であれば毎回返答内容固定
        )
        
        # 応答
        response = completion.choices[0].message.content
        
        # log
        self.chat_log.append({'role':'user', 'content':message})
        self.chat_log.append({'role':'assistant', 'content':response})

        # 応答内容出力
        return response



if __name__ == '__main__':
    # 質問内容
    message = "桃太郎を読んで"

    # ChatGPT起動
    chatgpt = ChatGPTThread()
    res = chatgpt.ask(message)
    # 出力
    print(res)

    # res = chatgpt.ask('じゃあそのジンについて詳しく教えて')
    # # 出力
    # print(res)