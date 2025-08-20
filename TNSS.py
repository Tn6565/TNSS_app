import os
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import tweepy
from filelock import FileLock  # ファイルロック追加
from openai import OpenAI

# ====== 初期設定 ======

load_dotenv()  # .envからAPIキーを環境変数に読み込み

# 各種APIキーをos.environから取得
openai_api_key = os.environ.get("TN_SYSTEM")
consumer_key = os.environ.get("TNSS_API_KEY_for_X")
consumer_secret = os.environ.get("TNSS_API_SECRET_KEY_for_X")
access_token = os.environ.get("TNSS_ACCESS_TOKEN")
access_token_secret = os.environ.get("TNSS_API_SECRET_KEY_for_X")

# APIキー未設定時のエラー
if not all([openai_api_key, consumer_key, consumer_secret, access_token, access_token_secret]):
    st.error("APIキーが設定されていません。環境変数または.envファイルを確認してください。")
    st.stop()

# LangChain(OpenAI) 初期化
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.9, openai_api_key=openai_api_key)

# Tweepy(X) 初期化
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

# 利用制限
MAX_REQUESTS_PER_DAY = 15
counter_file = "request_counter.txt"
lock_file = counter_file + ".lock"  # ファイルロック用

def read_count():
    with FileLock(lock_file):
        if not os.path.exists(counter_file):
            return 0
        with open(counter_file, "r") as f:
            return int(f.read().strip() or 0)

def write_count(count):
    with FileLock(lock_file):
        with open(counter_file, "w") as f:
            f.write(str(count))

today_count = read_count()

# ====== Streamlit UI ======
st.title("📝 X 投稿支援アプリ")
topic = st.text_input("投稿のトピックを入力してください:")

if "candidates" not in st.session_state:
    st.session_state.candidates = []

# ====== 投稿文生成 ======
if st.button("候補を生成する", disabled=(today_count >= MAX_REQUESTS_PER_DAY)):
    if today_count >= MAX_REQUESTS_PER_DAY:
        st.error("⚠️ 本日の投稿上限（15件）に達しました。")
    else:
        prompt = PromptTemplate(
            input_variables=["topic"],
            template="以下のトピックについて、ラフでカジュアルな口調で、140文字以内の投稿文を3つ作成してください。\n\nトピック: {topic}",
        )
        chain = LLMChain(llm=llm, prompt=prompt)
        try:
            result = chain.run(topic=topic)
            # 箇条書きや番号付きにも対応
            candidates = [c.lstrip("0123456789.・- ").strip() for c in result.split("\n") if c.strip()]
            st.session_state.candidates = [c[:140] for c in candidates if c]
            st.success("✅ 投稿候補を生成しました。")
        except Exception as e:
            st.error(f"生成に失敗しました: {e}")

# ====== 候補表示と投稿 ======
if st.session_state.candidates:
    st.subheader("生成された候補")
    for i, c in enumerate(st.session_state.candidates, 1):
        st.write(f"{i}. {c}")
        post_btn = st.button(
            f"この投稿を送信する → 候補 {i}",
            key=f"post_{i}",
            disabled=(today_count >= MAX_REQUESTS_PER_DAY)
        )
        if post_btn:
            if today_count >= MAX_REQUESTS_PER_DAY:
                st.error("⚠️ 本日の投稿上限（15件）に達しました。")
            else:
                try:
                    api.update_status(c)
                    st.success(f"✅ 投稿しました: {c}")
                    today_count += 1
                    write_count(today_count)
                    st.info(f"本日の利用回数: {today_count}/{MAX_REQUESTS_PER_DAY}")
                except Exception as e:
                    st.error(f"投稿に失敗しました: {e}")