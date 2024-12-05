import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import time
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh  # 추가

# 페이지 설정
st.set_page_config(
    page_title="KRW-FIL 가격 차트",
    layout="wide",
)

st.title('KRW-FIL 가격 차트')

# 페이지를 60초마다 자동 새로고침
count = st_autorefresh(interval=30000, key="fil_price_autorefresh")

# 업비트 API에서 시장 코드 가져오기
@st.cache_data
def get_market_codes():
    url = 'https://api.upbit.com/v1/market/all'
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        st.error(f"시장 코드 가져오기 실패: HTTP {response.status_code}")
        return None
    markets = response.json()
    return markets

# 업비트 API에서 1분봉 데이터 가져오기
@st.cache_data(ttl=60)
def fetch_minute_data(market='KRW-BTC', unit=1, count=200):
    url = f'https://api.upbit.com/v1/candles/minutes/{unit}'
    params = {
        'market': market,
        'count': count
    }
    headers = {"Accept": "application/json"}
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code != 200:
        st.error(f"API 요청 실패 ({market}): HTTP {response.status_code}")
        st.error(f"응답 내용: {response.text}")
        return None
    
    data = response.json()
    
    # 데이터가 비어 있는지 확인
    if not data:
        st.error(f"API 응답 데이터가 비어 있습니다 ({market}).")
        return None
    
    # 데이터에 에러 메시지가 있는지 확인
    if isinstance(data, dict) and data.get('error'):
        st.error(f"API 에러 ({market}): {data['error']['message']}")
        return None
    
    return data

# 데이터 처리
def process_data(data, market):
    if data is None:
        return None
    df = pd.DataFrame(data)
    expected_column = 'candle_date_time_kst'
    if expected_column not in df.columns:
        st.error(f"'{expected_column}' 컬럼이 없습니다 ({market}).")
        st.write("데이터프레임 컬럼 목록:", df.columns)
        st.write("데이터프레임 내용:")
        st.write(df.head())
        return None
    df['date_time'] = pd.to_datetime(df['candle_date_time_kst'])
    df = df.sort_values('date_time')
    return df

def main():
    # 지원하는 시장 코드 가져오기
    markets = get_market_codes()
    if markets is None:
        st.error("시장 코드를 가져올 수 없습니다.")
        return
    market_codes = [market['market'] for market in markets]
    
    # 비트코인과 파일코인의 시장 코드 확인
    krw_btc_market = 'KRW-BTC'
    btc_fil_market = 'BTC-FIL'
    if krw_btc_market not in market_codes:
        st.error(f"{krw_btc_market} 시장 코드가 존재하지 않습니다.")
        return
    if btc_fil_market not in market_codes:
        st.error(f"{btc_fil_market} 시장 코드가 존재하지 않습니다.")
        return

    # 데이터 가져오기
    krw_btc_data = fetch_minute_data(market=krw_btc_market)
    time.sleep(0.1)
    krw_btc_df = process_data(krw_btc_data, krw_btc_market)
    if krw_btc_df is None:
        st.error("비트코인 데이터 처리에 실패했습니다.")
        return
    
    btc_fil_data = fetch_minute_data(market=btc_fil_market)
    time.sleep(0.1)
    btc_fil_df = process_data(btc_fil_data, btc_fil_market)
    if btc_fil_df is None:
        st.error("파일코인 데이터 처리에 실패했습니다.")
        return
    
    # 데이터 병합 및 KRW-FIL 가격 계산
    merged_df = pd.merge(
        krw_btc_df[['date_time', 'trade_price']],
        btc_fil_df[['date_time', 'trade_price']],
        on='date_time',
        suffixes=('_krw_btc', '_btc_fil')
    )
    merged_df['krw_fil_price'] = merged_df['trade_price_krw_btc'] * merged_df['trade_price_btc_fil']
    
    # 차트 그리기
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(merged_df['date_time'], merged_df['krw_fil_price'], label='KRW-FIL')
    ax.set_xlabel('Time')
    ax.set_ylabel('Price (KRW)')
    ax.set_title('KRW-FIL')
    ax.legend()
    ax.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 현재 가격을 차트에 표시
    current_price = merged_df['krw_fil_price'].iloc[-1]
    current_time = merged_df['date_time'].iloc[-1]

    # y=11,847에 빨간색 가로선 추가
    ax.axhline(y=11847, color='red', linestyle='--', label='기준선 (11,847 KRW)')
    
    # 텍스트로 현재 가격 표시
    ax.text(
        current_time, current_price,
        f"{current_price:,.0f} KRW",
        color='red', fontsize=12, ha='right', va='bottom'
    )

    # 마지막 데이터 포인트에 동그라미 표시
    ax.plot(current_time, current_price, 'ro')

    st.pyplot(fig)

    st.write(f"마지막 업데이트: {datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    main()
