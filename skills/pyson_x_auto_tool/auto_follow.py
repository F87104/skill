        try:
            # 現在のウィンドウを保存
            main_window = self.driver.current_window_handle
            
            # 新しいタブを開く
            initial_handles = self.driver.window_handles
            self.driver.execute_script("window.open('');")
            
            # タブが増えるまで待機
            wait_count = 0
            while len(self.driver.window_handles) <= len(initial_handles) and wait_count < 10:
                time.sleep(0.5)
                wait_count += 1
            
            if len(self.driver.window_handles) > len(initial_handles):
                # 新しいタブに切り替え
                self.driver.switch_to.window(self.driver.window_handles[-1])
                
                # ユーザーページに移動
                self.driver.get(f"https://x.com/{username}")
                time.sleep(3)
            else:
                log_warning("新しいタブを開けませんでした。メインタブで処理を継続します。")
            
            # フォロワー数を取得
            try:
                followers_link = self.driver.find_element(By.CSS_SELECTOR, f'a[href="/{username}/verified_followers"]')
                followers_text = followers_link.text
                info["followers"] = self._parse_count(followers_text)
            except:
                try:
                    followers_link = self.driver.find_element(By.CSS_SELECTOR, f'a[href="/{username}/followers"]')
                    followers_text = followers_link.text
                    info["followers"] = self._parse_count(followers_text)
                except:
                    pass
            
            # フォロー数を取得
            try:
                following_link = self.driver.find_element(By.CSS_SELECTOR, f'a[href="/{username}/following"]')
                following_text = following_link.text
                info["following"] = self._parse_count(following_text)
            except:
                pass
            
            # プロフィールを取得
            try:
                bio_elem = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="UserDescription"]')
                info["bio"] = bio_elem.text
            except:
                pass
            
            # フォロー済みかチェック
            try:
                unfollow_button = self.driver.find_element(By.CSS_SELECTOR, '[data-testid$="-unfollow"]')
                info["is_following"] = True
            except:
                info["is_following"] = False
            
            info["is_valid"] = True
            
        except Exception as e:
            log_warning(f"ユーザー情報取得エラー ({username}): {e}")
        finally:
            # タブを閉じて元に戻る
            try:
                if len(self.driver.window_handles) > 1:
                    if self.driver.current_window_handle != main_window:
                        self.driver.close()
                    self.driver.switch_to.window(main_window)
            except:
                pass
        
        return info
    
    def _parse_count(self, text: str) -> int:
        """フォロワー数などをパース（1.5万 → 15000）"""
        text = text.strip().lower()
        
        # 数字だけ抽出
        match = re.search(r'([\d,.]+)\s*(万|k|m)?', text)
        if not match:
            return 0
        
        num_str = match.group(1).replace(",", "")
        try:
            num = float(num_str)
        except:
            return 0
        
        unit = match.group(2)
        if unit == "万":
            num *= 10000
        elif unit == "k":
            num *= 1000
        elif unit == "m":
            num *= 1000000
        
        return int(num)
    
    def is_quality_user(self, info: dict) -> tuple:
        """質の高いユーザーかチェック"""
        
        # フォロワー数チェック
        if info["followers"] < MIN_FOLLOWERS:
            return False, f"フォロワー数不足 ({info['followers']} < {MIN_FOLLOWERS})"
        
        # フォロー/フォロワー比率チェック
        if info["followers"] > 0:
            ratio = info["following"] / info["followers"]
            if ratio > MAX_FOLLOWING_RATIO:
                return False, f"フォロー比率が高すぎ ({ratio:.1f} > {MAX_FOLLOWING_RATIO})"
        
        # 除外キーワードチェック
        bio_lower = info["bio"].lower()
        for keyword in EXCLUDE_KEYWORDS:
            if keyword.lower() in bio_lower:
                return False, f"除外キーワード検出: {keyword}"
        
        return True, "OK"
    
    def follow_user(self, username: str) -> bool:
        """ユーザーをフォロー"""
        try:
            # プロフィールページに移動
            self.driver.get(f"https://x.com/{username}")
            time.sleep(3)
            
            # フォローボタンを探す
            try:
                follow_button = self.driver.find_element(By.CSS_SELECTOR, '[data-testid$="-follow"]')
                follow_button.click()
                time.sleep(2)
                return True
            except NoSuchElementException:
                # 既にフォロー済みの可能性
                try:
                    self.driver.find_element(By.CSS_SELECTOR, '[data-testid$="-unfollow"]')
                    log_info("既にフォロー済み")
                    return False
                except:
                    log_warning("フォローボタンが見つかりません")
                    return False
            
        except Exception as e:
            log_warning(f"フォローエラー ({username}): {e}")
            return False
    
    def run_cycle(self) -> dict:
        """1サイクル実行"""
        log_phase("=" * 50)
        log_phase("自動フォローサイクル開始")
        log_phase("=" * 50)
        
        result = {
            "followed": 0,
            "skipped": 0,
            "checked": 0
        }
        
        # 今日のフォロー数をチェック
        today_count = self.follow_log.get_today_count()
        remaining = DAILY_FOLLOW_LIMIT - today_count
        
        log_info(f"本日のフォロー数: {today_count}/{DAILY_FOLLOW_LIMIT}")
        
        if remaining <= 0:
            log_warning("本日のフォロー上限に達しました")
            return result
        
        follows_this_cycle = 0
        max_follows = min(FOLLOWS_PER_CYCLE, remaining)
        
        # ランダムにキーワードを選択
        keywords_to_search = random.sample(KEYWORDS, min(3, len(KEYWORDS)))
        
        for keyword in keywords_to_search:
            if follows_this_cycle >= max_follows:
                break
            
            log_info(f"検索中: {keyword}")
            users = self.search_users(keyword)
            log_info(f"取得ユーザー: {len(users)}件")
            
            random.shuffle(users)
            
            for username in users:
                if follows_this_cycle >= max_follows:
                    break
                
                # 既にフォロー済みかチェック
                if self.follow_log.is_already_followed(username):
                    log_skip(f"@{username} - 既に記録済み")
                    continue
                
                result["checked"] += 1
                log_info(f"チェック中: @{username}")
                
                # ユーザー情報を取得
                info = self.get_user_info(username)
                
                if not info["is_valid"]:
                    result["skipped"] += 1
                    continue
                
                if info["is_following"]:
                    log_info("既にフォロー済み")
                    self.follow_log.add_follow(username)
                    result["skipped"] += 1
                    continue
                
                # 質チェック
                is_quality, reason = self.is_quality_user(info)
                
                if not is_quality:
                    log_skip(f"@{username} - {reason}")
                    result["skipped"] += 1
                    continue
                
                # フォロー実行
                log_info(f"フォロー中: @{username} (フォロワー: {info['followers']})")
                success = self.follow_user(username)
                
                if success:
                    result["followed"] += 1
                    follows_this_cycle += 1
                    self.follow_log.add_follow(username)
                    
                    today_total = self.follow_log.get_today_count()
                    log_success(f"✅ フォロー成功！ (本日: {today_total}/{DAILY_FOLLOW_LIMIT})")
                    
                    # 待機
                    wait_time = random.uniform(MIN_WAIT, MAX_WAIT)
                    log_info(f"次のフォローまで {wait_time:.0f}秒 待機...")
                    time.sleep(wait_time)
                else:
                    result["skipped"] += 1
                    time.sleep(3)
        
        log_phase(f"サイクル完了: {result['followed']}件フォロー")
        return result


def main():
    parser = argparse.ArgumentParser(description="Selenium自動フォロー v1.0")
    parser.add_argument("--loop", action="store_true", help="継続実行モード")
    parser.add_argument("--headless", action="store_true", help="バックグラウンド実行モード")
    args = parser.parse_args()
    
    print(BANNER)
    
    engine = SeleniumAutoFollow(headless=args.headless)
    
    try:
        if not engine.setup():
            return
        
        log_info("Xログイン状態を確認中...")
        if not engine.is_logged_in():
            log_error("Xにログインしていません。")
            log_error("開いたChromeでXにログインしてください。")
            log_info("ログイン後、Enterキーを押してください...")
            input()
            
            if not engine.is_logged_in():
                log_error("ログインが確認できません。終了します。")
                return
        
        log_success("ログイン確認OK！")
        
        print()
        log_info(f"フォロー条件:")
        log_info(f"  - フォロワー {MIN_FOLLOWERS}人以上")
        log_info(f"  - 詐欺・情報商材系を除外")
        log_info(f"  - 1日上限: {DAILY_FOLLOW_LIMIT}件")
        log_info(f"  - 1サイクル: {FOLLOWS_PER_CYCLE}件")
        
        if args.loop:
            log_info("継続モードで実行します（Ctrl+C で停止）")
            
            cycle = 1
            try:
                while True:
                    if not engine.follow_log.can_follow_today():
                        log_warning("本日のフォロー上限に達しました。1時間後に再チェックします。")
                        time.sleep(3600)
                        continue
                    
                    print()
                    log_phase(f"===== サイクル {cycle} =====")
                    
                    result = engine.run_cycle()
                    
                    # サイクル間の待機（5〜10分）
                    wait_time = random.randint(300, 600)
                    log_info(f"次のサイクルまで {wait_time//60}分 待機...")
                    time.sleep(wait_time)
                    
                    cycle += 1
                    
            except KeyboardInterrupt:
                print()
                log_info("停止しました")
        else:
            result = engine.run_cycle()
            
            print()
            log_phase("【実行結果】")
            print(f"フォロー成功: {result['followed']}件")
            print(f"スキップ: {result['skipped']}件")
            print(f"本日合計: {engine.follow_log.get_today_count()}/{DAILY_FOLLOW_LIMIT}件")
    
    finally:
        engine.close()


if __name__ == "__main__":
    main()
