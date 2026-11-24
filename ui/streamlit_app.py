"""채팅 UI. 실행: uv run streamlit run ui/streamlit_app.py"""
import os

import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="사장님 세무·노무 비서", page_icon="🧾")
st.title("🧾 사장님 세무·노무 비서")
st.caption("로컬 LLM으로 동작합니다. 입력한 내용은 외부로 전송되지 않습니다.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("예: 주 20시간 일하는 알바 시급 10,320원이면 주휴수당 얼마예요?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"), st.spinner("계산하고 법령을 찾는 중..."):
        history = st.session_state.messages[:-1][-6:]
        res = httpx.post(f"{API_URL}/chat", json={"message": prompt, "history": history}, timeout=180).json()
        st.markdown(res["answer"])
        if res.get("tool_calls"):
            with st.expander(f"🔧 사용한 도구 {len(res['tool_calls'])}개 · {res['latency_ms']}ms"):
                st.json(res["tool_calls"])
    st.session_state.messages.append({"role": "assistant", "content": res["answer"]})
