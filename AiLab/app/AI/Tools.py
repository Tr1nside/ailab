import json

from langchain_core.tools import tool

from typing import Dict
from app.AI.TechTool import CurrencyConverter, Code, GenerationPhoto, AnalysisPhoto, InternetSearch, ImageAnalysisInput


@tool
def AnalyzeImageTool(input_data: str) -> str:
    """Analyzes an image and answers questions about it. Requires a dictionary with image_path and question."""
    input_data = json.loads(input_data)

    image_path = input_data.get("image_path")
    question = input_data.get("question")

    analysis_photo_tool = AnalysisPhoto()

    return analysis_photo_tool.ask_llava(image_path, question)

@tool
def LoadFileTool(file_path) -> str:
    """Загружает содержимое файла в зависимости от его формата. Поддерживает PDF, DOCX, TXT, RTF, XLSX, PPTX, CSV, HTML, EPUB, MD, EML."""
    currency_converter = CurrencyConverter()
    return currency_converter.load_file(file_path)

@tool
def GenerateCodeTool(prompt: Dict) -> str:
    """Генерирует код на основе запроса. Принимает словарь с обязательными ключами: question, file_context, file_text"""
    code_tool = Code()
    return code_tool.ask_code(prompt)

@tool
def GenerateImageTool(prompt: str) -> str:
    """Генерирует изображение по текстовому описанию с помощью Stable Diffusion"""
    gen_photo_tool = GenerationPhoto()
    return gen_photo_tool.gen_img(prompt)

class AITools:
    def __init__(self):
        pass

    def get_all_tools_name(self):
        return [name.name for name in self.get_all_tools()]

    def get_all_tools(self):
        """Возвращает список всех инструментов класса"""
        return [
            LoadFileTool,
            GenerateCodeTool,
            GenerateImageTool,
            AnalyzeImageTool,
            # self.internet_search_tool,
        ]
