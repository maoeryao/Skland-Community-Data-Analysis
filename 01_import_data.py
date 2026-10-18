import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# ================= 配置区 =================
DB_PATH = 'skland_massive.db'
CSV_PATH = 'sample_data.csv'  # 你手敲的100条真实样本
TOTAL_ROWS = 1000000  # 模拟 100 万条数据
CHUNK_SIZE = 50000  # 分块写入大小，防止 OOM
TODAY = datetime(2026, 10, 16)  # 基准日期


# ==========================================

def load_real_sample():
    """读取真实的100条样本数据，提取业务分布"""
    if not os.path.exists(CSV_PATH):
        print(f"⚠️ 找不到 {CSV_PATH}，将直接使用默认分布生成数据。")
        return None

    # 尝试用 utf-8 或 gbk 读取（兼容你的 Excel 导出格式）
    try:
        df = pd.read_csv(CSV_PATH, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(CSV_PATH, encoding='gbk')

    print(f"✅ 成功读取真实样本 {len(df)} 条。")
    return df


def generate_massive_data(rows, sample_df):
    """基于真实样本分布，生成百万级模拟数据"""
    print(f"⏳ 正在生成 {rows} 条模拟数据...")

    # 提取真实的板块分布比例
    if sample_df is not None and 'board' in sample_df.columns:
        board_counts = sample_df['board'].value_counts(normalize=True)
        boards = board_counts.index.tolist()
        board_weights = board_counts.values.tolist()
        print(f"📊 基于真实样本的板块分布：{dict(zip(boards, np.round(board_weights, 2)))}")
    else:
        boards = ['攻略', '同人', '闲聊', '官方', '杂谈']
        board_weights = [0.10, 0.25, 0.55, 0.05, 0.05]

    selected_boards = random.choices(boards, weights=board_weights, k=rows)

    # 生成过去 30 天的随机日期 (格式：2026-10-16)
    date_list = [(TODAY - timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d') for _ in range(rows)]

    # 模拟互动数据：攻略互动高，闲聊互动低
    likes = []
    comments = []
    for b in selected_boards:
        if '攻略' in b:
            likes.append(np.random.randint(100, 5000))
            comments.append(np.random.randint(10, 500))
        elif '同人' in b:
            likes.append(np.random.randint(50, 3000))
            comments.append(np.random.randint(5, 300))
        else:
            likes.append(np.random.randint(1, 1000))
            comments.append(np.random.randint(0, 100))

    df = pd.DataFrame({
        'post_id': range(1, rows + 1),
        'title': ['模拟帖子_' + str(i) for i in range(1, rows + 1)],
        'board': selected_boards,
        'post_time': date_list,
        'likes': likes,
        'comments': comments
    })
    return df


def init_massive_db():
    # 1. 读取真实样本
    sample_df = load_real_sample()

    # 2. 连接数据库并建表
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 先清理旧表，防止重复运行导致主键冲突
    cursor.execute('DROP TABLE IF EXISTS posts')

    cursor.execute('''
        CREATE TABLE posts (
            post_id INTEGER PRIMARY KEY,
            title TEXT,
            board TEXT,
            post_time TEXT,
            likes INTEGER,
            comments INTEGER,
            days_alive INTEGER,
            daily_engagement REAL
        )
    ''')
    # 核心优化：建立 B-Tree 索引，大幅提升后续 SQL 分组查询速度
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_board ON posts(board);')
    conn.commit()
    conn.close()
    print("✅ 数据库表及索引创建完成！")

    # 3. 生成 100 万条数据
    df = generate_massive_data(TOTAL_ROWS, sample_df)

    # 4. 核心：Pandas 向量化运算（剔除时间累积偏差）
    print("🚀 正在执行向量化计算（计算存活天数与日均互动）...")

    # 向量化处理日期
    df['post_date'] = pd.to_datetime(df['post_time'])
    df['days_alive'] = (TODAY - df['post_date']).dt.days + 1
    df['days_alive'] = df['days_alive'].clip(lower=1)  # 防止除零报错

    # 向量化计算日均互动量
    df['daily_engagement'] = (df['likes'] + df['comments']) / df['days_alive']

    # 删除中间过程列
    df = df.drop(columns=['post_date'])

    # 5. 核心：分块写入数据库（防止内存溢出 OOM）
    print(f"📦 开始分块写入数据库（每块 {CHUNK_SIZE} 条）...")
    conn = sqlite3.connect(DB_PATH)

    # 使用 chunksize 参数实现流式写入
    df.to_sql('posts', conn, if_exists='append', index=False, chunksize=CHUNK_SIZE)

    conn.close()
    print(f"🎉 成功导入 {len(df)} 条数据，并完成日均互动量计算！")


if __name__ == '__main__':
    init_massive_db()