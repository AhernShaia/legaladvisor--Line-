# Python package
import sys
import configparser
import os

# Langchain
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain_community.vectorstores import Qdrant
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
# ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.chat_models.ollama import ChatOllama
# Qrant
from qdrant_client import QdrantClient

# Output format tool
from rich import print as pprint

# Flask
from flask import Flask, request, abort

# Line SDK
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)

# 取得當前檔案的目錄
current_dir = os.path.dirname(os.path.abspath(__file__))

# 連接 config.ini 檔案的完整路徑
config_file_path = os.path.join(current_dir, 'config.ini')

# Config Parser
config = configparser.ConfigParser()
config.read(config_file_path)

app = Flask(__name__)
channel_access_token = config['Line']['CHANNEL_ACCESS_TOKEN']
channel_secret = config['Line']['CHANNEL_SECRET']
if channel_secret is None:
    print("Specify LINE_CHANNEL_SECRET as environment variable.")
    sys.exit(1)
if channel_access_token is None:
    print("Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.")
    sys.exit(1)

handler = WebhookHandler(channel_secret)

configuration = Configuration(access_token=channel_access_token)


@app.route("/callback", methods=["POST"])
def callback():
    # get X-Line-Signature header value
    signature = request.headers["X-Line-Signature"]
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def message_text(event):
    azure_openai_result = azure_openai(event.message.text)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=azure_openai_result),
                ],
            )
        )


# azure_api_key = config['AzureOpenAI']['KEY']
# openai_model = config['AzureOpenAI']['NAME']
# openai_api_version = config['AzureOpenAI']['VERSION']
# azure_endpoint = config['AzureOpenAI']['BASE']
# embedding_model = config['AzureOpenAIEmbeddingModel']['NAME']


def azure_openai(user_input):
    # Ollama
    embedding_model = OllamaEmbeddings(model="mxbai-embed-large")
    model = ChatOllama(model="yabi/breeze-7b-instruct-v1_0_q6_k")
    client = QdrantClient()
    collection_name = "legalassistant-UAT"

    qdrant = Qdrant(
        client,
        collection_name,
        embedding_model
    )

    retriever = qdrant.as_retriever(search_kwargs={"k": 3})

    prompt = ChatPromptTemplate.from_template(
        """你是一位台灣的資深法律顧問，請回答依照 context 裡的資訊，使用臺灣繁體中文來回答問題:
    <context>
    {context}
    </context>
    Question: {input}
    附帶說明是引用哪一條法規，並給出解決方案。
    """

    )

    document_chain = create_stuff_documents_chain(
        model,
        prompt
    )

    retriever_chain = create_retrieval_chain(
        retriever,
        document_chain
    )

    response = retriever_chain.invoke(
        {"input": user_input})
    pprint(response['answer'])
    return response['answer']


if __name__ == "__main__":
    app.run()
