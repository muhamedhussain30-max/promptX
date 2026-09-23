"""Allow: python -m app.challenges.seeder"""
import asyncio
from app.challenges.seeder import run_seed

if __name__ == "__main__":
    asyncio.run(run_seed())
