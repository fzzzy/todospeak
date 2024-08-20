

install:
	python3 -m venv venv
	source venv/bin/activate && pip install -r requirements.txt


freeze:
	source venv/bin/activate && pip freeze > requirements.txt



all:
	source venv/bin/activate && uvicorn todospeak:app --reload



test:
	source venv/bin/activate && python test.py

