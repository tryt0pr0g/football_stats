from bs4 import BeautifulSoup, Tag
from typing import List, Dict, Any, Optional
from datetime import datetime
import re


class StatsParser:
    def parse_league_history(self, html: str) -> List[Dict[str, Any]]:
        """
        Парсит страницу истории (History).
        Возвращает список сезонов: [{'season': '2022-2023', 'url': '...'}, ...]
        """
        # Чистим от комментариев
        html = html.replace('<!--', '').replace('-->', '')
        soup = BeautifulSoup(html, 'lxml')

        # Обычно таблица называется "seasons"
        table = soup.select_one('table.stats_table')
        if not table: return []

        seasons_data = []
        rows = table.find('tbody').find_all('tr')

        for row in rows:
            # Год/Сезон обычно в th с data-stat="season" или "year_id"
            season_header = row.find('th', {'data-stat': 'year_id'}) or row.find('th', {'data-stat': 'season'})

            if not season_header: continue

            link = season_header.find('a')
            if not link: continue

            season_name = link.get_text().strip()  # "2023-2024"
            href = link['href']
            # Ссылка: /en/comps/9/2023-2024/2023-2024-Premier-League-Stats

            full_url = f"https://fbref.com{href}"

            seasons_data.append({
                "season": season_name,
                "url": full_url
            })

        return seasons_data

    def parse_leagues(self, html: str) -> List[Dict[str, Any]]:
        # Удаляем комментарии, чтобы видеть скрытые таблицы
        html = html.replace('<!--', '').replace('-->', '')
        soup = BeautifulSoup(html, 'lxml')

        tables = soup.select('table.stats_table')
        if not tables:
            return []

        leagues_data = []
        unique_slugs = set()

        for table in tables:
            rows = table.find('tbody').find_all('tr')
            for row in rows:
                league_header = row.find('th', {'data-stat': 'league_name'})
                if not league_header: continue

                league_name = league_header.get_text().strip()

                # Ищем ссылку
                all_links = row.find_all('a')
                target_href = None
                for link in all_links:
                    href = link['href']
                    parts = href.split('/')
                    # /en/comps/9/Premier-League-Stats
                    if len(parts) == 5 and parts[3].isdigit():
                        target_href = href
                        break

                if not target_href: continue

                parts = target_href.split('/')
                slug = parts[4]
                fbref_id = parts[3]

                if slug in unique_slugs: continue
                unique_slugs.add(slug)

                country = "International"
                country_cell = self._get_cell(row, 'country')
                if country_cell:
                    country = country_cell.get_text().strip() or "International"

                leagues_data.append({
                    "title": league_name,
                    "country": country,
                    "slug": slug,
                    "fbref_id": fbref_id
                })

        return leagues_data

    def parse_teams(self, html: str) -> List[Dict[str, Any]]:
        html = html.replace('<!--', '').replace('-->', '')
        soup = BeautifulSoup(html, 'lxml')

        tables = soup.select('table.stats_table')
        if not tables: return []

        teams_data = []
        unique_ids = set()

        for table in tables:
            rows = table.find('tbody').find_all('tr')
            for row in rows:
                team_cell = row.find('td', {'data-stat': 'team'})
                if not team_cell: continue

                link = team_cell.find('a')
                if not link: continue

                team_name = link.get_text().strip()
                href = link['href']
                parts = href.split('/')
                if len(parts) < 4: continue

                fbref_id = parts[3]

                if fbref_id in unique_ids: continue
                unique_ids.add(fbref_id)

                # --- ПОПЫТКА НАЙТИ ЛОГОТИП ---
                # Ищем тег img внутри ячейки команды или предыдущей ячейки (иногда там флаг)
                # На FBREF логотипов в таблице standings обычно нет, но если появятся - мы их возьмем.
                logo_url = None
                img_tag = team_cell.find('img')
                if img_tag:
                    logo_url = img_tag.get('src')

                teams_data.append({
                    "title": team_name,
                    "fbref_id": fbref_id,
                    "logo_url": logo_url,
                })
        return teams_data

    def parse_schedule(self, html: str, league_id: int, season: str) -> List[Dict[str, Any]]:
        html = html.replace('<!--', '').replace('-->', '')
        soup = BeautifulSoup(html, 'lxml')

        table = soup.select_one('table[id^="sched_"]')
        if not table: return []

        matches = []
        rows = table.find('tbody').find_all('tr')

        for row in rows:
            if 'class' in row.attrs and any(c in row.attrs['class'] for c in ['spacer', 'thead']):
                continue

            date_cell = row.find('td', {'data-stat': 'date'})
            if not date_cell or not date_cell.get_text().strip(): continue

            try:
                match_date = datetime.strptime(date_cell.get_text().strip(), "%Y-%m-%d").date()
            except ValueError:
                continue

            report_cell = row.find('td', {'data-stat': 'match_report'})
            match_report_link = report_cell.find('a') if report_cell else None

            fbref_match_id = None
            if match_report_link:
                fbref_match_id = match_report_link['href'].split('/')[3]
            else:
                continue

            home_cell = row.find('td', {'data-stat': 'home_team'})
            away_cell = row.find('td', {'data-stat': 'away_team'})
            h_link = home_cell.find('a') if home_cell else None
            a_link = away_cell.find('a') if away_cell else None

            if not h_link or not a_link: continue

            home_fbref_id = h_link['href'].split('/')[3]
            away_fbref_id = a_link['href'].split('/')[3]

            score_cell = row.find('td', {'data-stat': 'score'})
            home_score, away_score = None, None
            is_finished = False

            if score_cell and score_cell.get_text().strip():
                score_text = score_cell.get_text().strip()
                parts = re.split(r'\D+', score_text)
                if len(parts) >= 2 and parts[0] and parts[1]:
                    home_score = int(parts[0])
                    away_score = int(parts[1])
                    is_finished = True

            home_xg = self._get_float(row, 'home_xg')
            away_xg = self._get_float(row, 'away_xg')

            matches.append({
                "fbref_id": fbref_match_id,
                "date": match_date,
                "season": season,
                "league_id": league_id,
                "is_finished": is_finished,
                "home_score": home_score,
                "away_score": away_score,
                "home_xg": home_xg if is_finished else None,
                "away_xg": away_xg if is_finished else None,
                "home_fbref_id": home_fbref_id,
                "away_fbref_id": away_fbref_id,
            })

        return matches

    def parse_match_details(self, html: str, match_id: int, home_team_fbref: str, away_team_fbref: str) -> dict:
        # --- ВАЖНЕЙШАЯ СТРОКА: ДЕЛАЕМ СКРЫТЫЕ ДАННЫЕ ВИДИМЫМИ ---
        html = html.replace('<!--', '').replace('-->', '')
        # --------------------------------------------------------

        soup = BeautifulSoup(html, 'lxml')

        players_to_create = []
        stats_to_create = []
        unique_players_in_batch = set()

        teams_config = [(home_team_fbref, True), (away_team_fbref, False)]

        for team_fbref_id, is_home in teams_config:
            table_id = f"stats_{team_fbref_id}_summary"
            table = soup.find('table', id=table_id)

            if not table:
                print(f"   ⚠️ Таблица {table_id} не найдена")
                continue

            rows = table.find('tbody').find_all('tr')
            for row in rows:
                if 'class' in row.attrs and any(c in row.attrs['class'] for c in ['spacer', 'thead']):
                    continue

                player_th = row.find('th', {'data-stat': 'player'})
                if not player_th: continue

                link = player_th.find('a')
                if not link: continue

                player_name = link.get_text().strip()
                player_fbref_id = link['href'].split('/')[3]

                country = self._get_str(row, 'nationality')
                if country: country = country.split(' ')[-1]

                if player_fbref_id not in unique_players_in_batch:
                    players_to_create.append({
                        "name": player_name,
                        "fbref_id": player_fbref_id,
                        "country": country
                    })
                    unique_players_in_batch.add(player_fbref_id)

                stat_record = {
                    "match_id": match_id,
                    "player_fbref_id_temp": player_fbref_id,
                    "team_fbref_id_temp": team_fbref_id,

                    "minutes": self._get_int(row, "minutes"),
                    "position": self._get_str(row, "position"),
                    "rating": None,

                    "goals": self._get_int(row, "goals"),
                    "assists": self._get_int(row, "assists"),
                    "shots": self._get_int(row, "shots"),
                    "shots_on_target": self._get_int(row, "shots_on_target"),
                    "xg": self._get_float(row, "xg"),
                    "npxg": self._get_float(row, "npxg"),
                    "xa": self._get_float(row, "xg_assist"),

                    "touches": self._get_int(row, "touches"),
                    "passes_completed": self._get_int(row, "passes_completed"),
                    "passes_attempted": self._get_int(row, "passes"),
                    "progressive_carries": self._get_int(row, "progressive_carries"),

                    "tackles": self._get_int(row, "tackles"),
                    "interceptions": self._get_int(row, "interceptions"),
                    "blocks": self._get_int(row, "blocks"),
                }
                stats_to_create.append(stat_record)

        return {"players": players_to_create, "stats": stats_to_create}

    # --- Helpers ---
    def _get_cell(self, row: Tag, stat_name: str) -> Optional[Tag]:
        return row.find(['td', 'th'], {'data-stat': stat_name})

    def _get_str(self, row: Tag, stat_name: str) -> Optional[str]:
        cell = self._get_cell(row, stat_name)
        if cell:
            return cell.get_text().strip() or None
        return None

    def _get_int(self, row: Tag, stat_name: str) -> int:
        cell = self._get_cell(row, stat_name)
        if not cell: return 0
        text_val = cell.get_text().strip().replace(',', '')
        if not text_val: return 0
        try:
            return int(text_val)
        except ValueError:
            return 0

    def _get_float(self, row: Tag, stat_name: str) -> float:
        cell = self._get_cell(row, stat_name)
        if not cell: return 0.0
        text_val = cell.get_text().strip()
        if not text_val: return 0.0
        try:
            return float(text_val)
        except ValueError:
            return 0.0