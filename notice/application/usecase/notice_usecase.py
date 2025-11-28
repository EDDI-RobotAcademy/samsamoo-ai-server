class NoticeUsecase:
    def __init__(self, notice_repository):
        self.notice_repository = notice_repository

    def create_notice(self, title, content):
        return self.notice_repository.create_notice(title, content)

    def update_notice(self, notice_id, title, content):
        return self.notice_repository.update_notice(notice_id, title, content)

    def delete_notice(self, notice_id):
        return self.notice_repository.delete_notice(notice_id)

    def list_notices(self):
        return self.notice_repository.list_notices()

    # ⭐⭐ 여기 추가! 공지 상세 조회 ⭐⭐
    def get_notice(self, notice_id: int):
        return self.notice_repository.get_notice_by_id(notice_id)
