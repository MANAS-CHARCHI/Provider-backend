docker-compose build --no-cache

docker-compose up -d --build

alembic init alembic

docker-compose run backend alembic revision --autogenerate -m "added review and check user model"

docker-compose run backend alembic revision --autogenerate -m "tokenblacklist: create blacklist table-2"

docker-compose run backend alembic upgrade head
