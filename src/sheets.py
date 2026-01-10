"""Работа с Google Sheets: профили пользователей и истории басен."""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import CREDENTIALS_PATH, SPREADSHEET_ID

logger = logging.getLogger(__name__)


class GoogleSheetsClient:
    """Клиент для работы с Google Sheets."""
    
    def __init__(self):
        self.service = None
        self._init_service()
    
    def _init_service(self):
        """Инициализирует сервис Google Sheets."""
        try:
            creds = Credentials.from_service_account_file(
                str(CREDENTIALS_PATH),
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.service = build('sheets', 'v4', credentials=creds)
            logger.info("Google Sheets сервис инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации Google Sheets: {e}")
            raise
    
    def _get_sheet_id(self, sheet_name: str) -> Optional[int]:
        """Получает ID листа по имени."""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=SPREADSHEET_ID
            ).execute()
            
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']
            return None
        except Exception as e:
            logger.error(f"Ошибка получения ID листа {sheet_name}: {e}")
            return None
    
    def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает профиль пользователя из листа Users.
        Возвращает None, если пользователь не найден.
        """
        try:
            range_name = 'Users!A2:K'
            result = self.service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=range_name
            ).execute()
            
            rows = result.get('values', [])
            
            for row in rows:
                if len(row) > 0 and str(row[0]) == str(user_id):
                    return {
                        'user_id': str(row[0]) if len(row) > 0 else '',
                        'username': row[1] if len(row) > 1 else '',
                        'child_names': row[2] if len(row) > 2 else '',
                        'age': row[3] if len(row) > 3 else '',
                        'traits': row[4] if len(row) > 4 else '',
                        'created_at': row[5] if len(row) > 5 else '',
                        'updated_at': row[6] if len(row) > 6 else '',
                        'last_user_message': row[7] if len(row) > 7 else '',
                        'state': row[8] if len(row) > 8 else '',
                        'version': row[9] if len(row) > 9 else '1',
                        'story_total': row[10] if len(row) > 10 else '0'
                    }
            
            return None
        except Exception as e:
            logger.error(f"Ошибка получения профиля пользователя {user_id}: {e}")
            return None
    
    def create_user_profile(
        self,
        user_id: int,
        username: str,
        child_names: str,
        age: str,
        traits: str
    ) -> bool:
        """Создает новый профиль пользователя."""
        try:
            now = datetime.now().isoformat()
            values = [[
                str(user_id),
                username or '',
                child_names,
                age,
                traits,
                now,
                now,
                '',
                'active',
                '1'
                '0' # story_total
            ]]


            
            body = {'values': values}
            result = self.service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range='Users!A2',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            logger.info(f"Профиль пользователя {user_id} создан")
            return True
        except Exception as e:
            logger.error(f"Ошибка создания профиля пользователя {user_id}: {e}")
            return False
    
    def update_user_profile(
        self,
        user_id: int,
        profile_patch: Dict[str, Any]
    ) -> bool:
        """
        Обновляет профиль пользователя.
        profile_patch может содержать: child_names, age, traits, last_user_message
        """
        try:
            # Находим строку пользователя
            range_name = 'Users!A2:K'
            result = self.service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=range_name
            ).execute()
            
            rows = result.get('values', [])
            row_index = None
            
            for idx, row in enumerate(rows):
                if len(row) > 0 and str(row[0]) == str(user_id):
                    row_index = idx + 2  # +2 потому что заголовок и 0-based -> 1-based
                    break
            
            if row_index is None:
                logger.warning(f"Пользователь {user_id} не найден для обновления")
                return False
            
            # Получаем текущий профиль
            current_range = f'Users!A{row_index}:K{row_index}'
            current_result = self.service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=current_range
            ).execute()
            
            current_row = current_result.get('values', [[]])[0]
            
            # Обновляем значения
            updated_row = list(current_row)
            while len(updated_row) < 11:
                updated_row.append('')
            
            # Обновляем поля из patch
            if 'child_names' in profile_patch:
                updated_row[2] = str(profile_patch['child_names'])
            if 'age' in profile_patch:
                updated_row[3] = str(profile_patch['age'])
            if 'traits' in profile_patch:
                updated_row[4] = str(profile_patch['traits'])
            if 'last_user_message' in profile_patch:
                updated_row[7] = str(profile_patch['last_user_message'])
            
            # Обновляем updated_at
            updated_row[6] = datetime.now().isoformat()
            
            # Записываем обновленную строку
            body = {'values': [updated_row]}
            self.service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=current_range,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logger.info(f"Профиль пользователя {user_id} обновлен")
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления профиля пользователя {user_id}: {e}")
            return False
    
    def delete_user_profile(self, user_id: int) -> bool:
        """
        Удаляет профиль пользователя из листа Users.
        Также удаляет все басни пользователя из листа Stories.
        """
        try:
            # Получаем sheet_id для Users
            users_sheet_id = self._get_sheet_id('Users')
            if users_sheet_id is None:
                logger.error("Не удалось найти лист Users")
                return False
            
            # Находим строку пользователя в Users
            range_name = 'Users!A2:K'
            result = self.service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=range_name
            ).execute()
            
            rows = result.get('values', [])
            user_row_index = None
            
            for idx, row in enumerate(rows):
                if len(row) > 0 and str(row[0]) == str(user_id):
                    user_row_index = idx + 2  # +2 потому что заголовок и 0-based -> 1-based
                    break
            
            if user_row_index is None:
                logger.warning(f"Пользователь {user_id} не найден для удаления")
                return False
            
            # Удаляем строку профиля из Users
            requests = [{
                'deleteDimension': {
                    'range': {
                        'sheetId': users_sheet_id,
                        'dimension': 'ROWS',
                        'startIndex': user_row_index - 1,  # 0-based
                        'endIndex': user_row_index
                    }
                }
            }]
            
            # Удаляем все басни пользователя из Stories
            stories_sheet_id = self._get_sheet_id('Stories')
            if stories_sheet_id:
                stories_range = 'Stories!A2:B'
                stories_result = self.service.spreadsheets().values().get(
                    spreadsheetId=SPREADSHEET_ID,
                    range=stories_range
                ).execute()
                
                stories_rows = stories_result.get('values', [])
                # Собираем индексы строк для удаления (с конца к началу)
                rows_to_delete = []
                for idx, row in enumerate(stories_rows):
                    if len(row) >= 2 and str(row[1]) == str(user_id):
                        rows_to_delete.append(idx + 2)  # +2 потому что заголовок и 0-based -> 1-based
                
                # Сортируем в обратном порядке для удаления с конца
                rows_to_delete.sort(reverse=True)
                
                for row_idx in rows_to_delete:
                    requests.append({
                        'deleteDimension': {
                            'range': {
                                'sheetId': stories_sheet_id,
                                'dimension': 'ROWS',
                                'startIndex': row_idx - 1,  # 0-based
                                'endIndex': row_idx
                            }
                        }
                    })
            
            # Выполняем все удаления одним запросом
            if requests:
                body = {'requests': requests}
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=SPREADSHEET_ID,
                    body=body
                ).execute()
                
                logger.info(f"Профиль пользователя {user_id} и все его басни удалены")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Ошибка удаления профиля пользователя {user_id}: {e}")
            return False
            def increment_story_total(self, user_id: int) -> int:
                         """
        Увеличивает Users.story_total на 1 для пользователя.
        Колонка story_total = B
        updated_at = I
        """
        try:
            # Читаем Users (A:P чтобы захватить все поля)
            result = self.service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range='Users!A2:P'
            ).execute()

            rows = result.get('values', [])
            row_index = None
            current_value = 0

            for idx, row in enumerate(rows):
                if len(row) > 0 and str(row[0]) == str(user_id):
                    row_index = idx + 2  # строка в Google Sheets
                    if len(row) > 1 and row[1].strip() != "":
                        try:
                            current_value = int(row[1])
                        except ValueError:
                            current_value = 0
                    break

            if row_index is None:
                logger.warning(f"Пользователь {user_id} не найден для story_total")
                return 0

            new_value = current_value + 1
            now = datetime.now().isoformat()

            # Обновляем story_total (B) и updated_at (I)
            self.service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f'Users!B{row_index}',
                valueInputOption='RAW',
                body={'values': [[str(new_value)]]}
            ).execute()

            self.service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f'Users!I{row_index}',
                valueInputOption='RAW',
                body={'values': [[now]]}
            ).execute()

            logger.info(f"story_total={new_value} для user_id={user_id}")
            return new_value

        except Exception as e:
            logger.error(f"Ошибка increment_story_total для {user_id}: {e}")
            return 0
    def increment_story_total(self, user_id: int) -> int:
        """
        Увеличивает Users.story_total (колонка K) на 1 для пользователя user_id.
        Возвращает новое значение.
        """
        try:
            # Ищем строку пользователя
            range_name = 'Users!A2:K'
            result = self.service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=range_name
            ).execute()

            rows = result.get('values', [])
            row_index = None
            current_val = 0

            for idx, row in enumerate(rows):
                if len(row) > 0 and str(row[0]) == str(user_id):
                    row_index = idx + 2  # строка в Sheets (1-based, с учетом заголовка)
                    if len(row) > 10 and str(row[10]).strip() != "":
                        try:
                            current_val = int(float(str(row[10]).strip()))
                        except Exception:
                            current_val = 0
                    break

            if row_index is None:
                logger.warning(f"Пользователь {user_id} не найден для increment_story_total")
                return 0

            new_val = current_val + 1
            now = datetime.now().isoformat()

            # K = story_total, G = updated_at
            self.service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f'Users!K{row_index}',
                valueInputOption='RAW',
                body={'values': [[str(new_val)]]}
            ).execute()

            self.service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f'Users!G{row_index}',
                valueInputOption='RAW',
                body={'values': [[now]]}
            ).execute()

            logger.info(f"story_total incremented user_id={user_id} new_val={new_val}")
            return new_val

        except Exception as e:
            logger.error(f"Ошибка increment_story_total для {user_id}: {e}")
            return 0

    def save_story(
        self,
        user_id: int,
        story_text: str,
        model: str = 'deepseek'
    ) -> bool:
        """
        Сохраняет басню в лист Stories и выполняет trim до последних 5 записей.
        """
        try:
            # Генерируем уникальный ID для истории
            story_id = str(uuid.uuid4())
            ts = datetime.now().isoformat()
            
            # Добавляем новую запись
            values = [[ts, str(user_id), story_id, story_text, model]]
            body = {'values': values}
            
            self.service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range='Stories!A2',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            logger.info(f"Басня сохранена для пользователя {user_id}")
            self.increment_story_total(user_id)

            # Увеличиваем счетчик всех басен
            self.increment_story_total(user_id)

            # Выполняем trim до последних 5 записей
            self._trim_stories(user_id)

            return True

        except Exception as e:
            logger.error(f"Ошибка сохранения басни для пользователя {user_id}: {e}")
            return False
    
    def _trim_stories(self, user_id: int):
        """
        Оставляет только последние 5 басен для пользователя.
        Удаляет самые старые записи.
        """
        try:
            # Читаем все записи Stories (ts, user_id)
            range_name = 'Stories!A2:B'
            result = self.service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=range_name
            ).execute()
            
            rows = result.get('values', [])
            
            # Фильтруем записи для этого user_id и сортируем по ts
            user_stories = []
            for idx, row in enumerate(rows):
                if len(row) >= 2 and str(row[1]) == str(user_id):
                    try:
                        ts = datetime.fromisoformat(row[0])
                        user_stories.append((idx + 2, ts))  # +2 потому что заголовок и 0-based -> 1-based
                    except:
                        # Если не удалось распарсить дату, пропускаем
                        continue
            
            # Если записей больше 5, удаляем самые старые
            if len(user_stories) > 5:
                # Сортируем по времени (старые первыми)
                user_stories.sort(key=lambda x: x[1])
                
                # Определяем, сколько нужно удалить
                to_delete = len(user_stories) - 5
                
                # Получаем sheet_id для Stories
                sheet_id = self._get_sheet_id('Stories')
                if sheet_id is None:
                    logger.error("Не удалось найти лист Stories")
                    return
                
                # Удаляем самые старые записи (с конца, чтобы индексы не смещались)
                rows_to_delete = [row_idx for row_idx, _ in user_stories[:to_delete]]
                rows_to_delete.sort(reverse=True)  # С конца к началу
                
                # Формируем запросы на удаление
                requests = []
                for row_idx in rows_to_delete:
                    requests.append({
                        'deleteDimension': {
                            'range': {
                                'sheetId': sheet_id,
                                'dimension': 'ROWS',
                                'startIndex': row_idx - 1,  # 0-based
                                'endIndex': row_idx
                            }
                        }
                    })
                
                if requests:
                    body = {'requests': requests}
                    self.service.spreadsheets().batchUpdate(
                        spreadsheetId=SPREADSHEET_ID,
                        body=body
                    ).execute()
                    
                    logger.info(f"Удалено {len(requests)} старых басен для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка trim басен для пользователя {user_id}: {e}")

