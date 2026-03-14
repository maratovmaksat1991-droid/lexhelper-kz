import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
import io

# --------------- Конфигурация страницы ---------------

st.set_page_config(
    page_title="LexHelper KZ",
    page_icon="⚖️",
    layout="wide",
)

# --------------- Session State ---------------

if "documents" not in st.session_state:
    st.session_state.documents = []

if "result" not in st.session_state:
    st.session_state.result = ""

# --------------- Парсинг файлов ---------------

MAX_CHARS_PER_DOC = 3000


def parse_pdf(file) -> str:
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text


def parse_docx(file) -> str:
    doc = Document(file)
    return "\n".join(p.text for p in doc.paragraphs)


def parse_txt(file) -> str:
    return file.read().decode("utf-8", errors="ignore")


def parse_file(file) -> str:
    name = file.name.lower()
    if name.endswith(".pdf"):
        return parse_pdf(file)
    elif name.endswith(".docx"):
        return parse_docx(file)
    elif name.endswith(".txt"):
        return parse_txt(file)
    return ""


# --------------- Сборка системного промпта ---------------


def build_system_prompt(documents: list[dict]) -> str:
    prompt = (
        "Ты — персональный AI-помощник казахстанского юриста.\n\n"
    )

    if documents:
        prompt += "ДОКУМЕНТЫ ЮРИСТА (его стиль и шаблоны):\n\n"
        for i, doc in enumerate(documents, 1):
            truncated = doc["text"][:MAX_CHARS_PER_DOC]
            prompt += f"=== Документ {i}: {doc['name']} ===\n{truncated}\n\n"

    prompt += (
        "ИНСТРУКЦИИ:\n"
        "1. Пиши в стиле этих документов — та же структура, те же обороты\n"
        "2. Ссылайся на нормы РК (ГК РК, ГПК РК и т.д.) с конкретными статьями\n"
        "3. Используй заглушки: [ДАТА], [НАИМЕНОВАНИЕ СУДА], [ФИО ИСТЦА] и т.д.\n"
        "4. Выдавай только сам документ, без пояснений\n"
        "5. Язык — русский\n"
    )

    return prompt


# --------------- Генерация документа ---------------


def generate_document(api_key: str, user_request: str) -> str:
    genai.configure(api_key=api_key)
    system_prompt = build_system_prompt(st.session_state.documents)

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-lite",
        system_instruction=system_prompt,
    )

    response = model.generate_content(user_request)
    return response.text


# --------------- Sidebar ---------------

with st.sidebar:
    st.header("Настройки")

    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        help="Получите бесплатно на aistudio.google.com",
    )

    st.divider()
    st.header("Документы юриста")

    uploaded_files = st.file_uploader(
        "Загрузите ваши документы",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        help="PDF, DOCX или TXT — система изучит ваш стиль",
    )

    if uploaded_files:
        # Парсим только новые файлы
        existing_names = {d["name"] for d in st.session_state.documents}
        for f in uploaded_files:
            if f.name not in existing_names:
                text = parse_file(f)
                if text.strip():
                    st.session_state.documents.append(
                        {"name": f.name, "text": text}
                    )

    doc_count = len(st.session_state.documents)
    if doc_count > 0:
        st.success(f"Загружено документов: {doc_count}")
        for doc in st.session_state.documents:
            chars = len(doc["text"])
            st.caption(f"📄 {doc['name']} ({chars} символов)")

    if st.button("Очистить базу", type="secondary"):
        st.session_state.documents = []
        st.session_state.result = ""
        st.rerun()

# --------------- Основная область ---------------

st.title("⚖️ LexHelper KZ")
st.caption("Персональный AI-помощник казахстанского юриста")

user_request = st.text_area(
    "Опишите, какой документ нужно составить:",
    height=150,
    placeholder="Например: Составь исковое заявление о взыскании задолженности по договору поставки на сумму 5 000 000 тенге",
)

col1, col2 = st.columns([1, 5])

with col1:
    generate_btn = st.button("Составить документ", type="primary")

# Генерация
if generate_btn:
    if not api_key:
        st.error("Введите Gemini API Key в боковой панели.")
    elif not user_request.strip():
        st.error("Введите описание документа.")
    else:
        with st.spinner("Генерация документа..."):
            try:
                st.session_state.result = generate_document(api_key, user_request)
            except Exception as e:
                st.error(f"Ошибка: {e}")

# Вывод результата
if st.session_state.result:
    st.divider()
    st.subheader("Готовый документ")
    st.text_area(
        "Результат",
        value=st.session_state.result,
        height=400,
        label_visibility="collapsed",
    )
    st.download_button(
        label="Скачать .txt",
        data=st.session_state.result,
        file_name="document.txt",
        mime="text/plain",
    )
