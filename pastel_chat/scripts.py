from config import NAVER_CLIENT_SECRET, NAVER_CLIENT_ID, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET


def initialize_db():
    from pastel_chat import db
    from pastel_chat.oauth.models import Platform, PlatformSession, User
    from pastel_chat.models import Calendar, CalendarPlatformSync, PlatformSyncBy, \
                Schedule, ScheduleRecurrence, AttachedFile, Region, HashTag, \
                user_hashtag, schedule_schedule_recurrence, calendar_schedule, \
                CalendarListPlatformSync, Message, Conversation
    db.drop_all()
    db.create_all()

    platform_google = Platform(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET
    )
    platform_naver = Platform(
        name='naver',
        client_id=NAVER_CLIENT_ID,
        client_secret=NAVER_CLIENT_SECRET
    )
    db.session.add(platform_google)
    db.session.add(platform_naver)
    db.session.commit()


def compress():
    from flask_assets import Bundle
    from pastel_chat import assets

    pastel_css = Bundle('assets/css/pastel.css', filters='cssmin', output='gen/pastel.min.css')
    assets.register('pastel_css', pastel_css)
    pastel_mobile_css = Bundle('assets/css/pastel-mobile.css', filters='cssmin', output='gen/pastel-mobile.min.css')
    assets.register('pastel_mobile_css', pastel_mobile_css)
    pastel_desktop_css = Bundle('assets/css/pastel-desktop.css', filters='cssmin', output='gen/pastel-desktop.min.css')
    assets.register('pastel_desktop_css', pastel_desktop_css)

    icloud_login = Bundle('assets/js/icloud_login.js', filters='jsmin', output='gen/icloud_login.min.js')
    assets.register('icloud_login', icloud_login)


def build_compressed_assets():
    import logging
    log = logging.getLogger('webassets')
    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.DEBUG)

    from webassets.script import CommandLineEnvironment
    from pastel_chat import assets
    cmdenv = CommandLineEnvironment(assets, log)
    cmdenv.build()


def upload_to_s3():
    from flask_s3 import create_all
    from pastel_chat import app
    create_all(app, filepath_filter_regex=r'^(assets|gen|libs|resource|fonts)')
