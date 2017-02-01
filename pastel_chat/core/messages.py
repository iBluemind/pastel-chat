# -*- coding: utf-8 -*-

# Pre-defined Requests
TERMS_AGREE = '동의해요'
TERMS_DENY = '동의하지 않아요'
PLEASE_AGREE_TERMS = '개인정보취급방침과 린더 서비스 이용약관에 동의해주셔야 계속해서 사용하실 수 있습니다!'
PLEASE_ADD_OAUTH = '린더를 선택해주셔서 감사합니다! 아래 URL 주소에 접속하셔서 캘린더 연동을 해주세요.\n\nhttp://linder.kr/users/%s'
BAD_REQUEST = '린더는 일정 관련 일만을 처리하는 인공지능 캘린더로 해당 기능을 지원하지 않습니다.'

# Formatted Responses
CHECK_NEW_SCHEDULE = '네, %s님,\n\n내용: %s\n일시: %s\n장소: %s\n\n을(를) 캘린더에 추가할까요?'
CONFIRM_ADD_SCHEDULE = '네, 캘린더에 추가하겠습니다.'
CANCEL_ADD_SCHEDULE = '알겠습니다. 추가하지 않겠습니다.'


class FormattedText(object):
    def __init__(self, id, message):
        self.id = id
        self.message = message

    def __str__(self):
        return self.message


formatted_request = {
    'terms_agree': FormattedText(1, TERMS_AGREE),
    'terms_deny': FormattedText(2, TERMS_DENY),
    'please_agree_terms': FormattedText(3, PLEASE_AGREE_TERMS),
    'please_add_oauth': FormattedText(4, PLEASE_ADD_OAUTH),
    'bad_request': FormattedText(5, BAD_REQUEST)
}


formatted_response = {
    'check_new_schedule': FormattedText(6, CHECK_NEW_SCHEDULE),
    'confirm_add_schedule': FormattedText(7, CONFIRM_ADD_SCHEDULE),
    'cancel_add_schedule': FormattedText(8, CANCEL_ADD_SCHEDULE)
}
