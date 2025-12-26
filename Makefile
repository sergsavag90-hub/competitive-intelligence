PROJECT_NAME=competitive-intelligence

dev:
	docker-compose -f docker-compose.yml -f docker-compose.override.yml up --build

test:
	docker-compose -f docker-compose.yml -f docker-compose.selenium.yml -f docker-compose.test.yml up --build --abort-on-container-exit

prod:
	docker-compose -f docker-compose.yml up -d --build
