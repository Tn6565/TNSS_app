import os
import streamlit as st
import tweepy
from openai import OpenAI
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
load_dotenv()

# --- APIキー読み込み ---
OPENAI_API_KEY = os.environ.get("TN_system")
X_BEARER_TOKEN = os.environ.get("TNSS_BEARER_TOKEN")
X_API_KEY = os.environ.get("TNSS_API_KEY_for_X")
X_API_SECRET = os.environ.get("TNSS_API_SECRET_KEY_for_X")
X_ACCESS_TOKEN = os.environ.get("TNSS_ACCESS_TOKEN")
X_ACCESS_SECRET = os.environ.get("TNSS_ACCSES_TOKEN_SECRET")

# --- OpenAIクライアント ---
client_ai = OpenAI(api_key=OPENAI_API_KEY)

# --- Tweepyクライアント ---
client = tweepy.Client(
    bearer_token=X_BEARER_TOKEN,
    consumer_key=X_API_KEY,
    consumer_secret=X_API_SECRET,
    access_token=X_ACCESS_TOKEN,
    access_token_secret=X_ACCESS_SECRET
)

st.title("TN SERCH POST FOR X")

# --- お気に入り管理 ---
if "favorites" not in st.session_state:
    st.session_state.favorites = []

username = st.text_input("ユーザー名（@以降）を入力してお気に入りに追加")

if st.button("お気に入りに追加"):
    if username and username not in st.session_state.favorites:
        st.session_state.favorites.append(username)
        st.success(f"{username} をお気に入りに追加しました")

# --- 指定日付の投稿参照 ---
st.header("指定日付の投稿を参照してリライト")
if st.session_state.favorites:
    selected_user = st.selectbox("お気に入りから選択", st.session_state.favorites)
    target_date = st.date_input("参照したい日付を選択", value=date.today() - timedelta(days=1))
    if st.button("指定日付の投稿を取得"):
        try:
            user_info = client.get_user(username=selected_user)
            user_id = user_info.data.id

            # 指定日の0:00:00～23:59:59で範囲指定
            start_time = datetime.combine(target_date, datetime.min.time()).strftime("%Y-%m-%dT%H:%M:%SZ")
            end_time = (datetime.combine(target_date, datetime.max.time()) - timedelta(microseconds=999999)).strftime("%Y-%m-%dT%H:%M:%SZ")

            tweets = client.get_users_tweets(
                id=user_id,
                start_time=start_time,
                end_time=end_time,
                max_results=10,
                tweet_fields=["created_at"]
            )

            if tweets.data:
                for i, tweet in enumerate(tweets.data, 1):
                    st.write(f"【{i}件目】{tweet.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    st.write(tweet.text)
                    if st.button(f"このツイートをリライト {i}"):
                        response = client_ai.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": "与えられた文章を自然にリライトしてください"},
                                {"role": "user", "content": tweet.text}
                            ]
                        )
                        rewritten = response.choices[0].message.content
                        st.subheader("リライト結果（プレビュー）")
                        st.write(rewritten)
                        if st.button(f"この内容で投稿 {i}"):
                            client.create_tweet(text=rewritten)
                            st.success("投稿しました！")
            else:
                st.warning("指定日付の投稿が見つかりませんでした。")
        except Exception as e:
            st.error(f"エラーが発生しました: {str(e)}")

# --- 手動コピペリライト ---
st.header("手動でコピペしたテキストをリライト")
manual_text = st.text_area("リライトしたい文章をここに貼り付けてください")
if st.button("コピペ文をリライト"):
    if manual_text.strip():
        try:
            response = client_ai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "与えられた文章を自然にリライトしてください"},
                    {"role": "user", "content": manual_text}
                ]
            )
            rewritten = response.choices[0].message.content
            st.subheader("リライト結果（プレビュー）")
            st.write(rewritten)
            if st.button("この内容で投稿（コピペ文）"):
                client.create_tweet(text=rewritten)
                st.success("投稿しました！")
        except Exception as e:
            st.error(f"エラーが発生しました: {str(e)}")
    else:
        st.warning("文章を入力してください。")