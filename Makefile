
SHELL := /bin/zsh

all:
	source venv/bin/activate && uvicorn todospeak:app --reload --host 0.0.0.0



test:
	source venv/bin/activate && python3 test.py



venv:
	python3 -m venv venv
	source venv/bin/activate && pip3 install -r requirements.txt


freeze:
	source venv/bin/activate && pip3 freeze > requirements.txt


clean:
	rm -rf venv
	rm -rf __pycache__

