'''
csv 전처리 작업
import os
import pymysql
from dotenv import load_dotenv
import pandas as pd

# 파일 위치 확인하기
# print("현재 실행 위치:", os.getcwd())
# print("현재 파일 위치:", os.path.dirname(__file__))

"""-------- 인코딩 err 확인하기 ------------"""
encodings = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr', 'latin1']
csv_path = '../data/csv/gangnam.csv'
tests = [
    {'encoding': 'utf-8'},
    {'encoding': 'utf-8-sig'},
    {'encoding': 'cp949'},
    {'encoding': 'euc-kr'},
    {'encoding': 'utf-16'},
    {'encoding': 'utf-16le'},
    {'encoding': 'utf-16be'},
]

# for t in tests:
#     try:
#         df = pd.read_csv(csv_path, encoding=t['encoding'], engine='python')
#         print(f"\n성공: {t['encoding']}")
#         print(df.columns.tolist()[:10])
#     except Exception as e:
#         print(f"\n실패: {t['encoding']} -> {e}")

"""---------------------   err 확인 완료----------------------------"""


"""-----전처리 : 데이터 정제(영업중만 추출 후 강남구 30곳추출)-----"""
df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)

# 사용할 열 선택
selected_cols = [1,3,6,7,8,9,13, 14,15]
df = df.iloc[:, selected_cols]
df = df[df['전화번호'].notna()]
# df = df.head(30)
# print(df)

df_gangnam = df[df['지번주소'].astype(str).str.contains('강남구', na=False)]
df_gangnam = df_gangnam.head(30)
print(df_gangnam)


# 저장 경로
output_path = '../data/csv/gangnam_2.csv'

# CSV 저장
df_gangnam.to_csv(output_path, index=False, encoding='utf-8-sig')

print("저장 완료:", output_path)

'''