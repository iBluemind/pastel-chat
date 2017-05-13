# -*- coding: utf-8 -*-

# Pre-defined Requests
HELP_LINDER = '도움말'


# Formatted Responses
PLEASE_ADD_OAUTH = "[테스트 초대완료]\n린더를 선택해주셔서 감사합니다!\n\n#저는 바쁘고 혼란스러운 일상 속 주인님의 일정 등록을 도와주는 인공지능 캘린더 로봇, 린더에요.\n\n아래 링크에 접속하셔서 캘린더를 연동해주세요.\n(베타 버전인 린더는 현재 구글 캘린더만을 지원합니다)\n\nhttps://chat.linder.kr/users/%s\n\n#캘린더 연동이 끝나셨으면 '완료'라고 말씀해주세요."
COMPLETE_ADD_OAUTH = '[캘린더 연동완료]\n축하합니다!\n\n#린더를 사용하시기 위한 모든 절차가 끝났습니다.\n\n#그럼 지금부터 린더의 사용법에 대해 간략하게 소개해드려도 될까요?'
NOT_YET_ADD_OAUTH = "캘린더 연동이 아직 끝나지 않았습니다.\n\n캘린더 연동이 끝나시면 '완료'라고 말씀해주세요."
BAD_REQUEST = '린더는 일정 관련 일만을 처리하는 인공지능 캘린더로 해당 기능을 지원하지 않습니다.'
PLEASE_INPUT_INVITATION_CODE = '올바른 초대코드를 입력해주세요.'
WELCOME_FIRST_ADD_SCHEDULE = "[첫 일정 등록완료]\n린더를 통한 첫 일정 등록이 완료되었습니다.\n\n#린더에 대해 궁금한 사항은 FAQ 페이지를 살펴보시거나 저희 린더 트레이너(contact@hiddentrack.co)들에게 언제든지 연락주세요.\n\n#혹은 대화창에 '도움말'을 입력하시면 안내받으실 수 있습니다.\n\n그럼 앞으로 일정에 관련된 모든 일은 린더에게 맡겨만주세요!"
README = '[린더 도움말]\n린더는 챗봇 기반의 대화형 일정관리 서비스로 고객님의 일정관리를 위해 최선의 노력을 다하고 있습니다.\n\n#캘린더 동기화 링크\nhttps://chat.linder.kr/users/%s\n\n#린더 일정 추가 예시\n린더 내일 오후 3시 강남에서 희연이랑 점심 등록해줘\n\n#FAQ 바로가기\nhttps://chat.linder.kr/faq\n\n#린더는 현재 베타 버전으로 이용하시는데 다소 제한이 있을 수 있습니다. 이점 양해 부탁드립니다.'
INTRODUCE_LINDER = '[린더 소개]\n네, 우선 베타 버전인 린더는 현재 일정 등록 기능만을 갖추고 있습니다.\n\n#일정을 등록하고 싶으시다면 린더에게 언제, 어디서, 무엇을 할지 말해보세요.\n\nex) 린더야 1월 20일 오후 3시 강남에서 희연이랑 점심 등록해줘\n\n#린더 대화체 안내\n(등록해, 추가해, 저장해)\n\n그럼 지금 한번 해볼까요?'
COMPLETE_SIGNUP = '린더에 대해 궁금한 사항이 있으실 경우 FAQ 페이지를 살펴보시거나 린더 트레이너(contact@hiddentrack.co)들에게 언제든지 연락주세요.\n\n그럼 앞으로 일정에 관련된 모든 일은 린더에게 맡겨주세요!\n\n#린더 대화체 안내(등록해, 추가해, 저장해)'
CHECK_NEW_SCHEDULE = '네, %s님,\n\n내용: %s\n일시: %s\n장소: %s\n\n을(를) 캘린더에 추가할까요?'
CONFIRM_ADD_SCHEDULE = '네, 캘린더에 추가하겠습니다.'
CANCEL_ADD_SCHEDULE = '알겠습니다. 추가하지 않겠습니다.'

CHECK_ADD_CALENDAR = '네, %s님.\n\n%s 캘린더에 포함된 %s개의 일정을 저장할까요?'
NO_CALENDAR_FOUND = '%s님, 안타깝지만 말씀해주신 캘린더는 아직 추가하실 수 없습니다. 앞으로 더 많은 일정을 추가하실 수 있도록 노력하겠습니다.'
CONFIRM_ADD_CALENDAR = '네, 해당 일정들을 저장하겠습니다.'
CANCEL_ADD_CALENDAR = '알겠습니다. 일정들을 저장하지 않겠습니다.'
NO_RECOMMENDED_SCHEDULE = '%s님, 아쉽지만 말씀해주신 것과 관련된 추천드릴 일정이 아직 없습니다.'
RECOMMENDED_SCHEDULES = '네, %s님.\n\n%s\n추천 내역은 아래와 같습니다.\n\n%s'


class FormattedText(object):
    def __init__(self, id, message):
        self.id = id
        self.message = message

    def __str__(self):
        return self.message


formatted_request = {
    'please_add_oauth': FormattedText(4, PLEASE_ADD_OAUTH),
    'bad_request': FormattedText(5, BAD_REQUEST)
}


formatted_response = {
    'check_new_schedule': FormattedText(6, CHECK_NEW_SCHEDULE),
    'confirm_add_schedule': FormattedText(7, CONFIRM_ADD_SCHEDULE),
    'cancel_add_schedule': FormattedText(8, CANCEL_ADD_SCHEDULE),
    'welcome_first_add_schedule': FormattedText(9, WELCOME_FIRST_ADD_SCHEDULE)
}
