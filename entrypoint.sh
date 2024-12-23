#!/bin/bash

# Проверяем наличие базы данных
if [ ! -d /data/databases/neo4j ]; then
  echo "Initializing Neo4j database..."
  /var/lib/neo4j/bin/neo4j-admin set-initial-password ${PASSWORD}
else
  echo "Neo4j database already exists. Skipping initialization..."
fi

# # Запускаем Neo4j
# exec /var/lib/neo4j/bin/neo4j console
echo Запуск вашу мать
