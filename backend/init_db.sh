#!/bin/bash

# Exit on error
set -e

# Create database if it doesn't exist
createdb compliwave || true

# Initialize Alembic
alembic init migrations

# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Run migrations
alembic upgrade head

echo "Database initialized successfully!" 