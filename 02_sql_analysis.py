import sqlite3
import pandas as pd

DB_PATH = 'skland_massive.db'


def run_analysis():
    conn = sqlite3.connect(DB_PATH)

    print("=" * 60)
    print("📊 核心发现 1：各内容类型的日均互动对比（剔除时间偏差）")
    print("=" * 60)
    sql1 = """
    SELECT 
        board AS "内容类型",
        COUNT(*) AS "帖子数",
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM posts), 2) AS "占比(%)",
        ROUND(AVG(daily_engagement), 1) AS "日均互动量"
    FROM posts
    GROUP BY board
    ORDER BY "日均互动量" DESC;
    """
    df1 = pd.read_sql_query(sql1, conn)
    print(df1.to_string(index=False))

    print("\n" + "=" * 60)
    print("📈 核心发现 2：各板块的日均互动效率")
    print("=" * 60)
    sql2 = """
    SELECT 
        board AS "板块",
        COUNT(*) AS "帖子数",
        ROUND(AVG(daily_engagement), 1) AS "日均互动量"
    FROM posts
    GROUP BY board
    ORDER BY "日均互动量" DESC;
    """
    df2 = pd.read_sql_query(sql2, conn)
    print(df2.to_string(index=False))

    print("\n" + "=" * 60)
    print("📉 核心发现 3：每日发帖量趋势（过去 7 天）")
    print("=" * 60)
    sql3 = """
    SELECT 
        post_time AS "日期",
        COUNT(*) AS "发帖量"
    FROM posts
    GROUP BY post_time
    ORDER BY post_time DESC
    LIMIT 7;
    """
    df3 = pd.read_sql_query(sql3, conn)
    print(df3.to_string(index=False))

    conn.close()
    print("\n✅ 分析完成！")


if __name__ == '__main__':
    run_analysis()