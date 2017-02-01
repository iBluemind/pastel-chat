# -*- coding: utf-8 -*-

from flask_wtf import Form
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired


class LoginForm(Form):
    email = StringField(u'이메일 주소', validators=[DataRequired(message=u'이메일 주소를 입력해주세요')])
    password = PasswordField(u'비밀번호', validators=[DataRequired(message=u'비밀번호를 입력해주세요')])
