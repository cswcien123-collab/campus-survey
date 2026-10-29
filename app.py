import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import re
from collections import Counter

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="캠퍼스 생활 설문조사 & 텍스트 분석 대시보드",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 캠퍼스 생활 만족도 & 학생 한 줄 의견 분석 시스템")
st.markdown("설문조사 수치 데이터와 **학생들의 주관식 한 줄 의견(텍스트)**을 함께 분석하여 인사이트를 도출합니다.")

# -----------------------------------------------------------------------------
# 2. 감성 사전 및 불용어 정의
# -----------------------------------------------------------------------------
POSITIVE_WORDS = {
    "좋다", "만족", "깨끗", "친절", "훌륭", "최고", "편리", "유익", "쾌적",
    "추천", "즐겁", "넓다", "다양", "도움", "재미", "최신", "알차", "성장", "좋음"
}

NEGATIVE_WORDS = {
    "부족", "불편", "불만", "아쉽", "낡다", "좁다", "불친절", "개선", "힘들",
    "복잡", "어렵", "최악", "고장", "비싸", "오래", "시끄럽", "더럽", "답답", "낙후"
}

STOPWORDS = {
    "너무", "정말", "진짜", "많이", "조금", "약간", "매우", "더", "다", "거의",
    "학교", "캠퍼스", "학생", "있는", "없는", "합니다", "있음", "같음", "생각"
}


# -----------------------------------------------------------------------------
# 3. 샘플 데이터 생성 함수
# -----------------------------------------------------------------------------
@st.cache_data
def get_sample_data():
    np.random.seed(42)
    departments = ["컴퓨터공학과", "경영학과", "디자인학과", "기계공학과", "전자공학과", "미디어커뮤니케이션학과"]
    years = [1, 2, 3, 4]

    sample_comments = [
        "도서관 시설이 정말 쾌적하고 조용해서 공부하기에 최고입니다.",
        "강의실 냉난방 시설이 너무 낙후되어 여름에 덥고 불편합니다.",
        "교수님들의 강의가 알차고 실습 위주라 진로에 큰 도움이 됩니다.",
        "학생 식당 메뉴가 다양하지 못하고 가격이 너무 비싸서 아쉽습니다.",
        "학식 맛도 좋고 편의시설이 깨끗하게 잘 관리되어 만족스럽습니다.",
        "셔틀버스 배차 간격이 너무 길어서 등교할 때 너무 힘들고 불편해요.",
        "동아리 활동 지원이 풍부해서 즐겁고 활기찬 대학 생활을 하고 있습니다.",
        "실습실 컴퓨터 사양이 너무 낮고 자주 고장 나서 수업 진행이 어렵습니다.",
        "학과 라운지가 넓고 최신 시설로 리모델링되어 매우 만족합니다.",
        "주차 공간이 턱없이 부족해서 통학할 때마다 스트레스를 받습니다.",
        "교내 와이파이 연결이 자주 끊겨서 노트북으로 과제할 때 답답합니다.",
        "교수님과 조교님들이 항상 친절하게 질문을 받아주셔서 훌륭합니다.",
        "기숙사 시설이 깨끗하고 안전해서 거주 환경이 매우 편안합니다.",
        "휴게 공간이 너무 좁고 부족하여 쉴 곳이 마땅치 않습니다.",
        "전공 수업 커리큘럼이 최신 트렌드를 반영하고 있어서 정말 유익해요."
    ]

    data = []
    for i in range(1, 101):
        dept = str(np.random.choice(departments))
        year = int(np.random.choice(years))
        study_hours = round(float(np.random.uniform(5, 30)), 1)
        commute_time = int(np.random.choice([15, 30, 45, 60, 90, 120]))

        satisfaction = int(np.clip(round(np.random.normal(3.7, 0.8)), 1, 5))
        facility_sat = int(np.clip(round(np.random.normal(3.5, 0.9)), 1, 5))
        lecture_sat = int(np.clip(round(np.random.normal(3.8, 0.7)), 1, 5))
        comment = str(np.random.choice(sample_comments))

        data.append({
            "응답자ID": f"RESP_{i:03d}",
            "학과": dept,
            "학년": year,
            "통학시간(분)": commute_time,
            "주당공부시간(시간)": study_hours,
            "종합만족도": satisfaction,
            "시설만족도": facility_sat,
            "강의만족도": lecture_sat,
            "한줄의견": comment
        })

    dirty_data = [
        {"응답자ID": "ERR_001", "학과": None, "학년": 2, "통학시간(분)": 40, "주당공부시간(시간)": 10.0, "종합만족도": 4, "시설만족도": 3, "강의만족도": 4,
         "한줄의견": "무난합니다."},
        {"응답자ID": "ERR_002", "학과": "컴퓨터공학과", "학년": 1, "통학시간(분)": 30, "주당공부시간(시간)": 15.0, "종합만족도": 99, "시설만족도": 4,
         "강의만족도": 5, "한줄의견": "시설 최고!"},
        {"응답자ID": "ERR_003", "학과": "경영학과", "학년": 3, "통학시간(분)": 50, "주당공부시간(시간)": 8.0, "종합만족도": -1, "시설만족도": 2,
         "강의만족도": 3, "한줄의견": "불편해요."},
        {"응답자ID": "ERR_004", "학과": "디자인학과", "학년": 4, "통학시간(분)": None, "주당공부시간(시간)": 12.0, "종합만족도": 5, "시설만족도": 5,
         "강의만족도": 5, "한줄의견": "만족합니다."},
        {"응답자ID": "ERR_005", "학과": "기계공학과", "학년": 2, "통학시간(분)": 60, "주당공부시간(시간)": None, "종합만족도": 3, "시설만족도": 3,
         "강의만족도": 3, "한줄의견": "보통입니다."}
    ]
    return pd.DataFrame(data + dirty_data)


# -----------------------------------------------------------------------------
# 4. 사이드바: 데이터 업로드
# -----------------------------------------------------------------------------
st.sidebar.header("📁 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("설문조사 CSV 파일을 업로드하세요", type=["csv"])

if uploaded_file is not None:
    try:
        raw_df = pd.read_csv(uploaded_file)
        st.sidebar.success("CSV 파일 업로드 완료!")
    except Exception as e:
        st.sidebar.error(f"파일 오류: {e}")
        raw_df = get_sample_data()
else:
    st.sidebar.info("기본 제공 샘플 데이터를 사용합니다.")
    raw_df = get_sample_data()

# -----------------------------------------------------------------------------
# 5. 데이터 정제 및 유효성 검사
# -----------------------------------------------------------------------------
required_cols = ["학과", "학년", "통학시간(분)", "주당공부시간(시간)", "종합만족도", "시설만족도", "강의만족도"]
if "한줄의견" not in raw_df.columns:
    raw_df["한줄의견"] = "의견 없음"

missing_cols = [c for c in required_cols if c not in raw_df.columns]
if missing_cols:
    st.error(f"필수 컬럼이 누락되었습니다: {missing_cols}")
    st.stop()

total_rows = len(raw_df)
has_na = raw_df[required_cols].isna().any(axis=1)

score_cols = ["종합만족도", "시설만족도", "강의만족도"]
valid_score_range = raw_df[score_cols].apply(
    lambda s: pd.to_numeric(s, errors="coerce").between(1, 5)
).all(axis=1)

valid_mask = (~has_na) & valid_score_range
clean_df = raw_df[valid_mask].copy()
invalid_df = raw_df[~valid_mask].copy()

for col in score_cols + ["통학시간(분)", "주당공부시간(시간)"]:
    clean_df[col] = pd.to_numeric(clean_df[col])

valid_count = len(clean_df)
invalid_count = len(invalid_df)

# -----------------------------------------------------------------------------
# 6. 정제 결과 요약 카드
# -----------------------------------------------------------------------------
st.subheader("📊 데이터 정제 및 검증 현황")
m1, m2, m3, m4 = st.columns(4)
m1.metric("전체 수집 건수", f"{total_rows:,} 건")
m2.metric("정상 데이터 건수", f"{valid_count:,} 건")
m3.metric("제외된 오류 데이터", f"{invalid_count:,} 건", delta=f"-{invalid_count} 건", delta_color="inverse")
m4.metric("데이터 유효율", f"{(valid_count / total_rows * 100):.1f} %")

with st.expander("🔍 정제된 데이터 및 제외된 불량 데이터 미리보기"):
    t1, t2 = st.tabs(["유효 데이터", "제외 내역"])
    with t1:
        st.dataframe(clean_df.head(5), use_container_width=True)
    with t2:
        if invalid_count > 0:
            st.warning("결측치(NaN) 또는 만족도 척도(1~5점)를 벗어난 데이터 목록입니다.")
            st.dataframe(invalid_df, use_container_width=True)
        else:
            st.info("제외된 데이터가 없습니다.")

# -----------------------------------------------------------------------------
# 7. 학과 필터 (사이드바)
# -----------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("🎯 학과 선택 필터")
all_departments = sorted(clean_df["학과"].dropna().unique().tolist())
select_all = st.sidebar.checkbox("전체 학과 선택", value=True)

if select_all:
    selected_depts = st.sidebar.multiselect("학과 선택:", all_departments, default=all_departments)
else:
    selected_depts = st.sidebar.multiselect("학과 선택:", all_departments,
                                            default=[all_departments[0]] if all_departments else [])

if not selected_depts:
    st.warning("최소 1개 이상의 학과를 선택해 주세요.")
    st.stop()

filtered_df = clean_df[clean_df["학과"].isin(selected_depts)]

# -----------------------------------------------------------------------------
# 8. 학과별 평균 만족도 지표
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader(f"📌 선택 학과 요약 지표 ({len(selected_depts)}개 학과 / {len(filtered_df)}명)")
k1, k2, k3, k4 = st.columns(4)
k1.metric("⭐ 종합 만족도 평균", f"{filtered_df['종합만족도'].mean():.2f} / 5.0")
k2.metric("🏢 시설 만족도 평균", f"{filtered_df['시설만족도'].mean():.2f} / 5.0")
k3.metric("📖 강의 만족도 평균", f"{filtered_df['강의만족도'].mean():.2f} / 5.0")
k4.metric("⏱️ 주당 공부시간 평균", f"{filtered_df['주당공부시간(시간)'].mean():.1f} 시간")

# -----------------------------------------------------------------------------
# 9. 시각화: 상자그림 & 산점도
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("📈 만족도 분포 및 상관관계 분석")
c1, c2 = st.columns(2)

with c1:
    st.markdown("#### 📦 학과별 만족도 상자그림 (Box Plot)")
    sat_metric = st.selectbox("항목 선택:", ["종합만족도", "시설만족도", "강의만족도"], key="box_metric")
    fig_box = px.box(
        filtered_df,
        x="학과",
        y=sat_metric,
        color="학과",
        points="all",
        title=f"학과별 {sat_metric} 분포",
        template="plotly_white"
    )
    fig_box.update_layout(showlegend=False, yaxis=dict(range=[0.5, 5.5]))
    st.plotly_chart(fig_box, use_container_width=True)

with c2:
    st.markdown("#### 🔵 통학/공부시간 vs 만족도 산점도 (Scatter Plot)")
    x_axis = st.selectbox("X축 항목 선택:", ["주당공부시간(시간)", "통학시간(분)"], key="scatter_x")
    fig_scatter = px.scatter(
        filtered_df,
        x=x_axis,
        y="종합만족도",
        color="학과",
        size="시설만족도",
        hover_data=["응답자ID", "학년"],
        title=f"{x_axis}에 따른 만족도 산점도",
        template="plotly_white"
    )
    fig_scatter.update_layout(yaxis=dict(range=[0.5, 5.5]))
    st.plotly_chart(fig_scatter, use_container_width=True)

# -----------------------------------------------------------------------------
# 10. 한 줄 의견 텍스트 분석
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("💬 학생 한 줄 의견(Review) 텍스트 분석")

all_comments = filtered_df["한줄의견"].dropna().astype(str).tolist()

tokens = []
pos_count = 0
neg_count = 0

for text in all_comments:
    cleaned_text = re.sub(r"[^가-힣a-zA-Z\s]", " ", text)
    words = cleaned_text.split()

    for word in words:
        if len(word) >= 2 and word not in STOPWORDS:
            tokens.append(word)

        if any(pos in word for pos in POSITIVE_WORDS):
            pos_count += 1
        elif any(neg in word for neg in NEGATIVE_WORDS):
            neg_count += 1

total_sentiment_count = pos_count + neg_count

txt_col1, txt_col2, txt_col3 = st.columns(3)
txt_col1.metric("총 분석된 의견 수", f"{len(all_comments):,} 개")
txt_col2.metric("😊 긍정 단어 등장 횟수", f"{pos_count:,} 회",
                delta=f"{((pos_count / total_sentiment_count * 100) if total_sentiment_count else 0):.1f}%")
txt_col3.metric("🙁 부정 단어 등장 횟수", f"{neg_count:,} 회",
                delta=f"-{((neg_count / total_sentiment_count * 100) if total_sentiment_count else 0):.1f}%",
                delta_color="inverse")

t_chart1, t_chart2 = st.columns([3, 2])

with t_chart1:
    st.markdown("#### 🏆 자주 등장하는 단어 TOP 10")
    if tokens:
        word_freq = Counter(tokens).most_common(10)
        word_df = pd.DataFrame(word_freq, columns=["단어", "등장횟수"]).sort_values(by="등장횟수", ascending=True)

        fig_bar = px.bar(
            word_df,
            x="등장횟수",
            y="단어",
            orientation="h",
            text="등장횟수",
            color="등장횟수",
            color_continuous_scale="Teal",
            title="한 줄 의견 최빈출 단어 상위 10개"
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(showlegend=False, template="plotly_white")
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("분석할 단어가 충분하지 않습니다.")

with t_chart2:
    st.markdown("#### ⚖️ 긍정 vs 부정 단어 비율")
    if total_sentiment_count > 0:
        sentiment_df = pd.DataFrame({
            "감성": ["긍정 단어", "부정 단어"],
            "등장횟수": [pos_count, neg_count]
        })
        fig_donut = px.pie(
            sentiment_df,
            values="등장횟수",
            names="감성",
            hole=0.45,
            color="감성",
            color_discrete_map={"긍정 단어": "#2ca02c", "부정 단어": "#d62728"},
            title="의견 내 감성 단어 분포"
        )
        fig_donut.update_traces(textinfo="percent+value")
        fig_donut.update_layout(template="plotly_white")
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.info("감성 단어가 탐지되지 않았습니다.")