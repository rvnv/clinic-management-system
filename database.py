import os
import mysql.connector


class DatabaseManager:

    def __init__(self):
        self.connection = None

    def connect(self):

        try:

            self.connection = mysql.connector.connect(

                host=os.environ.get(
                    "MYSQLHOST",
                    "localhost"
                ),

                port=int(
                    os.environ.get(
                        "MYSQLPORT",
                        "3306"
                    )
                ),

                user=os.environ.get(
                    "MYSQLUSER",
                    "root"
                ),

               password=os.environ.get(
                    "MYSQLPASSWORD",
                    ""
                ),

                database=os.environ.get(
                    "MYSQLDATABASE",
                    "clinic_management"
                )
            )

            if self.connection.is_connected():

                return True

        except mysql.connector.Error as error:

            print(
                "Database connection failed:",
                error
            )

            return False

        return False


    def execute(self, query, values=None):

        cursor = self.connection.cursor()

        try:

            cursor.execute(
                query,
                values
            )

            self.connection.commit()

            return cursor.rowcount

        except mysql.connector.Error as error:

            self.connection.rollback()

            print(
                "Database error:",
                error
            )

            return 0

        finally:

            cursor.close()


    def fetch_one(self, query, values=None):

        cursor = self.connection.cursor()

        try:

            cursor.execute(
                query,
                values
            )

            return cursor.fetchone()

        except mysql.connector.Error as error:

            print(
                "Database error:",
                error
            )

            return None

        finally:

            cursor.close()


    def fetch_all(self, query, values=None):

        cursor = self.connection.cursor()

        try:

            cursor.execute(
                query,
                values
            )

            return cursor.fetchall()

        except mysql.connector.Error as error:

            print(
                "Database error:",
                error
            )

            return []

        finally:

            cursor.close()


    def close(self):

        if (
            self.connection
            and self.connection.is_connected()
        ):

            self.connection.close()


if __name__ == "__main__":

    db = DatabaseManager()

    if db.connect():

        print(
            "Database connected successfully!"
        )

        db.close()

        print(
            "Database connection closed."
        )