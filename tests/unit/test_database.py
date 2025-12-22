from src.database.db_manager import DatabaseManager


def test_create_user_hash():
    db = DatabaseManager()
    user = db.create_user("unit@example.com", "Pass123!")
    assert user.email == "unit@example.com"
