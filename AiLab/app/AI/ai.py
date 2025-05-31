import os
from datetime import datetime

from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain_ollama import OllamaLLM
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredFileLoader,
    UnstructuredRTFLoader,
    UnstructuredExcelLoader,
    UnstructuredPowerPointLoader,
    CSVLoader,
    UnstructuredHTMLLoader,
    UnstructuredEPubLoader,
    UnstructuredMarkdownLoader,
    UnstructuredEmailLoader,
)
from langchain.chains.conversation.base import ConversationChain


class AI_BOT_V3:
    def __init__(self):
        self.general_llm = OllamaLLM(model="mistral")

    def _load_file(self, file_path: str) -> str:
        # Загружает содержимое файла в зависимости от его формата
        try:
            if not os.path.exists(file_path):
                return "Ошибка: Файл не найден"

            file_path = file_path.strip().lower()

            if file_path.endswith(".pdf"):
                loader = PyPDFLoader(file_path)
            elif file_path.endswith(".docx") or file_path.endswith(".doc"):
                loader = Docx2txtLoader(file_path)
            elif file_path.endswith(".txt"):
                loader = TextLoader(file_path)
            elif file_path.endswith(".rtf"):
                loader = UnstructuredRTFLoader(file_path)
            elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
                loader = UnstructuredExcelLoader(file_path)
            elif file_path.endswith(".pptx") or file_path.endswith(".ppt"):
                loader = UnstructuredPowerPointLoader(file_path)
            elif file_path.endswith(".csv"):
                loader = CSVLoader(file_path)
            elif file_path.endswith(".html") or file_path.endswith(".htm"):
                loader = UnstructuredHTMLLoader(file_path)
            elif file_path.endswith(".epub"):
                loader = UnstructuredEPubLoader(file_path)
            elif file_path.endswith(".md"):
                loader = UnstructuredMarkdownLoader(file_path)
            elif file_path.endswith(".eml") or file_path.endswith(".msg"):
                loader = UnstructuredEmailLoader(file_path)
            else:
                loader = UnstructuredFileLoader(file_path)

            documents = loader.load()
            response = (
                file_path + " : " + "\n".join([doc.page_content for doc in documents])
            )
            return response
        except Exception as e:
            return f"Ошибка обработки файла: {str(e)}"

    def _load_storage(self, context_file: str) -> ConversationBufferMemory:
        chat_memory = FileChatMessageHistory(context_file)
        return ConversationBufferMemory(chat_memory=chat_memory, return_messages=False)

    def _save_storage(
        self, context_file: str, human_message: str, ai_message: str = ""
    ) -> None:
        chat_memory = FileChatMessageHistory(context_file)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        chat_memory.add_user_message(f"[{timestamp}] {human_message}")
        if ai_message:
            chat_memory.add_ai_message(f"[{timestamp}] {ai_message}")

    def ask(self, prompt: str, context_path: str, file_context: list = []) -> str:
        print("запрос принят." + prompt)
        memory = self._load_storage(context_path)

        conversation = ConversationChain(memory=memory, llm=self.general_llm)

        if file_context:
            file_context = [self._load_file(file) for file in file_context]
        full_input = f"""
                ### Инструкции:
                Ты AI ассистент, ответь на запрос пользователя.

                ### Контекст:
                - Данные из файлов: {"".join(file_context)}

                ### Запрос пользователя:
                {prompt}

                ### Ответ:
                """

        response = conversation.predict(input=full_input)

        self._save_storage(context_path, prompt, response)
        return response
