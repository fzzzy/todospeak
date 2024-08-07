

all:
	source venv/bin/activate && uvicorn todospeak:app --reload



test:
	source venv/bin/activate && python test.py

