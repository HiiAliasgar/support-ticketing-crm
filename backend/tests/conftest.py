import os
import tempfile

# Isolate tests from any real/production database and disable demo seeding.
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/ci.db"
os.environ["AUTO_SEED_DEMO"] = "0"