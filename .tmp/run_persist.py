import asyncio, sys
sys.path.insert(0, "scripts")
import selftest
print(asyncio.run(selftest.scenario_persistence()))
