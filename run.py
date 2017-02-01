# -*- coding: utf-8 -*-

from pastel_chat import app
from config import PORT, DEBUG

if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=DEBUG, port=PORT, use_reloader=False)
