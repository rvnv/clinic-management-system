from database import DatabaseManager
class AuthManager:
    def __init__(self, db):
        self.db = db
        self.current_user = None
    def login(self, username, password):
        query = """
            SELECT user_id, username, full_name, role
            FROM users
            WHERE username = %s
              AND password = %s
              AND status = 'Active'
        """
        user = self.db.fetch_one(
            query,
            (username, password)
        )
        if user:
            self.current_user = {
                "user_id": user[0],
                "username": user[1],
                "full_name": user[2],
                "role": user[3]
            }
            return self.current_user
        return None
    def logout(self):
        self.current_user = None

if __name__ == "__main__":

    db = DatabaseManager()

    if db.connect():

        auth = AuthManager(db)

        username = input("Username: ")
        password = input("Password: ")

        user = auth.login(username, password)

        if user:
            print("\nLogin successful!")
            print("Welcome,", user["full_name"])
            print("Role:", user["role"])
        else:
            print("\nInvalid username or password.")

        db.close()