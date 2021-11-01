from .db import Db
from .mongo_db import MongoDb
from .sql_db import SqlDb
from .sqlite_db import SQLiteDb


class DbManager:

    def __init__(self, options: dict) -> None:
        self._options = options
        self._connections: dict(str, list) = dict()
        settings = options["settings"] if "settings" in options else None
        for k, setting in [(k.split(".", 2)[1:], v) for k, v in settings.items() if k.find("connections.") == 0]:
            db_type = k[0].lower()
            name = k[1].lower()
            self._connections[name] = [db_type, setting]

    def open_connection(self, key: str) -> Db:
        ret_val: Db = None
        try:
            data = self._connections[key]
        except KeyError as ex:
            raise Exception(
                f"Connection setting with name '{key}' not found!") from ex
        db_type = data[0]
        setting = data[1]
        if db_type == "sql":
            ret_val = SqlDb(data[1])
        elif db_type == "sqlite":
            ret_val = SQLiteDb(setting)
        elif db_type == "mongo":
            ret_val = MongoDb(setting)
        else:
            print(
                f"Data base of type '{db_type}' not supported in this vestion")
        return ret_val

    def open_sql_connection(self, key: str) -> SqlDb:
        return self.open_connection(key)

    def open_sqllite_connection(self, key: str) -> SQLiteDb:
        return self.open_connection(key)

    def open_mongo_connection(self, key: str) -> MongoDb:
        return self.open_connection(key)