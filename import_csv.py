import pandas as pd
import pymysql
from pyproj import Transformer

# 좌표 변환기
transformer = Transformer.from_crs("EPSG:5174", "EPSG:4326", always_xy=True)

# CSV 읽기
df = pd.read_csv("gangnam_2.csv")

# 좌표 변환
lon, lat = transformer.transform(df["좌표정보(X)"].values, df["좌표정보(Y)"].values)

df["longitude"] = lon
df["latitude"] = lat

print(df[["사업장명","latitude","longitude"]].head())

# DB 연결
conn = pymysql.connect(
    host="localhost",
    user="python",
    password="1234",
    database="bwlog",
    charset="utf8"
)

cursor = conn.cursor()

for _, row in df.iterrows():
    sql = """
    INSERT INTO restaurants (
        restaurant_category_id,
        name,
        address,
        road_address,
        latitude,
        longitude,
        phone,
        business_hours,
        description,
        region_sido,
        region_sigungu,
        region_dong,
        owner_id,
        status
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    cursor.execute(sql, (
        1,
        row["사업장명"],
        row["지번주소"],
        row["도로명주소"],
        row["latitude"],
        row["longitude"],
        row["전화번호"],
        "10:00-21:00",
        "CSV 업로드 맛집",
        "서울특별시",
        "강남구",
        "역삼동",
        1,
        "OPEN"
    ))

conn.commit()
conn.close()

print("CSV 데이터 DB 삽입 완료")