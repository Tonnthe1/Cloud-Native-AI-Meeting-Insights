.PHONY: up start status logs down stop reset doctor test

up start:
	bash scripts/quickstart.sh up

status:
	bash scripts/quickstart.sh status

logs:
	bash scripts/quickstart.sh logs

down stop:
	bash scripts/quickstart.sh down

reset:
	CONFIRM_RESET=yes bash scripts/quickstart.sh reset

doctor:
	bash scripts/quickstart.sh doctor

test:
	cd backend && python -m pytest -q
	cd frontend && npm run build
