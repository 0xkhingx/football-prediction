.PHONY: refresh bootstrap pull clean features split train evaluate test api web

# Fresh-clone setup: fetch data, build everything through the simulator.
# football-data.co.uk pull is best-effort (may 503); openfootball covers 2526+.
bootstrap: pull clean features split train evaluate score simulate
	@echo "bootstrap complete — api + web ready to run"

# Weekly state refresh (frozen weights): new results in, Elo/form rebuilt.
refresh: pull clean features split
	@echo "state refreshed — retrain monthly, not weekly"

pull:
	python -m src.pull_openfootball
	python src/data_pull.py

clean:
	python src/clean.py

features:
	python src/features.py

split:
	python src/split.py

# Monthly (or gated): retrain prod tuned + re-evaluate + regen plots
train:
	python -m src.train_tuned_prod

evaluate:
	python -m src.evaluate
	python -m src.shap_analysis

score:
	python -m src.score_live

simulate:
	python -m src.simulate

test:
	python -m pytest tests/ -v

api:
	python -m uvicorn api:app --port 8000

web:
	cd web && npm run dev
