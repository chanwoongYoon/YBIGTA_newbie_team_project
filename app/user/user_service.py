from app.user.user_repository import UserRepository
from app.user.user_schema import User, UserLogin, UserUpdate

class UserService:
    def __init__(self, userRepoitory: UserRepository) -> None:
        self.repo = userRepoitory

    def login(self, user_login: UserLogin) -> User:
        """이메일과 비밀번호로 로그인을 검증한다."""
        user = self.repo.get_user_by_email(user_login.email)
        if user is None:
            raise ValueError("User not Found.")
        if user.password != user_login.password:
            raise ValueError("Invalid ID/PW")
        return user
        
    def register_user(self, new_user: User) -> User:
        ## TODO
        if self.repo.get_user_by_email(new_user.email) is not None:
            raise ValueError("User already Exists.")
        elif new_user.password == "":
            raise ValueError("Please enter your passward")
        elif new_user.username == "":
            raise ValueError("Please enter your name")
        self.repo.save_user(new_user)
        return new_user

    def delete_user(self, email: str) -> User:
        ## TODO
        deleted_user = self.repo.get_user_by_email(email)
        if (deleted_user is None):
            raise ValueError("User not Found.")
        self.repo.delete_user(deleted_user)
        return deleted_user

    def update_user_pwd(self, user_update: UserUpdate) -> User:
        """사용자의 비밀번호를 새 값으로 변경한다."""
        user = self.repo.get_user_by_email(user_update.email)
        if user is None:
            raise ValueError("User not Found.")
        user.password = user_update.new_password
        updated_user = self.repo.save_user(user)
        return updated_user