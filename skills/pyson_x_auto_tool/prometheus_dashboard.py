import json
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import os

# =====================================================
# Project Prometheus v13.0 [Performance Dashboard]
# 活動の成果を可視化し、データに基づいた戦略改善を支援
# =====================================================

class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def log_info(msg):
    print(Colors.BLUE + "[INFO]" + Colors.RESET + " " + str(msg))

def log_success(msg):
    print(Colors.GREEN + "[SUCCESS]" + Colors.RESET + " " + str(msg))

class DashboardGenerator:
    def __init__(self, session_dir, output_path):
        self.session_dir = Path(session_dir)
        self.output_path = Path(output_path)
        self.liked_users_file = self.session_dir / 'liked_users.json'
        self.followed_users_file = self.session_dir / 'followed_users.json'

    def load_data(self):
        log_info("履歴データを読み込んでいます...")
        # いいね履歴
        try:
            with self.liked_users_file.open('r', encoding='utf-8') as f:
                likes_data = json.load(f)
            likes_df = pd.DataFrame(likes_data.items(), columns=['user', 'timestamp'])
            likes_df['timestamp'] = pd.to_datetime(likes_df['timestamp'])
            likes_df['date'] = likes_df['timestamp'].dt.date
        except FileNotFoundError:
            likes_df = pd.DataFrame(columns=['user', 'timestamp', 'date'])

        # フォロー履歴
        try:
            with self.followed_users_file.open('r', encoding='utf-8') as f:
                followed_data = json.load(f)
            
            records = []
            for user, data in followed_data.items():
                records.append({
                    'user': user,
                    'followed_at': data.get('followed_at'),
                    'status': data.get('status')
                })
            
            follows_df = pd.DataFrame(records)
            follows_df['followed_at'] = pd.to_datetime(follows_df['followed_at'])
            follows_df['date'] = follows_df['followed_at'].dt.date
        except FileNotFoundError:
            follows_df = pd.DataFrame(columns=['user', 'followed_at', 'status', 'date'])

        return likes_df, follows_df

    def generate_dashboard(self, likes_df, follows_df):
        log_info("データを集計し、ダッシュボードを生成しています...")
        # 日毎の集計
        daily_likes = likes_df.groupby('date').size().rename('likes')
        daily_follows = follows_df[follows_df['status'] == 'pending'].groupby('date').size().rename('follows')
        daily_unfollows = follows_df[follows_df['status'] == 'unfollowed'].groupby('date').size().rename('unfollows')

        df = pd.concat([daily_likes, daily_follows, daily_unfollows], axis=1).fillna(0).astype(int)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        # 累計フォロー数
        df['cumulative_follows'] = (df['follows'] - df['unfollows']).cumsum()

        # KPIサマリー
        total_likes = df['likes'].sum()
        total_follows = df['follows'].sum()
        total_unfollows = df['unfollows'].sum()
        net_followers = total_follows - total_unfollows

        # ダッシュボード作成
        fig = make_subplots(
            rows=2, cols=2,
            specs=[[{'type': 'indicator'}, {'type': 'indicator'}], [{'colspan': 2, 'type': 'scatter'}, None]],
            row_heights=[0.3, 0.7],
            subplot_titles=("総いいね数", "総フォロワー純増数", "日別アクション数とフォロワー推移")
        )

        # インジケーター
        fig.add_trace(go.Indicator(
            mode = "number",
            value = int(total_likes),
            title = {"text": "Likes"}),
            row=1, col=1
        )

        fig.add_trace(go.Indicator(
            mode = "number+delta",
            value = int(net_followers),
            delta = {'reference': 0, 'increasing': {'color': "green"}, 'decreasing': {'color': "red"}},
            title = {"text": "Net Followers"}),
            row=1, col=2
        )

        # 時系列グラフ
        fig.add_trace(go.Bar(x=df.index, y=df['likes'], name='いいね', marker_color='lightblue'), row=2, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['follows'], name='フォロー', marker_color='lightgreen'), row=2, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['unfollows'], name='アンフォロー', marker_color='lightcoral'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['cumulative_follows'], name='フォロワー純増数 (累計)', mode='lines+markers', yaxis='y2', line={'color': 'orange'}), row=2, col=1)

        # レイアウト更新
        fig.update_layout(
            title_text="Project Prometheus - パフォーマンス・ダッシュボード",
            barmode='stack',
            yaxis=dict(title='日別アクション数'),
            yaxis2=dict(title='フォロワー純増数 (累計)', overlaying='y', side='right'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        log_info("HTMLファイルに書き出しています...")
        fig.write_html(str(self.output_path))

    def run(self):
        likes_df, follows_df = self.load_data()
        self.generate_dashboard(likes_df, follows_df)
        log_success("ダッシュボードの生成が完了しました: " + str(self.output_path))

def main():
    log_info("--- Project Prometheus v13.0 [Performance Dashboard] ---")
    session_dir = os.path.expanduser('~/.prometheus_v11_session')
    output_path = os.path.expanduser('~/prometheus/prometheus_dashboard.html')
    generator = DashboardGenerator(session_dir, output_path)
    generator.run()

if __name__ == "__main__":
    main()
