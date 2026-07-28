import os
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

GEMINI_API_KEY = "your_actual_api_key_here"
import streamlit as st
from google import genai
# SecretsからAPIキーを取得
api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)
# ---------------------------------------------------------
# ページ設定
# ---------------------------------------------------------
st.set_page_config(page_title="お買い物決断アシスタント", page_icon="🛍️", layout="centered")

st.title("🛍️ 迷い解消！お買い物決断アプリ")
st.caption("Gemini APIが、あなたの状況に合わせた質問から最適な選択肢を導き出します。")

# ---------------------------------------------------------
# Clientの初期化（secrets.toml または 環境変数に対応）
# ---------------------------------------------------------
@st.cache_resource
def get_client():
    api_key = None
    # 1. secrets.toml からの取得を優先
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    # 2. ターミナルの環境変数からの取得
    elif os.environ.get("GEMINI_API_KEY"):
        api_key = os.environ.get("GEMINI_API_KEY")
        
    if not api_key:
        return None
        
    return genai.Client(api_key=api_key)

# グローバル変数として client を定義
client = get_client()

if client is None:
    st.error("APIキーが設定されていません。`.streamlit/secrets.toml` ファイルまたは環境変数を確認してください。")
    st.stop()

# ---------------------------------------------------------
# Pydantic Schema（構造化データの定義）
# ---------------------------------------------------------
class Question(BaseModel):
    question_text: str = Field(description="購入判断のための質問文")
    option1: str = Field(description="商品Aが適している選択肢")
    option2: str = Field(description="商品Bが適している選択肢")
    option3: str = Field(description="どちらでもない・両方不要・その他の選択肢")

class QuestionList(BaseModel):
    questions: list[Question] = Field(description="必ず3つの質問のリスト")

class DecisionResult(BaseModel):
    verdict: str = Field(description="結論（例：『商品Aを買うべき』『商品Bを買うべき』『両方買うべき』『どちらも買わないべき』のいずれか）")
    summary: str = Field(description="判断を一言で表したまとめ")
    reasons: list[str] = Field(description="判断に至った詳細な理由（3つ程度）")
    advice: str = Field(description="購入や使用に向けたワンポイントアドバイス")

# ---------------------------------------------------------
# セッション状態（State）の初期化
# ---------------------------------------------------------
if "step" not in st.session_state:
    st.session_state.step = 1
if "questions" not in st.session_state:
    st.session_state.questions = None
if "category" not in st.session_state:
    st.session_state.category = ""
if "item_a" not in st.session_state:
    st.session_state.item_a = ""
if "item_b" not in st.session_state:
    st.session_state.item_b = ""
if "result" not in st.session_state:
    st.session_state.result = None

# =========================================================
# STEP 1: カテゴリー選択と製品入力
# =========================================================
if st.session_state.step == 1:
    st.subheader("Step 1: 迷っている商品を教えてください")
    
    category = st.selectbox(
        "カテゴリーを選択してください",
        ["食べ物", "日用品", "娯楽", "美容"]
    )
    
    col1, col2 = st.columns(2)
    with col1:
        item_a = st.text_input("商品A", placeholder="例: 高級オリーブオイル")
    with col2:
        item_b = st.text_input("商品B", placeholder="例: トリュフフレーバーオイル")

    if st.button("質問を作成する 🪄", type="primary", use_container_width=True):
        if not item_a or not item_b:
            st.warning("商品Aと商品Bの両方を入力してください。")
        else:
            st.session_state.category = category
            st.session_state.item_a = item_a
            st.session_state.item_b = item_b

            prompt = f"""
            ユーザーは「{category}」カテゴリーで、以下の2つの製品のどちらを買うか（あるいは両方か、どちらも買わないか）迷っています。
            - 商品A: {item_a}
            - 商品B: {item_b}

            このユーザーが最適な買い物の判断をするために必要な、カテゴリー「{category}」の特性を反映した質問を【正確に3つ】作成してください。
            各質問には、回答しやすい3つの選択肢（商品A向き、商品B向き、どちらでもない/不要）を用意してください。
            """

            with st.spinner("AIが最適な3つの質問を作成中..."):
                try:
                    response = client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=QuestionList,
                        ),
                    )
                    question_data = QuestionList.model_validate_json(response.text)
                    st.session_state.questions = question_data.questions
                    st.session_state.step = 2
                    st.rerun()
                except Exception as e:
                    st.error(f"質問の生成中にエラーが発生しました: {e}")

# =========================================================
# STEP 2: 質問への回答
# =========================================================
elif st.session_state.step == 2:
    st.subheader("Step 2: 以下の3つの質問に答えてください")
    st.info(f"📂 **{st.session_state.category}** | ⚖️ **{st.session_state.item_a}** VS **{st.session_state.item_b}**")

    answers = []
    
    for i, q in enumerate(st.session_state.questions):
        st.markdown(f"**Q{i+1}. {q.question_text}**")
        ans = st.radio(
            label=f"q_{i}_label",
            options=[q.option1, q.option2, q.option3],
            key=f"q_{i}",
            label_visibility="collapsed"
        )
        answers.append(f"質問{i+1}: {q.question_text}\n回答: {ans}")
        st.write("---")

    col_back, col_submit = st.columns([1, 2])
    with col_back:
        if st.button("戻る", use_container_width=True):
            st.session_state.step = 1
            st.rerun()

    with col_submit:
        if st.button("診断結果を見る ✨", type="primary", use_container_width=True):
            user_answers_text = "\n\n".join(answers)
            
            prompt = f"""
            ユーザーは「{st.session_state.category}」カテゴリーで、以下の2つの購入を迷っています。
            - 商品A: {st.session_state.item_a}
            - 商品B: {st.session_state.item_b}

            ユーザーの質問への回答結果:
            {user_answers_text}

            【指示】
            上記の回答内容を分析し、以下の4パターンのいずれかの明確な判定を下してください。
            1. 「{st.session_state.item_a}」を買うべき
            2. 「{st.session_state.item_b}」を買うべき
            3. 両方買うべき
            4. どちらも買わないべき（両方買わないべき）

            あわせて、なぜその結論になったのか納得感のある理由（複数）とアドバイスを出力してください。
            """

            with st.spinner("回答を分析して診断結果を抽出中..."):
                try:
                    response = client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=DecisionResult,
                        ),
                    )
                    result = DecisionResult.model_validate_json(response.text)
                    st.session_state.result = result
                    st.session_state.step = 3
                    st.rerun()
                except Exception as e:
                    st.error(f"判定の生成中にエラーが発生しました: {e}")

# =========================================================
# STEP 3: 判定結果の表示
# =========================================================
elif st.session_state.step == 3:
    st.subheader("🎉 診断結果")
    result = st.session_state.result

    if result:
        st.success(f"### {result.verdict}")
        st.write(f"**【結論の一言】** {result.summary}")

        st.markdown("#### 💡 判断理由")
        for reason in result.reasons:
            st.write(f"- {reason}")

        st.markdown("#### 📝 ワンポイントアドバイス")
        st.info(result.advice)

    st.write("")
    if st.button("最初からやり直す 🔄", use_container_width=True):
        st.session_state.step = 1
        st.session_state.questions = None
        st.session_state.result = None
        st.rerun()
